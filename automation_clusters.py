from PySide6.QtCore import QObject, Signal, Property, Slot, QThread
from hardware_controllers import *
from cores import LivePlot
import os
import csv
import re
import niscope
import numpy as np
import pyqtgraph as pg
import time
from datetime import datetime


class Worker(QObject):
    """ Object that creates a thread for automation logic then moves logic
    to that thread. All you have to do is create the object with the function 
    that you want to run on a separate thread. """
    finished = Signal()
    error = Signal(str)
    
    def __init__(self, func):
        """ Passes the function, sets _is_running to true to denote
        that a proccess is running. """
        super().__init__()
        self.func = func
        self._is_running = True
        self.thread = None
    
    def start(self):
        """Automatically create thread and start it"""
        self.thread = QThread()
        
        # Move object (i.e. anything that uses self) to the thread
        self.moveToThread(self.thread)
        
        # Connect QThread signals. Have to use this if using the QThread object.
        self.thread.started.connect(self.run)
        self.finished.connect(self.thread.quit)
        self.finished.connect(self.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        
        # Start the thread
        self.thread.start()
    
    def run(self):
        """ Execute the function that was passed """
        self.func()
        self.finished.emit()
    
    def stop(self):
        """ Stop button for later use """
        self._is_running = False
    
    def is_running(self):
        """Check if worker is currently running"""
        if self.thread is None:
            return False
        try:
            return self.thread.isRunning()
        except RuntimeError:
            # Thread was already deleted
            return False

class HyperSpectralExtinction(QObject):
    """Extinction automation using hyperspectral setup"""

    def __init__(self, xwing, cornerstone, pmt):
        super().__init__()
        self.digi = NIScopeClient()
        self.plotter = None
        self.worker = None
        self.pmt = pmt
        self.xwing = xwing
        self.cornerstone = cornerstone
        self.gain_map = {}

        print("Extinction Automation Online")
    
    @Slot()
    def threading(self):
        """Start the extinction scan automation"""
        if self.worker is not None and self.worker.is_running():
            print("Hold ur horses...")
            return
        
        if self.plotter is None:
            self.plotter = LivePlot()
        
        self.worker = Worker(self._extinction)
        self.worker.start()
        print("Scan started")
    
    @Slot()
    def stopScan(self):
        """Stop the current scan"""
        if self.worker:
            self.worker.stop()
            self.worker = None
            self.pmt.commandSend("0")
            print("Stopping scan...")
    
    def _scanPosition(self, coord, scan_type, adjust_gain=True):
        """
        Scan a single position with optional gain adjustment
        
        Args:
            coord: Dictionary with 'x', 'y', 'region', 'type'
            adjust_gain: If True, adjust gain. If False, use gain values from coordinate dictionary.
        
        Returns:
            List of measurement dictionaries
        """
        TARGET_VOLTAGE = 8.0
        VOLTAGE_TOLERANCE = 0.5
        VOLTAGE_MIN = 4
        VOLTAGE_MAX = 12
        MAX_GAIN_ADJUSTMENTS = 30
        
        step_size = (self.cornerstone.endWavelength - self.cornerstone.startWavelength) / self.cornerstone.numSteps
        
        x, y = coord['x'], coord['y']
        region = coord.get('region', 'REF')
        
        # Move to position
        self.xwing.ac.commandSend(f"G1 X{x} Y{y} F{self.xwing.rate}")
        print(f"\nScanning {scan_type} for Region {region}: X={x}, Y={y}")
        time.sleep(4)
        
        self.plotter.resetPlot()
        
        measurements = []
        
        # Scan through wavelengths
        for j in range(self.cornerstone.numSteps):
            if not self.worker._is_running:
                break
            
            wavelength = self.cornerstone.startWavelength + j * step_size
            self.cornerstone.mono.goto(wavelength)
            time.sleep(1)
            
            if adjust_gain:
                # Adjust gain to target voltage
                dataPoint = self.digi.record()
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
                        dataPoint = self.digi.record()
                        adjustment_count += 1
                
                # Store gain for this region and wavelength
                key = round(wavelength, 2)
                self.gain_map[key] = self.gain
                
            else:
                # SAMPLE: Use locked gain from reference
                key = round(wavelength, 2)
                if key in self.gain_map:
                    self.gain = self.gain_map[key]
                    self.pmt.changeGain(self.gain)
                    time.sleep(1.5)
                else:
                    print(f"No reference gain found for Region {region}, λ={wavelength:.2f} nm")
                
                dataPoint = self.digi.record()
            
            measurements.append({
                'region': region,
                'scan_type': scan_type,
                'x': x,
                'y': y,
                'wavelength': wavelength,
                'voltage': dataPoint,
                'gain': self.gain
            })
            
            # Update UI
            self.xwing._x = x
            self.xwing._y = y
            self.xwing.xChanged.emit()
            self.xwing.yChanged.emit()
            
            self.cornerstone.currentWavelength = wavelength
            self.cornerstone.waveChanged.emit()
            
            self.plotter.updatePlot(wavelength, dataPoint)
            
            print(f"  λ={wavelength:.2f} nm, V={dataPoint:.2f}V, Gain={self.gain:.3f}")
        
        return measurements
    
    def _extinction(self):
        """
        Main automation logic.
        Scans all regions: reference first (with gain adjustment), then samples (locked gains).
        """
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

        print(f"\n{'='*50}")
        print(f"Scanning REFERENCE")
        print(f"{'='*50}")
        
        # Scan reference ONCE (with gain adjustment)
        ref_data = self._scanPosition(self.xwing.reference, "reference", adjust_gain=True)
        all_data.extend(ref_data)
        
        # Scan all samples (with locked gains from reference)
        print(f"\n{'='*50}")
        print(f"Scanning SAMPLES")
        print(f"{'='*50}")
        
        for sample in self.xwing.samples:
            if not self.worker._is_running:
                break
            sample_data = self._scanPosition(sample, "sample", adjust_gain=False)
            all_data.extend(sample_data)
        
        # Save all data
        with open(csv_filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'region', 'scan_type', 'x', 'y', 'wavelength', 'voltage', 'gain'
            ])
            writer.writeheader()
            writer.writerows(all_data)
        
        print(f"\nSaved extinction data - {len(all_data)} measurements")
        
        self.cornerstone.mono.close_shutter()
        print(f"Scan complete! Data saved to: {csv_filename}")

