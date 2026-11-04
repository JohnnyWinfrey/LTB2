"""TCSPC SPAD -- standalone auto_gui launcher.

Run: python -m automations.tcspc.spad [--sim]
No monochromator: the TimeHarp 260 count rate is shown live as a number, and
Start acquires one decay histogram, redrawing it as it builds up. addRun keeps
the last histogram and overplots it; saveRuns writes every kept run to one HDF5
file. --sim uses the fake board and stage.

The KPZ101 piezo stage is included as hardware: queue points with addPoint
(vx, vy in DAC codes, 0..32767) and Start moves to each one in turn, lets it
settle, and acquires a histogram that is kept automatically, labeled with its
position. With no points queued, Start does not move the stage and behaves as
before (one histogram, addRun to keep it).

Real hardware is driven straight through th260lib64.dll (hardware.TH260) and
the Kinesis Piezo DLL (hardware.kpz101). The board settings are fixed for this
configuration and hard-coded below; only the bin width can be changed, with
setBinWidth. The histogram is summed from chunks of chunkMs until tacq of
photon time has been collected, redrawing after each chunk.
"""
import time

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

    def __init__(self, stage, th260):
        self.stage = stage
        self.th260 = th260
        self.plotter = None       # histogram: live trace + kept runs
        self.sampleName = "sample"
        self.region = "A"
        self.chunkMs = 500        # histogram redraw interval, ms of acquisition
        self.settleTime = 0.5     # s to let the piezo stop ringing before each shot
        self.points = []          # queued (vx, vy) DAC codes; empty = don't move
        self._initRateView()      # rate display, driver lock, setBinWidth
        self._lastRun = None      # last finished acquisition, until added
        self.runs = []            # kept runs, all saved together by saveRuns
        self._chunkProgress = None
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

    def setSettleTime(self, value_str):
        self.settleTime = max(0.0, float(value_str))
        print(f"Settle time: {self.settleTime} s")

    # --- point queue (KPZ101): Start visits each point, one histogram each ---
    def addPoint(self, vx, vy):
        self.points.append((self._clampDac(vx), self._clampDac(vy)))
        print(f"Added point ({self.points[-1][0]}, {self.points[-1][1]}) "
              f"-- {len(self.points)} queued")

    def clearPoints(self):
        self.points = []
        print("Points cleared -- Start will not move the stage")

    def getPoints(self):
        if not self.points:
            return "(empty -- Start will not move the stage)"
        return ", ".join(f"({x}, {y})" for x, y in self.points)

    def _clampDac(self, value):
        return int(round(min(max(float(value), 0.0), self.stage.DAC_MAX)))

    # --- histogram acquisition (Start/Stop panel) ---
    def _acquireOne(self, bins):
        """One full histogram, summed from chunks of chunkMs; the live trace
        redraws after each chunk. Returns the run dict, or None if Stop came
        before any chunk finished."""
        th = self.th260
        time.sleep(th.sleeptime)
        nChunks = max(1, int(np.ceil(th.tacq / self.chunkMs)))
        print(f"Acquiring {th.tacq} ms in {nChunks} chunks of <= {self.chunkMs} ms, "
              f"{bins} bins of {th.resolutionPs:.0f} ps")

        total = None
        syncRates, countRates = [], []
        collectedMs = 0
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
            if self._chunkProgress is not None:
                self._chunkProgress(j, nChunks, chunk / 1000.0)

        if total is None:
            return None
        th.lastCounts = total
        return {
            'counts': np.minimum(total, np.iinfo(np.uint32).max).astype(np.uint32),
            'resolution_ps': th.resolutionPs,
            'tacq_ms': collectedMs,
            'sync_rate': int(np.mean(syncRates)),
            'count_rate': [int(v) for v in np.mean(countRates, axis=0)],
        }

    def _acquireHistogram(self):
        """Start: with no points queued, the stage doesn't move and this is
        the usual single histogram (addRun keeps it); with points queued, it
        visits each in turn, settling, then shooting -- every point's
        histogram is kept automatically."""
        th = self.th260
        bins = self._resolveBins()
        if bins is None:
            return None
        points = list(self.points)
        nBefore = len(self.runs)
        self._acquiring = True
        try:
            if not points:
                self._chunkProgress = getattr(self, "progress", None)
                run = self._acquireOne(bins)
                if run is None:
                    print("No data collected")
                    return None
                trace = run["counts"][th.channel]
                print(f"Histogram done: {run['tacq_ms']} ms, {int(trace.sum())} counts "
                      f"on channel {th.channel} -- addRun to keep it")
                self._lastRun = run
                return self._lastRun

            if self.runs:
                first = self.runs[0]
                if (first["counts"].shape[1] != bins
                        or first["resolution_ps"] != th.resolutionPs):
                    print(f"Kept runs are {first['counts'].shape[1]} bins of "
                          f"{first['resolution_ps']:.0f} ps but this scan uses "
                          f"{bins} bins of {th.resolutionPs:.0f} ps -- "
                          f"saveRuns/clearRuns first")
                    return None

            self._chunkProgress = None
            print(f"Visiting {len(points)} points, {th.tacq} ms per point, "
                  f"{self.settleTime:.1f} s settle after each move")
            stepTimes = []
            for j, (vx, vy) in enumerate(points):
                if getattr(self, "_stop", False):
                    break
                t0 = time.time()
                self.stage.goto(vx, vy)
                time.sleep(self.settleTime)

                run = self._acquireOne(bins)
                if run is None:
                    break
                run["vx"], run["vy"] = vx, vy
                run["label"] = f"P{j + 1} ({vx}, {vy})"
                self.runs.append(run)
                self._plotKept(run)

                stepTimes.append(time.time() - t0)
                if hasattr(self, "progress"):
                    self.progress(j, len(points) - 1, float(np.average(stepTimes)))
                print(f"  P{j + 1} ({vx}, {vy}): {int(run['counts'][th.channel].sum())} counts")
        finally:
            self._acquiring = False
            self._chunkProgress = None

        print(f"Point scan complete: {len(self.runs) - nBefore}/{len(points)} points, "
              f"{len(self.runs)} runs kept")
        return self.runs

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
        self._plotKept(run)
        print(f"Added '{run['label']}' ({len(self.runs)} runs kept)")

    def _plotKept(self, run):
        """Draw a kept run on the plot -- the kept curve replaces the live trace."""
        if self.plotter is None:
            return
        trace = run["counts"][self.th260.channel]
        self.plotter.clear()
        t_ns = np.arange(len(trace)) * (run["resolution_ps"] / 1000.0)
        self.plotter.keep(t_ns, trace, run["label"])

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


TITLE = "TCSPC SPAD"


def main(sim=False):
    from auto_gui import run_gui
    from . import experiment

    stage = experiment.stage(sim)
    th260 = experiment.th260(TH260_SETTINGS, BIN_WIDTH_PS, sim)
    live = TCSPCLive(stage, th260)
    live.rateDisplay = makeRateDisplay()
    live.plotter = _makeHistogramPlot(title="TCSPC histogram",
                                      xlabel="time (ns)", ylabel="counts")
    live.setBinWidth(BIN_WIDTH_PS)
    live.startLiveView()

    run_gui(
        automation=live,
        run=live._acquireHistogram,
        hardware=[stage, th260, live],
        title=TITLE,
    )
    live.stopLiveView()


if __name__ == "__main__":
    import sys
    main(sim="--sim" in sys.argv)
