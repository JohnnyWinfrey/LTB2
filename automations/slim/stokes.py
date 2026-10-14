import time
import numpy as np
from .helpers import saveHDF5

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
        self.avgStepTime = []
        for angleStep in range(0, 91, 10):
            if getattr(self, "_stop", False):    # Stop button pressed?
                break
            t0 = time.time()
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
            t1=time.time()

            self.avgStepTime.append(t1-t0)
            self.progress(angleStep, 10, np.average(self.avgStepTime))

        self.PSG_DeathStar.home()
        self.PSA_DeathStar.home()

        # Save everything collected (skip if stopped before the first scan).
        if all_data:
            s = self.spectro
            saveHDF5(all_data, "stokesScan",
                     name=s.sampleName, region=s.region, side=s.side,
                     scanX=s.scanX, scanY=s.scanY, integration=s.intTime,
                     sta=s.scansToAvg)
        return all_data


TITLE = "SLIM Stokes"


def main(sim=False):
    from auto_gui import run_gui, LivePlot
    from . import experiment

    psg, psa, spectro = experiment.psg(sim), experiment.psa(sim), experiment.spectrometer(sim)
    slim = SLIMStokes(psg, psa, spectro)
    slim.plotter = LivePlot(title="SLIM live spectrum", xlabel="wavelength (nm)",
                            ylabel="counts", mode="replace")

    run_gui(
        automation=slim,
        run=slim._stokes,
        hardware=[psg, psa, spectro],
        title=TITLE,
    )


if __name__ == "__main__":
    import sys
    main(sim="--sim" in sys.argv)
