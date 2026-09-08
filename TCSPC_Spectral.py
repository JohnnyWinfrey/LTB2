"""TCSPC spectral scan -- standalone auto_gui launcher.

Run: python TCSPC_Spectral.py
Sweeps the monochromator across its wavelength range at a single fixed point
and records a TimeHarp 260 decay histogram at each step, then writes one HDF5
file. Set sim = 0 for real hardware, sim = 2 to drive the native stub helper
built by helpers/build.sh.
"""
import time
from datetime import datetime

import numpy as np

from th260_helpers import saveTCSPCHDF5


class TCSPCSpectral():

    def __init__(self, cornerstone, th260):
        self.cornerstone = cornerstone
        self.th260 = th260
        self.plotter = None
        self.sampleName = "sample"
        self.region = "A"
        self.settleTime = 1.0     # seconds to let the monochromator settle
        self.avgStepTime = []
        print("TCSPCSpectral Ready")

    def setSampleName(self, value_str):
        self.sampleName = str(value_str)
        print(f"Sample name: {self.sampleName}")

    def setRegion(self, value_str):
        self.region = str(value_str)
        print(f"Region: {self.region}")

    def _spectralScan(self):
        cs = self.cornerstone
        step_size = (cs.endWavelength - cs.startWavelength) / cs.numSteps
        print(f"Sweeping {cs.startWavelength}-{cs.endWavelength} nm in "
              f"{cs.numSteps} steps, {self.th260.tacq} ms per point")

        cs.mono.open_shutter()
        cs.shutterState = "Open"
        all_data = []
        self.avgStepTime = []

        try:
            for j in range(cs.numSteps):
                if getattr(self, "_stop", False):
                    break
                t0 = time.time()

                wavelength = cs.startWavelength + j * step_size
                cs.mono.goto(wavelength)
                time.sleep(self.settleTime)
                cs.currentWavelength = wavelength

                result = self.th260._acquire()
                counts = result["counts"]
                all_data.append({
                    'wavelength': wavelength,
                    'counts': counts,
                    'sync_rate': result["sync_rate"],
                    'count_rate': result["count_rate"],
                })

                trace = counts[self.th260.channel]
                if self.plotter is not None:
                    self.plotter.setData(self.th260._timeAxisNs(len(trace)), trace)

                self.avgStepTime.append(time.time() - t0)
                if hasattr(self, "progress"):
                    self.progress(j, cs.numSteps, np.average(self.avgStepTime))

                print(f"  lambda={wavelength:.2f} nm, {int(trace.sum())} counts, "
                      f"rate={self.th260.lastCountRate}/s")
        finally:
            cs.mono.close_shutter()
            cs.shutterState = "Closed"

        # Guard: a Stop before the first point would otherwise write a broken file.
        if all_data:
            saveTCSPCHDF5(all_data, name=self.sampleName, region=self.region,
                          resolution_ps=self.th260.resolutionPs,
                          tacq_ms=self.th260.tacq, channel=self.th260.channel)
        else:
            print("No data collected -- nothing saved")

        print(f"Scan complete! {len(all_data)} wavelengths")
        return all_data


if __name__ == "__main__":
    from auto_gui import run_gui, LivePlot

    sim = 1
    if sim == 1:
        from hardware import FakeCornerstone as Cornerstone, FakeTH260 as TH260
        cornerstone = Cornerstone()
        th260 = TH260()
    elif sim == 2:
        # Real client + real helper code, fake board (helpers/build.sh stub).
        from hardware import FakeCornerstone, TH260
        cornerstone = FakeCornerstone()
        th260 = TH260("/tmp/th260_helper_stub")
    else:
        from hardware import Cornerstone, TH260
        cornerstone = Cornerstone()
        th260 = TH260()

    scan = TCSPCSpectral(cornerstone, th260)
    scan.plotter = LivePlot(title="TCSPC decay (current wavelength)",
                            xlabel="time (ns)", ylabel="counts",
                            mode="replace")

    run_gui(
        automation=scan,
        run=scan._spectralScan,
        hardware=[cornerstone, th260],
        title="TCSPC Spectral Scan",
    )
