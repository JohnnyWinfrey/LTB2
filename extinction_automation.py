"""
Hyperspectral Extinction Automation
====================================
Run directly:  python extinction_automation.py

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

class _ExtinctionScan:
    TARGET_VOLTAGE     = 8.0
    VOLTAGE_TOLERANCE  = 0.5
    VOLTAGE_MIN        = 4
    VOLTAGE_MAX        = 12
    MAX_GAIN_ADJUSTMENTS = 30

    def __init__(self, xwing, cornerstone, pmt):
        self.xwing       = xwing
        self.cornerstone = cornerstone
        self.pmt         = pmt
        self.digi        = NIScopeClient()
        self.gain        = 0
        self.gain_map    = {}
        self._cancel     = False
        self._plotter    = None
        self.pmt.changeGain(self.gain)
        print("Extinction Automation Online")

    def cancel(self):
        self._cancel = True

    def _scan_position(self, coord, scan_type, adjust_gain=True):
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
            time.sleep(1)

            if adjust_gain:
                dataPoint = self.digi.record()
                print(f"Initial measurement for {region} {wavelength} = {dataPoint}")
                adjustment_count = 0

                if dataPoint > self.VOLTAGE_MAX or (dataPoint < self.VOLTAGE_MIN and self.gain < 1):
                    while (
                        abs(dataPoint - self.TARGET_VOLTAGE) > self.VOLTAGE_TOLERANCE
                        and adjustment_count < self.MAX_GAIN_ADJUSTMENTS
                        and self.gain < 1
                    ):
                        voltage_error = dataPoint - self.TARGET_VOLTAGE
                        step = 0.1 if abs(voltage_error) > 2 else (0.01 if abs(voltage_error) > 1 else 0.001)

                        if voltage_error > 0:
                            self.gain -= step * 0.7
                            print(f"    Voltage {dataPoint:.2f}V (target {self.TARGET_VOLTAGE:.1f}V), reducing gain to {self.gain:.3f}")
                        elif self.gain + step < 1:
                            self.gain += step
                            print(f"    Voltage {dataPoint:.2f}V (target {self.TARGET_VOLTAGE:.1f}V), increasing gain to {self.gain:.3f}")
                        else:
                            print("too much sauce")
                            break

                        self.pmt.changeGain(self.gain)
                        time.sleep(1.5)
                        dataPoint = self.digi.record()
                        adjustment_count += 1

                self.gain_map[round(wavelength, 2)] = self.gain

            else:
                key = round(wavelength, 2)
                if key in self.gain_map:
                    self.gain = self.gain_map[key]
                    self.pmt.changeGain(self.gain)
                    time.sleep(1.5)
                else:
                    print(f"No reference gain found for Region {region}, λ={wavelength:.2f} nm")
                dataPoint = self.digi.record()

            measurements.append({
                'region':    region,
                'scan_type': scan_type,
                'x':         x,
                'y':         y,
                'wavelength': wavelength,
                'voltage':   dataPoint,
                'gain':      self.gain,
            })

            # Keep core position displays in sync
            self.xwing._x = x
            self.xwing._y = y
            self.xwing.xChanged.emit()
            self.xwing.yChanged.emit()
            self.cornerstone.currentWavelength = wavelength
            self.cornerstone.waveChanged.emit()
            self._plotter.updatePlot(wavelength, dataPoint)

            print(f"  λ={wavelength:.2f} nm, V={dataPoint:.2f}V, Gain={self.gain:.3f}")

        return measurements

    def run(self):
        self._cancel  = False
        self.gain_map = {}
        self._plotter = self._plotter or LivePlot()

        timestamp  = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = os.path.join("data", timestamp)
        os.makedirs(output_dir, exist_ok=True)
        csv_path   = os.path.join(output_dir, 'extinction_scan.csv')

        print(f"Saving data to: {output_dir}")

        if self.xwing.reference is None:
            print("No reference position stored — aborting.")
            return
        if not self.xwing.samples:
            print("Warning: no sample positions stored.")

        self.cornerstone.mono.open_shutter()
        all_data = []

        print(f"\n{'='*50}\nScanning REFERENCE\n{'='*50}")
        all_data.extend(self._scan_position(self.xwing.reference, "reference", adjust_gain=True))

        print(f"\n{'='*50}\nScanning SAMPLES\n{'='*50}")
        for sample in self.xwing.samples:
            if self._cancel:
                break
            all_data.extend(self._scan_position(sample, "sample", adjust_gain=False))

        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(
                f, fieldnames=['region', 'scan_type', 'x', 'y', 'wavelength', 'voltage', 'gain']
            )
            writer.writeheader()
            writer.writerows(all_data)

        self.cornerstone.mono.close_shutter()
        print(f"\nSaved {len(all_data)} measurements → {csv_path}")
        print("Scan complete!" if not self._cancel else "Scan cancelled.")


_scan = _ExtinctionScan(xwing, cornerstone, pmt)


# ── Node card ─────────────────────────────────────────────────────────────────

@core(stop=_scan.cancel)
def run_extinction():
    """
    Hyperspectral extinction scan with auto gain adjustment.

    Before running:
      1. Store a reference position via the XWing panel.
      2. Store one or more sample positions via the XWing panel.
      3. Set the wavelength range in the Cornerstone panel.
    """
    _scan.run()


if __name__ == "__main__":
    run(title="Extinction Automation")
