"""XWing -- XY sample stage."""
from ._shared import ArduinoClient, _FakeArduinoClient


class XWing:
    """XY sample stage. QML-free port of cores.XWing (ArduinoClient / G-code)."""

    def __init__(self, comNum):
        self._x = 0.0
        self._y = 0.0
        self._home_x = 0.0
        self._home_y = 0.0
        self._step = 0.1            # mm per jog-button press
        self.rate = 50
        self.reference = None
        self.samples = []
        self._connect(comNum)
        print(f"{type(self).__name__} online")

    def _connect(self, comNum):
        self.ac = ArduinoClient(comNum, 115200)

    def moveUp(self):
        self._y += self._step
        self.ac.commandSend(f"G1 Y{self._y} F{self.rate}")
        print("Move Up ->", self._y)

    def moveDown(self):
        self._y -= self._step
        self.ac.commandSend(f"G1 Y{self._y} F{self.rate}")
        print("Move Down ->", self._y)

    def moveRight(self):
        self._x += self._step
        self.ac.commandSend(f"G1 X{self._x} F{self.rate}")
        print("Move Right ->", self._x)

    def moveLeft(self):
        self._x -= self._step
        self.ac.commandSend(f"G1 X{self._x} F{self.rate}")
        print("Move Left ->", self._x)

    def home(self):
        self.ac.commandSend(f"G1 X0 Y0 F{self.rate}")
        self._x = self._home_x
        self._y = self._home_y
        print("Go Home ->", self._x, self._y)

    def setHome(self):
        self._home_x = self._x
        self._home_y = self._y
        print("Set Home ->", self._home_x, self._home_y)

    def setPosition(self, x_str, y_str):
        self.ac.commandSend(f"G1 X{x_str} Y{y_str} F{self.rate}")
        if x_str.strip():
            self._x = float(x_str)
        if y_str.strip():
            self._y = float(y_str)
        print("Set Position ->", self._x, self._y)

    def storeReference(self):
        self.reference = {'x': self._x, 'y': self._y}
        print("Stored reference:", self.reference)

    def storeSample(self, region):
        sample = {'x': self._x, 'y': self._y, 'region': region}
        self.samples.append(sample)
        print("Stored sample:", sample)

    def clearReference(self):
        self.reference = None
        print("Cleared reference")

    def clearSamples(self):
        self.samples = []
        print("Cleared all samples")

    def getPosition(self):
        return f"X={self._x:.2f}   Y={self._y:.2f}"


class FakeXWing(XWing):
    """Headless XWing: real jog/position logic driving a fake serial client."""

    def __init__(self, comNum="FAKE"):
        super().__init__(comNum)

    def _connect(self, comNum):
        self.ac = _FakeArduinoClient()
