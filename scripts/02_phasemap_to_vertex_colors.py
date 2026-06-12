"""
Step 2: Resample a 2D dorsal phase map onto per-vertex RGBA colors for the
isocortex mesh, saved as vertex_colors.npy.

INPUT FORMAT — this script expects an already-RGB-colored phase image:
    phase_colormap.npy  —  shape (H, W, 3), float32 in [0, 1].

    The colormap is applied upstream (e.g. in MATLAB with a cyclic colormap such
    as CET_C6, exported via mat73).  If you have raw phase values [0, 2*pi],
    apply your colormap first:

        import matplotlib.pyplot as plt
        phase_raw  = np.load("phase_map.npy")          # (H, W) in [0, 2*pi]
        cmap       = plt.cm.get_cmap("hsv")
        phase_rgb  = cmap(phase_raw / (2 * np.pi))[:, :, :3]
        np.save("phase_colormap.npy", phase_rgb.astype(np.float32))

    then point PHASE_RGB_PATH at the result.

COORDINATE SYSTEM — Allen CCF 25 μm atlas:
    axis 0 = AP  (0 .. 13 200 μm)
    axis 1 = DV  (0 ..  5 350 μm)
    axis 2 = ML  (0 .. 11 400 μm)

    Verified from isocortex.obj vertices:
        axis 0 range: 1 803 – 10 373
        axis 1 range:   151 –  5 535
        axis 2 range:   502 – 10 873

Pipeline:
    1. Load isocortex.obj vertices (N, 3) in Allen CCF μm.
    2. Build one RegularGridInterpolator per RGB channel over the phase image.
    3. Query each vertex at (AP=axis 0, ML=axis 2).
    4. Vertices outside the FOV → gray (0.15, 0.15, 0.15).
    5. Save vertex_colors.npy (N, 4) RGBA, float32.

The Blender render scripts (scripts/03_*.py) load vertex_colors.npy and assign it
to a "Phase" vertex-color layer on the Cortex object.

Run in a normal Python env (NOT inside Blender):
    pip install trimesh scipy numpy
    python 02_phasemap_to_vertex_colors.py
"""

import numpy as np
import trimesh
from scipy.interpolate import RegularGridInterpolator

# ---------------------------------------------------------------------------
# CONFIG (EDIT THESE)
# ---------------------------------------------------------------------------
MESH_PATH       = "isocortex.obj"
PHASE_RGB_PATH  = "phase_colormap.npy"  # (H, W, 3) float32 in [0, 1]
OUT_PATH        = "vertex_colors.npy"

# Allen CCF 25 μm atlas total extents (μm).
# H×W of phase_colormap.npy must equal (AP_BINS, ML_BINS).
AP_TOTAL_UM     = 13200.0   # 1320 voxels × 25 μm
ML_TOTAL_UM     = 11400.0   # 1140 voxels × 25 μm

# Mesh axis mapping (verify against your atlas export).
AP_AXIS = 0    # vertices[:, AP_AXIS]  is the AP coordinate
ML_AXIS = 2    # vertices[:, ML_AXIS]  is the ML coordinate
DV_AXIS = 1    # used for dorsal-facing normal test (optional)

# Dorsal-facing threshold: set to 0 to disable.  Vertices whose DV normal
# component is below this are painted gray (medial wall / ventral surface).
DORSAL_THRESH = 0.3

GRAY = [0.15, 0.15, 0.15, 1.0]

# ---------------------------------------------------------------------------
# 1. LOAD MESH + PHASE RGB IMAGE
# ---------------------------------------------------------------------------
mesh       = trimesh.load(MESH_PATH)
vertices   = mesh.vertices        # (N, 3) in CCF μm
normals    = mesh.vertex_normals  # (N, 3)

phase_rgb  = np.load(PHASE_RGB_PATH)   # (H, W, 3)
H, W       = phase_rgb.shape[:2]

ap_coords  = np.linspace(0, AP_TOTAL_UM, H)
ml_coords  = np.linspace(0, ML_TOTAL_UM, W)

# ---------------------------------------------------------------------------
# 2. BUILD PER-CHANNEL INTERPOLATORS
# ---------------------------------------------------------------------------
def make_interp(channel):
    return RegularGridInterpolator(
        (ap_coords, ml_coords),
        phase_rgb[:, :, channel],
        method="linear",
        bounds_error=False,
        fill_value=np.nan,   # NaN for vertices outside the image extent
    )

interp_r = make_interp(0)
interp_g = make_interp(1)
interp_b = make_interp(2)

# ---------------------------------------------------------------------------
# 3. QUERY EACH VERTEX
# ---------------------------------------------------------------------------
query = np.column_stack([vertices[:, AP_AXIS], vertices[:, ML_AXIS]])
r = interp_r(query)
g = interp_g(query)
b = interp_b(query)

# ---------------------------------------------------------------------------
# 4. MASK: outside FOV -> gray  (add `| non_dorsal` to also mask ventral)
# ---------------------------------------------------------------------------
out_of_fov = np.isnan(r)
non_dorsal = normals[:, DV_AXIS] < DORSAL_THRESH
invalid    = out_of_fov   # swap to `out_of_fov | non_dorsal` if needed

# ---------------------------------------------------------------------------
# 5. ASSEMBLE AND SAVE
# ---------------------------------------------------------------------------
vertex_colors            = np.column_stack([r, g, b, np.ones(len(vertices))])
vertex_colors[invalid]   = GRAY
vertex_colors            = np.clip(vertex_colors, 0.0, 1.0).astype(np.float32)

np.save(OUT_PATH, vertex_colors)
print(f"wrote {OUT_PATH}  shape={vertex_colors.shape}  "
      f"({(~invalid).sum()} / {len(vertices)} vertices colored)")
