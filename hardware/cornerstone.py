"""Cornerstone -- Oriel CS130 / CS260 monochromator, driven directly over USB.

  Cornerstone        what automations and the GUI use: a few simple methods
                     (cs.goto(500), cs.open_shutter(), cs.set_grating(2), ...)
                     that each call the client.
  CornerstoneClient  all the hardware code: every Cornerstone command as a
                     method, over pyusb + Microsoft's WinUSB driver.
  FakeCornerstone    Cornerstone on a simulated CS260 (--sim).

One-time WinUSB setup per PC (admin): plug the monochromator in, run Zadig
(https://zadig.akeo.ie), Options > List All Devices, pick the Cornerstone
(USB ID 1180 0012), choose WinUSB, Replace Driver. Newport's own software
won't see the unit afterwards; roll back the driver in Device Manager to undo.
helpers/cornerstone_probe.py checks the result. See
docs/cornerstone_usb_handoff.md.
"""
import functools
import threading
import time
from typing import Literal


def _usb_backend():
    """libusb backend from the libusb-package wheel (bundles libusb-1.0.dll on
    Windows); None lets pyusb search the system (Linux / macOS)."""
    try:
        import libusb_package
    except ImportError:
        return None
    return libusb_package.get_libusb1_backend()


def _num(x):
    """1.5 -> "1.5", 2.0 -> "2": plain decimal, never scientific notation."""
    return f"{float(x):.10f}".rstrip("0").rstrip(".") or "0"


class Unsupported(RuntimeError):
    """The connected unit doesn't have that grating or accessory (e.g.
    grating 3 on a CS130). Raised before anything is sent."""


