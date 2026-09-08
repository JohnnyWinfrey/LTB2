"""HDF5 saving for TCSPC scans -- the TH260 counterpart to slim_helpers."""
import os
from datetime import datetime

import numpy as np
import h5py


def saveTCSPCHDF5(all_data, scanType="tcspcSpectral", name="sample", region="A",
                  resolution_ps=0.0, tacq_ms=0, channel=0):
    """
    Save a TCSPC wavelength sweep to HDF5.

    all_data : list of per-wavelength dicts as built by TCSPC_Spectral, each
               holding 'wavelength', 'counts' (channels x bins), 'sync_rate'
               and 'count_rate'.

    Layout mirrors slim_helpers.saveHDF5: data/<name>_<timestamp>/ with the
    metadata as file attributes. `counts` is the selected channel; every
    channel is kept in `counts_all` when the board has more than one.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    name = name or "sample"

    output_dir = os.path.join("data", f"{name}_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    h5_path = os.path.join(output_dir, f"{name}_Region{region}_{scanType}.h5")

    wavelengths = np.array([d["wavelength"] for d in all_data], dtype=np.float64)
    counts_all = np.array([d["counts"] for d in all_data], dtype=np.uint32)  # (N, CH, bins)
    nBins = counts_all.shape[2]
    time_ns = np.arange(nBins) * (resolution_ps / 1000.0)

    with h5py.File(h5_path, "w") as f:
        f.attrs["region"] = region
        f.attrs["name"] = name
        f.attrs["timestamp"] = timestamp
        f.attrs["resolution_ps"] = resolution_ps
        f.attrs["bin_width_ps"] = resolution_ps
        f.attrs["tacq_ms"] = tacq_ms
        f.attrs["channel"] = channel

        f.create_dataset("wavelength", data=wavelengths)
        f.create_dataset("time_ns", data=time_ns)
        f.create_dataset("sync_rate", data=np.array([d["sync_rate"] for d in all_data]))
        f.create_dataset(
            "count_rate",
            data=np.array([d["count_rate"][channel] if channel < len(d["count_rate"]) else 0
                           for d in all_data]),
        )

        f.create_dataset("counts", data=counts_all[:, channel, :],
                         compression="gzip", compression_opts=4)
        if counts_all.shape[1] > 1:
            f.create_dataset("counts_all", data=counts_all,
                             compression="gzip", compression_opts=4)

    print(f"Saved {len(all_data)} spectra -> {h5_path}")
    return h5_path
