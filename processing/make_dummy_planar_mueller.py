"""Generate a dummy SLIM_planar_mueller output file for processing development.

Builds a physically consistent dual-rotating-retarder (DRRP) dataset: at each
of 41 stage points a known sample Mueller matrix is propagated through the
same optical train the rig uses ::

    analyzer(0 deg) . QWP(5*theta) . M_sample . QWP(theta) . polarizer(0 deg)

for theta = 0..360 in 61 steps, per wavelength. The data file is written
through automations.slim.helpers.saveMuellerHDF5, so its layout matches a real run.

Instrument realism is taken from a reference scan (a real single-point
muellerScan h5, --reference): its wavelength axis is reused verbatim
(non-uniform, ~398.8-1182.7 nm over 1044 pixels) and its mean spectrum becomes
the lamp x detector envelope, so the dead blue end and the ~870 nm peak are
where a processing script will actually find them. Counts are background
subtracted the way the rig delivers them -- a few hundred counts peak, drifting
slightly negative in the dark -- with the noise model fitted to that same scan
(sigma^2 = read^2 + gain * signal, read ~2.8 counts, gain ~0.048 counts/e-).

The sample is a depolarizing linear diattenuator + retarder whose retardance,
orientation and diattenuation vary along the stage axis -- so the inversion has
something non-trivial to recover, and gets the wrong answer loudly if the angle
conventions are off.

A companion <name>_ground_truth.h5 holds the exact Mueller matrices, so a
processing script can be scored against them.

Run::

    python processing/make_dummy_planar_mueller.py
    python processing/make_dummy_planar_mueller.py --noise 0    # noiseless
"""
import os
import sys
import argparse

import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from automations.slim.helpers import saveMuellerHDF5


# ──────────────────────────────────────────────────────────────────────────
# Mueller matrix primitives (all return (..., 4, 4) arrays)
# ──────────────────────────────────────────────────────────────────────────
def linearRetarder(angle_deg, delta_rad):
    """Linear retarder, fast axis at angle_deg, retardance delta_rad.

    angle_deg and delta_rad broadcast against each other, so passing a scalar
    angle and a per-wavelength retardance gives one matrix per wavelength.
    """
    a = np.deg2rad(np.asarray(angle_deg, dtype=float))
    d = np.asarray(delta_rad, dtype=float)
    a, d = np.broadcast_arrays(a, d)

    c, s = np.cos(2 * a), np.sin(2 * a)
    cd, sd = np.cos(d), np.sin(d)

    M = np.zeros(a.shape + (4, 4))
    M[..., 0, 0] = 1.0
    M[..., 1, 1] = c * c + s * s * cd
    M[..., 1, 2] = c * s * (1 - cd)
    M[..., 1, 3] = -s * sd
    M[..., 2, 1] = c * s * (1 - cd)
    M[..., 2, 2] = s * s + c * c * cd
    M[..., 2, 3] = c * sd
    M[..., 3, 1] = s * sd
    M[..., 3, 2] = -c * sd
    M[..., 3, 3] = cd
    return M


def linearDiattenuator(angle_deg, D):
    """Linear diattenuator, transmission axis at angle_deg, diattenuation D.

    D = 0 is a clear window, D = 1 an ideal polarizer. Normalised so m00 = 1
    (the overall throughput lives in the spectral transmission instead).
    """
    a = np.deg2rad(np.asarray(angle_deg, dtype=float))
    D = np.asarray(D, dtype=float)
    a, D = np.broadcast_arrays(a, D)

    c, s = np.cos(2 * a), np.sin(2 * a)
    b = np.sqrt(np.clip(1 - D * D, 0, None))   # sqrt(1 - D^2)

    M = np.zeros(a.shape + (4, 4))
    M[..., 0, 0] = 1.0
    M[..., 0, 1] = D * c
    M[..., 0, 2] = D * s
    M[..., 1, 0] = D * c
    M[..., 2, 0] = D * s
    M[..., 1, 1] = c * c + b * s * s
    M[..., 1, 2] = c * s * (1 - b)
    M[..., 2, 1] = c * s * (1 - b)
    M[..., 2, 2] = s * s + b * c * c
    M[..., 3, 3] = b
    return M


def depolarizer(p):
    """Isotropic depolarizer: keeps a fraction p of the polarized content."""
    p = np.asarray(p, dtype=float)
    M = np.zeros(p.shape + (4, 4))
    M[..., 0, 0] = 1.0
    for i in (1, 2, 3):
        M[..., i, i] = p
    return M


