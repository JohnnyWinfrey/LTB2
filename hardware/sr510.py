"""SR510 -- Stanford Research single-phase lock-in amplifier over RS232."""
import math
import random
import threading
import time
from collections import namedtuple

# Index -> value tables. G, T1 and T2 read and set indices, not values.
SR510_SENSITIVITY_V = {
    i + 1: v for i, v in enumerate([
        10e-9, 20e-9, 50e-9, 100e-9, 200e-9, 500e-9,
        1e-6, 2e-6, 5e-6, 10e-6, 20e-6, 50e-6,
        100e-6, 200e-6, 500e-6, 1e-3, 2e-3, 5e-3,
        10e-3, 20e-3, 50e-3, 100e-3, 200e-3, 500e-3,
    ])
}    # 1-3 only with an SRS preamp
SR510_PRE_TC_S = {
    i + 1: v for i, v in enumerate([1e-3, 3e-3, 10e-3, 30e-3, 100e-3, 300e-3,
                                    1.0, 3.0, 10.0, 30.0, 100.0])
}
SR510_POST_TC_S = {0: 0.0, 1: 0.1, 2: 1.0}

# Status byte (Y). Bit 0 is always set over RS232, so it isn't reported.
_SR510_STATUS = [
    (1 << 1, "parameter out of range"), (1 << 2, "no reference"),
    (1 << 3, "PLL unlocked"), (1 << 4, "signal overload"),
    (1 << 5, "bit 5"), (1 << 6, "bit 6"), (1 << 7, "bad command"),
]


def _si(value, unit):
    """50e-6, "V" -> "50 uV"."""
    for scale, prefix in ((1, ""), (1e-3, "m"), (1e-6, "u"), (1e-9, "n")):
        if abs(value) >= scale or scale == 1e-9:
            return f"{value / scale:g} {prefix}{unit}"


class SR510Link:
    """
    Serial link to an SR510's rear RS232 port: 9600 baud, 8N2, no flow control.

    Rear-panel SW2 must be in computer mode (bit 6 UP = no echo) and SW1 bit 6
    UP (DOWN echoes GPIB traffic onto RS232). Commands are "<cmd>\\r". Queries
    (no argument: "Q", "P", "G") answer with one "\\r"-terminated value; set
    commands (with an argument: "P90", "W0") answer with nothing, so never
    read after one. The SR510 won't transmit while DTR is low; pyserial
    raises DTR on open.

    The lock keeps one write+read pair atomic, so a GUI button and a running
    automation can't interleave replies. It's reentrant so SR510.getXY can
    hold it across a whole phase-rotate sequence.
    """
    BAUD = 9600

    def __init__(self, port, timeout_s=2.0):
        import serial

        self.port = port
        self.lock = threading.RLock()
        self.ser = serial.Serial(port, self.BAUD, bytesize=8, parity="N",
                                 stopbits=2, xonxoff=False, rtscts=False,
                                 timeout=timeout_s)
        self.ser.dtr = True
        # After power-up there can be a garbage character either way.
        self.ser.write(b"\r\r\r")
        self.ser.flush()
        time.sleep(0.2)
        self.ser.reset_input_buffer()

    def send(self, cmd):
        with self.lock:
            self.ser.write(f"{cmd}\r".encode("ascii"))
            # Wait until it's on the wire: on macOS the reset_input_buffer() in
            # the next query() also discards unsent output, truncating this command.
            self.ser.flush()

    def query(self, cmd):
        with self.lock:
            self.ser.reset_input_buffer()
            self.ser.write(f"{cmd}\r".encode("ascii"))
            reply = self.ser.read_until(b"\r").decode("ascii", "replace").strip()
        if not reply:
            raise TimeoutError(f"SR510 on {self.port}: no reply to {cmd!r}")
        if ">" in reply:
            raise RuntimeError(f"SR510 on {self.port}: got {reply!r} -- echo is on, "
                               f"set rear-panel SW2 bit 6 UP")
        return reply

    def close(self):
        self.ser.close()


