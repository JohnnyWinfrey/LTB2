import time
import numpy as np
from slim_helpers import saveHDF5

class SLIMEdgeLP():

    def __init__(self, PSG, PSA, spectrometer):
        self.PSG_DeathStar = PSG
        self.PSA_DeathStar = PSA
        self.spectro = spectrometer
        self.plotter = None
        print("SLIM AUTOMATION READY")

    def _edgeLP(self):
        all_data = []
        numSteps = 41
        self.avgStepTime = []
        for x in range(numSteps):                 # 0-20 mm in 0.5 mm steps
            if getattr(self, "_stop", False):
                break
            t0 = time.time()
            for angleStep in range(0, 136, 45):   # PSG linear polarization states
                if getattr(self, "_stop", False):
                    break
                for analyzeStep in range(0, 91, 90):
                    if getattr(self, "_stop", False):
                        break

                    T2 = float(x / 2)
                    self.PSG_DeathStar.setPosition(str(angleStep), str(angleStep), "0")
                    self.PSA_DeathStar.setPosition(str(analyzeStep), str(analyzeStep), str(T2))
                    print(f"T2={T2}")
                    time.sleep(1)

                    wavelengths, intensities = self.spectro.takeSpectrum()
                    if self.plotter is not None:
                        self.plotter.setData(wavelengths, intensities)

                    angles = {"IW_Theta": angleStep, "IP_Theta": angleStep,
                              "CW_Theta": analyzeStep, "CP_Theta": analyzeStep}
                    all_data.append((angles, np.array(intensities), np.array(wavelengths)))

            # Progress bar stuff
            t1 = time.time()
            self.avgStepTime.append(t1-t0)
            self.progress(x, numSteps, np.average(self.avgStepTime))

        self.PSA_DeathStar.resetHome()
        self.PSA_DeathStar.zHome()
        self.PSG_DeathStar.resetHome()

        if all_data:
            s = self.spectro
            saveHDF5(all_data, "LPscan",
                     name=s.sampleName, region=s.region, side=s.side,
                     scanX=s.scanX, scanY=s.scanY, integration=s.intTime,
                     sta=s.scansToAvg)
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

    slim = SLIMEdgeLP(psg, psa, spectro)
    slim.plotter = LivePlot(title="SLIM live spectrum", xlabel="wavelength (nm)",
                            ylabel="counts", mode="replace")

    run_gui(
        automation=slim,
        run=slim._edgeLP,
        hardware=[psg, psa, spectro],
        title="SLIM Planar Diffraction (LP)",
    )
