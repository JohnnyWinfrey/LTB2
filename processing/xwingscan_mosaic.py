"""
xwingscan_mosaic.py

Stitch images from an XWingScan camera-mode HDF5 file into a single
spatial mosaic using the stored X/Y stage positions.

Edit the variables below and run directly from your IDE, or pass them
as command-line arguments:
    python xwingscan_mosaic.py <path_to_h5> <pixels_per_mm> [output_path]

pixels_per_mm converts stage coordinates (mm) to canvas pixels.
For a 10x objective on the CS165MU (3.45 µm pixel): 10 / 0.00345 ≈ 2898
"""

import sys
import pathlib
import numpy as np
import h5py
import tifffile

# ── Configure here when running from IDE ─────────────────────────────────────
H5_FILE       = "data/example_xwing_scan_camera.h5"
PIXELS_PER_MM = 2898.0   # 10x objective, 3.45 µm pixel → 10 / 0.00345
OUTPUT_PATH   = ""       # leave blank to auto-derive from h5 path
# ─────────────────────────────────────────────────────────────────────────────


def load_camera_scan(h5_path):
    with h5py.File(h5_path, "r") as f:
        x      = f["x"][:]       # (N_pts,) mm
        y      = f["y"][:]       # (N_pts,) mm
        images = f["images"][:] # (N_pts, H, W) uint16

        sample_name = f.attrs.get("sample_name", "")
        nx          = int(f.attrs.get("nx", 0))
        ny          = int(f.attrs.get("ny", 0))
        spacing_mm  = float(f.attrs.get("spacing_mm", 0.0))

    return x, y, images, sample_name, nx, ny, spacing_mm


def build_mosaic(x, y, images, pixels_per_mm):
    """
    Place each image on a canvas using stage coordinates converted to pixels,
    averaging pixel values wherever frames overlap.
    """
    n_pts, H, W = images.shape

    x_px = np.round((x - x.min()) * pixels_per_mm).astype(int)
    y_px = np.round((y - y.min()) * pixels_per_mm).astype(int)

    canvas_h = int(y_px.max()) + H
    canvas_w = int(x_px.max()) + W

    acc   = np.zeros((canvas_h, canvas_w), dtype=np.float64)
    count = np.zeros((canvas_h, canvas_w), dtype=np.int32)

    for i in range(n_pts):
        xp, yp = int(x_px[i]), int(y_px[i])
        acc[yp:yp + H, xp:xp + W]   += images[i].astype(np.float64)
        count[yp:yp + H, xp:xp + W] += 1

    mosaic = np.zeros((canvas_h, canvas_w), dtype=np.uint16)
    filled = count > 0
    mosaic[filled] = (acc[filled] / count[filled]).astype(np.uint16)

    return mosaic


def save_mosaic(mosaic, out_path):
    tifffile.imwrite(out_path, mosaic)


def stitch(h5_path, pixels_per_mm, out_path=None):
    h5_path = pathlib.Path(h5_path)

    if out_path is None:
        out_path = h5_path.with_name(h5_path.stem + "_mosaic.tiff")
    out_path = pathlib.Path(out_path)

    print(f"Loading {h5_path.name} …")
    x, y, images, sample_name, nx, ny, spacing_mm = load_camera_scan(h5_path)
    print(f"  {len(images)} frames  ({nx} × {ny} grid, {spacing_mm} mm spacing)")
    print(f"  Frame size: {images.shape[1]} × {images.shape[2]} px")

    print(f"Building mosaic at {pixels_per_mm:.1f} px/mm …")
    mosaic = build_mosaic(x, y, images, pixels_per_mm)
    print(f"  Canvas: {mosaic.shape[1]} × {mosaic.shape[0]} px")

    print(f"Saving → {out_path}")
    save_mosaic(mosaic, out_path)
    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        h5_path       = sys.argv[1]
        pixels_per_mm = float(sys.argv[2])
        out_path      = sys.argv[3] if len(sys.argv) >= 4 else None
    elif len(sys.argv) == 1:
        h5_path       = H5_FILE
        pixels_per_mm = PIXELS_PER_MM
        out_path      = OUTPUT_PATH or None
    else:
        print("Usage: python xwingscan_mosaic.py <path_to_h5> <pixels_per_mm> [output_path]")
        sys.exit(1)

    stitch(h5_path, pixels_per_mm, out_path)
