"""
Single Fluorophore Spectral Scan Automation
=============================================
Run directly:  python singlefluor_automation.py

Three control panels open automatically:
  - XWing Stage      (jog, go-to, store reference/samples)
  - Cornerstone      (wavelength, shutter, scan range)
  - PMT Gain Shield  (gain control)

Use the panels to configure positions and wavelength range,
then click Run in the node card below to start the scan.
"""

import os
import csv
import time
from datetime import datetime

from autogui import core, run
from cores import XWing, Cornerstone, PMTShield, LivePlot
from hardware_controllers import NIScopeClient

# ── Hardware ─────────────────────────────────────────────────────────────────

xwing       = XWing("COM3")
cornerstone = Cornerstone()
pmt         = PMTShield()

# ── Scan logic ───────────────────────────────────────────────────────────────

class _SingleFluorScan:
    def __init__(self, xwing, cornerstone, pmt):
        self.xwing       = xwing
        self.cornerstone = cornerstone
        self.pmt         = pmt
        self.digi        = NIScopeClient()
        self.gain        = 0
        self._cancel     = False
        self._plotter    = None
        self.pmt.changeGain(self.gain)
        print("Single Fluor Automation Online")

    def cancel(self):
        self._cancel = True

    def _scan_position(self, coord, scan_type):
        step_size = (
            (self.cornerstone.endWavelength - self.cornerstone.startWavelength)
            / self.cornerstone.numSteps
        )
        x, y   = coord['x'], coord['y']
        region = coord.get('region', 'REF')

        self.xwing.ac.commandSend(f"G1 X{x} Y{y} F{self.xwing.rate}")
        print(f"\nScanning {scan_type} for Region {region}: X={x}, Y={y}")
        time.sleep(4)

        self._plotter.resetPlot()
        measurements = []

        for j in range(self.cornerstone.numSteps):
            if self._cancel:
                break

            wavelength = self.cornerstone.startWavelength + j * step_size
            self.cornerstone.mono.goto(wavelength)
            time.sleep(2)

            # 4-measurement average, no gain adjustment
            d1, d2, d3, d4 = (self.digi.record() for _ in range(4))
            dataPoint = (d1 + d2 + d3 + d4) / 4

            measurements.append({
                'region':     region,
                'scan_type':  scan_type,
                'x':          x,
                'y':          y,
                'wavelength': wavelength,
                'voltage':    dataPoint,
                'gain':       self.gain,
            })

            self.cornerstone.currentWavelength = wavelength
            self.cornerstone.waveChanged.emit()
            self._plotter.updatePlot(wavelength, dataPoint)

            print(f"  λ={wavelength:.2f} nm, V={dataPoint:.2f}V, Gain={self.gain:.3f}")

        # Sync position display after each position
        self.xwing._x = x
        self.xwing._y = y
        self.xwing.xChanged.emit()
        self.xwing.yChanged.emit()

        return measurements

    def run(self):
        self._cancel  = False
        self._plotter = self._plotter or LivePlot()

        timestamp  = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = os.path.join("data", timestamp)
        os.makedirs(output_dir, exist_ok=True)
        csv_path   = os.path.join(output_dir, 'fluor_scan.csv')

        print(f"Saving data to: {output_dir}")

        if not self.xwing.samples:
            print("No sample positions stored — aborting.")
            return
        if self.xwing.reference is None:
            print("FYI: No reference position stored.")

        self.cornerstone.mono.open_shutter()
        all_data = []

        if self.xwing.reference:
            print(f"\n{'='*50}\nScanning REFERENCE\n{'='*50}")
            all_data.extend(self._scan_position(self.xwing.reference, "reference"))

        print(f"\n{'='*50}\nScanning SAMPLES\n{'='*50}")
        for sample in self.xwing.samples:
            if self._cancel:
                break
            all_data.extend(self._scan_position(sample, "sample"))

        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(
                f, fieldnames=['region', 'scan_type', 'x', 'y', 'wavelength', 'voltage', 'gain']
            )
            writer.writeheader()
            writer.writerows(all_data)

        self.cornerstone.mono.close_shutter()
        print(f"\nSaved {len(all_data)} measurements → {csv_path}")
        print("Scan complete!" if not self._cancel else "Scan cancelled.")


_scan = _SingleFluorScan(xwing, cornerstone, pmt)


# ── Node card ─────────────────────────────────────────────────────────────────

@core(stop=_scan.cancel)
def run_single_fluor():
    """
    Single fluorophore spectral scan (4-measurement average, no auto gain).

    Before running:
      1. Optionally store a reference position via the XWing panel.
      2. Store one or more sample positions via the XWing panel.
      3. Set the wavelength range in the Cornerstone panel.
    """
    _scan.run()


if __name__ == "__main__":
    run(title="Single Fluor Automation")
