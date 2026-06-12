# Rotating Wave Phase Map on a 3D Mouse Brain

Render a 2D dorsal cortical phase map (rotating waves) or spiral-density data
onto a 3D Allen CCF mouse brain in Blender.  Produces publication-quality PNGs
for journal covers, posters, and supplementary figures.

---

## Background — what is this pipeline doing?

### What are the .obj brain mesh files?

The mouse brain has a well-defined 3D coordinate system called the
**Allen Common Coordinate Framework (CCF)**.  Every point in the brain is
assigned a position in micrometres along three axes:

```
AP  — anterior–posterior (front to back)
DV  — dorsal–ventral     (top to bottom)
ML  — medial–lateral     (left to right)
```

The Allen Institute provides atlas data for the entire mouse brain at this
coordinate system, including the 3D shape of every brain region.
`brainglobe-atlasapi` downloads this atlas and extracts the **surface mesh**
of any region as a `.obj` file — the same format used by 3D modelling software
like Blender.  A surface mesh is just a list of vertices (3D points) and the
triangular faces connecting them that together describe the outer shell of the
structure.

This pipeline exports two meshes:
- **`root.obj`** — the outer surface of the whole brain, used as a
  semi-transparent context shell in the render.
- **`isocortex.obj`** — the surface of the dorsal isocortex, the region where
  the rotating waves are recorded.  This is the mesh that receives the phase
  colors.

These meshes are fixed anatomical structures — they come from the atlas and
do not depend on your experimental data.  You only need to export them once.

---

### How is the 2D phase map overlaid onto the 3D brain?

The key insight is that the phase map and the brain mesh live in the **same
coordinate space** (Allen CCF).  The phase map is a top-down (dorsal) image
of the cortex where each pixel corresponds to a specific AP–ML location in the
atlas.  The mesh vertices also each have an AP–ML position.  This means we can
directly look up the phase color for any vertex:

```
For each vertex in isocortex.obj:
    1. Read its AP coordinate (axis 0) and ML coordinate (axis 2).
    2. Look up that (AP, ML) location in the 2D phase image.
    3. Read the RGB color at that pixel (bilinear interpolation).
    4. Assign that color to the vertex.
```

This produces a `vertex_colors.npy` array — one RGBA color per vertex — which
Blender uses to paint the cortex surface.  No 3D registration or warping is
needed because both datasets are already in CCF space.

Vertices that fall outside the recorded field of view (e.g. medial wall,
ventral surface) are painted a neutral gray.

```
phase_colormap.npy                      isocortex.obj
(1320 × 1140 pixels, RGB)              (N vertices, each with AP/ML position)

  pixel at (AP=5000µm, ML=3000µm) ──► vertex at (AP=5000, DV=200, ML=3000)
  pixel at (AP=6000µm, ML=4000µm) ──► vertex at (AP=6000, DV=180, ML=4100)
  ...                                  ...

                        └──────────────┘
                        bilinear interpolation
                        (scipy RegularGridInterpolator)
                                │
                                ▼
                        vertex_colors.npy
                        (N vertices × 4 RGBA channels)
```

---

## Pipeline overview

Brain mesh export and phase map preparation are **independent** — run them in
either order, then bring the outputs together for rendering.

```
  Allen CCF atlas                        Your data (.mat files)
  (downloaded once)                      (from your analysis pipeline)
        │                                         │
        ▼                                         ▼
  scripts/01_export_brain_meshes.py    notebooks/phase_colormap_workflow.py
        │                                         │
        ▼                                         ▼
  root.obj  isocortex.obj              vertex_colors.npy
        │                                         │
        └──────────────┬──────────────────────────┘
                       ▼
           scripts/03_render_blender.py  (and variants)
                       │
                       ▼
                  render.png
```

---

## Prerequisites

