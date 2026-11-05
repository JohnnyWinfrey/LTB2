"""PMT gain shield."""
from ._shared import ArduinoClient, _FakeArduinoClient


class PMTShield:
    """PMT gain shield. QML-free port of cores.PMTShield (ArduinoClient)."""

    def __init__(self, comNum="COM4"):
        self._gain = 0.0
        self._connect(comNum)
        print(f"{type(self).__name__} online")

    def _connect(self, comNum):
        self.pmt = ArduinoClient(comNum, 115200)

    def changeGain(self, desiredGain):
        self._gain = float(desiredGain)
        self.pmt.commandSend(f"{self._gain:.3f}")
        print(f"Gain set to: {self._gain:.3f}")

    def getGain(self):
        return f"{self._gain:.3f}"


class FakePMTShield(PMTShield):
    """Headless PMT gain shield: real logic driving a fake serial client."""

    def __init__(self, comNum="FAKE"):
        super().__init__(comNum)

    def _connect(self, comNum):
        self.pmt = _FakeArduinoClient()
