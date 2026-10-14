import time

import numpy as np

from .helpers import saveHDF5


class SLIMDRMCalibration():

    def __init__(self, PSG, PSA, spectrometer):
        super().__init__()
        self.PSG_DeathStar = PSG
        self.PSA_DeathStar = PSA
        self.spectro       = spectrometer
        self.plotter       = None   # optional auto_gui.LivePlot (replace mode)
        self.DeathStarWait = 1

        print("SLIM AUTOMATION READY")

    # ──────────────────────────────────────────────────────────────────────
    # Scan sequences
    # ──────────────────────────────────────────────────────────────────────
    def _dualRotatingWaveplate(self):
        numSteps = 61
        psg_waveplate_angles = np.linspace(0, 360, numSteps)

        all_data = []
        self.avgStepTime = []
        try:
            for i in range(len(psg_waveplate_angles)):
                # Cooperative stop: auto_gui's Stop button sets self._stop.
                if getattr(self, "_stop", False): 
                    break
                t0=time.time()

                psg_angle = psg_waveplate_angles[i]
                psa_angle = psg_angle * 5   # PSA waveplate spins 5x the PSG's

                self.PSG_DeathStar.setPosition("0", str(psg_angle))
                self.PSA_DeathStar.setPosition("0", str(psa_angle))
                time.sleep(self.DeathStarWait)

                wavelengths, intensities = self.spectro.takeSpectrum()
                if self.plotter is not None:
                    self.plotter.setData(wavelengths, intensities)   # live spectrum

                angles = {"IW_Theta": psg_angle, "IP_Theta": 0,
                          "CW_Theta": psa_angle, "CP_Theta": 0}
                all_data.append((angles, np.array(intensities), np.array(wavelengths)))


                t1 = time.time()
                self.avgStepTime.append(t1-t0)
                self.progress(i, numSteps, np.average(self.avgStepTime))

        finally:
            self.PSG_DeathStar.home()
            self.PSA_DeathStar.home()

        # Save everything collected (skip if stopped before the first scan).
        if all_data:
            s = self.spectro
            saveHDF5(all_data, "muellerScan",
                     name=s.sampleName, region=s.region, side=s.side,
                     scanX=s.scanX, scanY=s.scanY, integration=s.intTime,
                     sta=s.scansToAvg)
        return all_data


TITLE = "SLIM DRM Calibration"


def main(sim=False):
    from auto_gui import run_gui, LivePlot
    from . import experiment

    psg, psa, spectro = experiment.psg(sim), experiment.psa(sim), experiment.spectrometer(sim)
    slim = SLIMDRMCalibration(psg, psa, spectro)
    slim.plotter = LivePlot(title="SLIM live spectrum", xlabel="wavelength (nm)",
                            ylabel="counts", mode="replace")

    run_gui(
        automation=slim,
        run=slim._dualRotatingWaveplate,
        hardware=[psg, psa, spectro],
        title=TITLE,
    )


if __name__ == "__main__":
    import sys
    main(sim="--sim" in sys.argv)
