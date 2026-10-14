"""Pieces shared by several device modules."""
import time
from pathlib import Path

# Vendor DLLs / helper executables. Anchored to the repo, not the working
# directory, so scripts can be launched from anywhere.
HELPERS_DIR = Path(__file__).resolve().parent.parent / "helpers"


class ArduinoClient:
    """Line-based serial link to an Arduino (DeathStar, XWing, PMTShield)."""

    def __init__(self, serPort, baud_rate):
        import serial

        self.devPort = serial.Serial(serPort, baud_rate)
        time.sleep(2)

    def serialRead(self):
        return self.devPort.readline().decode('utf-8').strip()

    def commandSend(self, command):
        self.devPort.write(command.encode() + b'\n')
        time.sleep(0.5)
        return self.serialRead()

    def serialClose(self):
        self.devPort.close()
        return 0


class _FakeArduinoClient:
    """No-op stand-in for ArduinoClient."""

    def __init__(self, *args, **kwargs):
        pass

    def commandSend(self, command):
        return ""

    def serialRead(self):
        return ""

    def serialClose(self):
        return 0
