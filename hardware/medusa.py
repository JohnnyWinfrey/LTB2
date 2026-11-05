"""Medusa -- PSG + PSA polarizers/waveplates and the xwing on one Arduino Mega.

Replaces the PSG/PSA DeathStar pair. Firmware: firmware/medusa/medusa.ino,
which documents the serial protocol. Rotary axes are in degrees, the xwing in
mm. The Mega is the source of truth for position; nothing is tracked here.
"""
import threading
import time
from typing import Literal

# Protocol axis names, in pin order (PUL/DIR 2/3, 4/5, 6/7, 8/9, 10/11).
PSG_POL, PSG_WAVE, XWING, PSA_WAVE, PSA_POL = "GP", "GW", "X", "AW", "AP"
AXES = (PSG_POL, PSG_WAVE, XWING, PSA_WAVE, PSA_POL)
ROTARY = (PSG_POL, PSG_WAVE, PSA_WAVE, PSA_POL)

Jog = Literal["-", "+"]


class _MedusaLink:
    """Serial link: one command line out, one reply line back."""

    def __init__(self, port, baud=115200, timeout=5.0):
        import serial

        self.devPort = serial.Serial(port, baud, timeout=timeout)
        # Opening the port resets the Mega; wait for its banner.
        deadline = time.time() + 10
        while time.time() < deadline:
            if self.devPort.readline().decode(errors="replace").strip() == "Medusa ready":
                return
        raise TimeoutError(f"Medusa on {port} never reported ready")

    def transact(self, command):
        self.devPort.write(command.encode() + b"\n")
        reply = self.devPort.readline().decode(errors="replace").strip()
        if not reply:
            raise TimeoutError(f"Medusa: no reply to {command!r}")
        return reply

    def close(self):
        self.devPort.close()