class CornerstoneClient:
    """
    Direct USB link to a Cornerstone: every command Newport's Cornerstone.dll
    exposes, as a method. Cornerstone wraps the common ones; the rest are
    reachable as cs.client.<method>.

    Wavelength:  goto(nm), position(), step(n), units(), set_units(u)
    Shutter:     open_shutter(), close_shutter(), shutter_open()
    Gratings:    grating(), set_grating(n), grating_info(n), grating_lines(n),
                 grating_label(n), grating_zero(n), grating_offset(n),
                 grating_factor(n); stored calibration, recalibration only:
                 set_grating_lines / _label / _zero / _offset / _factor(n, v)
    Filter:      filter(), set_filter(n), filter_label(n), set_filter_label(n, s)
    Slits:       slit_width(slit), set_slit_width(slit, um), bandpass(),
                 set_bandpass(nm)
    The unit:    info, model, serial, firmware, gratings, has_filter_wheel,
                 slits, describe(); raw query(cmd) / command(cmd)

    Wire format: ASCII "<cmd>\\r\\n" on bulk OUT 0x01, replies on bulk IN 0x81,
    64-byte packets. Set commands (GOWAVE, SHUTTER) get no reply; queries
    (WAVE?, SHUTTER?) get one line.

    How the firmware answers (measured on a CS130, firmware V04.30):
      - IN 0x81 is a reply *buffer*, not a stream. Reads return the whole
        64-byte buffer again and again. Its first line is the latest reply;
        the rest is leftovers from longer, older replies.
      - When the unit takes a command it zeroes the start of the buffer
        ("busy"); a query's reply replaces that 60-150 ms later. Between the
        two, reads can also come back as zero-length packets or time out.
      - The unit runs one command at a time. A write made while it is busy
        (e.g. mid-move) blocks until it is free, so a query sent right after
        GOWAVE or GRAT is answered once the move has finished.
      - Never have two commands in flight: queries piled up during a move
        leave the firmware answering every later query with the reply to an
        earlier one, until it is power-cycled. Everything here goes through
        the lock and waits for each query's reply before the next write.
      - Unsupported commands (GRAT3... on a CS130) get no reply at all.

    open() works out what the unit has (model, gratings, filter wheel,
    motorized slits); asking for something it lacks raises Unsupported
    before anything is sent.
    """
    VID, PID = 0x1180, 0x0012
    EP_OUT, EP_IN = 0x01, 0x81
    PACKET = 64
    PROBE_TIMEOUT_S = 0.5   # capability checks: a missing feature never replies

    def __init__(self, timeout_s=2.0):
        self.name = "Cornerstone"
        self.timeout_s = timeout_s      # one query, unit idle (replies take <0.2 s)
        self.lock = threading.RLock()
        self.dev = None
        self.info = ""
        self.model = "Cornerstone"
        self.serial = ""
        self.firmware = ""
        self.gratings = {}              # {number: lines/mm} of installed gratings
        self.has_filter_wheel = False
        self.slits = []                 # motorized slits, 1-3

    def open(self):
        import usb.core
        import usb.util

        self._usb = usb
        dev = usb.core.find(idVendor=self.VID, idProduct=self.PID,
                            backend=_usb_backend())
        if dev is None:
            raise RuntimeError(f"no Cornerstone on USB ({self.VID:04x}:{self.PID:04x})")
        try:
            dev.set_configuration()
        except usb.core.USBError:
            pass    # already configured
        try:
            usb.util.claim_interface(dev, 0)
        except NotImplementedError as e:
            raise RuntimeError(
                f"{self.name}: can't open the monochromator: it's still on "
                "Newport's CYUSB driver. Swap it to WinUSB with Zadig "
                "(docs/cornerstone_usb_handoff.md).") from e
        except usb.core.USBError as e:
            raise RuntimeError(
                f"{self.name}: can't open the monochromator ({e}); another "
                "program (or another LTB2 window) probably has it open.") from e
        self.dev = dev
        # Newport turns handshake on around moves; a crashed session may have
        # left it on, which adds a status line to every reply.
        self.command("HANDSHAKE 0")
        self._check_sync()
        self._detect()

    def _check_sync(self):
        """INFO? must come back as the model string. Anything else means the
        firmware is answering an earlier query (see class docstring)."""
        for _ in range(2):
            try:
                reply = self.query("INFO?")
            except RuntimeError:
                continue
            if "CORNERSTONE" in reply.upper():
                self.info = reply   # "Oriel Instruments,Model Cornerstone 130,SN1007,V04.30"
                return
        raise RuntimeError(f"{self.name}: replies are out of step with queries; "
                           "power-cycle the monochromator")

    def _detect(self):
        """Fill in model / serial / firmware from INFO? and find out which
        gratings, filter wheel and motorized slits answer. A CS130 reports
        FILTER? 0 and SLITnMICRONS? 0 without those accessories."""
        parts = [p.strip() for p in self.info.split(",")]
        self.model = next((p.replace("Model ", "") for p in parts
                           if "CORNERSTONE" in p.upper()), "Cornerstone")
        self.serial = next((p[2:] for p in parts if p.upper().startswith("SN")), "")
        self.firmware = parts[-1] if len(parts) >= 4 else ""

        def ask(cmd):
            try:
                return self._float(cmd, self.PROBE_TIMEOUT_S)
            except (RuntimeError, ValueError):
                return 0

        self.gratings = {n: int(ask(f"GRAT{n}LINES?")) for n in (1, 2, 3)}
        self.gratings = {n: lines for n, lines in self.gratings.items() if lines > 0}
        self.has_filter_wheel = ask("FILTER?") > 0
        self.slits = [n for n in (1, 2, 3) if ask(f"SLIT{n}MICRONS?") > 0]

    def describe(self):
        """One line, e.g. "Cornerstone 130 SN1007 V04.30: gratings 1 (600 l/mm),
        2 (600 l/mm); no filter wheel; no motorized slits"."""
        gratings = ", ".join(f"{n} ({lines} l/mm)" for n, lines in self.gratings.items())
        wheel = "filter wheel" if self.has_filter_wheel else "no filter wheel"
        slits = (f"motorized slits {', '.join(map(str, self.slits))}" if self.slits
                 else "no motorized slits")
        name = " ".join(p for p in (self.model, f"SN{self.serial}" if self.serial else "",
                                    self.firmware) if p)
        return f"{name}: gratings {gratings or 'none found'}; {wheel}; {slits}"

    def _need_grating(self, n):
        n = int(n)
        if n not in self.gratings:
            have = ", ".join(map(str, self.gratings)) or "none"
            raise Unsupported(f"{self.model} has no grating {n} (gratings: {have})")
        return n

    def _need_filter_wheel(self):
        if not self.has_filter_wheel:
            raise Unsupported(f"{self.model} has no filter wheel")

    def _need_slit(self, slit):
        slit = int(slit)
        if slit not in self.slits:
            have = ", ".join(map(str, self.slits)) or "none"
            raise Unsupported(f"{self.model} has no motorized slit {slit} "
                              f"(motorized slits: {have})")
        return slit

    # --- transport ---------------------------------------------------------

    def _read_packet(self, timeout_s):
        """One read of the reply buffer: bytes, b"" for a zero-length packet,
        or None if the read timed out."""
        try:
            return bytes(self.dev.read(self.EP_IN, self.PACKET,
                                       max(1, int(timeout_s * 1000))))
        except self._usb.core.USBTimeoutError:
            return None

    def _write(self, cmd, timeout_s):
        self.dev.write(self.EP_OUT, (cmd + "\r\n").encode("ascii"),
                       max(1, int(timeout_s * 1000)))

    def command(self, cmd, timeout_s=None):
        """Send a command that has no reply (GOWAVE, SHUTTER O, GRAT 2, ...).
        Returns once the unit has taken it, not when it has finished; the next
        query waits for that."""
        with self.lock:
            self._write(cmd, timeout_s or self.timeout_s)

    def query(self, cmd, timeout_s=None):
        """Send a query and return its reply. timeout_s covers any move still
        running from an earlier command; the default assumes the unit is idle.

        The reply is the first line of the first full buffer read after the
        unit has shown it took the command (busy buffer, zero-length packet or
        a read that timed out), so a reply still sitting from the previous
        query is never mistaken for this one."""
        timeout_s = timeout_s or self.timeout_s
        with self.lock:
            deadline = time.monotonic() + timeout_s
            self._write(cmd, timeout_s)
            taken = False
            while time.monotonic() < deadline:
                data = self._read_packet(min(0.1, max(0.001, deadline - time.monotonic())))
                if not data or data[0] == 0:
                    taken = True
                elif taken and b"\r\n" in data:
                    return data.split(b"\r\n", 1)[0].decode("ascii", "replace").strip()
                time.sleep(0.002)
            raise RuntimeError(f"{self.name}: no reply to {cmd!r} in {timeout_s:g} s")

    def _float(self, cmd, timeout_s=None):
        return float(self.query(cmd, timeout_s))

    def _int(self, cmd, timeout_s=None):
        return int(float(self.query(cmd, timeout_s)))

    # --- wavelength --------------------------------------------------------

    def goto(self, nm, timeout_s=120.0, tol_nm=0.05):
        """GOWAVE, then WAVE?, which the unit answers once the move is done."""
        nm = float(nm)
        with self.lock:
            self.command(f"GOWAVE {nm:.3f}")
            pos = self.position(timeout_s)
        if abs(pos - nm) > tol_nm:
            raise RuntimeError(f"{self.name}: GOWAVE {nm:.3f} ended at {pos}")

    def position(self, timeout_s=None):
        return self._float("WAVE?", timeout_s)

    def step(self, n):
        """Move the grating drive by n motor steps."""
        self.command(f"STEP {int(n)}")

    def units(self):
        """"NM", "UM" or "WN" (wavenumbers): the units of goto/position."""
        return self.query("UNITS?").upper()

    def set_units(self, units):
        units = units.upper()
        if units not in ("NM", "UM", "WN"):
            raise ValueError(f"units must be NM, UM or WN, not {units!r}")
        self.command(f"UNITS {units}")

    # --- shutter -----------------------------------------------------------

    def open_shutter(self):
        self.command("SHUTTER O")

    def close_shutter(self):
        self.command("SHUTTER C")

    def shutter_open(self):
        """True if the shutter reads open ("SHUTTER?" -> "O" / "C")."""
        return not self.query("SHUTTER?").upper().startswith("C")

    # --- gratings ----------------------------------------------------------
    # GRAT? answers "<n>,<lines/mm>,<label>", e.g. "2,600,1000".

    def grating(self, timeout_s=None):
        return int(self.query("GRAT?", timeout_s).split(",")[0])

    def set_grating(self, n, timeout_s=120.0):
        """Switch turret to grating n (CS260: 1-3, CS130: 1-2) and wait; takes
        about 11 s on a CS130. The wavelength is NOT kept: the unit reports
        wherever the new grating ended up (e.g. 3164 nm or 0 nm), so goto()
        afterwards."""
        n = self._need_grating(n)
        with self.lock:
            self.command(f"GRAT {n}")
            now = self.grating(timeout_s)
        if now != n:
            raise RuntimeError(f"{self.name}: GRAT {n} left grating {now} selected")

    def grating_lines(self, n):
        """Groove density of grating n, lines/mm."""
        return self._int(f"GRAT{self._need_grating(n)}LINES?")

    def grating_label(self, n):
        return self.query(f"GRAT{self._need_grating(n)}LABEL?")

    def grating_info(self, n=None):
        """{"number", "lines", "label"} for grating n (default: current)."""
        n = self.grating() if n is None else self._need_grating(n)
        return {"number": n, "lines": self.grating_lines(n), "label": self.grating_label(n)}

    # Calibration values, stored in the unit. Setting these changes where
    # GOWAVE puts the light; only touch them when recalibrating.

    def grating_zero(self, n):
        return self._float(f"GRAT{self._need_grating(n)}ZERO?")

    def grating_offset(self, n):
        return self._float(f"GRAT{self._need_grating(n)}OFFSET?")

    def grating_factor(self, n):
        return self._float(f"GRAT{self._need_grating(n)}FACTOR?")

    def set_grating_zero(self, n, value):
        self.command(f"GRAT{self._need_grating(n)}ZERO {_num(value)}")

    def set_grating_offset(self, n, value):
        self.command(f"GRAT{self._need_grating(n)}OFFSET {_num(value)}")

    def set_grating_factor(self, n, value):
        self.command(f"GRAT{self._need_grating(n)}FACTOR {_num(value)}")

    def set_grating_lines(self, n, lines):
        self.command(f"GRAT{self._need_grating(n)}LINES {int(lines)}")

    def set_grating_label(self, n, label):
        self.command(f"GRAT{self._need_grating(n)}LABEL {label}")

    # --- filter wheel (optional accessory) ---------------------------------

    def filter(self, timeout_s=None):
        """Filter wheel position; 0 if there is no wheel."""
        return self._int("FILTER?", timeout_s)

    def set_filter(self, n, timeout_s=30.0):
        self._need_filter_wheel()
        n = int(n)
        with self.lock:
            self.command(f"FILTER {n}")
            now = self.filter(timeout_s)
        if now != n:
            raise RuntimeError(f"{self.name}: FILTER {n} left position {now} selected")

    def filter_label(self, n):
        self._need_filter_wheel()
        return self.query(f"FILTER{int(n)}LABEL?")

    def set_filter_label(self, n, label):
        self._need_filter_wheel()
        self.command(f"FILTER{int(n)}LABEL {label}")

    # --- motorized slits (optional accessory) ------------------------------
    # Slit 1 = input port A, 2 = off-axis output B, 3 = on-axis output C.

    def slit_width(self, slit):
        """Width of slit 1-3 in microns."""
        return self._int(f"SLIT{int(slit)}MICRONS?")

    def set_slit_width(self, slit, microns):
        self.command(f"SLIT{self._need_slit(slit)}MICRONS {int(microns)}")

    def bandpass(self):
        """Bandpass in nm, from the motorized slit widths."""
        return self._float("BANDPASS?")

    def set_bandpass(self, nm):
        if not self.slits:
            raise Unsupported(f"{self.model} has no motorized slits")
        self.command(f"BANDPASS {_num(nm)}")

    # No handshake(): HANDSHAKE 1 makes every command end with a status line
    # ("0" ok, "32" error) that overwrites a query's value ~4 ms after it
    # appears, which query() can't read reliably. open() turns it off.

    def close(self):
        if self.dev is None:
            return
        try:
            self._usb.util.release_interface(self.dev, 0)
            self._usb.util.dispose_resources(self.dev)
        except Exception:
            pass
        self.dev = None


