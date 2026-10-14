"""Shared TCSPC pieces -- the TH260 counterpart to slim_helpers.

HDF5 saving, plus TH260RateView: the live count-rate window and bin-width
setter used by both TCSPC_Live and TCSPC_Spectral. Qt is imported lazily so
this module stays importable without it.
"""
import math
import os
import threading
import time
from datetime import datetime

import numpy as np
import h5py

from automations import DATA_DIR


def saveTCSPCHDF5(all_data, scanType="tcspcSpectral", name="sample", region="A",
                  resolution_ps=0.0, tacq_ms=0, channel=0):
    """
    Save a TCSPC wavelength sweep to HDF5.

    all_data : list of per-wavelength dicts as built by TCSPC_Spectral, each
               holding 'wavelength', 'counts' (channels x bins), 'sync_rate'
               and 'count_rate'.

    Layout mirrors slim_helpers.saveHDF5: data/<name>_<timestamp>/ with the
    metadata as file attributes. `counts` is the selected channel; every
    channel is kept in `counts_all` when the board has more than one.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    name = name or "sample"

    output_dir = os.path.join(DATA_DIR, f"{name}_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    h5_path = os.path.join(output_dir, f"{name}_Region{region}_{scanType}.h5")

    wavelengths = np.array([d["wavelength"] for d in all_data], dtype=np.float64)
    counts_all = np.array([d["counts"] for d in all_data], dtype=np.uint32)  # (N, CH, bins)
    nBins = counts_all.shape[2]
    time_ns = np.arange(nBins) * (resolution_ps / 1000.0)

    with h5py.File(h5_path, "w") as f:
        f.attrs["region"] = region
        f.attrs["name"] = name
        f.attrs["timestamp"] = timestamp
        f.attrs["resolution_ps"] = resolution_ps
        f.attrs["bin_width_ps"] = resolution_ps
        f.attrs["tacq_ms"] = tacq_ms
        f.attrs["channel"] = channel

        f.create_dataset("wavelength", data=wavelengths)
        f.create_dataset("time_ns", data=time_ns)
        f.create_dataset("sync_rate", data=np.array([d["sync_rate"] for d in all_data]))
        f.create_dataset(
            "count_rate",
            data=np.array([d["count_rate"][channel] if channel < len(d["count_rate"]) else 0
                           for d in all_data]),
        )

        f.create_dataset("counts", data=counts_all[:, channel, :],
                         compression="gzip", compression_opts=4)
        if counts_all.shape[1] > 1:
            f.create_dataset("counts_all", data=counts_all,
                             compression="gzip", compression_opts=4)

    print(f"Saved {len(all_data)} spectra -> {h5_path}")
    return h5_path


def saveTCSPCRunsHDF5(runs, scanType="tcspcRuns", name="sample", region="A",
                      resolution_ps=0.0, channel=0):
    """
    Save several separately acquired histograms to one HDF5 file.

    runs : list of dicts as kept by TCSPC_Live.addRun, each holding 'label',
           'counts' (channels x bins), 'tacq_ms', 'sync_rate' and 'count_rate'.
           Every run must have the same number of bins.

    Same folder/attribute layout as saveTCSPCHDF5, but indexed by run instead of
    wavelength, and with a per-run `label` and `tacq_ms` dataset.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    name = name or "sample"

    output_dir = os.path.join(DATA_DIR, f"{name}_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    h5_path = os.path.join(output_dir, f"{name}_Region{region}_{scanType}.h5")

    counts_all = np.array([r["counts"] for r in runs], dtype=np.uint32)  # (N, CH, bins)
    nBins = counts_all.shape[2]
    time_ns = np.arange(nBins) * (resolution_ps / 1000.0)

    with h5py.File(h5_path, "w") as f:
        f.attrs["region"] = region
        f.attrs["name"] = name
        f.attrs["timestamp"] = timestamp
        f.attrs["resolution_ps"] = resolution_ps
        f.attrs["bin_width_ps"] = resolution_ps
        f.attrs["channel"] = channel
        f.attrs["num_runs"] = len(runs)

        f.create_dataset("label", data=[r["label"] for r in runs],
                         dtype=h5py.string_dtype())
        f.create_dataset("time_ns", data=time_ns)
        f.create_dataset("tacq_ms", data=np.array([r["tacq_ms"] for r in runs]))
        f.create_dataset("sync_rate", data=np.array([r["sync_rate"] for r in runs]))
        f.create_dataset(
            "count_rate",
            data=np.array([r["count_rate"][channel] if channel < len(r["count_rate"]) else 0
                           for r in runs]),
        )

        f.create_dataset("counts", data=counts_all[:, channel, :],
                         compression="gzip", compression_opts=4)
        if counts_all.shape[1] > 1:
            f.create_dataset("counts_all", data=counts_all,
                             compression="gzip", compression_opts=4)

    print(f"Saved {len(runs)} runs -> {h5_path}")
    return h5_path


def makeRateDisplay(title="TH260 count rate"):
    """A small window showing the count rate as a big number (e.g. 2.53e+04).

    Same hand-off as auto_gui.LivePlot: setRate() may be called from any thread;
    it emits a signal and the labels are updated on the GUI thread.
    """
    import sys
    from PySide6.QtCore import QObject, Qt, Signal
    from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

    QApplication.instance() or QApplication(sys.argv)

    class RateDisplay(QObject):
        _rateReady = Signal(int, int, int)

        def __init__(self):
            super().__init__()
            self._win = QWidget()
            self._win.setWindowTitle(title)
            lay = QVBoxLayout(self._win)
            self._head = QLabel("count rate (ch 0)")
            self._head.setAlignment(Qt.AlignCenter)
            self._rate = QLabel("--")
            self._rate.setAlignment(Qt.AlignCenter)
            self._rate.setStyleSheet("font-size: 48px; font-weight: bold; "
                                     "font-family: monospace;")
            self._sync = QLabel("sync: --")
            self._sync.setAlignment(Qt.AlignCenter)
            self._sync.setStyleSheet("font-family: monospace;")
            for w in (self._head, self._rate, self._sync):
                lay.addWidget(w)
            self._win.resize(360, 160)
            self._win.show()
            self._rateReady.connect(self._on_rate)

        def setRate(self, rate, sync, channel):
            self._rateReady.emit(int(rate), int(sync), int(channel))

        def _on_rate(self, rate, sync, channel):
            self._head.setText(f"count rate (ch {channel})")
            self._rate.setText(f"{rate:.2e} /s")
            self._sync.setText(f"sync: {sync:.2e} /s")

    return RateDisplay()


class TH260RateView:
    """Mixin for TCSPC automations: live count rate + bin-width setter.

    The host sets self.th260 and calls _initRateView() in __init__. Its own
    acquisitions go through _measure(), which shares the driver lock with the
    rate poller and pushes each measurement's rates to the display. While the
    host sets self._acquiring, the bin width can't be changed.

    startLiveView / stopLiveView / setBinWidth become buttons in auto_gui when
    the automation is passed in the hardware list.
    """

    def _initRateView(self):
        self.rateDisplay = None   # makeRateDisplay() window, set by the launcher
        # One board, one driver: only one call into it at a time.
        self._lock = threading.Lock()
        self._acquiring = False

    def setBinWidth(self, value_ps):
        if self._acquiring:
            print("Can't change the bin width during an acquisition")
            return
        with self._lock:
            actual = self.th260.th.setBinWidth(float(value_ps))
        self.th260.resolutionPs = actual
        if self.th260.bins:
            print(f"Bin width set to {actual:.0f} ps "
                  f"({self.th260.bins} bins = {self.th260.bins * actual / 1000:.0f} ns window)")
        else:
            print(f"Bin width set to {actual:.0f} ps (bins: auto, one sync period)")

    def _pushRate(self, result):
        rates = result["count_rate"]
        ch = self.th260.channel
        rate = rates[ch] if ch < len(rates) else 0
        self.th260.lastCountRate = rate
        self.th260.lastSyncRate = result["sync_rate"]
        if self.rateDisplay is not None:
            self.rateDisplay.setRate(rate, result["sync_rate"], ch)

    BIN_MARGIN = 1.05             # auto bins: one sync period + 5% (rate wobble, offsets)

    def _resolveBins(self):
        """Bin count for the next acquisition / scan, or None if there's no sync.

        A fixed th260.bins is used as is; otherwise the histogram is sized to
        one sync period (photons can't arrive later than that). Called once at
        the start so every histogram in a scan has the same length.
        """
        th = self.th260
        with self._lock:
            sync, rates = th.th.rates()
        self._pushRate({"sync_rate": sync, "count_rate": rates})
        if sync <= 0:
            print("Turn on the laser, silly...")
            return None
        if th.bins:
            return th.bins

        divider = getattr(th.th, "settings", {}).get("sync_divider", 1)
        period_ps = divider / sync * 1e12
        bins = math.ceil(period_ps * self.BIN_MARGIN / th.resolutionPs)
        bins = min(bins, th.histLen)
        print(f"Auto bins: sync {sync:.2e}/s -> {period_ps / 1000:.1f} ns period "
              f"-> {bins} bins of {th.resolutionPs:.0f} ps")
        return bins

    def _measure(self, tacq_ms, bins):
        """One acquisition under the driver lock; also updates the rate display."""
        with self._lock:
            result = self.th260.th.measure(tacq_ms, bins)
        if result["overflow"]:
            print("WARNING: TH260 histogram overflowed")
        self._pushRate(result)
        return result

    def startLiveView(self):
        if getattr(self, "_live_running", False):
            print("Live view already running")
            return
        from auto_gui import _Worker
        self._live_running = True

        def _loop():
            # Polls between the host's acquisitions: the lock makes this wait
            # out a running measure(), whose own rates are pushed meanwhile.
            while self._live_running:
                try:
                    with self._lock:
                        sync, rates = self.th260.th.rates()
                    self._pushRate({"sync_rate": sync, "count_rate": rates})
                except Exception as e:
                    print("Live view error:", e)
                    break
                time.sleep(0.1)  # the board refreshes its rates every 100 ms

        self._live_worker = _Worker(_loop)
        self._live_worker.start()
        print("Count-rate live view started")

    def stopLiveView(self):
        self._live_running = False
        print("Count-rate live view stopping...")
