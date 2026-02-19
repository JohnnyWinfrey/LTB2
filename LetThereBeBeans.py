import sys
import os
from pathlib import Path

os.environ["QT_QUICK_CONTROLS_STYLE"] = "Fusion"

from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QUrl, QObject, Slot

class AppBackend(QObject):
    """Simple backend to switch between automations"""
    
    def __init__(self, engine, app_path):
        super().__init__()
        self.engine = engine
        self.app_path = app_path
    
    @Slot(str)
    def loadAutomation(self, automation_type):
        """Load the selected automation"""
        print(f"Loading {automation_type}...")
        
        # Clear old QML
        self.engine.clearComponentCache()
        
        # Import and create cores based on automation type
        if automation_type == "extinction":
            from cores import XWing, Cornerstone, PMTShield
            from automation_clusters import HyperSpectralExtinction
            
            xwing = XWing()
            cornerstone = Cornerstone()
            pmt = PMTShield()
            automation = HyperSpectralExtinction(xwing, cornerstone, pmt)
            
            self.engine.rootContext().setContextProperty("XWingBackend", xwing)
            self.engine.rootContext().setContextProperty("CornerstoneBackend", cornerstone)
            self.engine.rootContext().setContextProperty("ExtinctionBackend", automation)
            self.engine.rootContext().setContextProperty("PMTGainShieldBackend", pmt)
            
            # Load extinction GUI
            qml_file = self.app_path / "components/extinction_main.qml"
            
        elif automation_type == "singlefluor":
            from cores import XWing, Cornerstone
            from automation_clusters import HyperSpectralSingleFluor
            
            xwing = XWing()
            cornerstone = Cornerstone()
            automation = HyperSpectralSingleFluor(xwing, cornerstone)
            
            self.engine.rootContext().setContextProperty("XWingBackend", xwing)
            self.engine.rootContext().setContextProperty("CornerstoneBackend", cornerstone)
            self.engine.rootContext().setContextProperty("SingleFluorBackend", automation)
            
            # Load single fluor GUI
            qml_file = self.app_path / "components/singlefluor_main.qml"
            
        elif automation_type == "slim":
            # TODO: Add your SLIM cores here when ready
            from cores import DeathStar
            from automation_clusters import SLIM
            
            deathstar1 = DeathStar()
            automation = SLIM(deathstar1)
            
            self.engine.rootContext().setContextProperty("DeathStar1Backend", deathstar1)
            self.engine.rootContext().setContextProperty("DeathStar2Backend", deathstar1)
            self.engine.rootContext().setContextProperty("SLIMBackend", automation)
            
            # Load SLIM GUI
            qml_file = self.app_path / "components/slim_main.qml"
        
        # Load the new page
        self.engine.load(QUrl.fromLocalFile(str(qml_file)))

def main():
    app = QApplication(sys.argv)
    engine = QQmlApplicationEngine()
    app_path = Path(__file__).resolve().parent
    
    # Create simple backend
    app_backend = AppBackend(engine, app_path)
    engine.rootContext().setContextProperty("AppBackend", app_backend)
    
    # Load home page
    qml_file = app_path / "components/home.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()