"""Hyperspectral extinction scan -- standalone auto_gui launcher.

Run: python extinction.py
Scans the reference position once (servoing PMT gain to a target voltage at
each wavelength), then every sample position with those locked gains, and writes
a CSV. Reference + sample positions are hardcoded in __main__ (edit as needed);
alternatively jog the XWing window and use its store buttons before Start.
Set sim = 0 (and real COM ports / helper exe) for real hardware.
"""
import os
import csv
import time
from datetime import datetime


class Extinction():

    def __init__(self, xwing, cornerstone, pmt, digitizer):
        self.xwing = xwing
        self.cornerstone = cornerstone
        self.pmt = pmt
        self.digi = digitizer
        self.plotter = None
        self.gain = 0
        self.pmt.changeGain(self.gain)
        self.gain_map = {}
        print("Extinction Automation Online")

    def _scanPosition(self, coord, scan_type, adjust_gain=True):
        """Scan one position across the wavelength range.

        adjust_gain=True servos the PMT gain to TARGET_VOLTAGE and records the
        gain per wavelength; False re-uses the locked gains from the reference.
        Returns a list of measurement dicts.
        """
        TARGET_VOLTAGE = 8.0
        VOLTAGE_TOLERANCE = 0.5
        VOLTAGE_MIN = 4
        VOLTAGE_MAX = 12
        MAX_GAIN_ADJUSTMENTS = 30

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
            time.sleep(1)

            if adjust_gain:
                dataPoint = self.digi.measure()
                print(f"Inital measurement for {region} {wavelength} = {dataPoint}")
                adjustment_count = 0

                if dataPoint > VOLTAGE_MAX or (dataPoint < VOLTAGE_MIN and self.gain < 1):
                    while abs(dataPoint - TARGET_VOLTAGE) > VOLTAGE_TOLERANCE and (adjustment_count < MAX_GAIN_ADJUSTMENTS and self.gain < 1):
                        voltage_error = dataPoint - TARGET_VOLTAGE

                        if abs(voltage_error) > 2:
                            step = 0.1
                        elif abs(voltage_error) > 1:
                            step = 0.01
                        else:
                            step = 0.001

                        if voltage_error > 0:
                            self.gain -= step * 0.7
                            print(f"    Voltage {dataPoint:.2f}V (target {TARGET_VOLTAGE:.1f}V), reducing gain to {self.gain:.3f}")
                        else:
                            if (self.gain + step < 1):
                                self.gain += step
                                print(f"    Voltage {dataPoint:.2f}V (target {TARGET_VOLTAGE:.1f}V), increasing gain to {self.gain:.3f}")
                            else:
                                print("too much sauce")
                                break

                        self.pmt.changeGain(self.gain)
                        time.sleep(1.5)
                        dataPoint = self.digi.measure()
                        adjustment_count += 1

                key = round(wavelength, 2)
                self.gain_map[key] = self.gain
            else:
                key = round(wavelength, 2)
                if key in self.gain_map:
                    self.gain = self.gain_map[key]
                    self.pmt.changeGain(self.gain)
                    time.sleep(1.5)
                else:
                    print(f"No reference gain found for Region {region}, lambda={wavelength:.2f} nm")
                dataPoint = self.digi.measure()

            measurements.append({
                'region': region, 'scan_type': scan_type,
                'x': x, 'y': y, 'wavelength': wavelength,
                'voltage': dataPoint, 'gain': self.gain,
            })

            self.xwing._x = x
            self.xwing._y = y
            self.cornerstone.currentWavelength = wavelength

            if self.plotter is not None:
                self.plotter.append(wavelength, dataPoint)

            print(f"  lambda={wavelength:.2f} nm, V={dataPoint:.2f}V, Gain={self.gain:.3f}")

        return measurements

    def _extinction(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = os.path.join("data", timestamp)
        os.makedirs(output_dir, exist_ok=True)
        csv_filename = os.path.join(output_dir, 'extinction_scan.csv')
        print(f"Saving data to: {output_dir}")

        if self.xwing.reference is None:
            print("No reference")
            return
        if len(self.xwing.samples) == 0:
            print("No regions")

        self.cornerstone.mono.open_shutter()
        all_data = []
        self.gain_map = {}

        print("\n" + "=" * 50 + "\nScanning REFERENCE\n" + "=" * 50)
        all_data.extend(self._scanPosition(self.xwing.reference, "reference", adjust_gain=True))

        print("\n" + "=" * 50 + "\nScanning SAMPLES\n" + "=" * 50)
        for sample in self.xwing.samples:
            if getattr(self, "_stop", False):
                break
            all_data.extend(self._scanPosition(sample, "sample", adjust_gain=False))

        with open(csv_filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'region', 'scan_type', 'x', 'y', 'wavelength', 'voltage', 'gain'])
            writer.writeheader()
            writer.writerows(all_data)
        print(f"\nSaved extinction data - {len(all_data)} measurements")

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

    ext = Extinction(xwing, cornerstone, pmt, digi)
    ext.plotter = LivePlot(title="Extinction (per-position spectrum)",
                           xlabel="wavelength (nm)", ylabel="voltage (V)",
                           mode="append")

    run_gui(
        automation=ext,
        run=ext._extinction,
        hardware=[xwing, cornerstone, pmt, digi],
        title="Extinction Scan",
    )
