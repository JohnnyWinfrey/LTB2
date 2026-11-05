"""DeathStar -- rotating polarizer + waveplate stage."""
from ._shared import ArduinoClient, _FakeArduinoClient


class DeathStar:
    """Rotating polarizer + waveplate stage. QML-free port of cores.DeathStar.

    "Clockwise"/"counter-clockwise" are as seen looking toward the incoming
    light. Wraps an ArduinoClient speaking GRBL-style G-code.
    """

    def __init__(self, comNum, ZAxis=False, id="First"):
        self._thetaP = 0            # polarizer angle
        self._thetaW = 0            # waveplate angle
        self._z = 0.0
        self.rate = 10000
        self.ZAxis = ZAxis
        self.name = id
        self._connect(comNum)
        # Zero the controller, nudge to prove motion, then return to zero.
        self.ac.commandSend("G10 L20 P1 X0 Y0")
        self.ac.commandSend(f"G1 X15 Y15 F{self.rate}")
        self.ac.commandSend(f"G1 X0 Y0 F{self.rate}")
        print(self.name, f" {type(self).__name__} online")

    def _connect(self, comNum):
        self.ac = ArduinoClient(comNum, 115200)

    def home(self):
        """Move to the nearest 0th degree."""
        self.ac.commandSend(f"G1 X0 Y0 F{self.rate}")
        self._thetaP = 0
        self._thetaW = 0
        print(self.name, " Go Home ->", self._thetaP, self._thetaW)

    def resetHome(self):
        """Move to the nearest 0th degree and set that as the new zero."""
        returnP = self._thetaP % 360
        returnW = self._thetaW % 360
        self.ac.commandSend(
            f"G1 X{self._thetaP - returnP} Y{self._thetaW - returnW} F{self.rate}"
        )
        self.ac.commandSend("G10 L20 P1 X0 Y0")
        self._thetaP = 0
        self._thetaW = 0
        print(self.name, " Set Zero")

    def zHome(self):
        """Return the Z axis to zero (only if this stage has one)."""
        if self.ZAxis:
            self._z = 0.0
            self.ac.commandSend("G1 Z0 F40")
            print(self.name, " Z Go Home ->", self._z)

    def setPosition(self, p_str, w_str, z=""):
        if z:
            self._z = float(z)
            self.ac.commandSend(f"G1 Z{z} F40")
        self.ac.commandSend(f"G1 X{p_str} Y{w_str} F{self.rate}")
        if p_str.strip():
            self._thetaP = float(p_str)
        if w_str.strip():
            self._thetaW = float(w_str)
        print(self.name, " setting Position ->", self._thetaP, self._thetaW, z)

    def setRate(self, rate_str):
        self.rate = float(rate_str)
        print(self.name, " rate ->", self.rate)

    def getAngles(self):
        """Current polarizer / waveplate angles, mod 360."""
        return f"P={self._thetaP % 360:.2f}   W={self._thetaW % 360:.2f}"


class FakeDeathStar(DeathStar):
    """Headless DeathStar: real angle logic driving a fake serial client."""

    def __init__(self, comNum="FAKE", ZAxis=False, id="Fake"):
        super().__init__(comNum, ZAxis, id)

    def _connect(self, comNum):
        self.ac = _FakeArduinoClient()
