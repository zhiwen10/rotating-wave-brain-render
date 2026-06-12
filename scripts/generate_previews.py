"""Generate top-down vertex-color preview PNGs for phase map and density map."""
import numpy as np
import mat73
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import gaussian_filter

SAMPLE = "sample_data"
AP_BINS, ML_BINS = 1320, 1140
AP_UM, ML_UM     = 13200.0, 11400.0
SMOOTH_SIGMA     = 8.0
GRAY             = [0.15, 0.15, 0.15, 1.0]

# ── 1. Convert spiral_density.mat → unique_spirals.npy ───────────────────
data = mat73.loadmat(f"{SAMPLE}/spiral_density.mat")
s = np.array(data["unique_spirals"], dtype=np.float32)
s[:, 0] *= 10   # AP pixel indices → µm  (10 µm per pixel)
s[:, 1] *= 10   # ML pixel indices → µm
np.save(f"{SAMPLE}/unique_spirals.npy", s)
print(f"unique_spirals: AP {s[:,0].min():.0f}–{s[:,0].max():.0f} µm  "
      f"ML {s[:,1].min():.0f}–{s[:,1].max():.0f} µm")

# ── 2. Build density image from weighted histogram ────────────────────────
ap_edges = np.linspace(0, AP_UM, AP_BINS + 1)
ml_edges = np.linspace(0, ML_UM, ML_BINS + 1)
density_img, _, _ = np.histogram2d(s[:,0], s[:,1],
                                   bins=[ap_edges, ml_edges],
                                   weights=s[:,2])
density_img = gaussian_filter(density_img, sigma=SMOOTH_SIGMA)
density_norm = (density_img - density_img.min()) / (density_img.max() - density_img.min() + 1e-12)
rgb_density = plt.cm.get_cmap("hot")(density_norm)[:, :, :3].astype(np.float32)

# ── 3. Interpolate density onto mesh vertices ─────────────────────────────
mesh     = trimesh.load(f"{SAMPLE}/isocortex.obj")
vertices = mesh.vertices
ap_coords = np.linspace(0, AP_UM, AP_BINS)
ml_coords = np.linspace(0, ML_UM, ML_BINS)
query = np.column_stack([vertices[:, 0], vertices[:, 2]])

def interp_channel(img, ch):
    return RegularGridInterpolator(
        (ap_coords, ml_coords), img[:, :, ch],
        method="linear", bounds_error=False, fill_value=np.nan)(query)

r, g, b = interp_channel(rgb_density, 0), interp_channel(rgb_density, 1), interp_channel(rgb_density, 2)
invalid = np.isnan(r)
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