def _warn_if_unsupported(method):
    """Print a warning and do nothing when the unit doesn't have that grating
    or accessory (grating 3 on a CS130, a filter on a unit without a wheel)."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except Unsupported as e:
            print(f"Cornerstone warning: {e}; nothing sent")
    return wrapper


class Cornerstone:
    """The monochromator, made simple. Use this in automations:

        cs.goto(550)              # move to 550 nm; waits until it's there
        cs.position()             # where it is now, in nm
        cs.open_shutter()
        cs.close_shutter()
        cs.shutter_open()         # True if the shutter is open
        cs.set_grating(2)         # switch grating; stays at the same wavelength
        cs.grating()              # which grating is in use
        cs.set_filter(3)          # filter wheel position (if it has a wheel)
        cs.filter()
        cs.set_slit_width(1, 500) # slit 1 to 500 um (if it has motorized slits)
        cs.slit_width(1)

    Slits: 1 = input, 2 = side output, 3 = front output.

    Asking for something this monochromator doesn't have (grating 3 on a
    CS130) prints a warning and does nothing.

    The GUI fills in a scan range for automations to read: startWavelength,
    endWavelength, numSteps.

    Every method here just calls CornerstoneClient (cs.client), which has all
    the hardware code and the less common commands.
    """

    def __init__(self):
        self._connect()
        self.startWavelength = 600
        self.endWavelength = 800
        self.numSteps = 50
        print(f"{type(self).__name__} online")

    def _connect(self):
        client = CornerstoneClient()
        try:
            client.open()
        except Exception:
            client.close()
            raise
        self.client = client
        print(f"Cornerstone: {client.describe()}")

    # --- wavelength --------------------------------------------------------

    def goto(self, nm):
        """Move to a wavelength in nm, e.g. cs.goto(550). Waits until it's there."""
        self.client.goto(float(nm))

    def position(self):
        """The current wavelength, in nm."""
        return self.client.position()

    # --- shutter -----------------------------------------------------------

    def open_shutter(self):
        self.client.open_shutter()

    def close_shutter(self):
        self.client.close_shutter()

    def shutter_open(self):
        """True if the shutter is open."""
        return self.client.shutter_open()

    # --- grating -----------------------------------------------------------

    @_warn_if_unsupported
    def set_grating(self, n: Literal["1", "2", "3"]):
        """Switch to grating n, e.g. cs.set_grating(2), then go back to the
        wavelength from before (the monochromator itself doesn't keep it)."""
        n = self.client._need_grating(n)
        wavelength = self.client.position()
        self.client.set_grating(n)
        self.client.goto(wavelength)
        print(f"Grating {n} selected, back at {self.client.position()} nm")

    def grating(self):
        """Which grating is in use (1, 2 or 3)."""
        return self.client.grating()

    # --- filter wheel ------------------------------------------------------

    @_warn_if_unsupported
    def set_filter(self, n):
        """Turn the filter wheel to position n, e.g. cs.set_filter(3)."""
        self.client.set_filter(int(n))
        print(f"Filter {n} selected")

    def filter(self):
        """Filter wheel position; 0 if there is no wheel."""
        return self.client.filter()

    # --- slits -------------------------------------------------------------

    @_warn_if_unsupported
    def set_slit_width(self, slit, microns):
        """Set a motorized slit's width, e.g. cs.set_slit_width(1, 500)."""
        self.client.set_slit_width(int(slit), int(float(microns)))
        print(f"Slit {slit} set to {microns} um")

    def slit_width(self, slit):
        """Width of slit 1, 2 or 3 in microns; 0 if it isn't motorized."""
        return self.client.slit_width(int(slit))

    # --- GUI: scan range for automations, grating readout -----------------

    def setStartWavelength(self, value_str):
        self.startWavelength = float(value_str)
        print(self.startWavelength)

    def setEndWavelength(self, value_str):
        self.endWavelength = float(value_str)
        print(self.endWavelength)

    def setNumSteps(self, value_str):
        self.numSteps = int(value_str)
        print(self.numSteps)

    def getGratingInfo(self):
        """GUI readout: e.g. "2: 600 l/mm 1000" (number, groove density, label)."""
        info = self.client.grating_info()
        return f"{info['number']}: {info['lines']} l/mm {info['label']}".strip()


