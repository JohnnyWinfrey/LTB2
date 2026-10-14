"""TCSPC spectral scan -- standalone auto_gui launcher.

Run: python -m automations.tcspc.spectral [--sim]
Sweeps the monochromator across its wavelength range at a single fixed point
and records a TimeHarp 260 decay histogram at each step, then writes one HDF5
file. The count rate is shown live as a number throughout (between steps too,
while the monochromator moves and settles). --sim uses the fake
monochromator and board.

The TH260 is driven straight through th260lib64.dll (hardware.TH260) with
the board settings below; the bin width can also be changed with setBinWidth.
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


class TCSPCSpectral(TH260RateView):

    def __init__(self, cornerstone, th260):
        self.cornerstone = cornerstone
        self.th260 = th260
        self.sampleName = "sample"
        self.region = "A"
        self.settleTime = 1.0     # seconds to let the monochromator settle
        self.avgStepTime = []
        self._initRateView()      # rate display, driver lock, setBinWidth
        print("TCSPCSpectral Ready")

    def setSampleName(self, value_str):
        self.sampleName = str(value_str)
        print(f"Sample name: {self.sampleName}")

    def setRegion(self, value_str):
        self.region = str(value_str)
        print(f"Region: {self.region}")

    def setSettleTime(self, value_str):
        self.settleTime = max(0.0, float(value_str))
        print(f"Settle time: {self.settleTime} s")

    def _spectralScan(self):
        cs = self.cornerstone
        th = self.th260
        bins = self._resolveBins()   # once, so every wavelength has the same length
        if bins is None:
            return []
        step_size = (cs.endWavelength - cs.startWavelength) / cs.numSteps
        print(f"Sweeping {cs.startWavelength}-{cs.endWavelength} nm in "
              f"{cs.numSteps} steps, {th.tacq} ms per point, "
              f"{bins} bins of {th.resolutionPs:.0f} ps")

        cs.mono.open_shutter()
        cs.shutterState = "Open"
        all_data = []
        self.avgStepTime = []
        self._acquiring = True    # locks the bin width for the whole scan

        try:
            for j in range(cs.numSteps):
                if getattr(self, "_stop", False):
                    break
                t0 = time.time()

                wavelength = cs.startWavelength + j * step_size
                cs.mono.goto(wavelength)
                time.sleep(self.settleTime)
                cs.currentWavelength = wavelength

                result = self._measure(th.tacq, bins)
                counts = result["counts"]
                th.lastCounts = counts
                all_data.append({
                    'wavelength': wavelength,
                    'counts': counts,
                    'sync_rate': result["sync_rate"],
                    'count_rate': result["count_rate"],
                })

                self.avgStepTime.append(time.time() - t0)
                if hasattr(self, "progress"):
                    self.progress(j, cs.numSteps, np.average(self.avgStepTime))

                print(f"  lambda={wavelength:.2f} nm, {int(counts[th.channel].sum())} counts, "
                      f"rate={th.lastCountRate:.2e}/s")
        finally:
            self._acquiring = False
            cs.mono.close_shutter()
            cs.shutterState = "Closed"

        # Guard: a Stop before the first point would otherwise write a broken file.
        if all_data:
            saveTCSPCHDF5(all_data, name=self.sampleName, region=self.region,
                          resolution_ps=th.resolutionPs,
                          tacq_ms=th.tacq, channel=th.channel)
        else:
            print("No data collected -- nothing saved")

        print(f"Scan complete! {len(all_data)} wavelengths")
        return all_data


TITLE = "Spectral TCSPC"


def main(sim=False):
    from auto_gui import run_gui
    from . import experiment

    cornerstone = experiment.cornerstone(sim)
    th260 = experiment.th260(TH260_SETTINGS, BIN_WIDTH_PS, sim)
    scan = TCSPCSpectral(cornerstone, th260)
    scan.rateDisplay = makeRateDisplay()
    scan.setBinWidth(BIN_WIDTH_PS)
    scan.startLiveView()

    run_gui(
        automation=scan,
        run=scan._spectralScan,
        hardware=[cornerstone, th260, scan],
        title=TITLE,
    )
    scan.stopLiveView()


if __name__ == "__main__":
    import sys
    main(sim="--sim" in sys.argv)
