"""
Step 2: Convert a 2D dorsal phase map into per-vertex RGBA colors for the
isocortex mesh, saved as vertex_colors.npy.

Pipeline:
    1. Load isocortex.obj (from step 1) -> vertex (x, y, z) in Allen CCF um.
    2. Load your 2D phase map (registered to the Allen CCF dorsal projection).
    3. For each vertex, look up the phase value at its (AP, ML) position via
       bilinear interpolation.
    4. Mask out vertices that fall outside the field of view OR do not face
       dorsally (medial wall / ventral surface should stay neutral gray).
    5. Map phase -> RGBA with a cyclic colormap and save vertex_colors.npy.

The Blender script (step 3) loads vertex_colors.npy and assigns it to a
"Phase" vertex color layer on the Cortex object.

Run in a normal Python env (NOT inside Blender):
    pip install trimesh scipy matplotlib numpy
    python 02_phasemap_to_vertex_colors.py

IMPORTANT: the two values you must set for your own registration are the
AP/ML extents of your phase map (ap_min/ap_max, ml_min/ml_max) and which
CCF axes correspond to AP and ML. Defaults below assume axis 0 = AP and
axis 2 = ML, with the full 25um CCF extents. Verify against your own data.
"""

import numpy as np
import trimesh
from scipy.interpolate import RegularGridInterpolator
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# CONFIG (EDIT THESE)
# ---------------------------------------------------------------------------
MESH_PATH       = "isocortex.obj"
PHASE_MAP_PATH  = "phase_map.npy"     # 2D array, values in [0, 2*pi]
OUT_PATH        = "vertex_colors.npy"

# AP / ML extents (in um) that your phase map image spans.
# Full Allen CCF is roughly AP 0..13200, ML 0..11400.
AP_MIN, AP_MAX  = 0.0, 13200.0
ML_MIN, ML_MAX  = 0.0, 11400.0

# Which CCF axis is AP vs ML for your isocortex.obj. Typically:
#   axis 0 = AP, axis 1 = DV (depth), axis 2 = ML
AP_AXIS_IDX = 0
ML_AXIS_IDX = 2
DV_AXIS_IDX = 1   # used for the dorsal-facing normal test

# Dorsal-facing threshold: vertices whose normal points up by less than this
# are treated as non-dorsal and painted gray. Sign/axis depend on convention.
DORSAL_NORMAL_THRESH = 0.3

CYCLIC_CMAP = "hsv"   # or a colorcet cyclic map, e.g. cc.cm.CET_C2
GRAY        = [0.15, 0.15, 0.15, 1.0]

# ---------------------------------------------------------------------------
# 1. LOAD MESH + PHASE MAP
# ---------------------------------------------------------------------------
mesh = trimesh.load(MESH_PATH)
vertices = mesh.vertices            # (N, 3) in CCF um
normals  = mesh.vertex_normals      # (N, 3)

phase_map = np.load(PHASE_MAP_PATH)  # (H, W), values 0..2*pi

# ---------------------------------------------------------------------------
# 2. BUILD INTERPOLATOR over the phase image
# ---------------------------------------------------------------------------
ap_axis = np.linspace(AP_MIN, AP_MAX, phase_map.shape[0])
ml_axis = np.linspace(ML_MIN, ML_MAX, phase_map.shape[1])

interpolator = RegularGridInterpolator(
    (ap_axis, ml_axis),
    phase_map,
    method="linear",
    bounds_error=False,
    fill_value=np.nan,   # vertices outside the image -> NaN
)

# ---------------------------------------------------------------------------
# 3. LOOK UP PHASE PER VERTEX
# ---------------------------------------------------------------------------
query_points = np.column_stack([vertices[:, AP_AXIS_IDX],
                                vertices[:, ML_AXIS_IDX]])
vertex_phase = interpolator(query_points)   # (N,)

# ---------------------------------------------------------------------------
# 4. MASK: must have data AND face dorsally
# ---------------------------------------------------------------------------
dorsal_mask = normals[:, DV_AXIS_IDX] > DORSAL_NORMAL_THRESH
valid = ~np.isnan(vertex_phase) & dorsal_mask

# ---------------------------------------------------------------------------
# 5. PHASE -> RGBA
# ---------------------------------------------------------------------------
cmap = plt.cm.get_cmap(CYCLIC_CMAP)
phase_norm = vertex_phase / (2 * np.pi)      # [0, 1]

vertex_colors = np.tile(np.array(GRAY), (len(vertices), 1))  # default gray
vertex_colors[valid] = cmap(phase_norm[valid])
vertex_colors = np.clip(vertex_colors, 0.0, 1.0)

np.save(OUT_PATH, vertex_colors)
print(f"wrote {OUT_PATH}  shape={vertex_colors.shape}  "
      f"({valid.sum()} / {len(vertices)} vertices colored)")
