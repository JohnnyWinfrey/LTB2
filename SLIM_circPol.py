import time
import numpy as np
from slim_helpers import saveHDF5

class SLIMEdgeCP():

    def __init__(self, PSG, PSA, spectrometer):
        self.PSG_DeathStar = PSG
        self.PSA_DeathStar = PSA
        self.spectro = spectrometer
        self.plotter = None
        print("SLIM AUTOMATION READY")

    def _edgeCP(self):
        all_data = []
        for x in range(0, 41, 1):                  # 0-20 mm in 0.5 mm steps
            if getattr(self, "_stop", False):
                break
            for angleStep in range(-45, 46, 90):   # LH / RH circular states
                if getattr(self, "_stop", False):
                    break
                for analyzeStep in range(-45, 91, 45):
                    if getattr(self, "_stop", False):
                        break

                    T2 = float(x / 2)
                    self.PSG_DeathStar.setPosition(str(angleStep), "0", "0")
                    self.PSA_DeathStar.setPosition(str(analyzeStep), str(analyzeStep), str(T2))
                    time.sleep(1)

                    wavelengths, intensities = self.spectro.takeSpectrum()
                    if self.plotter is not None:
                        self.plotter.setData(wavelengths, intensities)

                    angles = {"IW_Theta": 0, "IP_Theta": angleStep,
                              "CW_Theta": analyzeStep, "CP_Theta": analyzeStep}
                    all_data.append((angles, np.array(intensities), np.array(wavelengths)))

        self.PSA_DeathStar.resetHome()
        self.PSA_DeathStar.zHome()
        self.PSG_DeathStar.resetHome()

        if all_data:
            s = self.spectro
            saveHDF5(all_data, "CPscan",
                     name=s._sampleName, region=s._region, side=s._side,
                     scanX=s._scanX, scanY=s._scanY, integration=s.intTime)
        return all_data


if __name__ == "__main__":
    from auto_gui import run_gui, LivePlot

    sim = 1
    if sim:
        from hardware import FakeDeathStar as DeathStar, FakeSpectreCore as Spectro
        psg = DeathStar(id="PSG")
        psa = DeathStar(ZAxis=True, id="PSA")
        spectro = Spectro()
    else:
        from hardware import DeathStar, SpectreCore as Spectro
        psg = DeathStar("COM10", False, "PSG")
        psa = DeathStar("COM9", True, "PSA")
        spectro = Spectro()

    slim = SLIMEdgeCP(psg, psa, spectro)
    slim.plotter = LivePlot(title="SLIM live spectrum", xlabel="wavelength (nm)",
                            ylabel="counts", mode="replace")

    run_gui(
        automation=slim,
        run=slim._edgeCP,
        hardware=[psg, psa, spectro],
        title="SLIM Circular Polarization (CP)",
    )
