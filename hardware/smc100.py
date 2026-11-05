"""SMC100 -- Newport single-axis motion controller (daisy-chainable)."""
import threading
import time


class SMC100Bus:
    """
    Serial link to a chain of Newport SMC100 controllers (CC or PP).

    Daisy-chained controllers all hang off ONE COM port and are told apart by
    their address (1-31, set on each controller's front panel / via the CC
    command). Every command is "<addr><CMD><arg>\\r\\n" and every query reply
    echoes "<addr><CMD>" before the value.

    Several axes share one bus: get it with SMC100Bus.shared(port) so all axes
    on a port reuse the same handle, and give it back with release(). The lock
    keeps one write+read pair atomic, so a GUI button and a running automation
    can talk to different axes on the same port without interleaving replies.
    """
    BAUD = 57600
    _open = {}    # port -> SMC100Bus

    def __init__(self, port, timeout_s=0.5):
        import serial

        self.port = port
        self._lock = threading.Lock()
        self._users = 0
        self.ser = serial.Serial(port, self.BAUD, bytesize=8, parity="N",
                                 stopbits=1, xonxoff=True, timeout=timeout_s)

    @classmethod
    def shared(cls, port):
        bus = cls._open.get(port)
        if bus is None:
            bus = cls._open[port] = cls(port)
        bus._users += 1
        return bus

    def release(self):
        self._users -= 1
        if self._users <= 0:
            self._open.pop(self.port, None)
            self.ser.close()

    def send(self, addr, cmd, arg=""):
        with self._lock:
            self.ser.write(f"{addr}{cmd}{arg}\r\n".encode("ascii"))
            # Wait until it's on the wire: on macOS the reset_input_buffer() in
            # the next query() also discards unsent output, truncating this command.
            self.ser.flush()

    def query(self, addr, cmd):
        """Send "<addr><cmd>" and return the value after the echoed prefix.

        Pass the command exactly as the manual spells it: "TS", "TP", "TE"
        and "VE" have no "?", parameter reads do ("VA?", "SL?").
        """
        prefix = f"{addr}{cmd.rstrip('?')}"
        with self._lock:
            self.ser.reset_input_buffer()
            self.ser.write(f"{addr}{cmd}\r\n".encode("ascii"))
            reply = self.ser.read_until(b"\r\n").decode("ascii", "replace").strip()
        if not reply:
            raise TimeoutError(f"SMC100 #{addr} on {self.port}: no reply to {addr}{cmd}")
        if not reply.startswith(prefix):
            raise RuntimeError(f"SMC100 #{addr} on {self.port}: bad reply {reply!r} to {addr}{cmd}")
        return reply[len(prefix):]


# Controller states, from the 2-char state code at the end of a TS reply.
_SMC_NOT_REFERENCED = {"0A", "0B", "0C", "0D", "0E", "0F", "10", "11"}
_SMC_READY = {"32", "33", "34", "35", "36", "37"}
_SMC_DISABLED = {"3C", "3D", "3E", "3F"}
_SMC_BUSY = {"1E", "1F", "28", "46", "47"}    # homing / moving / jogging

# TE replies: why the last command was refused ("@" = accepted).
_SMC_ERRORS = {
    "A": "unknown command", "B": "wrong address", "C": "parameter missing or out of range",
    "D": "command not allowed", "E": "homing already started", "F": "unknown ESP stage",
    "G": "displacement out of limits", "H": "not allowed in NOT REFERENCED (home first)",
    "I": "not allowed in CONFIGURATION", "J": "not allowed in DISABLE",
    "K": "not allowed in READY", "L": "not allowed in HOMING", "M": "not allowed in MOVING",
    "N": "position out of software limits", "S": "communication timeout",
    "U": "EEPROM error", "V": "error during execution",
    "W": "not allowed for PP", "X": "not allowed for CC",
}

