import time

import numpy as np

from .helpers import saveHDF5


class SLIMDRMCalibration():

    def __init__(self, medusa, spectrometer):
        super().__init__()
        self.medusa = medusa
        self.spectro       = spectrometer
        self.plotter       = None   # optional auto_gui.LivePlot (replace mode)
        self.settleWait    = 1      # s after each move (setPosition already waits for motion)

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

                self.medusa.setPosition(psgPol=0, psgWave=psg_angle,
                                        psaPol=0, psaWave=psa_angle)
                time.sleep(self.settleWait)

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
            self.medusa.home()

        # Save everything collected (skip if stopped before the first scan).
        if all_data:
            s = self.spectro
            saveHDF5(all_data, "muellerScan",
                     name=s.sampleName, region=s.region, side=s.side,
                     scanX=s.scanX, scanY=s.scanY, integration=s.intTime,
                     sta=s.scansToAvg)
        return all_data


TITLE = "DRM Calibration"


def main(sim=False):
    from auto_gui import run_gui, LivePlot
    from . import experiment

    medusa, spectro = experiment.medusa(sim), experiment.spectrometer(sim)
    slim = SLIMDRMCalibration(medusa, spectro)
    slim.plotter = LivePlot(title="SLIM live spectrum", xlabel="wavelength (nm)",
                            ylabel="counts", mode="replace")

    run_gui(
        automation=slim,
        run=slim._dualRotatingWaveplate,
        hardware=[medusa, spectro],
        title=TITLE,
    )


if __name__ == "__main__":
    import sys
    main(sim="--sim" in sys.argv)
