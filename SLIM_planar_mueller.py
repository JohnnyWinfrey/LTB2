"""Planar Mueller scan -- the SLIM_DRM dual-rotating-waveplate sequence run at
every point of an XWing line scan.

At each of NUM_POINTS stage positions the PSG waveplate steps through a full
rotation while the PSA waveplate spins 5x as fast (see SLIM_DRM.py); the whole
angle sweep is written to its own group in the HDF5 file, keyed by the XWing
location, so one file holds a Mueller matrix per point.
"""
import time

import numpy as np

from slim_helpers import saveMuellerHDF5


class SLIMPlanarMueller():

    def __init__(self, xwing, PSG, PSA, spectrometer):
        super().__init__()
        self.xwing         = xwing
        self.PSG_DeathStar = PSG
        self.PSA_DeathStar = PSA
        self.spectro       = spectrometer
        self.plotter       = None   # optional auto_gui.LivePlot (replace mode)
        self.DeathStarWait = 1

        # XWing line scan: 40 points, 0.5 mm apart, along X (same pitch as
        # SLIM_planarDiffraction).
        self.numPoints  = 40
        self.stepSize   = 0.5
        self.stageAxis  = "x"       # "x" or "y"
        self.stageWait  = 4         # s to let the stage settle after a move

        print("SLIM AUTOMATION READY")

    # ──────────────────────────────────────────────────────────────────────
    # Scan sequences
    # ──────────────────────────────────────────────────────────────────────
    def _moveTo(self, x, y):
        """Send the XWing to (x, y) mm and wait for it to settle."""
        self.xwing.setPosition(str(x), str(y))
        time.sleep(self.stageWait)

    def _dualRotatingWaveplate(self):
        """One full DRM angle sweep at the current stage position."""
        numSteps = 61
        psg_waveplate_angles = np.linspace(0, 360, numSteps)

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
        """Walk the XWing and run a DRM sweep at every point."""
        # Start from wherever the stage was left (jog + Set Home in the XWing
        # window to pick the line's origin).
        x0, y0 = self.xwing._x, self.xwing._y

        points = []
        self.avgStepTime = []
        try:
            for p in range(self.numPoints):
                if getattr(self, "_stop", False):
                    break
                t0 = time.time()

                offset = p * self.stepSize
                x = x0 + offset if self.stageAxis == "x" else x0
                y = y0 + offset if self.stageAxis == "y" else y0
                print(f"Point {p + 1}/{self.numPoints}: X={x} Y={y}")
                self._moveTo(x, y)

                all_data = self._dualRotatingWaveplate()
                if all_data:
                    points.append(({'x': x, 'y': y}, all_data))

                # Progress bar stuff
                t1 = time.time()
                self.avgStepTime.append(t1 - t0)
                self.progress(p, self.numPoints, np.average(self.avgStepTime))

        finally:
            self.PSG_DeathStar.home()
            self.PSA_DeathStar.home()
            self.xwing.setPosition(str(x0), str(y0))

        # Save everything collected (skip if stopped before the first point).
        if points:
            s = self.spectro
            saveMuellerHDF5(points, "planarMuellerScan",
                            name=s.sampleName, region=s.region, side=s.side,
                            integration=s.intTime, sta=s.scansToAvg)
        return points


if __name__ == "__main__":
    from auto_gui import run_gui, LivePlot

    sim = 1
    if sim:
        from hardware import (FakeXWing as XWing, FakeDeathStar as DeathStar,
                              FakeSpectreCore as Spectro)
        xwing = XWing()
        psg = DeathStar(id="PSG")
        psa = DeathStar(ZAxis=True, id="PSA")
        spectro = Spectro()
    else:
        from hardware import XWing, DeathStar, SpectreCore as Spectro
        xwing = XWing("COM3")
        psg = DeathStar("COM10", False, "PSG")
        psa = DeathStar("COM9", True, "PSA")
        spectro = Spectro()

    slim = SLIMPlanarMueller(xwing, psg, psa, spectro)

    slim.plotter = LivePlot(title="SLIM live spectrum", xlabel="wavelength (nm)",
                            ylabel="counts", mode="replace")

    run_gui(
        automation=slim,
        run=slim._planarMueller,
        hardware=[xwing, psg, psa, spectro],
        title="SLIM Planar Mueller",
    )
