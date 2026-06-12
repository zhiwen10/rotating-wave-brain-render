"""
Step 2b: Convert spiral-detection density data into per-vertex RGBA colors for
the isocortex mesh, saved as vertex_colors_density.npy.

INPUT FORMAT:
    unique_spirals.npy  —  shape (N, 3), columns [AP_um, ML_um, density_count].
    These are the detected spiral event coordinates (in Allen CCF μm) together
    with a per-event density or count weight.

Pipeline:
    1. Bin (AP, ML) coordinates into a 2D histogram in CCF space.
    2. Smooth with a Gaussian kernel for visual quality.
    3. Apply the 'hot' colormap (black → red → yellow → white).
    4. Interpolate per-vertex, identical to 02_phasemap_to_vertex_colors.py.
    5. Save vertex_colors_density.npy (N, 4) RGBA, float32.

Run in a normal Python env (NOT inside Blender):
    pip install trimesh scipy matplotlib numpy
    python 02b_density_to_vertex_colors.py
"""

import numpy as np
import trimesh
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import gaussian_filter
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# CONFIG (EDIT THESE)
# ---------------------------------------------------------------------------
MESH_PATH      = "isocortex.obj"
SPIRALS_PATH   = "unique_spirals.npy"       # (N, 3): [AP_um, ML_um, density]
OUT_PATH       = "vertex_colors_density.npy"

# Density image resolution (pixels per axis, matched to 25 μm atlas)
AP_BINS        = 1320
ML_BINS        = 1140
AP_TOTAL_UM    = 13200.0
ML_TOTAL_UM    = 11400.0

AP_AXIS        = 0   # vertices[:, AP_AXIS] is the AP coordinate
ML_AXIS        = 2   # vertices[:, ML_AXIS] is the ML coordinate
DV_AXIS        = 1   # used for optional dorsal-facing mask

# Gaussian smoothing kernel width in pixels (increase for smoother map)
SMOOTH_SIGMA   = 8.0

CMAP           = "hot"   # matplotlib colormap: 'hot', 'inferno', 'viridis', …
DORSAL_THRESH  = 0.3     # set to 0 to disable ventral masking
GRAY           = [0.15, 0.15, 0.15, 1.0]

# ---------------------------------------------------------------------------
# 1. LOAD MESH + SPIRAL COORDINATES
# ---------------------------------------------------------------------------
mesh        = trimesh.load(MESH_PATH)
vertices    = mesh.vertices        # (N, 3) in CCF μm
normals     = mesh.vertex_normals  # (N, 3)

spirals     = np.load(SPIRALS_PATH)   # (N, 3)
ap_pts      = spirals[:, 0]
ml_pts      = spirals[:, 1]

# ---------------------------------------------------------------------------
# 2. BUILD 2D DENSITY IMAGE VIA HISTOGRAM + SMOOTHING
# ---------------------------------------------------------------------------
ap_edges = np.linspace(0, AP_TOTAL_UM, AP_BINS + 1)
ml_edges = np.linspace(0, ML_TOTAL_UM, ML_BINS + 1)

density_img, _, _ = np.histogram2d(ap_pts, ml_pts, bins=[ap_edges, ml_edges])
density_img       = gaussian_filter(density_img, sigma=SMOOTH_SIGMA)

# ---------------------------------------------------------------------------
# 3. APPLY COLORMAP → RGB IMAGE
# ---------------------------------------------------------------------------
d_min, d_max  = density_img.min(), density_img.max()
density_norm  = (density_img - d_min) / (d_max - d_min + 1e-12)

cmap          = plt.cm.get_cmap(CMAP)
rgb_img       = cmap(density_norm)[:, :, :3].astype(np.float32)  # drop alpha

# ---------------------------------------------------------------------------
# 4. BUILD PER-CHANNEL INTERPOLATORS
# ---------------------------------------------------------------------------
ap_coords = np.linspace(0, AP_TOTAL_UM, AP_BINS)
ml_coords = np.linspace(0, ML_TOTAL_UM, ML_BINS)

def make_interp(channel):
    return RegularGridInterpolator(
        (ap_coords, ml_coords),
        rgb_img[:, :, channel],
        method="linear",
        bounds_error=False,
        fill_value=np.nan,
    )

interp_r = make_interp(0)
interp_g = make_interp(1)
interp_b = make_interp(2)

# ---------------------------------------------------------------------------
# 5. QUERY EACH VERTEX
# ---------------------------------------------------------------------------
query = np.column_stack([vertices[:, AP_AXIS], vertices[:, ML_AXIS]])
r = interp_r(query)
g = interp_g(query)
b = interp_b(query)

# ---------------------------------------------------------------------------
# 6. MASK & SAVE
# ---------------------------------------------------------------------------
out_of_fov = np.isnan(r)
non_dorsal = normals[:, DV_AXIS] < DORSAL_THRESH
invalid    = out_of_fov   # swap to `out_of_fov | non_dorsal` to also mask ventral

vertex_colors           = np.column_stack([r, g, b, np.ones(len(vertices))])
vertex_colors[invalid]  = GRAY
vertex_colors           = np.clip(vertex_colors, 0.0, 1.0).astype(np.float32)

np.save(OUT_PATH, vertex_colors)
print(f"wrote {OUT_PATH}  shape={vertex_colors.shape}  "
      f"({(~invalid).sum()} / {len(vertices)} vertices colored)")
