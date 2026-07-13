"""Hyperspectral single-fluorescence scan -- standalone auto_gui launcher.

Run: python single_fluor.py
Scans the reference (optional) then each sample position, sweeping the
monochromator and recording a 4x-averaged digitizer voltage per wavelength
(no gain servo), and writes a CSV. Reference + sample positions are hardcoded
in __main__ (edit as needed). Set sim = 0 for real hardware.
"""
import os
import csv
import time
from datetime import datetime


class SingleFluor():

    def __init__(self, xwing, cornerstone, pmt, digitizer):
        self.xwing = xwing
        self.cornerstone = cornerstone
        self.pmt = pmt
        self.digi = digitizer
        self.plotter = None
        self.gain = 0
        self.pmt.changeGain(self.gain)
        print("SingleFluor Ready")

    def _scanPosition(self, coord, scan_type):
        """Scan one position across the wavelength range (4x averaged voltage)."""
        step_size = (self.cornerstone.endWavelength - self.cornerstone.startWavelength) / self.cornerstone.numSteps
        x, y = coord['x'], coord['y']
        region = coord.get('region', 'REF')

        self.xwing.ac.commandSend(f"G1 X{x} Y{y} F{self.xwing.rate}")
        print(f"\nScanning {scan_type} for Region {region}: X={x}, Y={y}")
        time.sleep(4)

        if self.plotter is not None:
            self.plotter.clear()

        measurements = []
        for j in range(self.cornerstone.numSteps):
            if getattr(self, "_stop", False):
                break

            wavelength = self.cornerstone.startWavelength + j * step_size
            self.cornerstone.mono.goto(wavelength)
            time.sleep(2)

            dataPoint = (self.digi.measure() + self.digi.measure()
                         + self.digi.measure() + self.digi.measure()) / 4

            measurements.append({
                'region': region, 'scan_type': scan_type,
                'x': x, 'y': y, 'wavelength': wavelength,
                'voltage': dataPoint, 'gain': self.gain,
            })

            self.cornerstone.currentWavelength = wavelength
            if self.plotter is not None:
                self.plotter.append(wavelength, dataPoint)

            print(f"  lambda={wavelength:.2f} nm, V={dataPoint:.2f}V, Gain={self.gain:.3f}")

        self.xwing._x = x
        self.xwing._y = y
        return measurements

    def _singleFluor(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = os.path.join("data", timestamp)
        os.makedirs(output_dir, exist_ok=True)
        csv_filename = os.path.join(output_dir, 'fluor_scan.csv')
        print(f"Saving data to: {output_dir}")

        if self.xwing.reference is None:
            print("FYI: No reference")
        if len(self.xwing.samples) == 0:
            print("FYI: No regions")
            return

        self.cornerstone.mono.open_shutter()
        all_data = []

        if self.xwing.reference:
            print("\n" + "=" * 50 + "\nScanning REFERENCE\n" + "=" * 50)
            all_data.extend(self._scanPosition(self.xwing.reference, "reference"))

        print("\n" + "=" * 50 + "\nScanning SAMPLES\n" + "=" * 50)
        for sample in self.xwing.samples:
            if getattr(self, "_stop", False):
                break
            all_data.extend(self._scanPosition(sample, "sample"))

        with open(csv_filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'region', 'scan_type', 'x', 'y', 'wavelength', 'voltage', 'gain'])
            writer.writeheader()
            writer.writerows(all_data)
        print(f"\nSaved fluor data - {len(all_data)} measurements")

        self.cornerstone.mono.close_shutter()
        print(f"Scan complete! Data saved to: {csv_filename}")
        return all_data


if __name__ == "__main__":
    from auto_gui import run_gui, LivePlot

    sim = 1
    if sim:
        from hardware import (FakeXWing as XWing, FakeCornerstone as Cornerstone,
                              FakePMTShield as PMTShield, FakeDigitizer as Digitizer)
        xwing = XWing()
        cornerstone = Cornerstone()
        pmt = PMTShield()
        digi = Digitizer()
    else:
        from hardware import XWing, Cornerstone, PMTShield, Digitizer
        xwing = XWing("COM3")
        cornerstone = Cornerstone()
        pmt = PMTShield("COM4")
        digi = Digitizer()

    # Hardcoded positions -- edit, or jog the XWing window + store buttons instead.
    xwing.reference = {'x': 0.0, 'y': 0.0}
    xwing.samples = [
        {'x': 0.5, 'y': 0.0, 'region': 'A'},
        {'x': 1.0, 'y': 0.0, 'region': 'B'},
    ]

    fluor = SingleFluor(xwing, cornerstone, pmt, digi)
    fluor.plotter = LivePlot(title="SingleFluor (per-position spectrum)",
                             xlabel="wavelength (nm)", ylabel="voltage (V)",
                             mode="append")

    run_gui(
        automation=fluor,
        run=fluor._singleFluor,
        hardware=[xwing, cornerstone, pmt, digi],
        title="Single Fluorescence Scan",
    )