# ──────────────────────────────────────────────────────────────────────────
# The synthetic sample
# ──────────────────────────────────────────────────────────────────────────
def sampleMueller(z_mm, wavelengths, travel_mm):
    """Ground-truth sample Mueller matrix at one stage point.

    Returns (n_wl, 4, 4), normalised so m00 = 1 (the spectral transmission is
    applied separately, the way a real normalisation step would remove it).

    The sample is a wave-plate-like retarder stacked on a weak polarizer, with
    everything drifting across the stage travel:
      - orientation rotates 0 -> 90 deg along the scan
      - retardance is half-wave at 550 nm and disperses as 1/lambda
      - diattenuation ramps 0.05 -> 0.35
      - depolarization grows with wavelength and along the scan
    """
    frac = z_mm / travel_mm if travel_mm else 0.0        # 0 -> 1 along the scan

    orientation = 90.0 * frac                            # deg
    retardance = np.pi * (550.0 / wavelengths) * (0.3 + 0.7 * frac)
    diattenuation = 0.05 + 0.30 * frac
    depol = 1.0 - (0.05 + 0.15 * frac) * (wavelengths / 1100.0)

    M = (depolarizer(depol)
         @ linearRetarder(orientation, retardance)
         @ linearDiattenuator(orientation + 15.0, diattenuation))
    return M


def sampleTransmission(z_mm, wavelengths, travel_mm):
    """Unpolarized spectral throughput of the sample (a broad absorption dip)."""
    frac = z_mm / travel_mm if travel_mm else 0.0
    dip = 0.45 * np.exp(-0.5 * ((wavelengths - (620 + 120 * frac)) / 70.0) ** 2)
    return 0.85 - dip


def syntheticLamp(wavelengths):
    """Fallback source x detector response (shape only) if no reference scan."""
    wl = wavelengths
    lamp = (np.exp(-0.5 * ((wl - 870.0) / 190.0) ** 2)
            + 0.35 * np.exp(-0.5 * ((wl - 690.0) / 90.0) ** 2))
    blue_cut = 1.0 / (1.0 + np.exp((560.0 - wl) / 22.0))   # dead below ~550 nm
    nir_cut = 1.0 / (1.0 + np.exp((wl - 1110.0) / 22.0))
    return lamp * blue_cut * nir_cut


def referenceInstrument(path):
    """Wavelength axis + lamp envelope taken from a real muellerScan file.

    Returns (wavelengths, envelope). The envelope is the scan's mean spectrum
    over all waveplate angles, normalised to peak 1 -- it carries the real
    lamp, grating efficiency and detector response, dead blue end included.
    """
    with h5py.File(path, "r") as f:
        wavelengths = f["wavelength"][:]
        envelope = np.clip(f["intensity"][:].mean(axis=0), 0.0, None)
    return wavelengths, envelope / envelope.max()


# ──────────────────────────────────────────────────────────────────────────
# Forward model + file writing
# ──────────────────────────────────────────────────────────────────────────
def simulatePoint(z_mm, wavelengths, envelope, psg_angles, travel_mm, args):
    """One noiseless DRM angle sweep at one stage point.

    Returns (counts, M_truth) with counts shaped (n_angles, n_wavelengths) in
    arbitrary units -- main() rescales every point together so the brightest
    frame lands at --peak-counts, then adds noise.
    """
    # Quarter-wave at qwp_wavelength, dispersing as 1/lambda -- the PSG and PSA
    # plates are deliberately slightly different, as real ones are.
    delta_g = (np.pi / 2) * (args.qwp_wavelength / wavelengths)
    delta_a = (np.pi / 2) * (args.qwp_wavelength / wavelengths) * 1.02

    M_sample = sampleMueller(z_mm, wavelengths, travel_mm)          # (n_wl,4,4)
    throughput = envelope * sampleTransmission(z_mm, wavelengths, travel_mm)

    # Fixed polarizer at 0 deg: unit-intensity horizontal Stokes vector.
    S_in = np.array([1.0, 1.0, 0.0, 0.0])

    counts = np.empty((psg_angles.size, wavelengths.size))
    for k, theta in enumerate(psg_angles):
        Rg = linearRetarder(theta, delta_g)                  # (n_wl,4,4)
        Ra = linearRetarder(5.0 * theta, delta_a)            # PSA spins 5x

        S = np.einsum('wij,j->wi', Rg, S_in)
        S = np.einsum('wij,wj->wi', M_sample, S)
        S = np.einsum('wij,wj->wi', Ra, S)

        # Analyzer at 0 deg, then the ideal-polarizer 1/2 and the throughput.
        # The extra 1/2 is the input polarizer's own loss.
        counts[k] = 0.25 * (S[:, 0] + S[:, 1]) * throughput

    return counts, M_sample


def addNoise(counts, args, rng):
    """Detector noise fitted to the reference scan.

    sigma^2 = read^2 + gain * signal, in counts, beaten down by averaging
    scansToAvg frames. The rig hands back background-subtracted frames, so the
    result is free to go slightly negative in the dark -- no clipping.
    """
    shot = args.gain * np.clip(counts, 0.0, None)
    sigma = np.sqrt(shot + args.read_noise ** 2)
    sigma = sigma * args.noise / np.sqrt(args.scans_to_avg / args.ref_scans_to_avg)
    return counts + rng.normal(0.0, sigma, counts.shape)


