import sys
import os
from pathlib import Path

os.environ["QT_QUICK_CONTROLS_STYLE"] = "Fusion"

from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QUrl, QObject, Slot, Signal

class App(QObject):
    pageChanged = Signal(str)
    
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.backends = {}  # Store all backends here
    
    @Slot(str)
    def load(self, automation):
        print(f"Loading {automation}...")
        
        if automation == "extinction":
            from cores import XWing, Cornerstone, PMTShield
            from automation_clusters import HyperSpectralExtinction
            
            self.backends = {
                'xwing': XWing(),
                'cornerstone': Cornerstone(),
                'pmt': PMTShield()
            }
            self.backends['automation'] = HyperSpectralExtinction(
                self.backends['xwing'], 
                self.backends['cornerstone'], 
                self.backends['pmt']
            )
            
            self.engine.rootContext().setContextProperty("XWingBackend", self.backends['xwing'])
            self.engine.rootContext().setContextProperty("CornerstoneBackend", self.backends['cornerstone'])
            self.engine.rootContext().setContextProperty("PMTGainShieldBackend", self.backends['pmt'])
            self.engine.rootContext().setContextProperty("ExtinctionBackend", self.backends['automation'])
            
            self.pageChanged.emit("extinction_main.qml")
            
        elif automation == "singlefluor":
            from cores import XWing, Cornerstone, PMTShield
            from automation_clusters import HyperSpectralSingleFluor
            
            self.backends = {
                'xwing': XWing(),
                'cornerstone': Cornerstone(),
                'pmt': PMTShield()
            }
            self.backends['automation'] = HyperSpectralSingleFluor(
                self.backends['xwing'], 
                self.backends['cornerstone'], 
                self.backends['pmt']
            )
            
            self.engine.rootContext().setContextProperty("XWingBackend", self.backends['xwing'])
            self.engine.rootContext().setContextProperty("CornerstoneBackend", self.backends['cornerstone'])
            self.engine.rootContext().setContextProperty("PMTGainShieldBackend", self.backends['pmt'])
            self.engine.rootContext().setContextProperty("SingleFluorBackend", self.backends['automation'])
            
            self.pageChanged.emit("singlefluor_main.qml")
            
        elif automation == "slim":
            from cores import DeathStar
            from automation_clusters import SLIM
            
            self.backends = {
                'deathstar1': DeathStar()
            }
            self.backends['automation'] = SLIM(self.backends['deathstar1'])
            
            self.engine.rootContext().setContextProperty("DeathStar1Backend", self.backends['deathstar1'])
            self.engine.rootContext().setContextProperty("DeathStar2Backend", self.backends['deathstar1'])
            self.engine.rootContext().setContextProperty("SLIMBackend", self.backends['automation'])
            
            self.pageChanged.emit("slim_main.qml")
    
    @Slot()
    def home(self):
        self.pageChanged.emit("HomePage.qml")

app = QApplication(sys.argv)
engine = QQmlApplicationEngine()
app_backend = App(engine)

engine.rootContext().setContextProperty("App", app_backend)
engine.load(Path(__file__).parent / "components/MainWindow.qml")

sys.exit(app.exec())