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

> **Blender** (3.x or 4.x) is needed for Step 3 only — install it separately from [blender.org](https://www.blender.org/download/). The Python packages above are **not** needed inside Blender.

---

## Workflow

```
Step 1                    Step 2                         Step 3
──────────────────────    ──────────────────────────     ──────────────────────────
01_export_brain_meshes.py  02_prepare_for_blender.ipynb   03_render_blender.py
                           02b_density_to_vertex_colors.py  03b_render_density.py
runs on: Python            runs on: Python (Jupyter/CLI)  runs on: Blender (built-in Python)
uses:    brainglobe-       uses:    trimesh, scipy,        uses:    bpy (Blender API)
         atlasapi                   numpy, matplotlib,
                                    mat73
                                                                       │
input:   Allen CCF atlas   input:   raw_data/               input:   raw_data/
         (auto-download)             phase_colormap.npy               root.obj
                                     isocortex.obj                    isocortex.obj
                                     spiral_density.mat             processed_data/
                                                                     vertex_colors.npy
output:  raw_data/         output:  processed_data/         output:  processed_data/
           root.obj                   vertex_colors.npy               render_*.png
           isocortex.obj              vertex_colors_density.npy
```

---

## Steps

### Step 1 — Export brain meshes

> Skip this step if you are using the provided `raw_data/` files.

Run `scripts/01_export_brain_meshes.py` in the `brain_render_2d` conda env.

```bash
python scripts/01_export_brain_meshes.py
```

Downloads the Allen CCF 25 µm atlas via `brainglobe-atlasapi` (first run only,
~hundreds of MB) and exports `root.obj` and `isocortex.obj` into `raw_data/`.

---

### Step 2 — Prepare vertex colors

**Phase map** — open and run `notebooks/02_prepare_for_blender.ipynb`:

```bash
jupyter notebook notebooks/02_prepare_for_blender.ipynb
```

Loads `phase_colormap.npy` and `isocortex.obj` from `raw_data/`,
interpolates the phase colors onto the mesh vertices, shows a visual check,
and saves `processed_data/vertex_colors.npy`.

> To use your own phase map, set `PHASE_COLORMAP_PATH` in the first cell.

**Density map** — run `scripts/02b_density_to_vertex_colors.py`:

```bash
python scripts/02b_density_to_vertex_colors.py
```

Loads `spiral_density.mat` from `raw_data/` and saves
`processed_data/vertex_colors_density.npy`.

---

### Step 3 — Render in Blender

1. Open Blender → **Scripting** tab
2. Open a render script, set `raw_data_dir` and `processed_data_dir` at the top
3. Press **▶ Run Script** (or **Alt+P**)

| Script | Style | Input | Output |
|--------|-------|-------|--------|
| `scripts/03_render_blender.py` | Metallic / iridescent | `processed_data/vertex_colors.npy` | `processed_data/render_metallic.png` |
| `scripts/03b_render_density.py` | Metallic / density map | `processed_data/vertex_colors_density.npy` | `processed_data/render_density.png` |

---

## Data folders

### `raw_data/` — inputs (provided in this repo)

| File | Description |
|------|-------------|
| `phase_colormap.npy` | 2D phase map, shape `(1320, 1140, 3)` RGB, registered to Allen CCF |
| `spiral_density.mat` | Spiral event coordinates and density, columns: `[ML_voxel, AP_voxel, density]` |
| `isocortex.obj` | Dorsal isocortex surface mesh |
| `root.obj` | Whole-brain outer shell |

### `processed_data/` — outputs (generated by Steps 2–3)

| File | Generated by | Description |
|------|-------------|-------------|
| `vertex_colors.npy` | Step 2 notebook | Per-vertex RGBA phase colors |
| `vertex_colors_density.npy` | `02b_density_to_vertex_colors.py` | Per-vertex RGBA density colors |
| `render_metallic.png` | `03_render_blender.py` | 3D render — metallic style |
| `render_matte.png` | `03b_render_matte.py` | 3D render — matte style |
| `render_density.png` | `03b_render_density.py` | 3D render — density map |

---

## Changing the camera angle

Each render script has a hardcoded camera angle near the bottom. To capture a
new one:

1. Navigate to the desired view in the Blender 3D viewport
2. Run `scripts/extract_camera_params.py` with `MODE = 'viewport'`
3. Paste the printed `cam_obj.location` and `cam_obj.rotation_euler` into the render script

> Set `raw_data_dir` and `processed_data_dir` at the top of each render script before running.

> On macOS, launch Blender from Terminal to see printed output:
> `/Applications/Blender.app/Contents/MacOS/Blender`
