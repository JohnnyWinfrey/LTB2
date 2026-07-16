import random
import numpy as np

class PowerMeter:
    """Real Thorlabs power meter over pyvisa/USB."""

    def __init__(self):
        # Handles opened once via open(), closed once via close().
        self.rm    = None
        self.instr = None

    def open(self, wl):
        """Open the resource manager + instrument and apply one-time config."""
        # Import lazily so this module still imports on a machine without
        # pyvisa (the fake path never touches it).
        import pyvisa

        # Opens a resource manager
        self.rm = pyvisa.ResourceManager()

        # Opens the connection to the device. self.instr is the handle.
        # !!! The serial number (P00...) and PID (0x8078) must match the
        #     connected device. Check with the Windows Device Manager.
        self.instr = self.rm.open_resource(
            'USB0::0x1313::0x8078::P0011973::INSTR'
        )

        # print the device information
        # print(self.instr.query("SYST:SENS:IDN?"))

        # turn on auto-ranging
        self.instr.write("SENS:RANGE:AUTO ON")

        self.instr.write(f"SENS:CORR:WAV {wl}")
        # set units to Watts
        self.instr.write("SENS:POW:UNIT W")
        # set averaging to 1000 points (COUN is the count subcommand)
        self.instr.write("SENS:AVER:COUN 1000")

        print("Power meter connected")

    def measure(self):
        """Read a single power value from the already-open meter."""
        # query() returns the raw text response, e.g. "1.234567E-06\n";
        # cast to float so downstream arrays are numeric.
        power = float(self.instr.query("MEAS:POW?"))
        print(f"Measured power = {power}")
        return power

    def close(self):
        """Close the instrument and resource manager if they are open."""
        if self.instr is not None:
            try:
                self.instr.close()
            except Exception:
                pass
            self.instr = None

        if self.rm is not None:
            try:
                self.rm.close()
            except Exception:
                pass
            self.rm = None

        print("Power meter closed")


class FakePowerMeter:
    """Drop-in replacement for PowerMeter that returns synthetic readings."""

    def open(self):
        print("Fake power meter connected")

    def measure(self):
        power = random.uniform(1e-6, 1e-3)
        print(f"Measured power = {power}")
        return power

    def close(self):
        print("Fake power meter closed")


class FakeDeathStar:
    """Fake DeathStar rotation stage: no serial / Qt, just tracks angles.

    Mirrors the full public surface of the real hardware.DeathStar (setPosition,
    home, resetHome, zHome, setRate, getAngles) so SLIM scans -- which call
    homeAll() -> resetHome/zHome -- run headless and its auto_gui window matches.
    """

    def __init__(self, comNum=None, ZAxis=False, id="Fake"):
        self._thetaP = 0
        self._thetaW = 0
        self._z = 0.0
        self.rate = 10000
        self.ZAxis = ZAxis
        self.name = id
        print(self.name, " FakeDeathStar online")

    def setPosition(self, p_str, w_str, z=""):
        if z:
            self._z = float(z)
        if p_str.strip():
            self._thetaP = float(p_str)
        if w_str.strip():
            self._thetaW = float(w_str)
        print(self.name, " setting Position ->", self._thetaP, self._thetaW, z)

    def home(self):
        self._thetaP = 0
        self._thetaW = 0
        print(self.name, " Go Home ->", self._thetaP, self._thetaW)

    def resetHome(self):
        self._thetaP = 0
        self._thetaW = 0
        print(self.name, " Set Zero")

    def zHome(self):
        if self.ZAxis:
            self._z = 0.0
            print(self.name, " Z Go Home ->", self._z)

    def setRate(self, rate_str):
        self.rate = float(rate_str)
        print(self.name, " rate ->", self.rate)

    def getAngles(self):
        return f"P={self._thetaP % 360:.2f}   W={self._thetaW % 360:.2f}"


class DeathStar:
    """Rotating polarizer + waveplate stage. QML-free port of cores.DeathStar.

    "Clockwise"/"counter-clockwise" are as seen looking toward the incoming
    light. Wraps an ArduinoClient speaking GRBL-style G-code.
    """

    def __init__(self, comNum, ZAxis=False, id="First"):
        from hardware_controllers import ArduinoClient
        self._thetaP = 0            # polarizer angle
        self._thetaW = 0            # waveplate angle
        self._z = 0.0
        self.rate = 10000
        self.ZAxis = ZAxis
        self.name = id
        self.ac = ArduinoClient(comNum, 115200)
        # Zero the controller, nudge to prove motion, then return to zero.
        self.ac.commandSend("G10 L20 P1 X0 Y0")
        self.ac.commandSend(f"G1 X15 Y15 F{self.rate}")
        self.ac.commandSend(f"G1 X0 Y0 F{self.rate}")
        print(self.name, " DeathStar online")

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


