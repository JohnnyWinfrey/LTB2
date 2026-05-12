from PySide6.QtCore import QObject, Signal, Property, Slot, QThread
from PySide6.QtWidgets import QFileDialog
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtGui import QImage
from hardware_controllers import *
import pyqtgraph as pg
import numpy as np
from seabreeze.spectrometers import Spectrometer, list_devices
from pylablib.devices.Thorlabs import ThorlabsTLCamera



""" Create QObject classes for each hardware controller. """
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
        """ Checks if thread is still running """
        return self.thread is not None and self.thread.isRunning()

class XWing(QObject):
    
    xChanged = Signal()
    yChanged = Signal()
    memChanged = Signal()
    coordinatesChanged = Signal()

    def __init__(self, comNum):
        super().__init__()
        self._x = 0.0
        self._y = 0.0
        self._posMem = 1
        self._home_x = 0.0
        self._home_y = 0.0
        self._step = 0.1  # mm per button press (change as needed)
        self.rate = 50
        self.ac = ArduinoClient(comNum, 115200)
        self.reference = None
        self.samples = []
        print("XWing online")
        

    # --- X position as a float (if you ever want numeric binding) ---
    @Property(float, notify=xChanged)
    def xPos(self):
        return self._x

    # --- Y position ---
    @Property(float, notify=yChanged)
    def yPos(self):
        return self._y

    # --- String versions for your labels ---
    @Property(str, notify=xChanged)
    def xPosString(self):
        return f"{self._x:.2f}"

    @Property(str, notify=yChanged)
    def yPosString(self):
        return f"{self._y:.2f}"

    @Property('QVariantList', notify=coordinatesChanged)
    def coordinatesList(self):
        """Expose coordinates as QVariantList for QML"""
        return self.coordinates

    # --- Movement slots (called from QML) ---
    @Slot()
    def moveUp(self):
        
        self._y += self._step
        self.ac.commandSend(f"G1 Y{self._y} F{self.rate}")
        print("Move Up ->", self._y)
        self.yChanged.emit()


    @Slot()
    def moveDown(self):
        
        self._y -= self._step
        self.ac.commandSend(f"G1 Y{self._y} F{self.rate}")
        print("Move Down ->", self._y)
        self.yChanged.emit()

    @Slot()
    def moveRight(self):
        
        self._x += self._step
        self.ac.commandSend(f"G1 X{self._x} F{self.rate}")
        print("Move Right ->", self._x)
        self.xChanged.emit()

    @Slot()
    def moveLeft(self):
        
        self._x -= self._step
        self.ac.commandSend(f"G1 X{self._x} F{self.rate}")
        print("Move Left ->", self._x)
        self.xChanged.emit()

    @Slot()
    def home(self):
        self.ac.commandSend(f"G1 X{0} Y{0} F{self.rate}")
        self._x = self._home_x
        self._y = self._home_y
        print("Go Home ->", self._x, self._y)
        self.xChanged.emit()
        self.yChanged.emit()

    @Slot()
    def setHome(self):
        self._home_x = self._x
        self._home_y = self._y
        print("Set Home ->", self._home_x, self._home_y)

    @Slot(str, str)
    def setPosition(self, x_str, y_str):
        self.ac.commandSend(f"G1 X{x_str} Y{y_str} F{self.rate}")
        if x_str.strip():
            self._x = float(x_str)
        if y_str.strip():
            self._y = float(y_str)
        print("Set Position ->", self._x, self._y)
        self.xChanged.emit()
        self.yChanged.emit()

    @Slot()
    def storeReference(self):
        """Store current position as THE reference"""
        self.reference = {
            'x': self._x,
            'y': self._y
        }
        self.coordinatesChanged.emit()
        print(f"Stored reference: {self.reference}")
    
    @Slot(str)
    def storeSample(self, region):
        """
        Store current position as a sample for a region
        Args:
            region: "A", "B", "C", or "D"
        """
        if (region == "Other"):
            region = str(self._posMem)


        sample = {
            'x': self._x,
            'y': self._y,
            'region': region
        }
        self.samples.append(sample)
        self.coordinatesChanged.emit()
        print(f"Stored sample: {sample}")
    
    @Slot(int)
    def removeSample(self, index):
        """Remove a sample by index"""
        if 0 <= index < len(self.samples):
            removed = self.samples.pop(index)
            self.coordinatesChanged.emit()
            print(f"Removed sample: {removed}")
    
    @Slot()
    def clearReference(self):
        """Clear the reference"""
        self.reference = None
        self.coordinatesChanged.emit()
        print("Cleared reference")
    
    @Slot()
    def clearSamples(self):
        """Clear all samples"""
        self.samples = []
        self.coordinatesChanged.emit()
        print("Cleared all samples")
    
    @Slot(int)
    def memSelected(self, memPos):
        self._posMem = memPos
        print(f"Mem {memPos} Selected")


    def getSamplesByRegion(self, region):
        """Get all samples for a specific region"""
        return [s for s in self.samples if s['region'] == region]

    @Property('QVariantList', notify=coordinatesChanged)
    def samplesList(self):
        """Expose samples as QVariantList for QML"""
        return self.samples
    
    @Property('QVariant', notify=coordinatesChanged)
    def referencePosition(self):
        """Expose reference as QVariant for QML"""
        return self.reference if self.reference else {}

