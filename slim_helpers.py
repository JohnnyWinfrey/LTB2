"""Utility helpers for the SLIM calibration rig: progress bar + HDF5 saving."""
import os
from datetime import datetime

import numpy as np
import h5py


def progressBarCoolStyle(numSteps, currentStep):
    percentDone = (currentStep / numSteps) * 100
    leftover = (100 - percentDone)
    print("Pwogwess (witawy) =", "(", "|" * int(percentDone), "-" * int(leftover), ")")


def saveHDF5(all_data, scanType, name="sample", region="A", side="X",
             scanX=0.0, scanY=0.0, integration=100000):
    """
    Save SLIM scan data to HDF5.

    all_data : list of (angles_dict, intensities_array, wavelengths_array)
               tuples as returned by slimScan.

    Metadata is passed in explicitly (no more dummy placeholders): a standalone
    script reads it off its spectrometer, e.g.::

        saveHDF5(all_data, "stokesScan",
                 name=spectro._sampleName, region=spectro._region,
                 side=spectro._side, scanX=spectro._scanX,
                 scanY=spectro._scanY, integration=spectro.intTime)
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    name = name or "sample"

    output_dir = os.path.join("data", f"{name}_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    h5_path = os.path.join(
        output_dir, f"{name}_Region{region}_{side}_{scanType}.h5"
    )

    # tuple layout is (angles_dict, intensities, wavelengths)
    angles_list = [d[0] for d in all_data]           # list of dicts
    intensities = np.array([d[1] for d in all_data]) # (N_scans, N_wl)
    wavelengths = all_data[0][2]                      # same for every scan

    with h5py.File(h5_path, "w") as f:
        # Metadata
        f.attrs["region"]              = region
        f.attrs["side"]                = side
        f.attrs["x"]                   = scanX
        f.attrs["y"]                   = scanY
        f.attrs["integration_time_us"] = integration

        # Wavelength axis
        f.create_dataset("wavelength", data=wavelengths)

        # Per-scan angle columns
        for key in ["IW_Theta", "IP_Theta", "CW_Theta", "CP_Theta"]:
            f.create_dataset(
                key, data=np.array([a[key] for a in angles_list])
            )

        # Intensity matrix: (N_scans, N_wavelengths)
        f.create_dataset(
            "intensity", data=intensities,
            compression="gzip", compression_opts=4,
        )

    print(f"Saved {len(all_data)} scans → {h5_path}")
