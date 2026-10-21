"""Cornerstone -- Oriel CS130 / CS260 monochromator.

Two transports, same interface (open / goto / position / open_shutter /
close_shutter / close):

  CornerstoneUSB     direct USB via pyusb + Microsoft's WinUSB driver. No
                     Newport software, runs in normal 64-bit Python.
  CornerstoneClient  the old route: helpers/cornerstone_helper.exe (32-bit
                     Python + Newport's Cornerstone.dll + Cypress CyUSB.sys).

Cornerstone() tries USB first and falls back to the exe, so a PC works whether
or not its driver has been swapped yet.

One-time WinUSB setup per PC (admin): plug the monochromator in, run Zadig
(https://zadig.akeo.ie), Options > List All Devices, pick the Cornerstone
(USB ID 1180 0012), choose WinUSB, Replace Driver. Newport's own software
won't see the unit afterwards; roll back the driver in Device Manager to undo.
helpers/cornerstone_probe.py checks the result.
"""
import os
import subprocess
import threading
import time
from typing import Literal

from ._shared import HELPERS_DIR


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


class CornerstoneUSB:
    """
    Direct USB link to a Cornerstone, the same bytes Newport's Cornerstone.dll
    sends (read from its disassembly): ASCII "<cmd>\\r\\n" on bulk OUT 0x01,
    replies as "<value>\\r\\n" on bulk IN 0x81, 64-byte packets. Set commands
    (GOWAVE, SHUTTER) get no reply; queries (WAVE?, SHUTTER?) get one line.
    Covers every command Cornerstone.dll exposes; moves (goto, set_grating,
    set_filter) block until the unit reports it has arrived.

    Stale input is drained before every command so a stray reply can't be
    read as the answer to the next query. The lock keeps a write+read pair
    (and a whole goto) atomic between the GUI and a running automation.
    """
    VID, PID = 0x1180, 0x0012
    EP_OUT, EP_IN = 0x01, 0x81
    PACKET = 64

    def __init__(self, timeout_s=0.5):
        self.name = "Cornerstone USB"
        self.timeout_s = timeout_s
        self.lock = threading.RLock()
        self.dev = None
        self._rx = ""

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
        # Raises here if Windows still has the device on Cypress's CyUSB.sys
        usb.util.claim_interface(dev, 0)
        self.dev = dev
        # Newport turns handshake on for moves; make sure a crashed session
        # didn't leave it on, or every command would queue an extra reply.
        self._command("HANDSHAKE 0")
        time.sleep(0.05)
        self._drain()

    # --- transport ---------------------------------------------------------

    def _read_packet(self, timeout_s):
        try:
            data = self.dev.read(self.EP_IN, self.PACKET, max(1, int(timeout_s * 1000)))
        except self._usb.core.USBTimeoutError:
            return None
        return bytes(data).replace(b"\x00", b"").decode("ascii", "replace")

    def _drain(self):
        """Throw away anything already waiting on the IN pipe."""
        self._rx = ""
        for _ in range(50):
            if self._read_packet(0.02) is None:
                return

    def _readline(self, timeout_s):
        deadline = time.monotonic() + timeout_s
        while "\n" not in self._rx:
            remaining = deadline - time.monotonic()
            chunk = self._read_packet(remaining) if remaining > 0 else None
            if chunk is None:
                return None
            self._rx += chunk
        line, self._rx = self._rx.split("\n", 1)
        return line.strip()

    def _command(self, cmd):
        with self.lock:
            self._drain()
            self.dev.write(self.EP_OUT, (cmd + "\r\n").encode("ascii"),
                           int(self.timeout_s * 1000))

    def query(self, cmd):
        """Send a query and return its one-line reply, skipping blank lines
        and an echo of the command if the firmware sends one."""
        with self.lock:
            self._command(cmd)
            while True:
                line = self._readline(self.timeout_s)
                if line is None:
                    raise RuntimeError(f"{self.name}: no reply to {cmd!r}")
                if line and line.upper() != cmd.upper():
                    return line

    def command(self, cmd):
        """Send a command that has no reply (GOWAVE, SHUTTER O, GRAT 2, ...)."""
        self._command(cmd)

    def _wait_for(self, what, read, done, timeout_s):
        """Poll read() until done(value). Reads that time out or don't parse
        count as still busy (the unit may not answer while it moves)."""
        deadline = time.monotonic() + timeout_s
        value = None
        while time.monotonic() < deadline:
            time.sleep(0.05)
            try:
                value = read()
            except (RuntimeError, ValueError):
                continue
            if done(value):
                return value
        raise RuntimeError(f"{self.name}: {what} not done in {timeout_s:g} s (last read {value!r})")

    def _float(self, cmd):
        return float(self.query(cmd))

    def _int(self, cmd):
        return int(float(self.query(cmd)))

    # --- wavelength (CornerstoneClient interface) --------------------------

    def goto(self, nm, timeout_s=120.0, tol_nm=0.05):
        """GOWAVE, then poll WAVE? until it reads the target."""
        nm = float(nm)
        with self.lock:
            self._command(f"GOWAVE {nm:.3f}")
            self._wait_for(f"GOWAVE {nm:.3f}", self.position,
                           lambda pos: abs(pos - nm) <= tol_nm, timeout_s)

    def position(self):
        return self._float("WAVE?")

    def step(self, n):
        """Move the grating drive by n motor steps."""
        self._command(f"STEP {int(n)}")

    def units(self):
        """"NM", "UM" or "WN" (wavenumbers): the units of goto/position."""
        return self.query("UNITS?").upper()

    def set_units(self, units):
        units = units.upper()
        if units not in ("NM", "UM", "WN"):
            raise ValueError(f"units must be NM, UM or WN, not {units!r}")
        self._command(f"UNITS {units}")

    # --- shutter -----------------------------------------------------------

    def open_shutter(self):
        self._command("SHUTTER O")

    def close_shutter(self):
        self._command("SHUTTER C")

    def shutter_open(self):
        """True if the shutter reads open ("SHUTTER?" -> "O" / "C")."""
        return not self.query("SHUTTER?").upper().startswith("C")

    # --- gratings ----------------------------------------------------------
    # GRAT? may answer "1" or "1,1200,750"-style; the number comes first.

    def grating(self):
        return int(self.query("GRAT?").split(",")[0])

    def set_grating(self, n, timeout_s=120.0):
        """Switch turret to grating n (CS260: 1-3, CS130: 1-2) and wait. The
        unit keeps the current wavelength on the new grating."""
        n = int(n)
        with self.lock:
            self._command(f"GRAT {n}")
            self._wait_for(f"GRAT {n}", self.grating, lambda g: g == n, timeout_s)

    def grating_lines(self, n):
        """Groove density of grating n, lines/mm."""
        return self._int(f"GRAT{int(n)}LINES?")

    def grating_label(self, n):
        return self.query(f"GRAT{int(n)}LABEL?")

    def grating_info(self, n=None):
        """{"number", "lines", "label"} for grating n (default: current)."""
        n = self.grating() if n is None else int(n)
        return {"number": n, "lines": self.grating_lines(n), "label": self.grating_label(n)}

    # Calibration values, stored in the unit. Setting these changes where
    # GOWAVE puts the light; only touch them when recalibrating.

    def grating_zero(self, n):
        return self._float(f"GRAT{int(n)}ZERO?")

    def grating_offset(self, n):
        return self._float(f"GRAT{int(n)}OFFSET?")

    def grating_factor(self, n):
        return self._float(f"GRAT{int(n)}FACTOR?")

    def set_grating_zero(self, n, value):
        self._command(f"GRAT{int(n)}ZERO {_num(value)}")

    def set_grating_offset(self, n, value):
        self._command(f"GRAT{int(n)}OFFSET {_num(value)}")

    def set_grating_factor(self, n, value):
        self._command(f"GRAT{int(n)}FACTOR {_num(value)}")

    def set_grating_lines(self, n, lines):
        self._command(f"GRAT{int(n)}LINES {int(lines)}")

    def set_grating_label(self, n, label):
        self._command(f"GRAT{int(n)}LABEL {label}")

    # --- filter wheel (optional accessory) ---------------------------------

    def filter(self):
        return self._int("FILTER?")

    def set_filter(self, n, timeout_s=30.0):
        n = int(n)
        with self.lock:
            self._command(f"FILTER {n}")
            self._wait_for(f"FILTER {n}", self.filter, lambda f: f == n, timeout_s)

    def filter_label(self, n):
        return self.query(f"FILTER{int(n)}LABEL?")

    def set_filter_label(self, n, label):
        self._command(f"FILTER{int(n)}LABEL {label}")

    # --- motorized slits (optional accessory) ------------------------------
    # Slit 1 = input port A, 2 = off-axis output B, 3 = on-axis output C.

    def slit_width(self, slit):
        """Width of slit 1-3 in microns."""
        return self._int(f"SLIT{int(slit)}MICRONS?")

    def set_slit_width(self, slit, microns):
        self._command(f"SLIT{int(slit)}MICRONS {int(microns)}")

    def bandpass(self):
        """Bandpass in nm, from the motorized slit widths."""
        return self._float("BANDPASS?")

    def set_bandpass(self, nm):
        self._command(f"BANDPASS {_num(nm)}")

    def handshake(self, on):
        """HANDSHAKE 1 makes the unit send a status reply after each command.
        Newport turns it on around moves; this class polls instead and keeps
        it off."""
        self._command(f"HANDSHAKE {1 if on else 0}")

    def close(self):
        if self.dev is None:
            return
        try:
            self._usb.util.release_interface(self.dev, 0)
            self._usb.util.dispose_resources(self.dev)
        except Exception:
            pass
        self.dev = None