class DeathStar(QObject):
    # Important: What counts as Clockwise and Counterclockwise will be assuming you're looking 'towards' the incoming light
    wavePlateRotated = Signal()
    polarRotated = Signal()
    orientationChanged = Signal()

    def __init__(self, comNum, ZAxis = False, id = "First"):
        super().__init__()
        self._thetaW = 0
        self._thetaP = 0
        self._z = 0.0
        self.rate = 10000 
        self.ac = ArduinoClient(comNum, 115200)
        self.reference = None
        self.samples = []
        self.ac.commandSend(f"G10 L20 P1 X{0} Y{0}")
        self.ac.commandSend(f"G1 X{15} Y{15} F{10000}")
        self.ac.commandSend(f"G1 X{0} Y{0} F{10000}")
        self.ZAxis = ZAxis
        self.name = id
        print(self.name, " DeathStar online")
        self.polarRotated.emit()
        self.wavePlateRotated.emit()

    # --- Wave Plate Anglular ---
    @Property(int, notify=wavePlateRotated)
    def wPos(self):
        return self._thetaW%360

    # --- Polarizer Angular Position  ---
    @Property(int, notify=polarRotated)
    def pPos(self):
        return self._thetaP%360

    # --- String versions for your labels ---
    @Property(str, notify=wavePlateRotated)
    def wPosString(self):
        return f"{(self._thetaW%360):.2f}"

    @Property(str, notify=polarRotated)
    def pPosString(self):
        return f"{(self._thetaP%360):.2f}"
    
    @Slot()
    def set_Rate(self, newRate):
        self.rate = newRate

    # Returns to your 'home', ususally the nearest 0th degree 
    @Slot()
    def home(self):
        self.ac.commandSend(f"G1 X{0} Y{0} F{self.rate}")
        self._thetaP = 0
        self._thetaW = 0
        print("Go Home ->", self._thetaP, self._thetaW)
        self.polarRotated.emit()
        self.wavePlateRotated.emit()

    # Returns to the nearest 0th degree and sets it to home 
    @Slot()
    def resetHome(self):
        returnP = self._thetaP%360
        returnW = self._thetaW%360
        self.ac.commandSend(f"G1 X{self._thetaP-returnP} Y{self._thetaW-returnW} F{self.rate}")
        self.ac.commandSend(f"G10 L20 P1 X{0} Y{0}")
        print("Set Zero ->", self._thetaP, self._thetaW)
        self._thetaP = 0
        self._thetaW = 0 
        self.polarRotated.emit()
        self.wavePlateRotated.emit()

    # Returns z to home
    @Slot()
    def zHome(self):
        if (self.ZAxis):
            self._z = 0.0
            self.ac.commandSend(f"G1 Z{0} F{40}")
            print("Z Go Home ->", self._z)


    @Slot(str, str)
    def setPosition(self, p_str, w_str, z = ""):
        if (z):
            self._z = float(z)
            self.ac.commandSend(f"G1 Z{z} F{40}")
        self.ac.commandSend(f"G1 X{p_str} Y{w_str} F{self.rate}")
        if p_str.strip():
            self._thetaP = float(p_str)
        if w_str.strip():
            self._thetaW = float(w_str)
        print(self.name, " setting Position ->", self._thetaP, self._thetaW, z)
        self.polarRotated.emit()
        self.wavePlateRotated.emit()