class HyperSpectralSingleFluor(QObject):
     """Extinction automation using hyperspectral setup"""
     def __init__(self, xwing, cornerstone, pmt):
        super().__init__()
        self.digi = NIScopeClient()
        self.plotter = None
        self.worker = None
        self.pmt = pmt
        self.gain = 0
        self.pmt.changeGain(self.gain)
        self.xwing = xwing
        self.cornerstone = cornerstone
        self.gain_map = {}

        print("Extinction Automation Ready")
     @Slot()
     def threading(self):
        """Start the extinction scan automation"""
        if self.worker is not None and self.worker.is_running():
            print("Hold ur horses...")
            return
        
        if self.plotter is None:
            self.plotter = LivePlot()
        
        self.worker = Worker(self._singleFluor)
        self.worker.start()
        print("Scan started")
    
     @Slot()
     def stopScan(self):
        """Stop the current scan"""
        if self.worker:
            self.worker.stop()
            self.worker = None
            self.pmt.commandSend("0")
            print("Stopping scan...")
    
     def _scanPosition(self, coord, scan_type):
        """
        Scan a single position with optional gain adjustment
        
        Args:
            coord: Dictionary with 'x', 'y', 'region', 'type'
            adjust_gain: If True, adjust gain. If False, use gain values from coordinate dictionary.
        
        Returns:
            List of measurement dictionaries
        """
        self.gain = 1
        self.pmt.commandSend("1")
        
        step_size = (self.cornerstone.endWavelength - self.cornerstone.startWavelength) / self.cornerstone.numSteps
        
        x, y = coord['x'], coord['y']
        region = coord.get('region', 'REF')
        
        # Move to position
        self.xwing.ac.commandSend(f"G1 X{x} Y{y} F{self.xwing.rate}")
        print(f"\nScanning {scan_type} for Region {region}: X={x}, Y={y}")
        time.sleep(4)
        
        self.plotter.resetPlot()
        
        measurements = []
                # Scan through wavelengths
        for j in range(self.cornerstone.numSteps):
            if not self.worker._is_running:
                break
            
            wavelength = self.cornerstone.startWavelength + j * step_size
            self.cornerstone.mono.goto(wavelength)
            time.sleep(30)
            dataPoint1 = self.digi.record()
            dataPoint2 = self.digi.record()
            dataPoint3 = self.digi.record()
            dataPoint4 = self.digi.record()

            dataPoint = (dataPoint1 + dataPoint2 + dataPoint3 + dataPoint4)/4

            measurements.append({
                'region': region,
                'scan_type': scan_type,
                'x': x,
                'y': y,
                'wavelength': wavelength,
                'voltage': dataPoint,
                'gain': self.gain
            })
            
            self.cornerstone.currentWavelength = wavelength
            self.cornerstone.waveChanged.emit()
            
            self.plotter.updatePlot(wavelength, dataPoint)

            print(f"  λ={wavelength:.2f} nm, V={dataPoint:.2f}V, Gain={self.gain:.3f}")
            
        # Update UI
        self.xwing._x = x
        self.xwing._y = y
        self.xwing.xChanged.emit()
        self.xwing.yChanged.emit()
            
        
        
        return measurements
    
     def _singleFluor(self):
        """
        Main automation logic.
        Scans all regions: reference first (with gain adjustment), then samples (locked gains).
        """
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

        print(f"\n{'='*50}")
        print(f"Scanning REFERENCE")
        print(f"{'='*50}")
        
        # Scan reference ONCE
        if self.xwing.reference:
            ref_data = self._scanPosition(self.xwing.reference, "reference")
            all_data.extend(ref_data)
        
        # Scan all samples
        print(f"\n{'='*50}")
        print(f"Scanning SAMPLES")
        print(f"{'='*50}")
        
        for sample in self.xwing.samples:
            if not self.worker._is_running:
                break
            sample_data = self._scanPosition(sample, "sample")
            all_data.extend(sample_data)
        
        # Save all data
        with open(csv_filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'region', 'scan_type', 'x', 'y', 'wavelength', 'voltage', 'gain'
            ])
            writer.writeheader()
            writer.writerows(all_data)
        
        print(f"\nSaved extinction data - {len(all_data)} measurements")
        
        self.cornerstone.mono.close_shutter()
        print(f"Scan complete! Data saved to: {csv_filename}")

