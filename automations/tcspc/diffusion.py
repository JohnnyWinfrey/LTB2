"""TCSPC stage scan -- standalone auto_gui launcher.

Run: python -m automations.tcspc.stage [--sim]
Sweeps the KDC101 DC servo stage across its travel and records a TimeHarp 260
decay histogram at each position, then writes one HDF5 file. The count rate
is shown live as a number throughout (between steps too, while the stage
moves and settles). --sim uses the fake stage and board.

The TH260 is driven straight through th260lib64.dll (hardware.TH260) with
the board settings below; the bin width can also be changed with setBinWidth.
Positions are millimeters -- set the serial in the "KDC101 stage" window,
press connect, press home, then set start mm, end mm, and the number of
steps. gotoMm waits for the stage to arrive before each measurement.
"""
import time

import numpy as np

from .helpers import TH260RateView, makeRateDisplay, saveTCSPCHDF5


# ─────────────────────────────────────────────────────────────────────────
# TH260 board settings for this configuration (TimeHarp 260 P).
# ─────────────────────────────────────────────────────────────────────────
TH260_SETTINGS = {
    "sync_divider": 1,             # "None"
    "sync_cfd_zero_cross": -10,    # mV
    "sync_cfd_level": -50,         # mV
    "sync_offset_ps": 0,
    "input_cfd_zero_cross": -10,   # mV, all channels
    "input_cfd_level": [-30, -100], # mV, per channel (ch 1, ch 2)
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


class TCSPCStage(TH260RateView):

    def __init__(self, stage, th260):
        self.stage = stage
        self.th260 = th260
        self.sampleName = "sample"
        self.region = "A"
        self.settleTime = 0.2    # seconds to let the stage settle after arrival
        self.avgStepTime = []
        self._initRateView()      # rate display, driver lock, setBinWidth
        print("TCSPCStage Ready")

    def setSampleName(self, value_str):
        self.sampleName = str(value_str)
        print(f"Sample name: {self.sampleName}")

    def setRegion(self, value_str):
        self.region = str(value_str)
        print(f"Region: {self.region}")

    def setSettleTime(self, value_str):
        self.settleTime = max(0.0, float(value_str))
        print(f"Settle time: {self.settleTime} s")

    def _moveTo(self, mm):
        """One scan position: move the stage to mm (waits for arrival)."""
        self.stage.gotoMm(mm)

    def _stageScan(self):
        st = self.stage
        th = self.th260
        bins = self._resolveBins()   # once, so every position has the same length
        if bins is None:
            return []
        n = max(1, int(st.numSteps))
        step_size = (st.endMm - st.startMm) / n
        print(f"Sweeping {st.startMm:.3f}-{st.endMm:.3f} mm in {n} steps, "
              f"{th.tacq} ms per point, {bins} bins of {th.resolutionPs:.0f} ps")

        all_data = []
        self.avgStepTime = []
        self._acquiring = True    # locks the bin width for the whole scan

        try:
            for j in range(n + 1):
                if getattr(self, "_stop", False):
                    break
                t0 = time.time()

                mm = st.startMm + j * step_size
                self._moveTo(mm)
                time.sleep(self.settleTime)

                result = self._measure(th.tacq, bins)
                counts = result["counts"]
                th.lastCounts = counts
                all_data.append({
                    'position': mm,
                    'counts': counts,
                    'sync_rate': result["sync_rate"],
                    'count_rate': result["count_rate"],
                })

                self.avgStepTime.append(time.time() - t0)
                if hasattr(self, "progress"):
                    self.progress(j, n, np.average(self.avgStepTime))

                print(f"  x={mm:.3f} mm, {int(counts[th.channel].sum())} counts, "
                      f"rate={th.lastCountRate:.2e}/s")
        finally:
            self._acquiring = False

        # Guard: a Stop before the first point would otherwise write a broken file.
        if all_data:
            lo, hi = st.client.travel_mm()
            saveTCSPCHDF5(all_data, scanType="tcspcStage", name=self.sampleName,
                          region=self.region, resolution_ps=th.resolutionPs,
                          tacq_ms=th.tacq, channel=th.channel,
                          coordinate="position",
                          extra_attrs={"stage": "KDC101",
                                       "serial": st.serial,
                                       "position_units": "mm",
                                       "travel_min_mm": lo,
                                       "travel_max_mm": hi})
        else:
            print("No data collected -- nothing saved")

        print(f"Scan complete! {len(all_data)} positions")
        return all_data


TITLE = "Diffusion"


def main(sim=False):
    from auto_gui import run_gui
    from . import experiment

    stage = experiment.kdc101(sim)
    th260 = experiment.th260(TH260_SETTINGS, BIN_WIDTH_PS, sim)
    scan = TCSPCStage(stage, th260)
    scan.rateDisplay = makeRateDisplay()
    scan.setBinWidth(BIN_WIDTH_PS)
    scan.startLiveView()

    run_gui(
        automation=scan,
        run=scan._stageScan,
        hardware=[stage, th260, scan],
        title=TITLE,
    )
    scan.stopLiveView()


if __name__ == "__main__":
    import sys
    main(sim="--sim" in sys.argv)
