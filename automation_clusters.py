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
        self.gain = 0
        self.pmt.changeGain(self.gain)
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

        print("SingleFluor Ready")
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
            self.pmt.changeGain(0)
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
            time.sleep(2)
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
    def __init__(self,  spectrometerCore, PSG, PSA):
        super().__init__()
        self.PSG_DeathStar = PSG
        self.PSA_DeathStar = PSA
        self.spectro = spectrometerCore
        self.worker = None

        print("SLIM AUTOMATION READY")

    @Slot(str)
    def threading(self, mode):
        """Start the SLIM automation for the given mode"""
        if self.worker is not None and self.worker.is_running():
            print("Hold ur horses...")
            return
        
        dispatch = {
            "mueller": self._mueller,
            "calibration": self._cali,
            "stokes": self._stokes,
            "edgeLP": self._edgeLP,
            "edgeCP": self._edgeCP,
        }
        
        func = dispatch.get(mode)
        if func is None:
            print(f"Unknown mode: {mode}")
            return
        
        self.worker = Worker(func)
        self.worker.start()
        print(f"{mode} scan started")

    @Slot()
    def stopScan(self):
        """Stop the current scan"""
        if self.worker:
            self.worker.stop()
            print("Stopping scan...")
        else:
            print("Nothing running")

    def homeAll(self):
        self.PSA_DeathStar.resetHome()
        self.PSG_DeathStar.resetHome()

    def saveFiles(self, all_data, scanType):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        name = self.spectro._sampleName or "sample"
        region = self.spectro._region
        side = self.spectro._side
        output_dir = os.path.join("data", f"{name}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        csv_filename = os.path.join(output_dir, f"{name}_Region{region}_{side}_{scanType}.csv")
        print(f"Saving data to: {output_dir}")

        with open(csv_filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'region', 'x', 'y', 'side', 'IW_Theta', 'IP_Theta', 'CW_Theta', 'CP_Theta', 'wavelength', 'intensity', 'integration_time'
            ])
            writer.writeheader()
            writer.writerows(all_data)
        
        print(f"\nSaved SLIM data - {len(all_data)} measurements")

# This is for saving measurements to a single file. 
    def saveFileSingles(self, spectrum_data, output_dir):
        """Save a single spectrum as its own .txt file"""
        name = self.spectro._sampleName or "sample"
        region = self.spectro._region
        side = self.spectro._side

        first = spectrum_data[0]
        iP = int(first['IP_Theta'])
        L4 = int(first['CW_Theta'])
        AP = int(first['CP_Theta'])

        filename = f"{name}_Reg{region}_{side}Side_{iP}iP_{L4}L4_{AP}AP.txt"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w') as f:
            for row in spectrum_data:
                f.write(f"{row['wavelength']}\t{row['intensity']}\n")

        print(f"Saved spectrum -> {filename}")

    def _stokes (self):
        self.PSA_DeathStar.set_Rate(6000)
        stokesSequence = [[0, 45, 45, 0],     # Polarizer
                          [0, 0, 45, 45]]    # Waveplate 
        all_data = [] 
        for angleStep in range(0, 91, 10):
            if not self.worker._is_running:
                break
            for s in range(len(stokesSequence[0])):
                if not self.worker._is_running:
                    break
                data = self.slimScan (angleStep,angleStep,stokesSequence[1][s],stokesSequence[0][s], moveTime = 1)
                all_data.extend(data)

        self.homeAll()
        self.saveFiles(all_data, "stokesScan")

    def _edgeLP(self): 
        all_data = [] 
        for x in range(0, 41, 1): # 20 milimeter across the sample edge by increments of 0.5 
            if not self.worker._is_running:
                break
            for angleStep in range(0, 91, 90): # PSG creates polarization states 0 to 90 degrees 
                if not self.worker._is_running:
                    break
                for anaylzeStep in range(0, 91, 90): # 2 Sets of Itensity Data to gather irradaiance 
                    if not self.worker._is_running:
                        break

                    data = self.slimScan (angleStep,angleStep,anaylzeStep,anaylzeStep,T1 = 0, T2 = float(x/2))  
                    all_data.extend(data)

        self.saveFiles(all_data, "LPscan")
        self.homeAll()

    def _edgeCP(self): 
        all_data = [] 
        for x in range(0, 41, 1): # 20 milimeter across the sample edge by increments of 0.5 
            if not self.worker._is_running:
                break
            for angleStep in range(-45, 46, 90): # PSG creates polarization states left handed, right handed
                if not self.worker._is_running:
                    break
                for anaylzeStep in range(0, 91, 90): # 2 Sets of Itensity Data to gather
                    if not self.worker._is_running:
                        break
                    data = self.slimScan (angleStep,0,anaylzeStep,anaylzeStep,T1 = 0, T2 = float(x/2))  
                    all_data.extend(data)

        self.saveFiles(all_data, "CPscan")
        self.homeAll()

    # Later on, probably change to an 18 sequence but for now we can do the min 
    # Going to need 40 measurements for good results 
    def _mueller(self, theta = 20, N = 16):
        all_data = []

        for value in range(theta, (theta*N)+1, theta):
            if not self.worker._is_running:
                break
            data = self.slimScan(0, value, value*5, 0)
            all_data.extend(data)
            print("Collection at R1: ",value, " R2: ", value*5)

        self.saveFiles(all_data, "muellerScan")
        self.homeAll()


    def _cali(self):
        self.spectro.takeBackground()

    def slimScan(self, P1, R1, R2, P2, T1 = '', T2 = '', moveTime = 0.75):
        self.PSG_DeathStar.setPosition(str(P1), str(R1), str(T1))
        self.PSA_DeathStar.setPosition(str(P2), str(R2), str(T2))
        time.sleep(moveTime) # Time for the rotation of the retarders 

        measurements = []
        x = self.spectro._scanX
        y = self.spectro._scanY
        region = self.spectro._region
        side = self.spectro._side
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
        self.PSA_DeathStar.setPosition(str(E_pol), str(E_wp))
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