class SLIM(QObject): # Still WIP
    def __init__(self, DeathStar,spectrometerCore):
        super().__init__()
        self.deathstar1 = DeathStar
        # self.deathstar2 = DeathStar2
        # self.xwing = xwing 
        self.spectro = spectrometerCore
        self.worker = None

        print("SLIM AUTOMATION READY")

    @Slot()
    def threading(self):
        """Start the SLIM automation"""
        if self.worker is not None and self.worker.is_running():
            print("Hold ur horses...")
            return
        
        self.worker = Worker(self._cali)
        self.worker.start()
        print("Scan started")

    def saveFiles(self, all_data, filename):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = os.path.join("data", timestamp)
        os.makedirs(output_dir, exist_ok=True)
        csv_filename = os.path.join(output_dir, f"{filename}.csv")
        print(f"Saving data to: {output_dir}")

        with open(csv_filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'region', 'x', 'y', 'side', 'IW_Theta', 'IP_Theta', 'CW_Theta', 'CP_Theta', 'wavelength', 'intensity', 'integration_time'
            ])
            writer.writeheader()
            writer.writerows(all_data)
        
        print(f"\nSaved mueller data - {len(all_data)} measurements")

    # Later on, probably change to an 18 sequence but for now we can do the min 
    def _mueller(self, theta = 20, N = 16):
        all_data = []

        for value in range(theta, (theta*N)+1, theta):
            data = self.slimScan(0, value, value*5, 0)
            all_data.extend(data)
            print("Collection at R1: ",value, " R2: ", value*5)

        self.saveFiles(all_data, "slim_scan")
        self.deathstar1.resetHome()

    def _cali(self):
        self.spectro.setIntegration(20000)
        self.deathstar1.set_Rate(10000)
        cal_data = [] 
        for i in range(11,3961,11):
            data = self.slimScan(0, i, i*5, 0)
            cal_data.extend(data)
            if (i == 1980):
                user_input = input("Enter to Continue: ")
            print("Collection at R1: ",i, " R2: ", i*5)
        self.saveFiles(cal_data, "PSG_Calibration")
        self.deathstar1.resetHome()

    def slimScan(self, P1, R1, R2, P2):
        self.deathstar1.setPosition(str(R1), str(R2))
        time.sleep(0.7) # Time for the rotation of the retarders 

        measurements = []
        x = 0 
        y = 0 #Change this later on, but for now they're just hard set 
        region = 1 
        side = 'x' 
        wavelength, intensities = self.spectro.takeSpectrum() 

        for i in range(len(wavelength)):
            measurements.append({
                'region': region,
                'x': x,
                'y': y,
                'side': side,
                'IW_Theta': R1,
                'IP_Theta': P1,
                'CW_Theta': R2,
                'CP_Theta': P2,
                'wavelength': wavelength[i],
                'intensity': intensities[i],
                'integration_time': self.spectro.integration,
            })

        return measurements

    def lateralCalibration(self):
        print ("Hello World")
        # This is for maximimizing intensity with translational movement
        # Do later 
            