class _FakeClient(CornerstoneClient):
    """CornerstoneClient with the USB swapped for a simulated CS260 with
    every accessory (3 gratings, filter wheel, motorized slits). All the
    client's methods and capability checks run unchanged on top: set
    commands store a value, queries read it back, and a query the real unit
    wouldn't answer raises the same "no reply" error."""

    def __init__(self):
        super().__init__()
        self._values = {"WAVE": "0.000", "UNITS": "nm", "SHUTTER": "C", "GRAT": "1",
                        "FILTER": "1", "STEP": "0", "BANDPASS": "4.000", "STB": "0"}
        for n, (lines, label) in {1: (1200, "350"), 2: (600, "750"), 3: (300, "1000")}.items():
            self._values.update({f"GRAT{n}LINES": str(lines), f"GRAT{n}LABEL": label,
                                 f"GRAT{n}ZERO": "0.0", f"GRAT{n}OFFSET": "0.0",
                                 f"GRAT{n}FACTOR": "1.0"})
        for n in range(1, 7):
            self._values[f"FILTER{n}LABEL"] = f"filter {n}"
        for n in (1, 2, 3):
            self._values[f"SLIT{n}MICRONS"] = "100"

    def open(self):
        self.info = "Oriel Instruments,Model Cornerstone 260 (simulated),SN0000,FAKE"
        self._detect()

    def close(self):
        pass

    def command(self, cmd, timeout_s=None):
        key, _, value = cmd.strip().partition(" ")
        key = key.upper()
        if key == "GOWAVE":
            self._values["WAVE"] = f"{float(value):.3f}"
        elif key == "STEP":
            self._values["STEP"] = str(int(self._values["STEP"]) + int(value))
        elif key in self._values:
            self._values[key] = value
        # anything else (HANDSHAKE, unknown commands) is ignored, as the unit does

    def query(self, cmd, timeout_s=None):
        key = cmd.strip().upper()
        if not key.endswith("?"):
            raise RuntimeError(f"{self.name}: {cmd!r} is not a query")
        key = key[:-1]
        if key == "INFO":
            return self.info
        if key == "GRAT":
            n = self._values["GRAT"]
            return f"{n},{self._values[f'GRAT{n}LINES']},{self._values[f'GRAT{n}LABEL']}"
        if key in self._values:
            return self._values[key]
        raise RuntimeError(f"{self.name}: no reply to {cmd!r} in {timeout_s or self.timeout_s:g} s")


class FakeCornerstone(Cornerstone):
    """Headless monochromator: real logic driving a simulated CS260."""

    def _connect(self):
        self.client = _FakeClient()
        self.client.open()
