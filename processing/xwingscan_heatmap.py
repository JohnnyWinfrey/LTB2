"""
xwingscan_heatmap.py

Plot a spatial heatmap of PMT voltage at a specified wavelength from an
XWingScan HDF5 file.

Edit the two variables below and run directly from your IDE, or pass them
as command-line arguments:
    python xwingscan_heatmap.py <path_to_h5> <wavelength_nm>
"""

import sys
import numpy as np
import h5py
import matplotlib.pyplot as plt

# ── Configure here when running from IDE ─────────────────────────────────────
H5_FILE           = "data/WS2-DC-3C-040826_xwing_scan.h5"
TARGET_WAVELENGTH = 610.0   # nm
# ─────────────────────────────────────────────────────────────────────────────


def load_scan(h5_path):
    with h5py.File(h5_path, "r") as f:
        x           = f["x"][:]            # (N_pts,)
        y           = f["y"][:]            # (N_pts,)
        wavelengths = f["wavelength"][:]   # (N_wl,)
        voltage     = f["voltage"][:,:]    # (N_pts, N_wl)

        sample_name = f.attrs.get("sample_name", "")
        nx          = int(f.attrs.get("nx", 0))
        ny          = int(f.attrs.get("ny", 0))
        spacing_mm  = float(f.attrs.get("spacing_mm", 0.0))

    return x, y, wavelengths, voltage, sample_name, nx, ny, spacing_mm


def build_grid(x, y, voltage_slice, nx, ny):
    """
    Reshape flat scan points into a 2D grid (ny, nx).
    The scan uses a boustrophedon pattern, so odd rows are reversed before
    reshaping to recover the correct spatial layout.
    """
    grid = np.full((ny, nx), np.nan)

    point = 0
    for iy in range(ny):
        ix_range = range(nx) if iy % 2 == 0 else range(nx - 1, -1, -1)
        for ix in ix_range:
            if point < len(voltage_slice):
                grid[iy, ix] = voltage_slice[point]
            point += 1

    return grid


def plot_heatmap(h5_path, target_wavelength):
    x, y, wavelengths, voltage, sample_name, nx, ny, spacing_mm = load_scan(h5_path)

    # Find the closest wavelength index
    wl_idx = int(np.argmin(np.abs(wavelengths - target_wavelength)))
    actual_wl = wavelengths[wl_idx]

    voltage_slice = voltage[:, wl_idx]   # (N_pts,)

    grid = build_grid(x, y, voltage_slice, nx, ny)

    x_coords = np.unique(np.sort(x))
    y_coords = np.unique(np.sort(y))

    fig, ax = plt.subplots(figsize=(7, 6))

    extent = [
        x_coords.min(), x_coords.max(),
        y_coords.min(), y_coords.max(),
    ]

    im = ax.imshow(
        grid,
        origin="lower",
        extent=extent,
        aspect="equal",
        cmap="inferno",
        interpolation="nearest",
    )

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("PMT Voltage (V)", fontsize=11)

    title = f"{sample_name}  —  λ = {actual_wl:.2f} nm"
    if abs(actual_wl - target_wavelength) > 0.5:
        title += f"\n(requested {target_wavelength:.2f} nm, nearest {actual_wl:.2f} nm)"
    ax.set_title(title, fontsize=12)
    ax.set_xlabel("X position (mm)", fontsize=11)
    ax.set_ylabel("Y position (mm)", fontsize=11)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    if len(sys.argv) == 3:
        h5_path           = sys.argv[1]
        target_wavelength = float(sys.argv[2])
    elif len(sys.argv) == 1:
        h5_path           = H5_FILE
        target_wavelength = TARGET_WAVELENGTH
    else:
        print("Usage: python xwingscan_heatmap.py <path_to_h5> <wavelength_nm>")
        sys.exit(1)

    plot_heatmap(h5_path, target_wavelength)