class XWing:
    """XY sample stage. QML-free port of cores.XWing (ArduinoClient / G-code)."""

    def __init__(self, comNum):
        from hardware_controllers import ArduinoClient
        self._x = 0.0
        self._y = 0.0
        self._home_x = 0.0
        self._home_y = 0.0
        self._step = 0.1            # mm per jog-button press
        self.rate = 50
        self.reference = None
        self.samples = []
        self.ac = ArduinoClient(comNum, 115200)
        print("XWing online")

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


class _SpectrometerLiveView:
    """Mixin: a standalone live spectrum view (start/stop buttons for auto_gui).

    Spins a background worker that repeatedly calls the host's takeSpectrum()
    and pushes each frame to a LivePlot (replace mode: counts vs. wavelength).
    Independent of any automation -- meant for watching the spectrometer while
    aligning optics, straight from its own device window.

    The host class only needs to provide takeSpectrum() -> (wavelengths, counts).
    All state is stored under `_live_*` names so auto_gui ignores it; the two
    public methods below become the Start/Stop live-view buttons.
    """

    def startLiveView(self):
        if getattr(self, "_live_running", False):
            print("Live view already running")
            return
        # Lazy import so `import hardware` stays free of Qt/pyqtgraph.
        import time
        from auto_gui import LivePlot, _Worker

        # LivePlot must be built on the GUI thread; a button click is on it.
        if getattr(self, "_live_plot", None) is None:
            self._live_plot = LivePlot(
                title="Spectrometer live view",
                xlabel="wavelength (nm)", ylabel="counts", mode="replace",
            )
        self._live_running = True

        def _loop():
            while getattr(self, "_live_running", False):
                try:
                    wavelengths, counts = self.takeSpectrum()
                    self._live_plot.setData(wavelengths, counts)  # thread-safe
                except Exception as e:
                    print("Live view error:", e)
                    break
                time.sleep(0.05)  # breathe between frames (real reads block on int. time)

        self._live_worker = _Worker(_loop)
        self._live_worker.start()
        print("Live view started")

    def stopLiveView(self):
        self._live_running = False
        print("Live view stopping...")


