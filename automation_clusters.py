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
import h5py


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

class SLIM(QObject):
    def __init__(self, spectrometerCore, PSG, PSA):
        super().__init__()
        self.PSG_DeathStar = PSG
        self.PSA_DeathStar = PSA
        self.spectro = spectrometerCore
        self.worker = None
 
        print("SLIM AUTOMATION READY")
 
    # ──────────────────────────────────────────────────────────────────────
    # Threading / dispatch
    # ──────────────────────────────────────────────────────────────────────
 
    @Slot(str)
    def threading(self, mode):
        """Start the SLIM automation for the given mode."""
        if self.worker is not None and self.worker.is_running():
            print("Hold ur horses...")
            return
 
        dispatch = {
            "mueller":      self._mueller,
            "calibration":  self._cali,
            "stokes":       self._stokes,
            "edgeLP":       self._edgeLP,
            "edgeCP":       self._edgeCP,
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
        """Stop the current scan."""
        if self.worker:
            self.worker.stop()
            print("Stopping scan...")
        else:
            print("Nothing running")
 
    # ──────────────────────────────────────────────────────────────────────
    # Hardware helpers
    # ──────────────────────────────────────────────────────────────────────
 
    def homeAll(self):
        self.PSA_DeathStar.resetHome()
        self.PSA_DeathStar.zHome()
        self.PSG_DeathStar.resetHome()
 
    # ──────────────────────────────────────────────────────────────────────
    # Save
    # ──────────────────────────────────────────────────────────────────────
 
    def saveHDF5(self, all_data, scanType):
        """
        Save scan data to HDF5.
 
        all_data : list of (angles_dict, intensities_array, wavelengths_array)
                   tuples as returned by slimScan.
        """
        timestamp  = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        name       = self.spectro._sampleName or "sample"
        region     = self.spectro._region
        side       = self.spectro._side
        output_dir = os.path.join("data", f"{name}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        h5_path    = os.path.join(
            output_dir, f"{name}_Region{region}_{side}_{scanType}.h5"
        )
 
        # FIX 1: tuple layout is (angles_dict, intensities, wavelengths)
        angles_list = [d[0] for d in all_data]          # list of dicts
        intensities = np.array([d[1] for d in all_data]) # (N_scans, N_wl)
        wavelengths = all_data[0][2]                      # same for every scan
 
        with h5py.File(h5_path, "w") as f:
            # Metadata
            f.attrs["region"]              = region
            f.attrs["side"]                = side
            f.attrs["x"]                   = self.spectro._scanX
            f.attrs["y"]                   = self.spectro._scanY
            f.attrs["integration_time_us"] = self.spectro.integration
 
            # Wavelength axis
            f.create_dataset("wavelength", data=wavelengths)
 
            # Per-scan angle columns
            for key in ["IW_Theta", "IP_Theta", "CW_Theta", "CP_Theta"]:
                f.create_dataset(
                    key, data=np.array([a[key] for a in angles_list])
                )
 
            # Intensity matrix: (N_scans, N_wavelengths)
            f.create_dataset(
                "intensity", data=intensities,
                compression="gzip", compression_opts=4,
            )
 
        print(f"Saved {len(all_data)} scans → {h5_path}")
 
    # ──────────────────────────────────────────────────────────────────────
    # Scan sequences
    # ──────────────────────────────────────────────────────────────────────
 
    def _stokes(self):
        # Each sub-list is one measurement configuration:
        #   [IP_Theta, CP_Theta]  (polarizer angles)
        #   [IW_Theta, CW_Theta] is always [angleStep, waveplate_angle]
        # FIX 2: named the sequence indices clearly to avoid axis confusion
        stokes_IP = [0, 45, 45, 0]   # PSA polarizer angles
        stokes_CW = [0, 0, 45, 45]  # PSA waveplate angles  
        # NOTE: original had stokesSequence[1] = [90,45,45,45] — verify these
        #       hardware values are correct for your Stokes basis before running.
 
        all_data = []
        for angleStep in range(0, 91, 10):
            if not self.worker._is_running:
                break
            for s in range(len(stokes_IP)):
                if not self.worker._is_running:
                    break
                # IW_Theta = IP_Theta = angleStep  (PSG side)
                # CW_Theta = stokes_CW[s], CP_Theta = stokes_IP[s]  (PSA side)
                data = self.slimScan(
                    P1=angleStep, R1=angleStep,
                    R2=stokes_CW[s], P2=stokes_IP[s],
                )
                all_data.append(data)  # FIX 3: append, not extend
 
        self.homeAll()
        self.saveHDF5(all_data, "stokesScan")
 
    def _edgeLP(self):
        all_data = []
        for x in range(0, 41, 1):           # 0–20 mm in 0.5 mm steps
            if not self.worker._is_running:
                break
            for angleStep in range(0, 136, 45):   # PSG linear polarization states
                if not self.worker._is_running:
                    break
                for analyzeStep in range(0, 91, 90):  # FIX 4: fixed typo 'anaylzeStep'
                    if not self.worker._is_running:
                        break
                    data = self.slimScan(
                        P1=angleStep, R1=angleStep,
                        R2=analyzeStep, P2=analyzeStep,
                        T1=0, T2=float(x / 2),
                    )
                    all_data.append(data)  # FIX 3: append, not extend
 
        self.saveHDF5(all_data, "LPscan")
        self.homeAll()
 
    def _edgeCP(self):
        all_data = []
        for x in range(0, 41, 1):           # 0–20 mm in 0.5 mm steps
            if not self.worker._is_running:
                break
            for angleStep in range(-45, 46, 90):   # LH / RH circular states
                if not self.worker._is_running:
                    break
                for analyzeStep in range(-45, 91, 45):  # FIX 4: fixed typo
                    if not self.worker._is_running:
                        break
                    data = self.slimScan(
                        P1=angleStep, R1=0,
                        R2=analyzeStep, P2=analyzeStep,
                        T1=0, T2=float(x / 2),
                    )
                    all_data.append(data)  # FIX 3: append, not extend
 
        self.saveHDF5(all_data, "CPscan")
        self.homeAll()
 
    def _mueller(self, theta=20, N=16):
        all_data = []
        for value in range(theta, (theta * N) + 1, theta):
            if not self.worker._is_running:
                break
            data = self.slimScan(P1=0, R1=value, R2=value * 5, P2=0)
            all_data.append(data)  # FIX 3: append, not extend
            print(f"Collection at R1: {value}  R2: {value * 5}")
 
        self.saveHDF5(all_data, "muellerScan")
        self.homeAll()
 
    def _cali(self):
        self.spectro.takeBackground()

    @Slot()
    def pauseCalibration(self):
        """Call from QML to pause the calibration mid-run."""
        self._cali_paused = True
 
    @Slot()
    def resumeCalibration(self):
        """Call from QML to resume after the midpoint pause."""
        self._cali_paused = False
 
    # ──────────────────────────────────────────────────────────────────────
    # Core measurement
    # ──────────────────────────────────────────────────────────────────────
 
    def slimScan(self, P1, R1, R2, P2, T1="", T2="", moveTime=0.5):
        """
        Move both arms to position and acquire one spectrum.
 
        Returns
        -------
        tuple : (angles_dict, intensities_array, wavelengths_array)
        """
        self.PSG_DeathStar.setPosition(str(P1), str(R1), str(T1))
        self.PSA_DeathStar.setPosition(str(P2), str(R2), str(T2))
        print(str(T2))
        time.sleep(moveTime)
 
        wavelengths, intensities = self.spectro.takeSpectrum()
 
        angles = {
            "IW_Theta": R1,
            "IP_Theta": P1,
            "CW_Theta": R2,
            "CP_Theta": P2,
        }
 
        # FIX 6: consistent tuple order (angles, intensities, wavelengths)
        #         matches what saveHDF5 expects at d[0], d[1], d[2]
        return (angles, np.array(intensities), np.array(wavelengths))
 
    # ──────────────────────────────────────────────────────────────────────
    # Stubs
    # ──────────────────────────────────────────────────────────────────────
 
    def lateralCalibration(self):
        # FIX 7: stubs now raise NotImplementedError so accidental calls fail loudly
        raise NotImplementedError("lateralCalibration not yet implemented")
 
    def scanIntensity(self, E_wp, E_pol):
        raise NotImplementedError("scanIntensity not yet implemented")
 
class XWingScan(QObject):
    progressChanged = Signal(str)
    statusChanged   = Signal(str)

    def __init__(self, xwing, cornerstone, pmt):
        super().__init__()
        self.xwing       = xwing
        self.cornerstone = cornerstone
        self.pmt         = pmt
        self.digi        = NIScopeClient()
        self.worker      = None
        self._sample_name = "sample"
        self._nx          = 5
        self._ny          = 5
        self._spacing     = 0.5   # mm
        self.gain         = 0
        self.pmt.changeGain(self.gain)
        print("XWingScan Automation Ready")

    @Slot(str)
    def setSampleName(self, value):
        self._sample_name = value.strip()
        print(f"Sample name set to: {self._sample_name}")

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
    def setSpacing(self, value):
        try:
            self._spacing = float(value)
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

    def _saveHDF5(self, all_x, all_y, wavelengths, all_voltages):
        timestamp  = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        name       = re.sub(r'[^\w\-]', '_', self._sample_name) or "sample"
        output_dir = os.path.join("data", f"{name}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        h5_path    = os.path.join(output_dir, f"{name}_xwing_scan.h5")

        voltage_matrix = np.array(all_voltages)   # (N_pts, N_wavelengths)

        with h5py.File(h5_path, "w") as f:
            f.attrs["sample_name"]      = self._sample_name
            f.attrs["nx"]               = self._nx
            f.attrs["ny"]               = self._ny
            f.attrs["spacing_mm"]       = self._spacing
            f.attrs["gain"]             = self.gain
            f.attrs["start_wavelength"] = self.cornerstone.startWavelength
            f.attrs["end_wavelength"]   = self.cornerstone.endWavelength
            f.attrs["num_steps"]        = self.cornerstone.numSteps

            f.create_dataset("x",          data=np.array(all_x))
            f.create_dataset("y",          data=np.array(all_y))
            f.create_dataset("wavelength", data=np.array(wavelengths))
            f.create_dataset(
                "voltage", data=voltage_matrix,
                compression="gzip", compression_opts=4,
            )

        print(f"Saved {len(all_x)} points → {h5_path}")

    def _scan(self):
        origin_x = self.xwing._x
        origin_y = self.xwing._y

        step_size   = (self.cornerstone.endWavelength - self.cornerstone.startWavelength) / self.cornerstone.numSteps
        wavelengths = [self.cornerstone.startWavelength + j * step_size
                       for j in range(self.cornerstone.numSteps)]

        total_points = self._nx * self._ny
        point_num    = 0
        all_x        = []
        all_y        = []
        all_voltages = []

        self.cornerstone.mono.open_shutter()
        self.statusChanged.emit("Running...")
        print(f"XWing scan: {self._nx}x{self._ny} pts, spacing={self._spacing}mm, "
              f"λ {self.cornerstone.startWavelength}–{self.cornerstone.endWavelength}nm "
              f"({self.cornerstone.numSteps} steps)")

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

                self.xwing._x = target_x
                self.xwing._y = target_y
                self.xwing.xChanged.emit()
                self.xwing.yChanged.emit()

                # Sweep wavelengths at this spatial position
                point_voltages = []
                for wavelength in wavelengths:
                    if not self.worker._is_running:
                        break

                    self.cornerstone.mono.goto(wavelength)
                    time.sleep(2)

                    d1 = self.digi.record()
                    d2 = self.digi.record()
                    d3 = self.digi.record()
                    d4 = self.digi.record()
                    voltage = (d1 + d2 + d3 + d4) / 4

                    point_voltages.append(voltage)

                    self.cornerstone.currentWavelength = wavelength
                    self.cornerstone.waveChanged.emit()

                    print(f"  Pt {point_num+1}/{total_points} "
                          f"X={target_x:.3f} Y={target_y:.3f} "
                          f"λ={wavelength:.2f}nm V={voltage:.4f}V")

                all_x.append(round(target_x, 4))
                all_y.append(round(target_y, 4))
                all_voltages.append(point_voltages)

                point_num += 1
                self.progressChanged.emit(f"Point {point_num}/{total_points}")

        self.cornerstone.mono.close_shutter()

        if all_voltages:
            self._saveHDF5(all_x, all_y, wavelengths, all_voltages)

        status = "Done." if self.worker._is_running else "Stopped."
        self.statusChanged.emit(status)
        print(f"Scan complete. {point_num} points measured.")