XYReading = namedtuple("XYReading", "x y r theta")
XYReading.__str__ = lambda s: (f"X={s.x:.4e}  Y={s.y:.4e}  "
                               f"R={s.r:.4e} V  theta={s.theta:.2f} deg")


class SR510:
    """Stanford Research SR510 lock-in, single phase.

    measure() reads the output display (X once S0 is set, which open does).
    The SR510 has no Y channel, so getXY() gets one by rotating the reference
    phase 90 deg, waiting for the output filters to settle, reading again and
    rotating back. That takes 2 x settleFactor x (pre + post time constant),
    about 2 s at 100 ms + 0.1 s, and assumes the signal holds steady meanwhile.

    Any phase or time-constant change sets a "settled at" time, and every
    reading sleeps until then, so a reading never mixes old and new phase.

    Sign of theta: the SR510 defines phase as delay from the reference. Check
    once against a known phase shift before trusting theta's sign.

    Never send "Z": it resets every front-panel setting to factory defaults.
    """

    def __init__(self, port, settleFactor=5.0, charDelay=0):
        self.name = f"SR510 ({port})"
        self.settleFactor = float(settleFactor)
        self._settledAt = 0.0
        self._connect(port)
        # W: per-character reply delay in 4 ms steps; the power-up W6 makes
        # every reply ~0.2 s. A USB dongle keeps up at W0; try W1-W2 if garbled.
        self.link.send(f"W{int(charDelay)}")
        self.link.send("S0")          # display X, so Q reads X
        self.link.query("Y")          # reading the status byte clears it
        print(f"{type(self).__name__} online: {self.getSettings()}")

    def _connect(self, port):
        self.link = SR510Link(port)

    # ── protocol helpers ────────────────────────────────────────────────

    def _float(self, cmd):
        return float(self.link.query(cmd))

    def _int(self, cmd):
        return int(float(self.link.query(cmd)))

    def _settleTime(self):
        """settleFactor x (pre + post time constant), read fresh from the
        unit since they can be changed on the front panel."""
        pre = SR510_PRE_TC_S[self._int("T1")]
        post = SR510_POST_TC_S[self._int("T2")]
        return self.settleFactor * (pre + post)

    def _markUnsettled(self):
        self._settledAt = max(self._settledAt, time.monotonic() + self._settleTime())

    def _waitSettled(self):
        remaining = self._settledAt - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)

    def _setPhase(self, degrees):
        """Set the reference phase, wrapped to [-180, 180)."""
        wrapped = (float(degrees) + 180.0) % 360.0 - 180.0
        self.link.send(f"P{wrapped:.2f}")
        self._markUnsettled()

    def _read(self):
        """Q, after waiting for the filters to settle."""
        self._waitSettled()
        return self._float("Q")

    # ── GUI-facing controls ─────────────────────────────────────────────

    def measure(self):
        """X in volts (the output display)."""
        return self._read()

    def getXY(self):
        """X, Y, R (V) and theta (deg), by rotating the phase 90 deg and back."""
        with self.link.lock:
            phi0 = self._float("P")
            x = self._read()
            try:
                self._setPhase(phi0 + 90.0)
                y = self._read()
            finally:
                self._setPhase(phi0)    # restore the saved phase, not P0
        theta = (phi0 + math.degrees(math.atan2(y, x)) + 180.0) % 360.0 - 180.0
        return XYReading(x, y, math.hypot(x, y), theta)

    def getPhase(self):
        return self._float("P")

    def setPhase(self, degrees):
        self._setPhase(degrees)
        print(f"{self.name} phase -> {self.getPhase():.2f} deg")

    def getFrequency(self):
        return self._float("F")

    def getSensitivity(self):
        i = self._int("G")
        return f"{i} ({_si(SR510_SENSITIVITY_V[i], 'V')})"

    def setSensitivity(self, index):
        """Index 1-24 (see SR510_SENSITIVITY_V): 24 = 500 mV, 13 = 100 uV."""
        i = int(index)
        if i not in SR510_SENSITIVITY_V:
            raise ValueError(f"sensitivity index must be 1-24, not {i}")
        self.link.send(f"G{i}")
        print(f"{self.name} sensitivity -> {self.getSensitivity()}")

    def getTimeConstant(self):
        pre, post = self._int("T1"), self._int("T2")
        return (f"pre {pre} ({_si(SR510_PRE_TC_S[pre], 's')}), "
                f"post {post} ({_si(SR510_POST_TC_S[post], 's') if post else 'none'})")

    def setTimeConstant(self, pre="", post=""):
        """Pre index 1-11 (5 = 100 ms), post index 0-2 (0 none, 1 0.1 s, 2 1 s).
        Leave either blank to keep it."""
        if str(pre).strip():
            if int(pre) not in SR510_PRE_TC_S:
                raise ValueError(f"pre time constant index must be 1-11, not {pre}")
            self.link.send(f"T1,{int(pre)}")
        if str(post).strip():
            if int(post) not in SR510_POST_TC_S:
                raise ValueError(f"post time constant index must be 0-2, not {post}")
            self.link.send(f"T2,{int(post)}")
        self._markUnsettled()
        print(f"{self.name} time constant -> {self.getTimeConstant()}")

    def getAnalogInput(self, channel):
        """Voltage on rear-panel analog input 1-4 (+-10.24 V)."""
        if int(channel) not in (1, 2, 3, 4):
            raise ValueError(f"analog input must be 1-4, not {channel}")
        volts = self._float(f"X{int(channel)}")
        print(f"{self.name} X{int(channel)} = {volts} V")
        return volts

    def getStatus(self):
        """Decode the status byte. Reading it clears it."""
        status = self._int("Y")
        flags = [text for bit, text in _SR510_STATUS if status & bit]
        return ", ".join(flags) if flags else "OK"

    def getSettings(self):
        """One line of run metadata: frequency, phase, sensitivity, time constants."""
        ref = "2f" if self._int("M") else "f"
        return (f"f={self.getFrequency():g} Hz (ref {ref}), phase={self.getPhase():.2f} deg, "
                f"sens {self.getSensitivity()}, {self.getTimeConstant()}")

    def lockFrontPanel(self):
        self.link.send("I1")

    def unlockFrontPanel(self):
        self.link.send("I0")

    def close(self):
        self.link.send("I0")
        self.link.close()


