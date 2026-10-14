"""TCSPC live view -- standalone auto_gui launcher.

Run: python -m automations.tcspc.live [--sim]
No monochromator: the TimeHarp 260 count rate is shown live as a number, and
Start acquires one decay histogram, redrawing it as it builds up. addRun keeps
the last histogram and overplots it; saveRuns writes every kept run to one HDF5
file. --sim uses the fake board.

Real hardware is driven straight through th260lib64.dll (hardware.TH260).
The board settings are fixed for this configuration and hard-coded below; only
the bin width can be changed, with setBinWidth. The histogram is summed from
chunks of chunkMs until tacq of photon time has been collected, redrawing after
each chunk.
"""
import numpy as np

from .helpers import TH260RateView, makeRateDisplay, saveTCSPCRunsHDF5


# ─────────────────────────────────────────────────────────────────────────
# TH260 board settings -- constant for this configuration (TimeHarp 260 P).
# Matches the TimeHarp control panel. Bin width is the only runtime setting.
# ─────────────────────────────────────────────────────────────────────────
TH260_SETTINGS = {
    "sync_divider": 1,             # "None"
    "sync_cfd_zero_cross": -10,    # mV
    "sync_cfd_level": -50,         # mV
    "sync_offset_ps": 0,
    "input_cfd_zero_cross": -10,   # mV, all channels
    "input_cfd_level": -100,       # mV, all channels
    "input_offset_ps": -25000,     # all channels
    "offset_ns": 0,                # acquisition offset
    "stop_overflow": 0,            # "Stop Of." unchecked
    "stop_count": 4294967295,      # "Stop at"
    # Only used on a nanosecond (260 N) board.
    "sync_trigger_edge": 0,
    "sync_trigger_level": -50,
    "input_trigger_edge": 0,
    "input_trigger_level": -50,
}
BIN_WIDTH_PS = 200                 # starting bin width; change with setBinWidth


def _makeHistogramPlot(**kwargs):
    """A LivePlot (live trace, replace mode) that can also hold kept runs.

    Built in a function so `import TCSPC_Live` stays free of Qt, like the
    other launchers. keep()/clearKept() follow the LivePlot hand-off: they emit
    a signal and the curves are drawn on the GUI thread.
    """
    import pyqtgraph as pg
    from PySide6.QtCore import Signal
    from auto_gui import LivePlot

    class HistogramPlot(LivePlot):
        _keepReady = Signal(object, object, str)

        def __init__(self, **kw):
            super().__init__(mode="replace", **kw)
            self._kept = []
            self._legend = self._win.addLegend()
            self._keepReady.connect(self._on_keep)

        def keep(self, xs, ys, label):
            self._keepReady.emit(list(xs), list(ys), label)

        def clearKept(self):
            self._keepReady.emit(None, None, "")

        def _on_keep(self, x, y, label):
            if x is None:
                for curve in self._kept:
                    self._win.removeItem(curve)
                self._legend.clear()
                self._kept = []
            else:
                pen = pg.mkPen(pg.intColor(len(self._kept), hues=9), width=1.5)
                self._kept.append(self._win.plot(x, y, pen=pen, name=label))

    return HistogramPlot(**kwargs)


