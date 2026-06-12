"""
Phase colormap → vertex colors

Converts phase_colormap.mat and spiral_density.mat (your analysis outputs)
into vertex_colors.npy for use by the Blender render scripts.

NOTE: Brain mesh export (root.obj, isocortex.obj) is a separate one-time step
using scripts/01_export_brain_meshes.py.  Run that first, then run this script.

INPUTS:
    isocortex.obj        — cortex mesh from scripts/01_export_brain_meshes.py
    phase_colormap.mat   — 2D phase map as RGB, registered to Allen CCF.
                           Variable: 'rgbImage', shape (1320, 1140, 3).
                           Cyclic colormap already applied (e.g. CET_C6).
    spiral_density.mat   — Spiral event coordinates.
                           Variable: 'unique_spirals', shape (N, 3):
                           [AP_µm, ML_µm, density_count].

OUTPUTS:
    phase_colormap.npy   — converted from .mat, shape (1320, 1140, 3) float32
    unique_spirals.npy   — converted from .mat, shape (N, 3) float32
    vertex_colors.npy    — per-vertex RGBA for phase map, shape (N, 4) float32
    interpolation_check.png  — visual sanity check of the registration

COORDINATE SYSTEM (Allen CCF 25 µm atlas):
    axis 0 = AP   0 – 13 200 µm   (image rows,    1 320 voxels)
    axis 1 = DV   0 –  5 350 µm   (depth — not used for 2D lookup)
    axis 2 = ML   0 – 11 400 µm   (image columns, 1 140 voxels)

Run in a normal Python environment (NOT inside Blender):
    pip install trimesh scipy matplotlib numpy mat73
    python notebooks/phase_colormap_workflow.py
"""

import numpy as np
import trimesh
import mat73
from scipy.interpolate import RegularGridInterpolator
import matplotlib.pyplot as plt

# ============================================================================
# STEP 1 — Convert .mat files to .npy  (one-time)
# ============================================================================

data = mat73.loadmat("phase_colormap.mat")
phase_rgb = np.array(data["rgbImage"], dtype=np.float32)
if phase_rgb.max() > 1.0:       # convert uint8 → float32 [0, 1] if needed
    phase_rgb = phase_rgb / 255.0
np.save("phase_colormap.npy", phase_rgb)
print(f"phase_colormap.npy  shape={phase_rgb.shape}  "
      f"range=[{phase_rgb.min():.3f}, {phase_rgb.max():.3f}]")

data2 = mat73.loadmat("spiral_density.mat")
unique_spirals = np.array(data2["unique_spirals"], dtype=np.float32)
np.save("unique_spirals.npy", unique_spirals)
print(f"unique_spirals.npy  shape={unique_spirals.shape}")

# ============================================================================
# STEP 2 — Load isocortex mesh
# ============================================================================
# Assumes isocortex.obj was already produced by scripts/01_export_brain_meshes.py

mesh     = trimesh.load("isocortex.obj")
vertices = mesh.vertices        # (N, 3) in Allen CCF µm
normals  = mesh.vertex_normals

print("Axis 0 (AP) range:", vertices[:, 0].min(), "–", vertices[:, 0].max())
print("Axis 1 (DV) range:", vertices[:, 1].min(), "–", vertices[:, 1].max())
print("Axis 2 (ML) range:", vertices[:, 2].min(), "–", vertices[:, 2].max())

# ============================================================================
# STEP 3 — Interpolate phase colormap onto mesh vertices
# ============================================================================

H, W    = phase_rgb.shape[:2]
ap_axis = np.linspace(0, 13200, H)   # 1320 voxels × 25 µm
ml_axis = np.linspace(0, 11400, W)   # 1140 voxels × 25 µm

def make_interp(channel):
    return RegularGridInterpolator(
        (ap_axis, ml_axis),
        phase_rgb[:, :, channel],
        method="linear",
        bounds_error=False,
        fill_value=np.nan,    # NaN for vertices outside the image FOV
    )

interp_r = make_interp(0)
interp_g = make_interp(1)
interp_b = make_interp(2)

# Each vertex is looked up by its (AP, ML) position — axis 0 and axis 2
query = np.column_stack([vertices[:, 0], vertices[:, 2]])
r = interp_r(query)
g = interp_g(query)
b = interp_b(query)

# ============================================================================
# STEP 4 — Assemble vertex colors; paint out-of-FOV vertices gray
# ============================================================================

GRAY    = [0.15, 0.15, 0.15, 1.0]
invalid = np.isnan(r)    # vertices outside the phase-map field of view

# Optional: also mask ventral/medial vertices (uncomment to enable)
# invalid = invalid | (normals[:, 1] < 0.3)

vertex_colors           = np.column_stack([r, g, b, np.ones(len(vertices))])
vertex_colors[invalid]  = GRAY
vertex_colors           = np.clip(vertex_colors, 0.0, 1.0).astype(np.float32)

np.save("vertex_colors.npy", vertex_colors)
print(f"vertex_colors.npy  shape={vertex_colors.shape}  "
      f"({(~invalid).sum()}/{len(vertices)} vertices colored)")

# ============================================================================
# STEP 5 — Visual sanity check: top-down scatter plot
# ============================================================================
# Open interpolation_check.png to verify the colors align with the brain outline.

fig, axes = plt.subplots(1, 3, figsize=(18, 6))

axes[0].imshow(phase_rgb, origin="lower")
axes[0].set_title("Original phase colormap")

ap = vertices[:, 0]
ml = vertices[:, 2]
axes[1].scatter(ml, ap, c=vertex_colors[:, :3], s=0.05, marker=".")
axes[1].set_aspect("equal")
axes[1].set_title("All vertices (top-down)")

valid_mask = ~np.all(np.isclose(vertex_colors[:, :3], 0.15), axis=1)
axes[2].scatter(ml[valid_mask], ap[valid_mask],
                c=vertex_colors[valid_mask, :3], s=0.05, marker=".")
axes[2].set_aspect("equal")
axes[2].set_title("Colored vertices only")

plt.tight_layout()
plt.savefig("interpolation_check.png", dpi=200)
plt.show()
print("Saved interpolation_check.png")
