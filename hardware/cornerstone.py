"""Cornerstone -- monochromator, driven through helpers/cornerstone_helper.exe."""
import os
import subprocess

from ._shared import HELPERS_DIR


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
    """Monochromator. QML-free port of cores.Cornerstone (CornerstoneClient)."""

    def __init__(self, exe_path=HELPERS_DIR / "cornerstone_helper.exe"):
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


class _FakeMono:
    """No-op stand-in for CornerstoneClient; remembers the last goto target."""

    def __init__(self, *args, **kwargs):
        self._pos = 0.0

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

    def close(self):
        pass


class FakeCornerstone(Cornerstone):
    """Headless monochromator: real logic driving a fake helper process."""

    def __init__(self, exe_path="FAKE"):
        super().__init__(exe_path)

    def _connect(self, exe_path):
        self.mono = _FakeMono()