#Assuming that you have the waveplates on the exictation arm 
    def scanIntensity(self, E_wp, E_pol):
        self.deathstar1.setPosition(str(E_pol), str(E_wp))
        #self.deathstar2.setPosition(str(0), str(0))
        time.sleep(0.5)

        #self.deathstar2.setPosition(str(90), str(90))
        time.sleep(0.5)


class XWingScan(QObject):
    progressChanged = Signal(str)
    statusChanged   = Signal(str)

    def __init__(self, xwing, spectro):
        super().__init__()
        self.xwing   = xwing
        self.spectro = spectro
        self.worker  = None
        self._sample_name      = "sample"
        self._nx               = 5
        self._ny               = 5
        self._spacing          = 0.5     # mm, fixed
        self._integration_time = 500000  # µs = 500 ms
        print("XWingScan Automation Ready")

    @Slot(str)
    def setSampleName(self, value):
        self._sample_name = value.strip()

    @Slot(str)
    def setNx(self, value):
        try:
            self._nx = max(1, int(value))
        except ValueError:
            pass

    @Slot(str)
    def setNy(self, value):
        try:
            self._ny = max(1, int(value))
        except ValueError:
            pass

    @Slot(str)
    def setIntegrationTime(self, value):
        try:
            self._integration_time = int(value)
            self.spectro.setIntegration(value)
        except ValueError:
            pass

    @Slot()
    def threading(self):
        if self.worker is not None and self.worker.is_running():
            print("Hold ur horses...")
            return
        self.worker = Worker(self._scan)
        self.worker.start()

    @Slot()
    def stopScan(self):
        if self.worker:
            self.worker.stop()
        self.statusChanged.emit("Stopped.")

    def _scan(self):
        origin_x = self.xwing._x
        origin_y = self.xwing._y

        timestamp  = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = os.path.join("data", timestamp)
        os.makedirs(output_dir, exist_ok=True)

        safe_name    = re.sub(r'[^\w\-]', '_', self._sample_name) or "sample"
        csv_filename = os.path.join(output_dir, f"{safe_name}_xwing_scan.csv")

        self.spectro.setIntegration(str(self._integration_time))
        self.statusChanged.emit("Running...")
        print(f"XWing scan: {self._nx}x{self._ny} pts, spacing={self._spacing}mm, "
              f"integration={self._integration_time}µs")
        print(f"Saving to: {csv_filename}")

        total_points = self._nx * self._ny
        point_num    = 0

        with open(csv_filename, 'w', newline='') as f:
            writer = csv.DictWriter(
                f, fieldnames=['sample_name', 'x', 'y', 'wavelength', 'intensity'])
            writer.writeheader()

            for iy in range(self._ny):
                if not self.worker._is_running:
                    break
                # Boustrophedon (snake) scan to minimise stage travel
                ix_range = range(self._nx) if iy % 2 == 0 else range(self._nx - 1, -1, -1)

                for ix in ix_range:
                    if not self.worker._is_running:
                        break

                    target_x = origin_x + ix * self._spacing
                    target_y = origin_y + iy * self._spacing

                    self.xwing.ac.commandSend(
                        f"G1 X{target_x:.4f} Y{target_y:.4f} F{self.xwing.rate}")
                    time.sleep(1.5)

                    # Update UI position readouts
                    self.xwing._x = target_x
                    self.xwing._y = target_y
                    self.xwing.xChanged.emit()
                    self.xwing.yChanged.emit()

                    wavelengths, intensities = self.spectro.takeSpectrum()

                    for i in range(len(wavelengths)):
                        writer.writerow({
                            'sample_name': self._sample_name,
                            'x':           round(target_x, 4),
                            'y':           round(target_y, 4),
                            'wavelength':  wavelengths[i],
                            'intensity':   intensities[i],
                        })
                    f.flush()

                    point_num += 1
                    self.progressChanged.emit(f"Point {point_num}/{total_points}")
                    print(f"  Point {point_num}/{total_points}: "
                          f"X={target_x:.3f}, Y={target_y:.3f}")

        status = "Done." if self.worker._is_running else "Stopped."
        self.statusChanged.emit(f"{status} Saved: {csv_filename}")
        print(f"Scan complete. {point_num} points measured.")
