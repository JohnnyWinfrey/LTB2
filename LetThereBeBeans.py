import subprocess
import sys

from auto_gui import run_gui


class Automations:
    def SLIM_PowerCurve(self):
        self._run("SLIM_powerCurve.py")
    def SLIM_Calibration(self):  
        self._run("SLIM_calibration.py")

    def SLIM_Stokes(self):       
        self._run("SLIM_stokes.py")

    def SLIM_Mueller(self):      
        self._run("SLIM_mueller.py")
        
    def SLIM_PlanarDiffraction(self):       
        self._run("SLIM_planarDiffraction.py")
 
    def SLIM_CircPol(self):       
        self._run("SLIM_circPol.py")

    def Hyperspectral_Extinction(self):        
        self._run("Hyperspectral_extinction.py")
        
    def Hyperspectral_SingleFluor(self):      
        self._run("Hyperspectral_singleFluor.py")

    def _run(self, script):
        # New process => its own QApplication; doesn't block this menu.
        subprocess.Popen([sys.executable, script])
        print(f"launched {script}")


if __name__ == "__main__":
    # No automation => run_gui shows only this window (the menu), no Start/Stop.
    run_gui(hardware=[Automations()], title="LTB2")
