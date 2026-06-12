"""Generate top-down vertex-color preview PNGs for phase map and density map."""
import numpy as np
import mat73
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.interpolate import RegularGridInterpolator, griddata

SAMPLE = "sample_data"
AP_BINS, ML_BINS = 1320, 1140
AP_UM, ML_UM     = 13200.0, 11400.0
GRAY             = [0.0, 0.0, 0.0, 1.0]

# ── 1. Convert spiral_density.mat → unique_spirals.npy ───────────────────
data = mat73.loadmat(f"{SAMPLE}/spiral_density.mat")
s = np.array(data["unique_spirals"], dtype=np.float32)
# Columns: [ML_voxel, AP_voxel, density]  (voxel indices in 10 µm CCF space)
np.save(f"{SAMPLE}/unique_spirals.npy", s)
ml_pts  = s[:, 0] * 10   # ML voxels → µm
ap_pts  = s[:, 1] * 10   # AP voxels → µm
density = s[:, 2]
print(f"unique_spirals: AP {ap_pts.min():.0f}–{ap_pts.max():.0f} µm  "
      f"ML {ml_pts.min():.0f}–{ml_pts.max():.0f} µm")

# ── 2. Interpolate scattered density → regular 2D grid ───────────────────
ap_axis = np.linspace(0, AP_UM, AP_BINS)
ml_axis = np.linspace(0, ML_UM, ML_BINS)
Xq, Yq = np.meshgrid(ap_axis, ml_axis, indexing='ij')

density_map  = griddata((ap_pts, ml_pts), density,
                         (Xq, Yq), method='linear', fill_value=0)
density_norm = np.clip((density_map - density_map.min()) /
                       (density_map.max() - density_map.min() + 1e-12), 0, 1)
rgb_density  = plt.colormaps["hot"](density_norm)[:, :, :3].astype(np.float32)

# ── 3. Interpolate density RGB onto mesh vertices ─────────────────────────
mesh     = trimesh.load(f"{SAMPLE}/isocortex.obj")
vertices = mesh.vertices
query    = np.column_stack([vertices[:, 0], vertices[:, 2]])   # (AP, ML)

def interp_ch(img, ch):
    return RegularGridInterpolator(
        (ap_axis, ml_axis), img[:, :, ch],
        method="linear", bounds_error=False, fill_value=np.nan)(query)

r, g, b = interp_ch(rgb_density, 0), interp_ch(rgb_density, 1), interp_ch(rgb_density, 2)
invalid    = np.isnan(r)
vc_density = np.column_stack([r, g, b, np.ones(len(vertices))])
vc_density[invalid] = GRAY
vc_density = np.clip(vc_density, 0.0, 1.0).astype(np.float32)
np.save(f"{SAMPLE}/vertex_colors_density.npy", vc_density)
print(f"vertex_colors_density.npy: {(~invalid).sum()}/{len(vertices)} colored")

# ── 4. Load phase map vertex colors ──────────────────────────────────────
vc_phase = np.load(f"{SAMPLE}/vertex_colors.npy")

# ── 5. Save preview PNGs ─────────────────────────────────────────────────
ap = vertices[:, 0]
ml = vertices[:, 2]

for label, vc, fname in [
    ("Phase map", vc_phase, f"{SAMPLE}/preview_phase.png"),
    ("Spiral density map", vc_density, f"{SAMPLE}/preview_density.png"),
]:
    fig, ax = plt.subplots(figsize=(5, 6), facecolor="#0a0a0a")
    ax.set_facecolor("#0a0a0a")
    ax.scatter(ml, ap, c=vc[:, :3], s=2, marker=".", linewidths=0, rasterized=True)
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.set_title(label, color="white", fontsize=13, pad=8)
    ax.set_xlabel("ML (µm)", color="white")
    ax.set_ylabel("AP (µm)", color="white")
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_edgecolor("#444")
    plt.tight_layout()
    plt.savefig(fname, dpi=200, facecolor=fig.get_facecolor())
    plt.close()
    print(f"Saved {fname}")