# Fault bits, from the 4 hex chars at the start of a TS reply.
_SMC_FAULTS = [
    (0x200, "80 W output power exceeded"), (0x100, "DC voltage too low"),
    (0x080, "wrong ESP stage"), (0x040, "homing timeout"),
    (0x020, "following error"), (0x010, "short circuit"),
    (0x008, "RMS current limit"), (0x004, "peak current limit"),
    (0x002, "positive end of run"), (0x001, "negative end of run"),
]


def _smc_state_name(state):
    for group, label in ((_SMC_NOT_REFERENCED, "NOT REFERENCED"), (_SMC_READY, "READY"),
                         (_SMC_DISABLED, "DISABLE"), (_SMC_BUSY, "MOVING/HOMING"),
                         ({"14"}, "CONFIGURATION")):
        if state in group:
            return f"{label} ({state})"
    return f"unknown ({state})"


class SMC100:
    """One axis on a Newport SMC100 controller (CC or PP), linear or rotary.

    The controller works in the stage's own units, so `units` only labels
    them: "mm" for a linear stage, "deg" for a rotation stage. All positions
    here are in those units.

    Daisy chain: make one SMC100 per controller, all with the same port and
    each with its own address (1-31, as set on the controller). They share a
    single serial link through SMC100Bus.shared::

        polarizer = SMC100("COM5", address=1, units="deg")
        waveplate = SMC100("COM5", address=2, units="deg", wrap="positive")

    Each axis gets its own auto_gui window. moveAbsolute / moveRelative block
    until the axis stops; to move several axes at once, start each with
    _startAbsolute / _startRelative, then call _waitReady() on each.

    offset : stage position that counts as 0 here (e.g. the waveplate fast
             axis), so positions are stage position - offset. setZero() sets
             it to wherever the stage is now.
    wrap   : rotation stages only. None = targets are literal (370 means 370).
             "shortest" / "positive" / "negative" = a target is an angle mod
             360, reached the shortest way or always turning + / -. Falls
             back to the other way round if the preferred one would cross a
             software limit.
    """

    WRAP_MODES = ("shortest", "positive", "negative")

    def __init__(self, port, address=1, units="mm", offset=0.0, wrap=None):
        if units not in ("mm", "deg"):
            raise ValueError(f"units must be 'mm' or 'deg', not {units!r}")
        self.address = int(address)
        self.units = units
        self.name = f"SMC100 #{self.address} ({port})"
        self.offset = float(offset)
        self.wrap = None
        self._step = 0.1 if units == "mm" else 1.0   # per jog-button press
        self.homeTimeout = 120.0     # s; homing runs at the (slower) OH velocity
        self._moveTimeout = 60.0     # s; reset by every _start* from the move length
        self._connect(port)
        q = lambda cmd: float(self.bus.query(self.address, cmd))
        self._rawMin, self._rawMax = q("SL?"), q("SR?")
        self._velocity, self._accel = q("VA?"), q("AC?")
        if wrap:
            self.setWrap(wrap)
        version = self.bus.query(self.address, "VE").strip()
        print(f"{type(self).__name__} #{self.address} online: {version}, "
              f"travel {self._rawMin} to {self._rawMax} {units}")

    def _connect(self, port):
        self.bus = SMC100Bus.shared(port)

    @property
    def minPos(self):
        """Software limits (SL / SR), shifted by offset like every position."""
        return self._rawMin - self.offset

    @property
    def maxPos(self):
        return self._rawMax - self.offset

    # ── protocol helpers ────────────────────────────────────────────────

    def _command(self, cmd, arg=""):
        """Send a command, then ask TE whether the controller accepted it."""
        self.bus.send(self.address, cmd, arg)
        code = self.bus.query(self.address, "TE").strip()
        if code != "@":
            raise RuntimeError(f"{self.name}: {cmd}{arg} refused -- "
                               f"{_SMC_ERRORS.get(code, code)}")

    def _status(self):
        """(fault bits, state code) from TS."""
        reply = self.bus.query(self.address, "TS").strip()
        return int(reply[:4], 16), reply[4:6]

    def _position(self):
        """Position relative to offset, never wrapped."""
        return float(self.bus.query(self.address, "TP")) - self.offset

    def _waitFor(self, states, timeout_s):
        """Poll TS until the state is in `states`. Missed replies are retried,
        since a controller rebooting after RS is silent for a moment."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            try:
                _, state = self._status()
            except TimeoutError:
                state = None
            if state in states:
                return
            if state is not None and state not in _SMC_BUSY and state not in states:
                faults, _ = self._status()
                raise RuntimeError(f"{self.name}: ended in {_smc_state_name(state)}"
                                   f"{self._faultText(faults)}")
            time.sleep(0.05)
        raise TimeoutError(f"{self.name}: not in the expected state after {timeout_s:.0f} s")

    def _waitReady(self, timeout_s=None):
        """Block until the axis is READY; stops it and raises on timeout."""
        try:
            self._waitFor(_SMC_READY, timeout_s or self._moveTimeout)
        except TimeoutError:
            self.stop()
            raise

    @staticmethod
    def _faultText(faults):
        names = [text for bit, text in _SMC_FAULTS if faults & bit]
        return f" -- faults: {', '.join(names)}" if names else ""

    def _unwrap(self, target, current):
        """Turn a wrapped angle into the literal position to move to."""
        d = (target - current) % 360.0      # the + way round, in [0, 360)
        ways = {"positive": [d, d - 360.0],
                "negative": [d - 360.0, d] if d else [0.0],
                "shortest": sorted([d, d - 360.0], key=abs)}[self.wrap]
        for way in ways:
            if self.minPos <= current + way <= self.maxPos:
                return current + way
        raise ValueError(f"{self.name}: {target % 360:.4f} deg can't be reached "
                         f"either way round within [{self.minPos}, {self.maxPos}] deg")

    def _startAbsolute(self, position):
        """Start a move to `position` and return without waiting."""
        target = float(position)
        current = self._position()
        if self.wrap:
            target = self._unwrap(target, current)
        if not self.minPos <= target <= self.maxPos:
            raise ValueError(f"{self.name}: {target} {self.units} is outside "
                             f"[{self.minPos}, {self.maxPos}] {self.units}")
        distance = abs(target - current)
        # Trapezoidal-move time plus margin; replaces pySMC100's fixed 12 s.
        self._moveTimeout = 2 * (distance / self._velocity
                                 + self._velocity / self._accel) + 5.0
        self._command("PA", f"{target + self.offset:.6f}")

    def _startRelative(self, distance):
        """Relative moves are literal: +400 deg turns more than once."""
        wrap, self.wrap = self.wrap, None
        try:
            self._startAbsolute(self._position() + float(distance))
        finally:
            self.wrap = wrap

    # ── GUI-facing controls ─────────────────────────────────────────────

    def home(self):
        """Reference the axis (OR). OR is only accepted from NOT REFERENCED, so
        an axis that is already referenced or disabled is reset (RS) first."""
        _, state = self._status()
        if state not in _SMC_NOT_REFERENCED:
            self.bus.send(self.address, "RS")
            time.sleep(0.5)
            self._waitFor(_SMC_NOT_REFERENCED, 15.0)
        self._command("OR")
        self._waitReady(self.homeTimeout)
        print(f"{self.name} homed -> {self.getPosition()}")

    def moveAbsolute(self, position):
        self._startAbsolute(position)
        self._waitReady()
        print(f"{self.name} -> {self.getPosition()}")

    def moveRelative(self, distance):
        self._startRelative(distance)
        self._waitReady()
        print(f"{self.name} -> {self.getPosition()}")

    def setStep(self, step):
        self._step = abs(float(step))
        print(f"{self.name} jog step set to {self._step} {self.units}")

    def jogPlus(self):
        self.moveRelative(self._step)

    def jogMinus(self):
        self.moveRelative(-self._step)

    def setOffset(self, offset):
        self.offset = float(offset)
        print(f"{self.name} offset set to {self.offset} {self.units}")

    def setZero(self):
        """Make the current stage position read 0 from now on."""
        self.setOffset(self._position() + self.offset)

    def setWrap(self, mode):
        """'shortest', 'positive', 'negative', or 'off' / blank for literal targets."""
        mode = str(mode or "").strip().lower()
        if mode in ("", "off", "none"):
            self.wrap = None
        elif self.units != "deg":
            raise ValueError(f"{self.name}: wrap only applies to units='deg'")
        elif mode not in self.WRAP_MODES:
            raise ValueError(f"wrap must be one of {self.WRAP_MODES} or 'off', not {mode!r}")
        else:
            self.wrap = mode
        print(f"{self.name} wrap -> {self.wrap or 'off'}")

    def stop(self):
        self.bus.send(self.address, "ST")
        print(f"{self.name} stopped")

    def enable(self):
        """Leave DISABLE (servo back on) -> READY."""
        self._command("MM", "1")

    def disable(self):
        """Enter DISABLE: motor unpowered, position kept, no re-homing needed."""
        self._command("MM", "0")

    def getPosition(self):
        pos = self._position()
        if self.wrap:
            return f"{pos % 360:.4f} deg (unwrapped {pos:.4f})"
        return f"{pos:.4f} {self.units}"

    def getStatus(self):
        faults, state = self._status()
        return _smc_state_name(state) + self._faultText(faults)

    def close(self):
        self.bus.release()


class _FakeSMC100Bus:
    """No-op stand-in for SMC100Bus: any address answers and moves finish
    instantly, but moves before home() are refused like the real controller.
    Shared per port like the real bus, so two axes given the same address
    really do drive the same simulated stage."""
    _open = {}    # port -> _FakeSMC100Bus

    def __init__(self):
        self._axes = {}

    @classmethod
    def shared(cls, port):
        return cls._open.setdefault(port, cls())

    def _axis(self, addr):
        return self._axes.setdefault(addr, {"pos": 0.0, "state": "0A", "err": "@",
                                            "limits": (-12.5, 12.5)})

    def send(self, addr, cmd, arg=""):
        ax = self._axis(addr)
        if cmd == "OR":
            ax["pos"], ax["state"] = 0.0, "32"
        elif cmd in ("PA", "PR"):
            if ax["state"] not in _SMC_READY:
                ax["err"] = "H" if ax["state"] in _SMC_NOT_REFERENCED else "J"
                return
            ax["pos"] = float(arg) + (ax["pos"] if cmd == "PR" else 0.0)
            ax["state"] = "33"
        elif cmd == "RS":
            ax["state"] = "0A"
        elif cmd == "MM":
            ax["state"] = "3C" if arg == "0" else "34"

    def query(self, addr, cmd):
        ax = self._axis(addr)
        if cmd == "TS":
            return "0000" + ax["state"]
        if cmd == "TP":
            return f"{ax['pos']:.6f}"
        if cmd == "TE":
            err, ax["err"] = ax["err"], "@"
            return err
        if cmd == "VE":
            return " SMC_CC FAKE"
        low, high = ax["limits"]
        return {"SL?": str(low), "SR?": str(high), "VA?": "2.0", "AC?": "10.0"}[cmd]

    def release(self):
        pass


class FakeSMC100(SMC100):
    """Headless SMC100 axis: real move/home logic driving a fake bus.
    `limits` sets the simulated software limits (default +-12.5 mm or +-720 deg)."""

    def __init__(self, port="FAKE", address=1, units="mm", offset=0.0, wrap=None,
                 limits=None):
        self._fakeLimits = limits or ((-360, 360) if units == "mm" else (-1800, 1800))
        super().__init__(port, address, units, offset, wrap)

    def _connect(self, port):
        self.bus = _FakeSMC100Bus.shared(port)
        self.bus._axis(self.address)["limits"] = self._fakeLimits

