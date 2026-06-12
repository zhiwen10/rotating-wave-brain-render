# Rotating Wave Phase Map on a 3D Mouse Brain

Render a 2D dorsal cortical phase map onto a 3D Allen CCF mouse brain in Blender.

---

## How it works

The phase map and the brain mesh share the same coordinate space — the **Allen Common Coordinate Framework (CCF)**. This makes the overlay straightforward:

1. **The brain mesh** (`isocortex.obj`) is a 3D surface where every vertex has a position in CCF micrometres (AP, DV, ML axes).
2. **The phase map** (`phase_colormap.npy`) is a 2D top-down image of the dorsal cortex, where rows = AP axis and columns = ML axis, also in CCF space.
3. **The overlay** is a bilinear lookup: for each 3D vertex, read its (AP, ML) coordinate and sample the corresponding pixel color from the phase image. No registration or warping is needed because both datasets are already aligned to CCF.

```
phase_colormap.npy               isocortex.obj
(2D image, AP × ML)              (3D mesh, vertices in CCF µm)
        │                                 │
        └──────── for each vertex: ───────┘
                  look up color at (AP, ML)
                  via bilinear interpolation
                        │
                        ▼
                vertex_colors.npy
                (one RGBA color per vertex)
                        │
                        ▼
                  Blender render
```

---

## Installation

### Option A — conda (recommended)

```bash
git clone https://github.com/zhiwen10/rotating-wave-brain-render.git
cd rotating-wave-brain-render
conda env create -f environment.yml
conda activate brain_render_2d
```

### Option B — pip

```bash
pip install trimesh scipy matplotlib numpy mat73 jupyter
```

> **Blender** (3.x or 4.x) is needed for Step 2 only — install it separately from [blender.org](https://www.blender.org/download/). The Python packages above are **not** needed inside Blender.

---

## Steps

### Step 1 — Prepare vertex colors

Open and run `notebooks/prepare_for_blender.ipynb`.

The notebook loads `phase_colormap.npy` and `isocortex.obj` from `sample_data/`,
interpolates the phase colors onto the mesh vertices, shows a visual check, and
saves `sample_data/vertex_colors.npy`.

> To use your own data, set `PHASE_COLORMAP_PATH` in the first cell.

---

### Step 2 — Render in Blender

1. Open Blender → **Scripting** tab
2. Open a render script and set `data_dir` to the `sample_data/` folder
3. Press **▶ Run Script** (or **Alt+P**)

| Script | Style |
|--------|-------|
| `scripts/03_render_blender.py` | Metallic / iridescent |
| `scripts/03b_render_matte.py` | Matte / scientific |

The render is saved as a PNG inside `data_dir`.

---

## Sample data

`sample_data/` contains everything needed to run both steps out of the box:

| File | Description |
|------|-------------|
| `phase_colormap.npy` | 2D phase map, shape `(1320, 1140, 3)` RGB, registered to Allen CCF 25 µm |
| `isocortex.obj` | Dorsal isocortex surface mesh |
| `root.obj` | Whole-brain outer shell |

---

## Changing the camera angle

Each render script has a hardcoded camera angle near the bottom. To capture a
new one:

1. Navigate to the desired view in the Blender 3D viewport
2. Run `scripts/extract_camera_params.py` with `MODE = 'viewport'`
3. Paste the printed `cam_obj.location` and `cam_obj.rotation_euler` into the render script

> On macOS, launch Blender from Terminal to see printed output:
> `/Applications/Blender.app/Contents/MacOS/Blender`