class SpectreCore(_SpectrometerLiveView):
    """Ocean-style spectrometer. QML-free port of cores.SpectreCore (seabreeze).

    Live view is provided by the _SpectrometerLiveView mixin: startLiveView() /
    stopLiveView() open a pyqtgraph window that streams takeSpectrum() frames on
    a background thread -- the auto_gui-friendly replacement for the old
    cores.SpectreCore.openLiveView.
    """

    def __init__(self):
        from seabreeze.spectrometers import Spectrometer, list_devices
        self.intTime = 500000
        self.spec = Spectrometer.from_first_available()
        self.spec.integration_time_micros(self.intTime)
        self.specInfo = list_devices()[0]
        self.background = 0.0
        self.scansToAvg = 1
        self._bgCounts = 0.0

        # Scan metadata
        self.scanX = 0.0
        self.scanY = 0.0
        self.side = "X"
        self.region = "A"
        self.sampleName = "sample"

        feat = self.specInfo.features['spectrometer'][0]
        self.intMin, self.intMax = feat.get_integration_time_micros_limits()
        self.maxIntensity = feat.get_maximum_intensity()
        print("Spectrometer Found:", self.spec)

    def setIntegration(self, value):
        try:
            val = int(value)
        except ValueError:
            return
        if val < self.intMin:
            print(f"Integration time {val} below minimum ({self.intMin}), clamping")
            val = self.intMin
        elif val > self.intMax:
            print(f"Integration time {val} above maximum ({self.intMax}), clamping")
            val = self.intMax
        self.intTime = val
        self.spec.integration_time_micros(self.intTime)
        print(f"Set Integration Time -> {self.intTime}")

    def setScansToAvg(self, value):
        try:
            self.scansToAvg = max(1, int(value))
        except ValueError:
            return
        print(f"Scans to average -> {self.scansToAvg}")

    def takeBackground(self):
        # The spectrometer streams continuously; take a throwaway read first so
        # the stored background reflects the current integration time.
        self.spec.intensities()
        self.spec.wavelengths()
        self.spec.wavelengths()
        self.background = self.spec.intensities(correct_dark_counts=True)
        sorted_bg = sorted(self.background, reverse=True)
        self._checkOversaturation(sorted_bg[0])
        top_10_count = max(1, len(sorted_bg) // 10)
        self._bgCounts = sum(sorted_bg[:top_10_count]) / top_10_count
        print(f"Background updated! Avg top 10%: {self._bgCounts:.2f}")

    def takeSpectrum(self):
        wavelengths = self.spec.wavelengths()
        intensities = 0
        for _ in range(self.scansToAvg):
            intensities += self.spec.intensities(correct_dark_counts=True) - self.background
        intensities = intensities / self.scansToAvg
        return wavelengths, intensities

    def setScanX(self, value):
        try:
            self.scanX = float(value)
        except ValueError:
            return
        print(f"Scan X -> {self.scanX}")

    def setScanY(self, value):
        try:
            self.scanY = float(value)
        except ValueError:
            return
        print(f"Scan Y -> {self.scanY}")

    def setSide(self, value):
        self.side = value
        print(f"Side -> {self.side}")

    def setRegion(self, value):
        self.region = value
        print(f"Region -> {self.region}")

    def setSampleName(self, value):
        self.sampleName = value
        print(f"Sample Name -> {self.sampleName}")

    def getBackgroundCounts(self):
        return f"{self.bgCounts:.2f}"

    def _checkOversaturation(self, maxMI):
        if maxMI >= (self.maxIntensity - 1):
            print("WARNING: MEASUREMENT OVERSATURATED")
            return True
        return False


class FakeSpectreCore(_SpectrometerLiveView):
    """Synthetic spectrometer: drop-in for SpectreCore with no seabreeze/hardware.

    Exposes the exact same public methods as SpectreCore (including the
    startLiveView/stopLiveView from _SpectrometerLiveView), so auto_gui builds an
    identical window. takeSpectrum() returns a synthetic frame -- two Gaussian
    peaks on a gentle baseline, scaled by integration time, plus noise -- minus
    whatever background was captured. Lets the whole hyperspectral pipeline and
    its auto_gui window be exercised on a laptop with nothing plugged in.
    """

    def __init__(self, num_pixels=1044):
        self.intTime = 500000
        self.background = 0.0
        self.scansToAvg = 1
        self.bgCounts = 0.0

        # Scan metadata (same fields SpectreCore carries)
        self.scanX = 0.0
        self.scanY = 0.0
        self.side = "X"
        self.region = "A"
        self.sampleName = "sample"

        # Fake spectrometer limits
        self.intMin = 1000
        self.intMax = 10_000_000
        self.maxIntensity = 65535

        # Synthetic wavelength axis (nm): Ocean-style visible/NIR range.
        self._wavelengths = np.linspace(398.0, 1100.0, num_pixels)
        print("FakeSpectreCore online (synthetic spectra)")

    # --- synthetic-frame helpers --------------------------------------------
    def _scale(self):
        """Brightness scale: longer integration time -> more counts."""
        return self.maxIntensity * (self.intTime / self.intMax)

    def _noise(self, scale, shape):
        return np.random.normal(0.0, 0.01 * scale + 5.0, size=shape)

    def _frame(self):
        """One synthetic intensity frame at the current integration time."""
        wl = self._wavelengths

        def gauss(center, width, amp):
            return amp * np.exp(-0.5 * ((wl - center) / width) ** 2)

        # Two emission peaks (488 nm Ar line + a broader 630 nm) on a baseline.
        signal = gauss(488.0, 8.0, 0.6) + gauss(630.0, 14.0, 0.35)
        baseline = 0.02 + 0.01 * (wl - wl.min()) / (wl.max() - wl.min())
        scale = self._scale()
        frame = (signal + baseline) * scale + self._noise(scale, wl.shape)
        return np.clip(frame, 0, self.maxIntensity)

    # --- identical surface to SpectreCore -----------------------------------
    def setIntegration(self, value):
        try:
            val = int(value)
        except ValueError:
            return
        if val < self.intMin:
            print(f"Integration time {val} below minimum ({self.intMin}), clamping")
            val = self.intMin
        elif val > self.intMax:
            print(f"Integration time {val} above maximum ({self.intMax}), clamping")
            val = self.intMax
        self.intTime = val
        print(f"Set Integration Time -> {self.intTime}")

    def setScansToAvg(self, value):
        try:
            self.scansToAvg = max(1, int(value))
        except ValueError:
            return
        print(f"Scans to average -> {self.scansToAvg}")

    def takeBackground(self):
        # A dark frame: baseline + noise, no peaks.
        wl = self._wavelengths
        scale = self._scale()
        self.background = np.clip(
            0.02 * scale + self._noise(scale, wl.shape), 0, self.maxIntensity
        )
        sorted_bg = sorted(self.background, reverse=True)
        self._checkOversaturation(sorted_bg[0])
        top_10_count = max(1, len(sorted_bg) // 10)
        self.bgCounts = sum(sorted_bg[:top_10_count]) / top_10_count
        print(f"Background updated! Avg top 10%: {self.bgCounts:.2f}")

    def takeSpectrum(self):
        wavelengths = self._wavelengths
        intensities = 0
        for _ in range(self.scansToAvg):
            intensities = intensities + (self._frame() - self.background)
        intensities = intensities / self.scansToAvg
        return wavelengths, intensities

    def setScanX(self, value):
        try:
            self.scanX = float(value)
        except ValueError:
            return
        print(f"Scan X -> {self.scanX}")

    def setScanY(self, value):
        try:
            self.scanY = float(value)
        except ValueError:
            return
        print(f"Scan Y -> {self.scanY}")

    def setSide(self, value):
        self.side = value
        print(f"Side -> {self.side}")

    def setRegion(self, value):
        self.region = value
        print(f"Region -> {self.region}")

    def setSampleName(self, value):
        self.sampleName = value
        print(f"Sample Name -> {self.sampleName}")

    def getBackgroundCounts(self):
        return f"{self.bgCounts:.2f}"

    def _checkOversaturation(self, maxMI):
        if maxMI >= (self.maxIntensity - 1):
            print("WARNING: MEASUREMENT OVERSATURATED")
            return True
        return False


class Cornerstone:
    """Monochromator. QML-free port of cores.Cornerstone (CornerstoneClient)."""

    def __init__(self, exe_path="helpers/cornerstone_helper.exe"):
        from hardware_controllers import CornerstoneClient
        self.mono = CornerstoneClient(exe_path)
        self.mono.open()
        self.targetWavelength = 630
        self.shutterState = "Closed"
        self.startWavelength = 600
        self.endWavelength = 800
        self.numSteps = 50
        self.currentGrating = 3
        self.currentWavelength = 0.0
        print("Cornerstone online")

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


class PMTShield:
    """PMT gain shield. QML-free port of cores.PMTShield (ArduinoClient)."""

    def __init__(self, comNum="COM4"):
        from hardware_controllers import ArduinoClient
        self._gain = 0.0
        self.pmt = ArduinoClient(comNum, 115200)
        print("PMT Gain Shield Online")

    def changeGain(self, desiredGain):
        self._gain = float(desiredGain)
        self.pmt.commandSend(f"{self._gain:.3f}")
        print(f"Gain set to: {self._gain:.3f}")

    def getGain(self):
        return f"{self._gain:.3f}"


class Digitizer:
    """NI digitizer: one averaged-voltage reading. QML-free port of the
    NIScopeClient use in the automation clusters.

    `measure()` is named so auto_gui shows it as a read-out button + value
    label; automations also call it directly (replacing the clusters' old
    self.digi.record()).
    """

    def __init__(self):
        from hardware_controllers import NIScopeClient
        self.scope = NIScopeClient()
        print("Digitizer online")

    def measure(self):
        voltage = self.scope.record()
        print(f"Digitizer measured {voltage} V")
        return voltage


# ──────────────────────────────────────────────────────────────────────────
# Fake devices for the QML-free ports (headless / sim mode)
# ──────────────────────────────────────────────────────────────────────────
# Each fake subclasses its real plain class and only overrides __init__ to swap
# the real transport for a no-op stand-in. Every control method is inherited
# unchanged, so auto_gui builds an identical window and the ported scripts run
# with `sim = 1` on a laptop with nothing plugged in.

class _FakeArduinoClient:
    """No-op stand-in for ArduinoClient (used by FakeXWing / FakePMTShield)."""

    def __init__(self, *args, **kwargs):
        pass

    def commandSend(self, command):
        return ""

    def serialRead(self):
        return ""

    def serialClose(self):
        return 0


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


class FakeXWing(XWing):
    """Headless XWing: real jog/position logic driving a fake serial client."""

    def __init__(self, comNum="FAKE"):
        self._x = 0.0
        self._y = 0.0
        self._home_x = 0.0
        self._home_y = 0.0
        self._step = 0.1
        self.rate = 50
        self.reference = None
        self.samples = []
        self.ac = _FakeArduinoClient()
        print("FakeXWing online")


class FakeCornerstone(Cornerstone):
    """Headless monochromator: real logic driving a fake helper process."""

    def __init__(self, exe_path="FAKE"):
        self.mono = _FakeMono()
        self.targetWavelength = 630
        self.shutterState = "Closed"
        self.startWavelength = 600
        self.endWavelength = 800
        self.numSteps = 50
        self.currentGrating = 3
        self.currentWavelength = 0.0
        print("FakeCornerstone online")


class FakePMTShield(PMTShield):
    """Headless PMT gain shield: real logic driving a fake serial client."""

    def __init__(self, comNum="FAKE"):
        self._gain = 0.0
        self.pmt = _FakeArduinoClient()
        print("FakePMTShield online")


class FakeDigitizer(Digitizer):
    """Synthetic digitizer: returns a random voltage in a plausible range."""

    def __init__(self):
        self.scope = None
        print("FakeDigitizer online")

    def measure(self):
        voltage = random.uniform(0.0, 10.0)
        print(f"Digitizer measured {voltage:.4f} V")
        return voltage
