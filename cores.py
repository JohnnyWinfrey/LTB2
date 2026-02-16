from PySide6.QtCore import QObject, Signal, Property, Slot, QThread
from PySide6.QtWidgets import QFileDialog
from hardware_controllers import *
import pyqtgraph as pg


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

    def __init__(self):
        super().__init__()
        self._x = 0.0
        self._y = 0.0
        self._posMem = 1
        self._home_x = 0.0
        self._home_y = 0.0
        self._step = 0.1  # mm per button press (change as needed)
        self.rate = 50
        self.ac = ArduinoClient("COM7", 115200)
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

# Important: What counts as Clockwise and Counterclockwise will be assuming you're looking 'towards' the incoming light

class DeathStar(QObject):
    
    wavePlateRotated = Signal()
    polarRotated = Signal()
    orientationChanged = Signal()

    def __init__(self):
        super().__init__()
        self._thetaW = 0
        self._thetaP = 0
        self._home_thetaW = 0
        self._home_thetaP = 0
        self._step = 120
        self.rate = 21000 
        self.ac = ArduinoClient("COM9", 115200)
        self.reference = None
        self.samples = []
        print("DeathStar online")



    # --- Wave Plate Anglular ---
    @Property(int, notify=wavePlateRotated)
    def wPos(self):
        return self._thetaW

    # --- Polarizer Angular Position  ---
    @Property(int, notify=polarRotated)
    def pPos(self):
        return self._thetaP

    # --- String versions for your labels ---
    @Property(str, notify=wavePlateRotated)
    def wPosString(self):
        return f"{self._thetaW:.3d}"

    @Property(str, notify=polarRotated)
    def pPosString(self):
        return f"{self._thetaP:.3d}"

    # --- Movement slots (called from QML. Test with cmd first) ---
    @Slot()
    def moveW_CW(self):
        
        self._thetaW += self._step
        self.ac.commandSend(f"G1 Y{self._thetaW} F{self.rate}")
        print("Move Up ->", self._thetaW)
        self.wavePlateRotated.emit()


    @Slot()
    def moveW_CC(self):
        
        self._thetaW -= self._step
        self.ac.commandSend(f"G1 Y{self._thetaW} F{self.rate}")
        print("Move Down ->", self._thetaW)
        self.wavePlateRotated.emit()

    @Slot()
    def moveP_CW(self):
        
        self._thetaP += self._step
        self.ac.commandSend(f"G1 X{self._thetaP} F{self.rate}")
        print("Rotate Right ->", self._thetaP)
        self.polarRotated.emit()

    @Slot()
    def moveP_CC(self):
        
        self._thetaP -= self._step
        self.ac.commandSend(f"G1 X{self._thetaP} F{self.rate}")
        print("Rotate Left ->", self._thetaP)
        self.polarRotated.emit()

    # It might be unnecessary to have be able to set 'home' for the rotating componets but I'll keep it in for testing
    @Slot()
    def home(self):
        self.ac.commandSend(f"G1 X{0} Y{0} F{self.rate}")
        self._thetaP = self._home_thetaP
        self._thetaW = self._home_thetaW
        print("Go Home ->", self._thetaP, self._thetaW)
        self.polarRotated.emit()
        self.wavePlateRotated.emit()

    @Slot()
    def setHome(self):
        self._home_thetaP = self._thetaP
        self._home_thetaW = self._thetaW
        print("Set Home ->", self._thetaP, self._thetaW)

    @Slot(str, str)
    def setPosition(self, p_str, w_str):
        self.ac.commandSend(f"G1 X{p_str} Y{w_str} F{self.rate}")
        if p_str.strip():
            self._thetaP = float(p_str)
        if w_str.strip():
            self._thetaW = float(w_str)
        print("Set Position ->", self._thetaP, self._thetaW)
        self.polarRotated.emit()
        self.wavePlateRotated.emit()


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

    """ Combined class with all cores. """
    # Re-declare all signals 
    xChanged = Signal()
    yChanged = Signal()
    waveChanged = Signal()
    shutterChanged = Signal()
    startWavelengthChanged = Signal()
    endWavelengthChanged = Signal()
    numStepsChanged = Signal()
    
    def __init__(self): # Initialize new cores here
        QObject.__init__(self)
        XWing.__init__(self)
        Cornerstone.__init__(self)
        print("MasterCore online")

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
    
    # Cornerstone properties
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
    
    # --- Movement slots (called from QML) ---
    @Slot()
    def moveUp(self):
        XWing.moveUp(self)

    @Slot()
    def moveDown(self):
        XWing.moveDown(self)

    @Slot()
    def moveRight(self):
        XWing.moveRight(self)

    @Slot()
    def moveLeft(self):
        XWing.moveLeft(self)

    @Slot()
    def home(self):
        XWing.home(self)

    @Slot()
    def setHome(self):
        XWing.setHome(self)

    @Slot(str, str)
    def setPosition(self, x_str, y_str):
        XWing.setPosition(self, x_str, y_str)

    @Slot(float, float)
    def storeCoordinates(self, x, y):
        XWing.storeCoordinates(self, x, y)

    @Slot()
    def recall(self):
        XWing.recall(self)
    
    # Cornerstone slots
    @Slot(str)
    def setStartWavelength(self, value_str):
        Cornerstone.setStartWavelength(self, value_str)
    
    @Slot(str)
    def setEndWavelength(self, value_str):
        Cornerstone.setEndWavelength(self, value_str)
    
    @Slot(str)
    def setNumSteps(self, value_str):
        Cornerstone.setNumSteps(self, value_str)
    
    @Slot(str)
    def setWavelength(self, target_str):
        Cornerstone.setWavelength(self, target_str)
    
    @Slot()
    def openShutter(self):
        Cornerstone.openShutter(self)
    
    @Slot()
    def closeShutter(self):
        Cornerstone.closeShutter(self)

    @Slot(str)
    def setSaveLocation(self, path):
        """Receive the selected path from QML"""
        self.save_directory = path
        print(f"Save location set to: {path}")