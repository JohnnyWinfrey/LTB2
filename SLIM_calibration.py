import time

import numpy as np
import pandas as pd


class SLIMCalibration():

    def __init__(self, PSG, PSA, powerMeter):
        super().__init__()
        self.PSG_DeathStar = PSG
        self.PSA_DeathStar = PSA
        self.powerMeter    = powerMeter

        print("SLIM AUTOMATION READY")

    # ──────────────────────────────────────────────────────────────────────
    # Scan sequences
    # ──────────────────────────────────────────────────────────────────────
    def _dualRotatingWaveplate(self):
        psg_waveplate_angles = np.linspace(0, 360, 61)
        intensities = []
        psa_waveplate_angles = []
        try:
            # Open the meter once at the start of the run.
            self.powerMeter.open()
            for i in range(len(psg_waveplate_angles)):
                # Cooperative stop: auto_gui's Stop button sets self._stop.
                if getattr(self, "_stop", False):
                    break
                print(i)
                psa_waveplate_angles.append(psg_waveplate_angles[i] * 5)
                self.PSG_DeathStar.setPosition("0", str(psg_waveplate_angles[i]))
                self.PSA_DeathStar.setPosition("0", str(psa_waveplate_angles[i]))
                time.sleep(1)

                intensities.append(self.powerMeter.measure())  # single power reading
                
                stepTime = 5
                totalSteps = len(psg_waveplate_angles)
                
                self.progress(i, totalSteps, stepTime)

                # Live view: safe to call from this worker thread -- LivePlot
                # marshals the point to the GUI thread. No-op if none attached.
                
                self.plotter.append(psg_waveplate_angles[i], intensities[-1])

        finally:
            # Always release the meter, even if a scan raised.
            self.powerMeter.close()

        # Save results to CSV. psa angles may be shorter than psg if the run
        # was stopped early, so trim all three to the completed count.
        n = len(intensities)
        pd.DataFrame({
            'Intensities': intensities,
            'PSG_Angles': psg_waveplate_angles[:n],
            'PSA_Angles': psa_waveplate_angles[:n],
        }).to_csv('output.csv', index=False)

        return (intensities, psg_waveplate_angles, psa_waveplate_angles)


if __name__ == "__main__":
    import sys
    from auto_gui import run_gui, LivePlot

    sim = 1#"--sim" in sys.argv
    if sim:
        from hardware import FakeDeathStar as DeathStar, FakePowerMeter as Meter
        psg = DeathStar(id="PSG")
        psa = DeathStar(id="PSA")
        meter = Meter()
    else:
        from hardware import DeathStar
        from hardware import PowerMeter as Meter
        psg = DeathStar("COM10", False, "PSG")
        psa = DeathStar("COM9", True, "PSA")
        meter = Meter()

    slim = SLIMCalibration(psg, psa, meter)

    slim.plotter = LivePlot(title="SLIM sweep", xlabel="PSG angle (deg)",
                            ylabel="intensity", mode="append")

    run_gui(
        automation=slim,
        run=slim._dualRotatingWaveplate,
        hardware=[psg, psa, meter],
        title="SLIM Calibration",
    )
