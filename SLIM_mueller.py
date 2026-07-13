import time
import numpy as np
from slim_helpers import saveHDF5

class SLIMMueller():

    def __init__(self, PSG, PSA, spectrometer):
        self.PSG_DeathStar = PSG
        self.PSA_DeathStar = PSA
        self.spectro = spectrometer
        self.plotter = None
        # Hardcoded scan params -- edit as needed:
        self.theta = 20
        self.N = 16
        print("SLIM AUTOMATION READY")

    def _mueller(self):
        all_data = []
        for value in range(self.theta, (self.theta * self.N) + 1, self.theta):
            if getattr(self, "_stop", False):
                break

            self.PSG_DeathStar.setPosition("0", str(value))
            self.PSA_DeathStar.setPosition("0", str(value * 5))
            time.sleep(1)

            wavelengths, intensities = self.spectro.takeSpectrum()
            if self.plotter is not None:
                self.plotter.setData(wavelengths, intensities)

            angles = {"IW_Theta": value, "IP_Theta": 0,
                      "CW_Theta": value * 5, "CP_Theta": 0}
            all_data.append((angles, np.array(intensities), np.array(wavelengths)))
            print(f"Collection at R1: {value}  R2: {value * 5}")

        # Home (also unwinds Mueller's >360 accumulation so manual moves are safe).
        self.PSA_DeathStar.resetHome()
        self.PSA_DeathStar.zHome()
        self.PSG_DeathStar.resetHome()

        if all_data:
            s = self.spectro
            saveHDF5(all_data, "muellerScan",
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

    slim = SLIMMueller(psg, psa, spectro)
    slim.plotter = LivePlot(title="SLIM live spectrum", xlabel="wavelength (nm)",
                            ylabel="counts", mode="replace")

    run_gui(
        automation=slim,
        run=slim._mueller,
        hardware=[psg, psa, spectro],
        title="SLIM Mueller",
    )