class TCSPCLive(TH260RateView):

    def __init__(self, th260):
        self.th260 = th260
        self.plotter = None       # histogram: live trace + kept runs
        self.sampleName = "sample"
        self.region = "A"
        self.chunkMs = 500        # histogram redraw interval, ms of acquisition
        self._initRateView()      # rate display, driver lock, setBinWidth
        self._lastRun = None      # last finished acquisition, until added
        self.runs = []            # kept runs, all saved together by saveRuns
        print("TCSPCLive Ready")

    def setSampleName(self, value_str):
        self.sampleName = str(value_str)
        print(f"Sample name: {self.sampleName}")

    def setRegion(self, value_str):
        self.region = str(value_str)
        print(f"Region: {self.region}")

    def setChunk(self, value_str):
        self.chunkMs = max(100, int(float(value_str)))
        print(f"Histogram redraw every {self.chunkMs} ms of acquisition")

    # --- histogram acquisition (Start/Stop panel) ---
    def _acquireHistogram(self):
        th = self.th260
        bins = self._resolveBins()
        if bins is None:
            return None
        nChunks = max(1, int(np.ceil(th.tacq / self.chunkMs)))
        print(f"Acquiring {th.tacq} ms in {nChunks} chunks of <= {self.chunkMs} ms, "
              f"{bins} bins of {th.resolutionPs:.0f} ps")

        total = None
        syncRates, countRates = [], []
        collectedMs = 0
        self._acquiring = True
        try:
            for j in range(nChunks):
                if getattr(self, "_stop", False):
                    break
                chunk = min(self.chunkMs, th.tacq - collectedMs)
                result = self._measure(chunk, bins)
                counts = result["counts"].astype(np.uint64)
                total = counts if total is None else total + counts
                collectedMs += chunk
                syncRates.append(result["sync_rate"])
                countRates.append(result["count_rate"])

                trace = total[th.channel]
                if self.plotter is not None:
                    self.plotter.setData(th._timeAxisNs(len(trace)), trace)
                if hasattr(self, "progress"):
                    self.progress(j, nChunks, chunk / 1000.0)
        finally:
            self._acquiring = False

        if total is None:
            print("No data collected")
            return None

        th.lastCounts = total
        trace = total[th.channel]
        print(f"Histogram done: {collectedMs} ms, {int(trace.sum())} counts "
              f"on channel {th.channel} -- addRun to keep it")

        self._lastRun = {
            'counts': np.minimum(total, np.iinfo(np.uint32).max).astype(np.uint32),
            'resolution_ps': th.resolutionPs,
            'tacq_ms': collectedMs,
            'sync_rate': int(np.mean(syncRates)),
            'count_rate': [int(v) for v in np.mean(countRates, axis=0)],
        }
        return self._lastRun

    # --- kept runs (buttons in this object's window) ---
    def addRun(self, label=""):
        run = self._lastRun
        if run is None:
            print("No new histogram to add -- press Start first")
            return
        if self.runs:
            first = self.runs[0]
            if (run["counts"].shape != first["counts"].shape
                    or run["resolution_ps"] != first["resolution_ps"]):
                print(f"Run is {run['counts'].shape[1]} bins of {run['resolution_ps']:.0f} ps "
                      f"but the kept runs are {first['counts'].shape[1]} bins of "
                      f"{first['resolution_ps']:.0f} ps -- saveRuns/clearRuns first")
                return
        run["label"] = str(label) or f"run {len(self.runs) + 1}"
        self.runs.append(run)
        self._lastRun = None      # so one acquisition can't be added twice

        trace = run["counts"][self.th260.channel]
        if self.plotter is not None:
            self.plotter.clear()  # the kept curve replaces the live trace
            t_ns = np.arange(len(trace)) * (run["resolution_ps"] / 1000.0)
            self.plotter.keep(t_ns, trace, run["label"])
        print(f"Added '{run['label']}' ({len(self.runs)} runs kept)")

    def clearRuns(self):
        self.runs = []
        if self.plotter is not None:
            self.plotter.clearKept()
        print("Kept runs cleared")

    def saveRuns(self):
        if not self.runs:
            print("No runs kept -- nothing saved")
            return
        saveTCSPCRunsHDF5(self.runs, name=self.sampleName, region=self.region,
                          resolution_ps=self.runs[0]["resolution_ps"],
                          channel=self.th260.channel)


TITLE = "TCSPC Live"


def main(sim=False):
    from auto_gui import run_gui
    from . import experiment

    th260 = experiment.th260(TH260_SETTINGS, BIN_WIDTH_PS, sim)
    live = TCSPCLive(th260)
    live.rateDisplay = makeRateDisplay()
    live.plotter = _makeHistogramPlot(title="TCSPC histogram",
                                      xlabel="time (ns)", ylabel="counts")
    live.setBinWidth(BIN_WIDTH_PS)
    live.startLiveView()

    run_gui(
        automation=live,
        run=live._acquireHistogram,
        hardware=[th260, live],
        title=TITLE,
    )
    live.stopLiveView()


if __name__ == "__main__":
    import sys
    main(sim="--sim" in sys.argv)
