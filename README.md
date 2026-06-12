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

The pipeline has two steps. Brain meshes are already provided in `sample_data/`
so you only need to run the preparation notebook once with your own data.

```
  Your data
  phase_colormap.npy                sample_data/
  (from your analysis pipeline)     root.obj  isocortex.obj  (provided)
          │                                 │
          └──────────────┬──────────────────┘
                         ▼
          notebooks/prepare_for_blender.ipynb
          (interpolates phase colors onto mesh vertices)
                         │
                         ▼
          sample_data/vertex_colors.npy
                         │
                         ▼
          scripts/03_render_blender.py  (run inside Blender)
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

### Your data file

| File | Description |
|------|-------------|
| `phase_colormap.npy` | 2D phase map as an RGB image, registered to Allen CCF. Shape `(1320, 1140, 3)`, float32 in `[0, 1]`. Cyclic colormap already applied in your analysis pipeline. |

> Brain mesh files (`root.obj`, `isocortex.obj`) are already provided in
> `sample_data/` — you do not need to download the atlas.

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

### Step 1 — Run the preparation notebook

Open `notebooks/prepare_for_blender.ipynb` in Jupyter and run all cells.

```bash
jupyter notebook notebooks/prepare_for_blender.ipynb
```

Edit the `PHASE_COLORMAP_PATH` variable in the first cell to point to your
`phase_colormap.npy` file.  Everything else is automatic.

The notebook will:
1. Load your phase colormap
2. Load `isocortex.obj` from `sample_data/`
3. Interpolate phase colors onto every 3D vertex of the cortex mesh
4. Show a visual check so you can confirm the alignment looks correct
5. Save `sample_data/vertex_colors.npy`

---

### Step 2 — Render in Blender

1. Open Blender
2. Go to the **Scripting** tab (top menu bar)
3. Click **Open** and load a render script
4. Set `data_dir` at the top of the script to the absolute path of `sample_data/`
5. Click **▶ Run Script** (or press **Alt+P**)

The render is saved automatically as a PNG inside `data_dir`.

**Choose the style that fits your use case:**

| Script | Style | Best for |
|--------|-------|----------|
| `scripts/03_render_blender.py` | Metallic / iridescent | Journal covers, posters |
| `scripts/03b_render_matte.py` | Matte / flat-color | Data figures, supplementary panels |
| `scripts/03c_render_density_scatter.py` | Metallic brain + scatter dots | Spiral event locations |

---

### (Optional) Choose a custom camera angle

Each render script has a saved camera angle hardcoded near the bottom.  To
capture a new angle:

1. Navigate to the desired view in the Blender **3D viewport**
2. Open `scripts/extract_camera_params.py` in the Scripting tab
3. Set `MODE = 'viewport'` and run the script
4. Paste the two printed lines (`cam_obj.location`, `cam_obj.rotation_euler`)
   into the camera section of your render script

> **macOS tip:** Launch Blender from Terminal to see `print()` output:
> ```bash
> /Applications/Blender.app/Contents/MacOS/Blender
> ```
> Values are also saved to a **CameraParams** text block in the Blender Text
> Editor, accessible without a terminal.

---

## File reference

```
rotating-wave-brain-render/
├── sample_data/                          ← provided, ready to use
│   ├── root.obj                          #   whole-brain outer shell
│   ├── isocortex.obj                     #   dorsal cortex surface mesh
│   ├── vertex_colors.npy                 #   pre-computed phase colors (sample)
│   └── spiral_density.mat                #   spiral event coordinates
│
├── notebooks/
│   ├── prepare_for_blender.ipynb         ← START HERE — build vertex_colors.npy
│   └── phase_colormap_workflow.py        #   same pipeline as a plain Python script
│
├── scripts/
│   ├── 01_export_brain_meshes.py         #   re-export .obj from Allen CCF atlas
│   ├── 02_phasemap_to_vertex_colors.py   #   phase map → vertex_colors.npy
│   ├── 02b_density_to_vertex_colors.py   #   density map → vertex_colors_density.npy
│   ├── 03_render_blender.py              #   Blender: metallic/iridescent style
│   ├── 03b_render_matte.py               #   Blender: matte/scientific style
│   ├── 03c_render_density_scatter.py     #   Blender: scatter dots on brain
│   └── extract_camera_params.py          #   Blender: capture camera angle
│
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