def writeGroundTruth(path, z_values, wavelengths, mueller, psg_angles):
    """Sidecar file holding the exact Mueller matrices used to build the data."""
    with h5py.File(path, "w") as f:
        f.attrs["description"] = (
            "Ground truth for the matching planarMuellerScan dummy file. "
            "mueller is (n_points, n_wavelengths, 4, 4), m00-normalised."
        )
        f.attrs["n_points"] = len(z_values)
        f.create_dataset("z", data=np.asarray(z_values))
        f.create_dataset("wavelength", data=wavelengths)
        f.create_dataset("IW_Theta", data=np.asarray(psg_angles))
        f.create_dataset(
            "mueller", data=np.asarray(mueller),
            compression="gzip", compression_opts=4,
        )
    print(f"Wrote ground truth → {path}")


def main():
    here = os.path.dirname(os.path.abspath(__file__))

    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", default="dummy", help="sample name (file prefix)")
    ap.add_argument("--region", default="A")
    ap.add_argument("--side", default="X")
    ap.add_argument("--reference",
                    default=os.path.join(here, "RG092c_RegionB_X_muellerScan.h5"),
                    help="real muellerScan h5 to copy the wavelength axis, lamp "
                         "envelope and metadata from ('' for a synthetic axis)")
    ap.add_argument("--num-points", type=int, default=41)
    ap.add_argument("--step-size", type=float, default=0.5, help="mm")
    ap.add_argument("--num-angles", type=int, default=61,
                    help="PSG waveplate steps over 0-360 deg")
    # Only used when there is no reference scan to copy the axis from.
    ap.add_argument("--num-pixels", type=int, default=1044)
    ap.add_argument("--wl-min", type=float, default=398.763)
    ap.add_argument("--wl-max", type=float, default=1182.694)

    ap.add_argument("--qwp-wavelength", type=float, default=550.0,
                    help="nm at which the PSG/PSA plates are quarter-wave")
    ap.add_argument("--peak-counts", type=float, default=675.0,
                    help="counts at the peak of the mean spectrum (real scan: 675)")
    ap.add_argument("--read-noise", type=float, default=2.77,
                    help="counts RMS, fitted to the reference scan")
    ap.add_argument("--gain", type=float, default=0.048,
                    help="counts per photoelectron, fitted to the reference scan")
    ap.add_argument("--scans-to-avg", type=int, default=3,
                    help="frames averaged per point; noise scales as 1/sqrt(N)")
    ap.add_argument("--ref-scans-to-avg", type=int, default=3,
                    help="scansToAvg of the scan the noise model was fitted to")
    ap.add_argument("--integration", type=int, default=1000000, help="us")
    ap.add_argument("--noise", type=float, default=1.0,
                    help="noise multiplier; 0 writes a noiseless file")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)

    if args.reference and os.path.exists(args.reference):
        wavelengths, envelope = referenceInstrument(args.reference)
        print(f"Instrument model from {args.reference}")
    else:
        if args.reference:
            print(f"No reference scan at {args.reference}; using a synthetic axis")
        wavelengths = np.linspace(args.wl_min, args.wl_max, args.num_pixels)
        envelope = syntheticLamp(wavelengths)
    print(f"  {wavelengths.size} pixels, {wavelengths[0]:.2f}-{wavelengths[-1]:.2f} nm")

    psg_angles = np.linspace(0, 360, args.num_angles)
    z_values = [i * args.step_size for i in range(args.num_points)]
    travel = (args.num_points - 1) * args.step_size

    raw, truth = [], []
    for z in z_values:
        counts, M = simulatePoint(z, wavelengths, envelope, psg_angles, travel, args)
        raw.append(counts)
        truth.append(M)
        print(f"  simulated z={z:.3f} mm")

    # Scale every point together so the brightest mean spectrum peaks at
    # --peak-counts, matching the real scan's signal level, then add noise.
    scale = args.peak_counts / max(c.mean(axis=0).max() for c in raw)

    points = []
    for z, counts in zip(z_values, raw):
        counts = counts * scale
        if args.noise:
            counts = addNoise(counts, args, rng)
        all_data = [
            ({"IW_Theta": float(theta), "IP_Theta": 0,
              "CW_Theta": float(5.0 * theta), "CP_Theta": 0},
             counts[k], wavelengths)
            for k, theta in enumerate(psg_angles)
        ]
        points.append(({'z': z}, all_data))

    h5_path = saveMuellerHDF5(
        points, "planarMuellerScan", name=args.name, region=args.region,
        side=args.side, integration=args.integration, sta=args.scans_to_avg,
    )
    writeGroundTruth(
        os.path.join(os.path.dirname(h5_path), f"{args.name}_ground_truth.h5"),
        z_values, wavelengths, truth, psg_angles,
    )


if __name__ == "__main__":
    main()