class SpectreCore(QObject):

    int_Time_Changed = Signal()
    spec_Taken = Signal()
    scanParamsChanged = Signal()
    backgroundChanged = Signal()

    def __init__(self):
        super().__init__()
        self.intTime = 500000
        self.spec = Spectrometer.from_first_available()
        self.spec.integration_time_micros(self.intTime)
        self.specInfo = list_devices()[0]
        self.background = 0.0 
        self.scansToAvg = 1
        self._bgCounts = 0.0  #peak average

        # Scan metadata (set from QML)
        self._scanX = 0.0
        self._scanY = 0.0
        self._side = "X"
        self._region = "A"
        self._sampleName = "sample"

        # Set limits on integration time and intensities based on spectrometer limits 
        self.intMin, self.intMax = self.specInfo.features['spectrometer'][0].get_integration_time_micros_limits()
        self.maxIntensity = self.specInfo.features['spectrometer'][0].get_maximum_intensity()

        print("Spectrometer Found:", self.spec)

    # --- Integration Time  ---
    @Property(int, notify=int_Time_Changed)
    def integration(self):
        return self.intTime
    
    @Property(str, notify=backgroundChanged)
    def bgCounts(self):
        return f"{self._bgCounts:.2f}"
    
    @Slot(str)
    def setIntegration(self, value):
        try:
            val = int(value)
            if val < self.intMin:
                print(f"Integration time {val} below minimum ({self.intMin}), clamping")
                val = self.intMin
            elif val > self.intMax:
                print(f"Integration time {val} above maximum ({self.intMax}), clamping")
                val = self.intMax
            self.intTime = val
            self.spec.integration_time_micros(self.intTime)
            self.int_Time_Changed.emit()
            print(f"Set Integration Time -> {self.intTime}")
        except ValueError:
            pass

    @Slot(str)
    def setScansToAvg(self, value):
        try:
            val = int(value)
            if val < 1:
                val = 1
            self.scansToAvg = val
            print(f"Scans to average -> {self.scansToAvg}")
        except ValueError:
            pass

    # Note: The way spectrometer works is that it seems to continiously load data. When int time change, need to take a measurement to 'clear' it from old one
    def takeBackground(self):
        self.spec.intensities()
        self.spec.wavelengths()

        self.spec.wavelengths()
        self.background = self.spec.intensities(correct_dark_counts=True)
        sorted_bg = sorted(self.background, reverse=True)

        self.checkOversaturation(sorted_bg[0]) 
        top_10_count = max(1, len(sorted_bg) // 10)
        self._bgCounts = sum(sorted_bg[:top_10_count]) / top_10_count
        self.backgroundChanged.emit()
        print(f"Background updated! Avg top 10%: {self._bgCounts:.2f}")


    def takeSpectrum(self):
        wavelengths = self.spec.wavelengths()
        intensities = 0 

        for i in range(self.scansToAvg):
            intensities += self.spec.intensities(correct_dark_counts=True) - self.background

        intensities = (intensities/self.scansToAvg)
        return wavelengths, intensities
    
    def checkOversaturation(self, maxMI):
        if (maxMI >= (self.maxIntensity-1)):
            print("WARNING: MEASUREMENT OVERSATURATED")
            return True 
        else:
            return False 
    
# --- Scan metadata properties ---
    @Property(float, notify=scanParamsChanged)
    def scanX(self):
        return self._scanX

    @Property(float, notify=scanParamsChanged)
    def scanY(self):
        return self._scanY

    @Property(str, notify=scanParamsChanged)
    def side(self):
        return self._side

    @Property(str, notify=scanParamsChanged)
    def region(self):
        return self._region
    
    @Property(str, notify=scanParamsChanged)
    def sampleName(self):
        return self._sampleName

    @Slot(str)
    def setScanX(self, value):
        try:
            self._scanX = float(value)
            self.scanParamsChanged.emit()
            print(f"Scan X -> {self._scanX}")
        except ValueError:
            pass

    @Slot(str)
    def setScanY(self, value):
        try:
            self._scanY = float(value)
            self.scanParamsChanged.emit()
            print(f"Scan Y -> {self._scanY}")
        except ValueError:
            pass

    @Slot(str)
    def setSide(self, value):
        self._side = value
        self.scanParamsChanged.emit()
        print(f"Side -> {self._side}")

    @Slot(str)
    def setRegion(self, value):
        self._region = value
        self.scanParamsChanged.emit()
        print(f"Region -> {self._region}")

    @Slot(str)
    def setSampleName(self, value):
        self._sampleName = value
        self.scanParamsChanged.emit()
        print(f"Sample Name -> {self._sampleName}")

class Cornerstone(QObject):
    waveChanged = Signal()
    shutterChanged = Signal()
    startWavelengthChanged = Signal()
    endWavelengthChanged = Signal()
    numStepsChanged = Signal()
    
    def __init__(self):
        super().__init__()
        self.mono = CornerstoneClient("helpers/cornerstone_helper.exe")
        self.mono.open()
        self.targetWavelength = 630
        self.shutterState = "Closed"
        self.startWavelength = 600
        self.endWavelength = 800
        self.numSteps = 50
        self.currentGrating = 3
        self.currentWavelength = 0.0
        print("Cornerstone online")
    
    @Property(str, notify=waveChanged)
    def wavePos(self):
        return str(self.currentWavelength)
    
    @Property(str, notify=shutterChanged)
    def shutterPos(self):
        return self.shutterState
    
    @Property(float, notify=startWavelengthChanged)
    def startWavelengthValue(self):
        return self.startWavelength
    
    @Property(float, notify=endWavelengthChanged)
    def endWavelengthValue(self):
        return self.endWavelength
    
    @Property(int, notify=numStepsChanged)
    def numStepsValue(self):
        return self.numSteps
    
    @Slot(str)
    def setStartWavelength(self, value_str):
        self.startWavelength = float(value_str)
        self.startWavelengthChanged.emit()
        print(self.startWavelength)
    
    @Slot(str)
    def setEndWavelength(self, value_str):
        self.endWavelength = float(value_str)
        self.endWavelengthChanged.emit()
        print(self.endWavelength)
    
    @Slot(str)
    def setNumSteps(self, value_str):
        self.numSteps = int(value_str)
        self.numStepsChanged.emit()
        print(self.numSteps)
    
    @Slot(str)
    def setWavelength(self, target_str):
        self.targetWavelength = float(target_str)
        self.mono.goto(self.targetWavelength)
        self.currentWavelength = self.mono.position()
        self.waveChanged.emit()
        print('Wavelength set')
    
    @Slot()
    def openShutter(self):
        self.mono.open_shutter()
        print("Shutter opened")
        self.shutterState = "Open"
        self.shutterChanged.emit()
    
    @Slot()
    def closeShutter(self):
        self.mono.close_shutter()
        print("Shutter closed")
        self.shutterState = "Closed"
        self.shutterChanged.emit()

class LivePlot(QObject):

    """ Creates a window with live plot """
    
    def __init__(self):
        
        # Create plot window
        self.plot_window = pg.plot(title=" Live Plot ")
        self.plot_window.setLabel('left', 'Counts')
        self.plot_window.setLabel('bottom', 'Wavelength', units='nm')
        self.plot_window.showGrid(x=True, y=True)
        self.plot_curve = self.plot_window.plot(pen='y')
        
        # Current position data
        self.wavelengths = []
        self.measurements = []
    
    def resetPlot(self):
        """Reset plot"""
        self.wavelengths = []
        self.measurements = []
        self.plot_curve.setData([], [])
    
    def updatePlot(self, wavelength, measurement):
        """Add a data point and update plot"""
        self.wavelengths.append(wavelength)
        self.measurements.append(measurement)
        self.plot_curve.setData(self.wavelengths, self.measurements)
        pg.QtWidgets.QApplication.processEvents()  # Force GUI update
    
    def closeClose(self):
        """Close the plot window"""
        if self.plot_window:
            self.plot_window.close()

    """Live oscilloscope waveform viewer"""
    
    def __init__(self):
        super().__init__()
        
        self.digi = NIScopeClient()
        
        # Create plot window
        self.plot_window = pg.plot(title="Oscilloscope")
        self.plot_window.setLabel('left', 'Voltage', units='V')
        self.plot_window.setLabel('bottom', 'Sample')
        self.plot_window.showGrid(x=True, y=True)
        self.plot_curve = self.plot_window.plot(pen='y')
        
        self.is_viewing = False
        self.viewer_worker = None
        
        print("Oscilloscope initialized")
    
    @Slot()
    def startLiveView(self):
        """Start continuous live viewing"""
        if self.is_viewing:
            print("Already viewing")
            return
        
        self.is_viewing = True
        self.viewer_worker = Worker(self._liveViewLoop)
        self.viewer_worker.start()
        print("Live view started")
    
    def _liveViewLoop(self):
        """Continuously capture and display waveforms"""
        while self.viewer_worker._is_running and self.is_viewing:
            try:
                # Capture waveform
                with niscope.Session("Dev1") as session:
                    session.channels[1].configure_vertical(range=40.0, coupling=niscope.VerticalCoupling.DC)
                    session.configure_horizontal_timing(
                        min_sample_rate=5000000,
                        min_num_pts=500,
                        ref_position=50.0,
                        num_records=1,
                        enforce_realtime=True
                    )
                
                    with session.initiate():
                        waveforms = session.channels[1].fetch()
                
                wfm = waveforms[0]
                samples = np.array(wfm.samples)
                
                # Update plot (PyQtGraph is thread-safe for this)
                self.plot_curve.setData(samples)
                
            except Exception as e:
                print(f"Error in live view: {e}")
                break
        
        print("Live view stopped")
    
    @Slot()
    def stopLiveView(self):
        """Stop live viewing"""
        self.is_viewing = False
        if self.viewer_worker:
            self.viewer_worker.stop()
        print("Stopping live view...")
    
    @Slot()
    def captureSingle(self):
        """Capture and display a single waveform"""
        try:
            with niscope.Session("Dev1") as session:
                session.channels[1].configure_vertical(range=40.0, coupling=niscope.VerticalCoupling.DC)
                session.configure_horizontal_timing(
                    min_sample_rate=5000000,
                    min_num_pts=5000000,
                    ref_position=50.0,
                    num_records=1,
                    enforce_realtime=True
                )
            
                with session.initiate():
                    waveforms = session.channels[1].fetch()
            
            wfm = waveforms[0]
            samples = np.array(wfm.samples)
            
            # Update plot
            self.plot_curve.setData(samples)
            print(f"Captured {len(samples)} samples")
            
        except Exception as e:
            print(f"Error capturing: {e}")
    
    def closePlot(self):
        """Close the plot window"""
        self.stopLiveView()
        if self.plot_window:
            self.plot_window.close()



class PMTShield(QObject):
    
    gainChanged = Signal()

    def __init__(self):
        super().__init__()
        self._gain = 0.0  # Make it a float
        self.pmt = ArduinoClient("COM4", 115200)
        print("PMT Gain Shield Online")
        

    # --- Current gain value ---
    @Property(float, notify=gainChanged)
    def gain(self):
        return self._gain

    # --- Changing gain value (called from QML) ---
    @Slot(str)
    def changeGain(self, desiredGain):
        self._gain = float(desiredGain)  # Convert string to float!
        self.pmt.commandSend(f"{self._gain:.3f}")
        print(f"Gain set to: {self._gain:.3f}")
        self.gainChanged.emit()


class TLCameraImageProvider(QQuickImageProvider):
    """QML image provider for TLCameraCore live frames.
    Registered as 'camera'; frames are requested via image://camera/frame?t=N."""

    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._current_frame = QImage(1440, 1080, QImage.Format.Format_Grayscale8)
        self._current_frame.fill(0)

    def requestImage(self, id, size, requestedSize):
        return self._current_frame

    def update_frame(self, qimage):
        self._current_frame = qimage


class TLCameraCore(QObject):
    """Hardware core for Thorlabs CS165MU (TL SDK) camera via pylablib."""

    frameChanged = Signal()
    exposureChanged = Signal()
    statusChanged = Signal()

    def __init__(self, camera_index=0, image_provider=None):
        super().__init__()
        self._camera_index = camera_index
        self._image_provider = image_provider
        self._exposure_ms = 10.0
        self._status = "Disconnected"
        self._is_live = False
        self._frame_counter = 0
        self._live_worker = None
        self._camera = None

        try:
            self._camera = ThorlabsTLCamera()
            self._status = "Connected"
            print("TLCameraCore online")
        except Exception as e:
            self._status = f"Error: {e}"
            print(f"TLCameraCore failed to connect: {e}")
        self.statusChanged.emit()

    # --- Properties ---

    @Property(str, notify=frameChanged)
    def liveFrame(self):
        return f"image://camera/frame?t={self._frame_counter}"

    @Property(float, notify=exposureChanged)
    def exposure(self):
        return self._exposure_ms

    @Property(str, notify=statusChanged)
    def status(self):
        return self._status

    # --- Slots ---

    @Slot(str)
    def setExposure(self, value_str):
        try:
            val = float(value_str)
            self._exposure_ms = val
            if self._camera is not None:
                self._camera.set_exposure(val / 1000.0)  # pylablib takes seconds
            self.exposureChanged.emit()
        except (ValueError, Exception):
            pass

    @Slot()
    def startLiveView(self):
        if self._is_live or self._camera is None:
            return
        self._is_live = True
        self._status = "Live"
        self.statusChanged.emit()

        def live_loop():
            try:
                self._camera.start_acquisition(nframes=100)
                while self._is_live:
                    try:
                        frame = self._camera.read_oldest_image(timeout=1.0)
                    except Exception:
                        # transient timeout or buffer miss — keep looping
                        continue
                    if frame is not None and self._image_provider is not None:
                        qimage = self._numpy_to_qimage(frame)
                        self._image_provider.update_frame(qimage)
                        self._frame_counter += 1
                        self.frameChanged.emit()
            except Exception as e:
                self._status = f"Error: {e}"
                self.statusChanged.emit()
            finally:
                try:
                    self._camera.stop_acquisition()
                except Exception:
                    pass
                self._is_live = False
                self._status = "Connected"
                self.statusChanged.emit()

        self._live_worker = Worker(live_loop)
        self._live_worker.start()

    @Slot()
    def stopLiveView(self):
        self._is_live = False
        if self._live_worker is not None:
            self._live_worker.stop()

    @Slot()
    def close(self):
        self.stopLiveView()
        if self._camera is not None:
            try:
                self._camera.close()
            except Exception:
                pass

    # --- Python-only capture methods (call stopLiveView() first) ---

    def captureFrame(self):
        """Capture a single frame. Returns a uint16 numpy array or None."""
        if self._camera is None:
            return None
        try:
            self._camera.start_acquisition(nframes=1)
            frame = self._camera.read_oldest_image(timeout=2.0)
            self._camera.stop_acquisition()
            return frame
        except Exception as e:
            print(f"TLCameraCore captureFrame error: {e}")
            return None

    def captureAveraged(self, n):
        """Capture n frames and return their float64 mean, or None on failure."""
        if self._camera is None:
            return None
        try:
            self._camera.start_acquisition(nframes=n)
            frames = []
            for _ in range(n):
                frame = self._camera.read_oldest_image(timeout=2.0)
                if frame is not None:
                    frames.append(frame.astype(np.float64))
            self._camera.stop_acquisition()
            if not frames:
                return None
            return np.mean(frames, axis=0)
        except Exception as e:
            print(f"TLCameraCore captureAveraged error: {e}")
            return None

    # --- Internal helpers ---

    def _numpy_to_qimage(self, arr):
        """Normalise a uint16 2D array to uint8 and wrap in a QImage."""
        lo, hi = arr.min(), arr.max()
        if hi > lo:
            arr8 = ((arr.astype(np.float32) - lo) / (hi - lo) * 255).astype(np.uint8)
        else:
            arr8 = np.zeros_like(arr, dtype=np.uint8)
        arr8 = np.ascontiguousarray(arr8)
        h, w = arr8.shape
        qimg = QImage(arr8.data, w, h, w, QImage.Format.Format_Grayscale8)
        return qimg.copy()  # copy ensures Python owns the pixel buffer