class Medusa:
    """Five steppers on one Mega: PSG polarizer + waveplate, xwing linear stage,
    PSA waveplate + polarizer.

    setPosition() and the home methods block until motion finishes, so a scan
    can measure as soon as they return. Jogs return immediately and stack, so
    clicking jog+ three times moves three steps.
    """

    def __init__(self, comNum, name="Medusa"):
        self.name = name
        self.jogDeg = 1.0           # rotary jog step
        self.jogMm = 0.1            # xwing jog step
        self.pollInterval = 0.05    # s between status polls while waiting
        # The GUI thread (jog/stop buttons) and the automation worker share the
        # port; the lock keeps each command paired with its own reply.
        self._lock = threading.Lock()
        self._connect(comNum)
        print(self.name, f" {type(self).__name__} online")

    def _connect(self, comNum):
        self._link = _MedusaLink(comNum)

    # ── transport ───────────────────────────────────────────────────────────
    def _send(self, command):
        with self._lock:
            reply = self._link.transact(command)
        if reply.startswith("error"):
            raise RuntimeError(f"Medusa {command!r} -> {reply}")
        return reply

    def _status(self):
        """(idle, {axis: position}) parsed from the '?' reply."""
        state, *fields = self._send("?").split()
        positions = {k: float(v) for k, v in (f.split("=") for f in fields)}
        return state == "Idle", positions

    def _waitIdle(self):
        while not self._status()[0]:
            time.sleep(self.pollInterval)

    def _moveTo(self, targets):
        """Absolute move of {axis: position}, all at once, then wait."""
        if targets:
            self._send("MOVE " + " ".join(f"{a} {float(v)}" for a, v in targets.items()))
            self._waitIdle()

    # ── moves ───────────────────────────────────────────────────────────────
    def setPosition(self, psgPol="", psgWave="", xwing="", psaWave="", psaPol=""):
        """Move any subset of axes (blank = leave alone); returns when stopped."""
        given = {PSG_POL: psgPol, PSG_WAVE: psgWave, XWING: xwing,
                 PSA_WAVE: psaWave, PSA_POL: psaPol}
        self._moveTo({a: v for a, v in given.items() if str(v).strip() != ""})
        print(self.name, " setting Position ->", self.getPosition())

    def home(self):
        """Rotate all four optics back to 0 deg (xwing stays put)."""
        self._moveTo({a: 0 for a in ROTARY})
        print(self.name, " Go Home")

    def resetHome(self):
        """Rotate each optic to its nearest full turn and call that 0 deg.

        Same angle as home(), without unwinding after a multi-turn sweep.
        """
        _, pos = self._status()
        self._moveTo({a: 360 * round(pos[a] / 360) for a in ROTARY})
        for a in ROTARY:
            self._send(f"ZERO {a}")
        print(self.name, " Set Zero")

    def xwingHome(self):
        """Return the xwing to 0 mm."""
        self._moveTo({XWING: 0})
        print(self.name, " xwing Go Home")

    def stop(self):
        """Decelerate every axis to a halt."""
        self._send("STOP")

    # ── settings ────────────────────────────────────────────────────────────
    def setJogStep(self, degrees="", mm=""):
        if str(degrees).strip():
            self.jogDeg = float(degrees)
        if str(mm).strip():
            self.jogMm = float(mm)
        print(self.name, f" jog step -> {self.jogDeg} deg, {self.jogMm} mm")

    def setSpeed(self, degPerSec="", mmPerSec=""):
        if str(degPerSec).strip():
            for a in ROTARY:
                self._send(f"SPEED {a} {float(degPerSec)}")
        if str(mmPerSec).strip():
            self._send(f"SPEED {XWING} {float(mmPerSec)}")
        print(self.name, f" speed -> {degPerSec or '-'} deg/s, {mmPerSec or '-'} mm/s")

    def getPosition(self):
        _, pos = self._status()
        return (f"PSG P={pos[PSG_POL]:.2f} W={pos[PSG_WAVE]:.2f}   "
                f"X={pos[XWING]:.3f}   "
                f"PSA W={pos[PSA_WAVE]:.2f} P={pos[PSA_POL]:.2f}")

    # ── jogs (auto_gui draws each as one row with a - and a + button) ───────
    def _jog(self, axis, direction):
        if direction not in ("-", "+"):
            raise ValueError(f"jog direction must be '-' or '+', not {direction!r}")
        step = self.jogMm if axis == XWING else self.jogDeg
        self._send(f"JOG {axis} {-step if direction == '-' else step}")

    def jogPsgPol(self, direction: Jog):   self._jog(PSG_POL, direction)
    def jogPsgWave(self, direction: Jog):  self._jog(PSG_WAVE, direction)
    def jogXwing(self, direction: Jog):    self._jog(XWING, direction)
    def jogPsaWave(self, direction: Jog):  self._jog(PSA_WAVE, direction)
    def jogPsaPol(self, direction: Jog):   self._jog(PSA_POL, direction)


class _FakeMedusaLink:
    """Stand-in for the Mega: answers the protocol, every move lands instantly."""

    def __init__(self):
        self.pos = dict.fromkeys(AXES, 0.0)

    def transact(self, command):
        cmd, *args = command.split()
        if cmd == "?":
            return "Idle " + " ".join(f"{a}={p:.3f}" for a, p in self.pos.items())
        if cmd == "MOVE":
            for a, v in zip(args[::2], args[1::2]):
                self.pos[a] = float(v)
        elif cmd == "JOG":
            self.pos[args[0]] += float(args[1])
        elif cmd == "HOME":
            for a in args or AXES:
                self.pos[a] = 0.0
        elif cmd == "ZERO":
            for a in args or AXES:
                self.pos[a] = 0.0
        return "ok"

    def close(self):
        pass


class FakeMedusa(Medusa):
    """Headless Medusa: real command logic driving a simulated Mega."""

    def __init__(self, comNum="FAKE", name="Fake Medusa"):
        super().__init__(comNum, name)

    def _connect(self, comNum):
        self._link = _FakeMedusaLink()