### Software
- **Python 3.8+** with pip
- **Blender 3.x or 4.x** — [download here](https://www.blender.org/download/)
  (NumPy is bundled with Blender's Python, no extra install needed inside Blender)

### Your data files

| File | Description |
|------|-------------|
| `phase_colormap.mat` | 2D phase map as an RGB image, registered to Allen CCF. Variable: `rgbImage`, shape `(1320, 1140, 3)`. Cyclic colormap (e.g. CET_C6) already applied in your analysis pipeline. |
| `spiral_density.mat` | Detected spiral event coordinates. Variable: `unique_spirals`, shape `(N, 3)` — columns are `[AP_µm, ML_µm, density_count]`. |

---

## Installation

```bash
# Clone the repo
git clone https://github.com/zhiwen10/rotating-wave-brain-render.git
cd rotating-wave-brain-render

# Install Python dependencies
pip install -r requirements.txt
```

---

## Step-by-step usage

### Step A — Export brain meshes  *(one-time, independent of your data)*

Downloads the Allen CCF atlas and exports the brain surface meshes.  This only
needs to be done once — the meshes are the same regardless of your experiment.

```bash
python scripts/01_export_brain_meshes.py
```

Produces:
- `root.obj` — whole-brain outer shell (used as transparent context in render)
- `isocortex.obj` — dorsal cortical surface (receives phase colors)

> The first run downloads the Allen CCF 25 µm atlas (~400 MB) and caches it
> in `~/.brainglobe/`.  Subsequent runs are instant.

---

### Step B — Prepare your data and build vertex colors  *(independent of Step A)*

Converts your MATLAB data files and maps the phase map onto the cortex mesh.

```bash
# Copy your .mat files into the working folder (or edit paths inside the script)
cp /path/to/phase_colormap.mat .
cp /path/to/spiral_density.mat .

python notebooks/phase_colormap_workflow.py
```

This produces:
- `phase_colormap.npy` — RGB phase image `(1320, 1140, 3)` float32
- `unique_spirals.npy` — spiral coordinates `(N, 3)` float32
- `vertex_colors.npy` — one RGBA color per cortex vertex
- `interpolation_check.png` — top-down scatter plot showing phase colors
  projected onto the cortex outline; open this to verify alignment before rendering

> Step B reads `isocortex.obj` from Step A, so Step A must be run first.

If you prefer to run the conversion and interpolation as individual scripts
rather than the notebook:

```bash
python scripts/02_phasemap_to_vertex_colors.py    # → vertex_colors.npy
python scripts/02b_density_to_vertex_colors.py    # → vertex_colors_density.npy
```

---

### Step C — Render in Blender

Collect `root.obj`, `isocortex.obj`, and `vertex_colors.npy` into one folder.

1. Open Blender
2. Go to the **Scripting** tab (top menu bar)
3. Click **Open** and load a render script — or paste it into a new text block
4. Set `data_dir` at the top of the script to the folder containing your files
5. Click **▶ Run Script** (or press **Alt+P**)

The render is saved automatically as a PNG in `data_dir`.

**Available render styles:**

| Script | Style | Best for |
|--------|-------|----------|
| `scripts/03_render_blender.py` | Metallic / iridescent | Journal covers, posters |
| `scripts/03b_render_matte.py` | Matte / flat-color | Data figures, supplementary panels |
| `scripts/03c_render_density_scatter.py` | Metallic brain + scatter dots | Spiral event locations |

> To switch between phase and density data in the matte render, change
> `VERTEX_COLORS_FILE` at the top of `03b_render_matte.py`.

---

### (Optional) Choose a custom camera angle

Each render script has a camera angle hardcoded near the bottom.  To capture a
new angle:

1. Navigate to the desired view in the Blender **3D viewport**
2. Open `scripts/extract_camera_params.py` in the Scripting tab
3. Set `MODE = 'viewport'` and run the script
4. Copy the printed `cam_obj.location` and `cam_obj.rotation_euler` lines into
   the camera section of your render script

> **macOS tip:** Launch Blender from Terminal to see `print()` output:
> ```bash
> /Applications/Blender.app/Contents/MacOS/Blender
> ```
> The values are also saved to a **CameraParams** text block in the Blender
> Text Editor, accessible without a terminal.

---

## File reference

```
rotating-wave-brain-render/
├── notebooks/
│   └── phase_colormap_workflow.py    # Convert .mat files + build vertex colors
├── scripts/
│   ├── 01_export_brain_meshes.py     # Download Allen CCF atlas, export .obj meshes
│   ├── 02_phasemap_to_vertex_colors.py    # Phase RGB image → vertex_colors.npy
│   ├── 02b_density_to_vertex_colors.py   # Spiral density → vertex_colors_density.npy
│   ├── 03_render_blender.py          # Blender: metallic/iridescent, phase map
│   ├── 03b_render_matte.py           # Blender: matte/scientific style
│   ├── 03c_render_density_scatter.py # Blender: scatter dots on iridescent brain
│   └── extract_camera_params.py      # Blender: capture viewport or scene camera angle
├── requirements.txt
└── README.md
```

---

## Troubleshooting

**Colors look misaligned on the brain**
→ Open `interpolation_check.png`.  The colored region should match the dorsal
cortex outline.  If not, check that `phase_colormap.mat` is registered to the
Allen CCF 25 µm dorsal projection — the image dimensions should be
1320 × 1140 pixels corresponding to AP 0–13 200 µm and ML 0–11 400 µm.

**`No module named bpy` error**
→ The render scripts (`03_*.py`, `extract_camera_params.py`) must be run
*inside* Blender, not from the terminal.  Use the Scripting tab in Blender.

**Atlas download fails**
→ Check your internet connection.  The atlas is cached after the first download
in `~/.brainglobe/`.  Delete that folder to force a re-download.

**Blender renders a black or gray cortex**
→ Make sure `vertex_colors.npy` exists in `data_dir` and that `data_dir` is
set correctly at the top of the render script.