class _FakeSR510Link:
    """No-op stand-in for SR510Link: a steady signal of amplitude `r` at phase
    `theta`, read through the current reference phase, plus a little noise."""

    def __init__(self, r=1e-3, theta=30.0):
        self.lock = threading.RLock()
        self.r, self.theta = r, theta
        # Short time constants (10 ms, no post) keep getXY quick in sim.
        self.state = {"P": 0.0, "G": 24, "T1": 3, "T2": 0, "S": 0, "M": 0,
                      "W": 6, "I": 0, "F": 1000.0}

    def send(self, cmd):
        cmd = cmd.replace(" ", "").upper()
        if cmd.startswith(("T1,", "T2,")):
            self.state[cmd[:2]] = int(cmd[3:])
        elif cmd[0] == "P":
            self.state["P"] = float(cmd[1:])
        elif cmd[0] in "GSMWI":
            self.state[cmd[0]] = int(cmd[1:])

    def query(self, cmd):
        cmd = cmd.replace(" ", "").upper()
        if cmd == "Q":
            if self.state["S"] != 0:
                return "0.000E+0"
            x = self.r * math.cos(math.radians(self.theta - self.state["P"]))
            return f"{x * (1 + random.gauss(0, 0.01)):.4E}"
        if cmd == "Y":
            return "1"
        if cmd[0] == "X":
            return f"{random.uniform(-0.01, 0.01):.4f}"
        value = self.state[cmd]
        return f"{value:.2f}" if isinstance(value, float) else str(value)

    def close(self):
        pass


class FakeSR510(SR510):
    """Headless SR510: real logic reading a fake link. `r` (V) and `theta`
    (deg) set the simulated signal."""

    def __init__(self, port="FAKE", settleFactor=5.0, charDelay=0, r=1e-3, theta=30.0):
        self._fakeSignal = (r, theta)
        super().__init__(port, settleFactor, charDelay)

    def _connect(self, port):
        self.link = _FakeSR510Link(*self._fakeSignal)