class CornerstoneClient:
    """Line-oriented stdin/stdout link to cornerstone_helper.exe. Every reply
    starts with "OK", or the command failed."""

    def __init__(self, exe_path):
        self.name = os.path.basename(exe_path)
        self.p = subprocess.Popen(
            [exe_path],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", bufsize=1
        )
        greet = self.p.stdout.readline()
        if not greet.startswith("OK"):
            raise RuntimeError(f"{self.name} not ready: {greet}")

    def _send(self, line):
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()
        resp = self.p.stdout.readline()
        if not resp.startswith("OK"):
            raise RuntimeError(f"{self.name}: {resp.strip()}")
        return resp

    def open(self):
        self._send("open")

    def goto(self, nm):
        self._send(f"goto {float(nm)}")

    def position(self):
        r = self._send("position")  # "OK POS=###.###"
        for tok in r.split():
            if tok.startswith("POS="):
                return float(tok.split("=")[1])
        raise RuntimeError(f"bad position line: {r}")

    def open_shutter(self):
        self._send("open_shutter")

    def close_shutter(self):
        self._send("close_shutter")

    def close(self):
        try:
            self._send("exit")
        except Exception:
            pass
        try:
            self.p.terminate()
        except Exception:
            pass


class Cornerstone:
    """Monochromator. QML-free port of cores.Cornerstone.

    transport: "auto" (USB, else the helper exe), "usb", or "exe".
    """

    def __init__(self, exe_path=HELPERS_DIR / "cornerstone_helper.exe", transport="auto"):
        self.transport = transport
        self._connect(exe_path)
        self.targetWavelength = 630
        self.shutterState = "Closed"
        self.startWavelength = 600
        self.endWavelength = 800
        self.numSteps = 50
        self.currentGrating = 3
        self.currentWavelength = 0.0
        print(f"{type(self).__name__} online")

    def _connect(self, exe_path):
        if self.transport in ("auto", "usb"):
            mono = CornerstoneUSB()
            try:
                mono.open()
                self.mono = mono
                print("Cornerstone: direct USB (WinUSB)")
                return
            except Exception as e:
                mono.close()
                if self.transport == "usb":
                    raise
                print(f"Cornerstone: direct USB unavailable ({e}); "
                      f"falling back to {os.path.basename(exe_path)}")
        self.mono = CornerstoneClient(exe_path)
        self.mono.open()

    def setStartWavelength(self, value_str):
        self.startWavelength = float(value_str)
        print(self.startWavelength)

    def setEndWavelength(self, value_str):
        self.endWavelength = float(value_str)
        print(self.endWavelength)

    def setNumSteps(self, value_str):
        self.numSteps = int(value_str)
        print(self.numSteps)

    def setWavelength(self, target_str):
        self.targetWavelength = float(target_str)
        self.mono.goto(self.targetWavelength)
        self.currentWavelength = self.mono.position()
        print("Wavelength set")

    def openShutter(self):
        self.mono.open_shutter()
        self.shutterState = "Open"
        print("Shutter opened")

    def closeShutter(self):
        self.mono.close_shutter()
        self.shutterState = "Closed"
        print("Shutter closed")

    def getWavelength(self):
        return str(self.currentWavelength)

    def getShutter(self):
        return self.shutterState

    # Grating, filter and slits need direct USB; the helper exe only does
    # wavelength and shutter.

    def _usb(self):
        if isinstance(self.mono, CornerstoneClient):
            raise RuntimeError("needs direct USB (WinUSB driver); the helper "
                               "exe only does wavelength and shutter")
        return self.mono

    def setGrating(self, grating: Literal["1", "2", "3"]):
        mono = self._usb()
        mono.set_grating(grating)
        self.currentGrating = int(grating)
        self.currentWavelength = mono.position()
        print(f"Grating {grating} selected")

    def getGrating(self):
        info = self._usb().grating_info()
        self.currentGrating = info["number"]
        return f"{info['number']}: {info['lines']} l/mm {info['label']}".strip()

    def setFilter(self, position):
        self._usb().set_filter(position)
        print(f"Filter {position} selected")

    def getFilter(self):
        return str(self._usb().filter())

    def setSlitWidth(self, slit, microns):
        self._usb().set_slit_width(slit, microns)
        print(f"Slit {slit} set to {microns} um")


class _FakeMono:
    """No-op stand-in for CornerstoneUSB; remembers what it was last told."""

    def __init__(self, *args, **kwargs):
        self._pos = 0.0
        self._grating = 1
        self._filter = 1
        self._slits = {1: 100, 2: 100, 3: 100}

    def open(self):
        pass

    def goto(self, nm):
        self._pos = float(nm)

    def position(self):
        return self._pos

    def open_shutter(self):
        pass

    def close_shutter(self):
        pass

    def grating(self):
        return self._grating

    def set_grating(self, n):
        self._grating = int(n)

    def grating_info(self, n=None):
        n = self._grating if n is None else int(n)
        return {"number": n, "lines": 1200, "label": "FAKE"}

    def filter(self):
        return self._filter

    def set_filter(self, n):
        self._filter = int(n)

    def slit_width(self, slit):
        return self._slits[int(slit)]

    def set_slit_width(self, slit, microns):
        self._slits[int(slit)] = int(microns)

    def close(self):
        pass


class FakeCornerstone(Cornerstone):
    """Headless monochromator: real logic driving a fake helper process."""

    def __init__(self, exe_path="FAKE"):
        super().__init__(exe_path)

    def _connect(self, exe_path):
        self.mono = _FakeMono()
