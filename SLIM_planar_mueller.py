"""Planar Mueller scan -- the SLIM_DRM dual-rotating-waveplate sequence run at
every point of a translation scan.

The sample stage is the Z axis of the PSA DeathStar (the same "xwing" travel
SLIM_planarDiffraction drives): 41 points, 0-20 mm in 0.5 mm steps. At each
point the PSG waveplate steps through a full rotation while the PSA waveplate
spins 5x as fast (see SLIM_DRM.py); the whole angle sweep is written to its own
group in the HDF5 file, keyed by the stage location, so one file holds a
Mueller matrix per point.
"""
import time

import numpy as np

from slim_helpers import saveMuellerHDF5


class SLIMPlanarMueller():

    def __init__(self, PSG, PSA, spectrometer):
        super().__init__()
        self.PSG_DeathStar = PSG
        self.PSA_DeathStar = PSA
        self.spectro       = spectrometer
        self.plotter       = None   # optional auto_gui.LivePlot (replace mode)
        self.DeathStarWait = 1

        # Stage line scan: 41 points, 0-20 mm in 0.5 mm steps (same travel as
        # SLIM_planarDiffraction).
        self.numPoints  = 41
        self.stepSize   = 0.5
        self.stageWait  = 4         # s to let the Z stage settle after a move
        self.numAngles  = 61        # PSG waveplate steps over a full rotation

        print("SLIM AUTOMATION READY")

    # ──────────────────────────────────────────────────────────────────────
    # Scan sequences
    # ──────────────────────────────────────────────────────────────────────
    def _dualRotatingWaveplate(self):
        """One full DRM angle sweep at the current stage position."""
        psg_waveplate_angles = np.linspace(0, 360, self.numAngles)

        all_data = []
        for i in range(len(psg_waveplate_angles)):
            # Cooperative stop: auto_gui's Stop button sets self._stop.
            if getattr(self, "_stop", False):
                break

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

        return all_data

    def _planarMueller(self):
        """Walk the PSA Z stage and run a DRM sweep at every point."""
        points = []
        self.avgStepTime = []
        try:
            for p in range(self.numPoints):
                if getattr(self, "_stop", False):
                    break
                t0 = time.time()

                # Translate, parking both waveplates at the sweep's start angle
                # in the same move, then let the stage settle.
                T2 = float(p * self.stepSize)
                print(f"Point {p + 1}/{self.numPoints}: T2={T2}")
                self.PSG_DeathStar.setPosition("0", "0")
                self.PSA_DeathStar.setPosition("0", "0", str(T2))
                time.sleep(self.stageWait)

                all_data = self._dualRotatingWaveplate()
                # Only keep complete sweeps: a run stopped part-way through one
                # never covers the full 360 deg rotation, so it cannot be
                # inverted into a Mueller matrix -- saving it would look like a
                # good point and quietly poison the processing.
                if len(all_data) == self.numAngles:
                    points.append(({'z': T2}, all_data))
                elif all_data:
                    print(f"  discarding partial sweep at T2={T2} "
                          f"({len(all_data)}/{self.numAngles} angles)")

                # Progress bar stuff
                t1 = time.time()
                self.avgStepTime.append(t1 - t0)
                self.progress(p, self.numPoints, np.average(self.avgStepTime))

        finally:
            self.PSA_DeathStar.resetHome()
            self.PSA_DeathStar.zHome()
            self.PSG_DeathStar.resetHome()

        # Save everything collected (skip if stopped before the first point).
        if points:
            s = self.spectro
            saveMuellerHDF5(points, "planarMuellerScan",
                            name=s.sampleName, region=s.region, side=s.side,
                            integration=s.intTime, sta=s.scansToAvg)
        return points


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

    slim = SLIMPlanarMueller(psg, psa, spectro)

    slim.plotter = LivePlot(title="SLIM live spectrum", xlabel="wavelength (nm)",
                            ylabel="counts", mode="replace")

    run_gui(
        automation=slim,
        run=slim._planarMueller,
        hardware=[psg, psa, spectro],
        title="SLIM Planar Mueller",
    )
