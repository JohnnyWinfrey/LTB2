"""
SLIM (Structured Illumination / Mueller Matrix) Automation
===========================================================
Run directly:  python slim_automation.py

Three control panels open automatically:
  - DeathStar PSG   (polarization state generator — polarizer + waveplate)
  - DeathStar PSA   (polarization state analyzer  — polarizer + waveplate)
  - Spectrometer    (integration time, scans to average, background)

Configure the spectrometer settings and take a background before scanning.
Each scan mode is a separate node card — click Run on the one you want.

NOTE (Mueller): Mueller is the only mode that rotates past 360°.
If cancelled mid-scan the stages will NOT auto-home, so the displayed angle
is N×360 + n internally. Home the stages manually before changing position.
"""

import os
import time
import numpy as np
import h5py
from datetime import datetime

from autogui import core, run
from cores import DeathStar, SpectreCore

# ── Hardware ─────────────────────────────────────────────────────────────────

psg    = DeathStar("COM10", False, "PSG")
psa    = DeathStar("COM9",  True,  "PSA")
spectro = SpectreCore()

# ── Scan logic ───────────────────────────────────────────────────────────────

class _SLIMScan:
    def __init__(self, spectro, psg, psa):
        self.spectro         = spectro
        self.PSG_DeathStar   = psg
        self.PSA_DeathStar   = psa
        self._cancel         = False
        self._total_steps    = 0
        self._current_step   = 0
        self._start_time     = None
        print("SLIM Automation Online")

    def cancel(self):
        self._cancel = True

    # ── Progress helpers ──────────────────────────────────────────────────────

    def _init_progress(self, total):
        self._total_steps  = total
        self._current_step = 0
        self._start_time   = time.time()
        print(f"Progress: 0/{total}")

    def _step_progress(self):
        self._current_step += 1
        n, t = self._current_step, self._total_steps
        if self._start_time and n > 0:
            elapsed  = time.time() - self._start_time
            avg      = elapsed / n
            remaining_mins = int(avg * (t - n) / 60) + 1
            eta = f" (~{remaining_mins} min remaining)" if remaining_mins > 1 else " (<1 min remaining)"
        else:
            eta = ""
        print(f"Progress: {n}/{t}{eta}")

    def _reset_progress(self):
        self._total_steps  = 0
        self._current_step = 0
        self._start_time   = None

    # ── Hardware helpers ──────────────────────────────────────────────────────

    def home_all(self):
        self.PSA_DeathStar.resetHome()
        self.PSA_DeathStar.zHome()
        self.PSG_DeathStar.resetHome()

    # ── Core measurement ──────────────────────────────────────────────────────

    def slim_scan(self, P1, R1, R2, P2, T1="", T2="", move_time=2):
        """Move both arms to position and acquire one spectrum.

        Returns (angles_dict, intensities_array, wavelengths_array).
        """
        self.PSG_DeathStar.setPosition(str(P1), str(R1), str(T1))
        self.PSA_DeathStar.setPosition(str(P2), str(R2), str(T2))
        print(str(T2))
        time.sleep(move_time)

        wavelengths, intensities = self.spectro.takeSpectrum()

        angles = {
            "IW_Theta": R1,
            "IP_Theta": P1,
            "CW_Theta": R2,
            "CP_Theta": P2,
        }
        return (angles, np.array(intensities), np.array(wavelengths))

    # ── Save ──────────────────────────────────────────────────────────────────

    def save_hdf5(self, all_data, scan_type):
        """Save list of (angles_dict, intensities, wavelengths) tuples to HDF5."""
        timestamp  = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        name       = self.spectro._sampleName or "sample"
        region     = self.spectro._region
        side       = self.spectro._side
        output_dir = os.path.join("data", f"{name}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        h5_path    = os.path.join(output_dir, f"{name}_Region{region}_{side}_{scan_type}.h5")

        angles_list = [d[0] for d in all_data]
        intensities = np.array([d[1] for d in all_data])
        wavelengths = all_data[0][2]

        with h5py.File(h5_path, "w") as f:
            f.attrs["region"]              = region
            f.attrs["side"]                = side
            f.attrs["x"]                   = self.spectro._scanX
            f.attrs["y"]                   = self.spectro._scanY
            f.attrs["integration_time_us"] = self.spectro.integration

            f.create_dataset("wavelength", data=wavelengths)

            for key in ["IW_Theta", "IP_Theta", "CW_Theta", "CP_Theta"]:
                f.create_dataset(key, data=np.array([a[key] for a in angles_list]))

            f.create_dataset(
                "intensity", data=intensities,
                compression="gzip", compression_opts=4,
            )

        print(f"Saved {len(all_data)} scans → {h5_path}")

    # ── Scan sequences ────────────────────────────────────────────────────────

    def run_mueller(self, theta=20, N=16):
        self._cancel = False
        self._init_progress(N)
        all_data = []

        for value in range(theta, (theta * N) + 1, theta):
            if self._cancel:
                break
            data = self.slim_scan(P1=0, R1=value, R2=value * 5, P2=0)
            all_data.append(data)
            print(f"Collection at R1: {value}  R2: {value * 5}")
            self._step_progress()

        self.save_hdf5(all_data, "muellerScan")
        self.home_all()
        self._reset_progress()

    def run_stokes(self):
        self._cancel = False
        stokes_IP = [0, 45, 45,  0]   # PSA polarizer angles
        stokes_CW = [0,  0, 45, 45]   # PSA waveplate angles
        num_angles = len(range(0, 91, 10))
        self._init_progress(num_angles * len(stokes_IP))

        all_data = []
        for angle_step in range(0, 91, 10):
            if self._cancel:
                break
            for s in range(len(stokes_IP)):
                if self._cancel:
                    break
                data = self.slim_scan(
                    P1=angle_step, R1=angle_step,
                    R2=stokes_CW[s], P2=stokes_IP[s],
                )
                all_data.append(data)
                self._step_progress()

        self.home_all()
        self.save_hdf5(all_data, "stokesScan")
        self._reset_progress()

    def run_cali(self):
        self._cancel = False
        self.spectro.takeBackground()

    def run_edge_lp(self):
        self._cancel = False
        num_x       = len(range(0, 41, 1))
        num_angle   = len(range(0, 136, 45))
        num_analyze = len(range(0, 91, 90))
        self._init_progress(num_x * num_angle * num_analyze)

        all_data = []
        for x in range(0, 41, 1):
            if self._cancel:
                break
            for angle_step in range(0, 136, 45):
                if self._cancel:
                    break
                for analyze_step in range(0, 91, 90):
                    if self._cancel:
                        break
                    data = self.slim_scan(
                        P1=angle_step,  R1=angle_step,
                        R2=analyze_step, P2=analyze_step,
                        T1=0, T2=float(x / 2),
                    )
                    all_data.append(data)
                    self._step_progress()

        self.save_hdf5(all_data, "LPscan")
        self.home_all()
        self._reset_progress()

    def run_edge_cp(self):
        self._cancel = False
        num_x       = len(range(0, 41, 1))
        num_angle   = len(range(-45, 46, 90))
        num_analyze = len(range(-45, 91, 45))
        self._init_progress(num_x * num_angle * num_analyze)

        all_data = []
        for x in range(0, 41, 1):
            if self._cancel:
                break
            for angle_step in range(-45, 46, 90):
                if self._cancel:
                    break
                for analyze_step in range(-45, 91, 45):
                    if self._cancel:
                        break
                    data = self.slim_scan(
                        P1=angle_step,   R1=0,
                        R2=analyze_step, P2=analyze_step,
                        T1=0, T2=float(x / 2),
                    )
                    all_data.append(data)
                    self._step_progress()

        self.save_hdf5(all_data, "CPscan")
        self.home_all()
        self._reset_progress()


_scan = _SLIMScan(spectro, psg, psa)


# ── Node cards ────────────────────────────────────────────────────────────────

#@core(stop=_scan.cancel)
def run_mueller():
    """
    Mueller matrix measurement (full 4×4 via rotating waveplates, 16 steps).
    Homes all axes when complete.
    WARNING: Rotates past 360° — home stages manually if cancelled mid-scan.
    """
    _scan.run_mueller()


@core(stop=_scan.cancel)
def stokes():
    """
    Stokes vector scan over PSG angles 0–90° in 10° steps, 4 PSA states each.
    """
    _scan.run_stokes()


#@core(stop=_scan.cancel)
def run_calibration():
    """
    Take a background spectrum for calibration (blocks until complete).
    Run this before any intensity scan.
    """
    _scan.run_cali()


@core(stop=_scan.cancel)
def planar_diffraction():
    """
    Planar diffraction edge scan using linear polarization states.
    Scans X position 0–20 mm in 0.5 mm steps, 3 PSG angles, 2 PSA angles.
    """
    _scan.run_edge_lp()


@core(stop=_scan.cancel)
def circ_pol():
    """
    Circular polarization edge scan (LH and RH circular states).
    Scans X position 0–20 mm in 0.5 mm steps.
    """
    _scan.run_edge_cp()


if __name__ == "__main__":
    run(title="SLIM Automation")
