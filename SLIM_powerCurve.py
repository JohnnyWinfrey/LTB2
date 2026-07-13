import time

import numpy as np
import pandas as pd

from slim_helpers import progressBarCoolStyle


class SLIMPowerCurve():

    def __init__(self, PSG, powerMeter):
        super().__init__()
        self.PSG_DeathStar = PSG
        self.powerMeter    = powerMeter
        # Seconds to wait after each move before reading (0 in sim mode).

        print("SLIM AUTOMATION READY")

    # ──────────────────────────────────────────────────────────────────────
    # Scan sequences
    # ──────────────────────────────────────────────────────────────────────
    def _powerCurve(self):
        psg_angles = np.linspace(0, 90, 10)
        intensities = []
        psa_angles = []
        try:
            # Open the meter once at the start of the run.
            self.powerMeter.open(488)
            for i in range(len(psg_angles)):
                # Cooperative stop: auto_gui's Stop button sets self._stop.
                if getattr(self, "_stop", False):
                    break
                print(i)
                self.PSG_DeathStar.setPosition(str(psg_angles[i]), str(psg_angles[i]))
                time.sleep(1)

                intensities.append(self.powerMeter.measure())  # single power reading
                progressBarCoolStyle(len(psg_angles), len(psa_angles))

                # Live view: safe to call from this worker thread -- LivePlot
                # marshals the point to the GUI thread. No-op if none attached.
                
                self.plotter.append(psg_angles[i], intensities[-1])

        finally:
            self.PSG_DeathStar.home()
            # Always release the meter, even if a scan raised.
            self.powerMeter.close()

        # Save results to CSV. psa angles may be shorter than psg if the run
        # was stopped early, so trim all three to the completed count.
        n = len(intensities)
        pd.DataFrame({
            'Intensities': intensities,
            'PSG_Angles': psg_angles[:n],
        }).to_csv('calibration/powerCurve.csv', index=False)

        return (intensities, psg_angles)


if __name__ == "__main__":
    import sys
    from auto_gui import run_gui, LivePlot

    sim = 0#"--sim" in sys.argv
    if sim:
        from hardware import FakeDeathStar as DeathStar, FakePowerMeter as Meter
        psg = DeathStar(id="PSG")
        meter = Meter()
    else:
        from hardware import DeathStar
        from hardware import PowerMeter as Meter
        psg = DeathStar("COM10", False, "PSG")
        meter = Meter()

    slim = SLIMPowerCurve(psg, meter)

    slim.plotter = LivePlot(title="SLIM sweep", xlabel="PSG angle (deg)",
                            ylabel="intensity", mode="append")

    run_gui(
        automation=slim,
        run=slim._powerCurve,
        hardware=[psg, meter],
        title="SLIM Calibration",
    )
