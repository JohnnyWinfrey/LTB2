import time
import numpy as np
from slim_helpers import saveHDF5

class SLIMStokes():

    def __init__(self, PSG, PSA, spectrometer):
        self.PSG_DeathStar = PSG
        self.PSA_DeathStar = PSA
        self.spectro = spectrometer
        self.plotter = None      # optional auto_gui.LivePlot (replace mode)
        print("SLIM AUTOMATION READY")

    # ──────────────────────────────────────────────────────────────────────
    # Scan sequences
    # ──────────────────────────────────────────────────────────────────────
    def _stokes(self):
        stokes_IP = [0, 45, 45, 0]   # PSA polarizer angles
        stokes_CW = [0, 0, 45, 45]   # PSA waveplate angles

        all_data = []
        for angleStep in range(0, 91, 10):
            if getattr(self, "_stop", False):    # Stop button pressed?
                break
            for s in range(len(stokes_IP)):
                if getattr(self, "_stop", False):
                    break

                self.PSG_DeathStar.setPosition(str(angleStep), str(angleStep))
                self.PSA_DeathStar.setPosition(str(stokes_IP[s]), str(stokes_CW[s]))
                time.sleep(1)

                wavelengths, intensities = self.spectro.takeSpectrum()
                if self.plotter is not None:
                    self.plotter.setData(wavelengths, intensities)   # live spectrum

                angles = {"IW_Theta": angleStep, "IP_Theta": angleStep,
                          "CW_Theta": stokes_CW[s], "CP_Theta": stokes_IP[s]}
                all_data.append((angles, np.array(intensities), np.array(wavelengths)))

        self.PSG_DeathStar.home()
        self.PSA_DeathStar.home()

        # Save everything collected (skip if stopped before the first scan).
        if all_data:
            s = self.spectro
            saveHDF5(all_data, "stokesScan",
                     name=s._sampleName, region=s._region, side=s._side,
                     scanX=s._scanX, scanY=s._scanY, integration=s.intTime)
        return all_data


if __name__ == "__main__":
    from auto_gui import run_gui, LivePlot

    sim = 0
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

    slim = SLIMStokes(psg, psa, spectro)
    slim.plotter = LivePlot(title="SLIM live spectrum", xlabel="wavelength (nm)",
                            ylabel="counts", mode="replace")

    run_gui(
        automation=slim,
        run=slim._stokes,
        hardware=[psg, psa, spectro],
        title="SLIM Stokes",
    )
