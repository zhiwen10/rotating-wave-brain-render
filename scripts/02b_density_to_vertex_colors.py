"""
Step 2b: Convert spiral-detection density data into per-vertex RGBA colors for
the isocortex mesh, saved as processed_data/vertex_colors_density.npy.

INPUT FORMAT:
    raw_data/spiral_density.mat  —  contains unique_spirals array, shape (N, 3):
        column 0 = ML voxel index (10 µm CCF space)
        column 1 = AP voxel index (10 µm CCF space)
        column 2 = pre-computed density value

Pipeline:
    1. Load spiral_density.mat and scale voxel indices → µm (×10).
    2. Interpolate scattered (AP, ML, density) onto a regular 2D grid with griddata.
    3. Apply the 'hot' colormap (black → red → yellow → white).
    4. Interpolate RGB image onto mesh vertices (same as 02_phasemap_to_vertex_colors.py).
    5. Save vertex_colors_density.npy — shape (N, 4) RGBA, float32.

Run in a normal Python env (NOT inside Blender):
    pip install trimesh scipy matplotlib numpy mat73
    python 02b_density_to_vertex_colors.py
"""

import numpy as np
import trimesh
import mat73
from scipy.interpolate import RegularGridInterpolator, griddata
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# CONFIG (EDIT THESE)
# ---------------------------------------------------------------------------
MESH_PATH    = "raw_data/isocortex.obj"
SPIRALS_PATH = "raw_data/spiral_density.mat"   # contains unique_spirals (N, 3)
OUT_PATH     = "processed_data/vertex_colors_density.npy"

AP_BINS      = 1320
ML_BINS      = 1140
AP_TOTAL_UM  = 13200.0
ML_TOTAL_UM  = 11400.0

CMAP         = "hot"
GRAY         = [0.0, 0.0, 0.0, 1.0]   # black for out-of-FOV (matches hot low end)

# ---------------------------------------------------------------------------
# 1. LOAD MESH
# ---------------------------------------------------------------------------
mesh     = trimesh.load(MESH_PATH)
vertices = mesh.vertices        # (N, 3) in CCF µm

# ---------------------------------------------------------------------------
# 2. LOAD SPIRAL COORDINATES AND SCALE TO µm
# ---------------------------------------------------------------------------
data    = mat73.loadmat(SPIRALS_PATH)
spirals = np.array(data["unique_spirals"], dtype=np.float32)   # (N, 3)
# col0 = ML voxel index, col1 = AP voxel index, col2 = density
ml_pts  = spirals[:, 0] * 10     # ML voxels → µm
ap_pts  = spirals[:, 1] * 10     # AP voxels → µm
density = spirals[:, 2]

# ---------------------------------------------------------------------------
# 3. INTERPOLATE SCATTER → REGULAR 2D GRID
# ---------------------------------------------------------------------------
ap_axis = np.linspace(0, AP_TOTAL_UM, AP_BINS)
ml_axis = np.linspace(0, ML_TOTAL_UM, ML_BINS)
Xq, Yq = np.meshgrid(ap_axis, ml_axis, indexing='ij')   # (AP, ML) grid

density_map = griddata((ap_pts, ml_pts), density,
                        (Xq, Yq), method='linear', fill_value=0)

# ---------------------------------------------------------------------------
# 4. APPLY HOT COLORMAP
# ---------------------------------------------------------------------------
d_min, d_max  = density_map.min(), density_map.max()
density_norm  = np.clip((density_map - d_min) / (d_max - d_min + 1e-12), 0, 1)

cmap    = plt.colormaps["hot"]
rgb_img = cmap(density_norm)[:, :, :3].astype(np.float32)   # (AP, ML, 3)

# ---------------------------------------------------------------------------
# 5. INTERPOLATE RGB IMAGE ONTO MESH VERTICES
# ---------------------------------------------------------------------------
def make_interp(ch):
    return RegularGridInterpolator(
        (ap_axis, ml_axis), rgb_img[:, :, ch],
        method="linear", bounds_error=False, fill_value=np.nan)

query = np.column_stack([vertices[:, 0], vertices[:, 2]])   # (AP, ML) per vertex
r = make_interp(0)(query)
g = make_interp(1)(query)
b = make_interp(2)(query)

# ---------------------------------------------------------------------------
# 6. ASSEMBLE AND SAVE
# ---------------------------------------------------------------------------
invalid       = np.isnan(r)
vertex_colors = np.column_stack([r, g, b, np.ones(len(vertices))])
vertex_colors[invalid] = GRAY
vertex_colors = np.clip(vertex_colors, 0.0, 1.0).astype(np.float32)

np.save(OUT_PATH, vertex_colors)
print(f"Saved {OUT_PATH}  shape={vertex_colors.shape}  "
      f"({(~invalid).sum()}/{len(vertices)} vertices colored)")
