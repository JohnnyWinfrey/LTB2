"""SpectreCore -- Ocean-style spectrometer (seabreeze)."""
import time

import numpy as np


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
    a background thread.
    """

    def __init__(self):
        self.intTime = 500000
        self.background = 0.0
        self.scansToAvg = 1
        self.bgCounts = 0.0

        # Scan metadata
        self.scanX = 0.0
        self.scanY = 0.0
        self.side = "X"
        self.region = "A"
        self.sampleName = "sample"

        self._connect()
        self.spec.integration_time_micros(self.intTime)

    def _connect(self):
        """Open the device; sets self.spec, intMin/intMax and maxIntensity."""
        from seabreeze.spectrometers import Spectrometer, list_devices
        self.spec = Spectrometer.from_first_available()
        feat = list_devices()[0].features['spectrometer'][0]
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
        self._storeBackground(self.spec.intensities(correct_dark_counts=True))

    def _storeBackground(self, background):
        self.background = background
        sorted_bg = sorted(self.background, reverse=True)
        self._checkOversaturation(sorted_bg[0])
        top_10_count = max(1, len(sorted_bg) // 10)
        self.bgCounts = sum(sorted_bg[:top_10_count]) / top_10_count
        print(f"Background updated! Avg top 10%: {self.bgCounts:.2f}")

    def takeSpectrum(self):
        wavelengths = self.spec.wavelengths()
        intensities = 0
        for _ in range(self.scansToAvg):
            intensities = intensities + (self.spec.intensities(correct_dark_counts=True)
                                         - self.background)
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


class _FakeSpectrometer:
    """No-op stand-in for seabreeze's Spectrometer.

    Frames are two Gaussian peaks on a gentle baseline, scaled by integration
    time, plus noise. dark() is the same frame without the peaks.
    """

    INT_MIN = 1000
    INT_MAX = 10_000_000
    MAX_INTENSITY = 65535

    def __init__(self, num_pixels=1044):
        # Synthetic wavelength axis (nm): Ocean-style visible/NIR range.
        self._wavelengths = np.linspace(398.0, 1100.0, num_pixels)
        self._intTime = 500000

    def integration_time_micros(self, value):
        self._intTime = value

    def wavelengths(self):
        return self._wavelengths

    def _scale(self):
        """Brightness scale: longer integration time -> more counts."""
        return self.MAX_INTENSITY * (self._intTime / self.INT_MAX)

    def _noise(self, scale):
        return np.random.normal(0.0, 0.01 * scale + 5.0, size=self._wavelengths.shape)

    def intensities(self, correct_dark_counts=False):
        wl = self._wavelengths

        def gauss(center, width, amp):
            return amp * np.exp(-0.5 * ((wl - center) / width) ** 2)

        # Two emission peaks (488 nm Ar line + a broader 630 nm) on a baseline.
        signal = gauss(488.0, 8.0, 0.6) + gauss(630.0, 14.0, 0.35)
        baseline = 0.02 + 0.01 * (wl - wl.min()) / (wl.max() - wl.min())
        scale = self._scale()
        frame = (signal + baseline) * scale + self._noise(scale)
        return np.clip(frame, 0, self.MAX_INTENSITY)

    def dark(self):
        scale = self._scale()
        return np.clip(0.02 * scale + self._noise(scale), 0, self.MAX_INTENSITY)


class FakeSpectreCore(SpectreCore):
    """Headless spectrometer: real logic reading synthetic spectra."""

    def _connect(self):
        self.spec = _FakeSpectrometer()
        self.intMin = _FakeSpectrometer.INT_MIN
        self.intMax = _FakeSpectrometer.INT_MAX
        self.maxIntensity = _FakeSpectrometer.MAX_INTENSITY
        print("FakeSpectreCore online (synthetic spectra)")

    def takeBackground(self):
        # The real background is taken with the light blocked; a dark frame
        # keeps the synthetic peaks visible after subtraction.
        self._storeBackground(self.spec.dark())

