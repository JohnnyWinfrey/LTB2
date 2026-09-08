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
             scanX=0.0, scanY=0.0, integration=100000, sta=1):
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
        f.attrs["scansToAvg"]          = sta

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


def saveMuellerHDF5(points, scanType, name="sample", region="A", side="X",
                    integration=100000, sta=1):
    """
    Save a multi-position Mueller scan to HDF5, one group per stage location.

    points : list of (coord_dict, all_data) tuples, where coord_dict is
             {'x': mm, 'y': mm} (the XWing position) and all_data is the
             list of (angles_dict, intensities, wavelengths) tuples collected
             at that position -- i.e. exactly what saveHDF5 takes.

    Layout::

        /                       attrs: region, side, integration_time_us, ...
        /x0.000_y0.000/         attrs: x, y, point_index
            wavelength          (N_wl,)
            IW_Theta ...        (N_scans,)
            intensity           (N_scans, N_wl)
        /x0.500_y0.000/
            ...

    Groups are written in acquisition order (track_order), so iterating the
    file walks the stage path.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    name = name or "sample"

    output_dir = os.path.join("data", f"{name}_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    h5_path = os.path.join(
        output_dir, f"{name}_Region{region}_{side}_{scanType}.h5"
    )

    total = 0
    with h5py.File(h5_path, "w", track_order=True) as f:
        # Metadata shared by every position
        f.attrs["region"]              = region
        f.attrs["side"]                = side
        f.attrs["integration_time_us"] = integration
        f.attrs["scansToAvg"]          = sta
        f.attrs["n_points"]            = len(points)

        for idx, (coord, all_data) in enumerate(points):
            if not all_data:
                continue

            grp = f.create_group(
                f"x{coord['x']:.3f}_y{coord['y']:.3f}", track_order=True
            )
            grp.attrs["x"]           = coord["x"]
            grp.attrs["y"]           = coord["y"]
            grp.attrs["point_index"] = idx

            # tuple layout is (angles_dict, intensities, wavelengths)
            angles_list = [d[0] for d in all_data]
            intensities = np.array([d[1] for d in all_data])
            wavelengths = all_data[0][2]

            grp.create_dataset("wavelength", data=wavelengths)
            for key in ["IW_Theta", "IP_Theta", "CW_Theta", "CP_Theta"]:
                grp.create_dataset(
                    key, data=np.array([a[key] for a in angles_list])
                )
            grp.create_dataset(
                "intensity", data=intensities,
                compression="gzip", compression_opts=4,
            )
            total += len(all_data)

    print(f"Saved {total} scans over {len(points)} positions → {h5_path}")
    return h5_path
