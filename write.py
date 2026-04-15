"""
Writeback layer for LTB2 scan data.

Decoupled from acquisition — receives Measurements, calls to_dict(), dumps.
"""

import os
import csv
import numpy as np
import h5py
from datetime import datetime


class ScanWriter:
    """
    Accumulates Measurements and writes them out.

    Parameters
    ----------
    output_dir : str or None
        Directory to write into. Auto-generated from timestamp if None.
    fmt : str
        'csv' or 'hdf5'
    write_on : str
        'finish'  — buffer everything, write once at finalize()
        'scan'    — flush per checkpoint() call
        'point'   — flush every append()
    """

    def __init__(self, output_dir=None, fmt='csv', write_on='finish'):
        self.fmt = fmt
        self.write_on = write_on
        self._buffer = []
        self._flushed_count = 0

        if output_dir is None:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            output_dir = os.path.join("data", timestamp)
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def append(self, measurement):
        self._buffer.append(measurement)
        if self.write_on == 'point':
            self._flush()

    def checkpoint(self):
        if self.write_on == 'scan':
            self._flush()

    def finalize(self, filename='scan_data'):
        if self._buffer:
            self._flush(filename=filename)

    # ── flush ────────────────────────────────────────────────────────────

    def _flush(self, filename='scan_data'):
        if not self._buffer:
            return

        dicts = [m.to_dict() for m in self._buffer]

        if self.fmt == 'csv':
            self._write_csv(dicts, filename)
        elif self.fmt == 'hdf5':
            self._write_hdf5(dicts, filename)

        self._flushed_count += len(self._buffer)
        self._buffer.clear()

    def _write_csv(self, dicts, filename):
        path = os.path.join(self.output_dir, f"{filename}.csv")
        is_new = not os.path.exists(path)

        # Filter out array-valued keys (spectra go to HDF5)
        scalar_keys = [k for k, v in dicts[0].items()
                       if not isinstance(v, np.ndarray)]

        with open(path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=scalar_keys,
                                    extrasaction='ignore')
            if is_new:
                writer.writeheader()
            writer.writerows(dicts)

    def _write_hdf5(self, dicts, filename):
        path = os.path.join(self.output_dir, f"{filename}.h5")
        sample = dicts[0]

        with h5py.File(path, 'w') as f:
            for key, val in sample.items():
                if isinstance(val, np.ndarray):
                    # Array column — stack across measurements
                    f.create_dataset(
                        key, data=np.array([d[key] for d in dicts]),
                        compression="gzip", compression_opts=4)
                elif isinstance(val, str):
                    f.create_dataset(
                        key, data=[d[key] for d in dicts],
                        dtype=h5py.string_dtype())
                else:
                    f.create_dataset(key, data=[d[key] for d in dicts])
