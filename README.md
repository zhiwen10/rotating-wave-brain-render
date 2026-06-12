# Rotating Wave Phase Map on a 3D Mouse Brain

Render a 2D dorsal cortical phase map (rotating waves) or spiral-density data
onto a 3D Allen CCF mouse brain in Blender.  Produces publication-quality PNGs
for journal covers, posters, and supplementary figures.

**Example outputs:**
- Metallic / iridescent brain with phase-colored cortex (journal cover style)
- Matte / scientific brain for data figures
- Iridescent brain with hot-colormap scatter dots (spiral event locations)

---

## Overview

Brain mesh export and phase map preparation are **independent** — run them in
either order, then combine at the render step.

```
  Allen CCF atlas                        Your data (.mat files)
  (downloaded once)                      (from your analysis pipeline)
        │                                         │
        ▼                                         ▼
  scripts/01_export_brain_meshes.py    notebooks/phase_colormap_workflow.py
        │                                         │
        ▼                                         ▼
  root.obj, isocortex.obj              vertex_colors.npy
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
Place these in a working folder before starting:

| File | Description |
|------|-------------|
| `phase_colormap.mat` | 2D phase map as an RGB image, registered to the Allen CCF atlas. Variable name: `rgbImage`, shape `(1320, 1140, 3)`. Cyclic colormap (e.g. CET_C6) already applied. |
| `spiral_density.mat` | Detected spiral event coordinates. Variable name: `unique_spirals`, shape `(N, 3)` — columns are `[AP_µm, ML_µm, density_count]`. |

---

## Installation

```bash
# Clone the repo
git clone https://github.com/your-username/rotating-wave-brain-render.git
cd rotating-wave-brain-render

# Install Python dependencies
pip install -r requirements.txt
```

> **First run note:** Step 1 downloads the Allen CCF 25 µm atlas (~400 MB) and
> caches it locally.  All subsequent runs skip the download.

---

## Step-by-step usage

The two preparation steps (A and B below) are **independent** — run them in
either order, then bring the results together for rendering.

---

### Step A — Export brain meshes  *(one-time)*

This only needs to be done once.  The meshes come from the Allen CCF atlas and
never change regardless of your experimental data.

```bash
python scripts/01_export_brain_meshes.py
```

Produces:
- `root.obj` — whole-brain outer shell
- `isocortex.obj` — dorsal cortical surface (this is what gets colored)

> First run downloads and caches the Allen CCF 25 µm atlas (~400 MB).
> Subsequent runs are instant.

---

### Step B — Convert your data and build vertex colors

Run the notebook workflow script to convert your MATLAB data and map it onto
the cortex mesh:

```bash
# Copy your .mat files into the working folder (or edit paths inside the script)
cp /path/to/phase_colormap.mat .
cp /path/to/spiral_density.mat .

python notebooks/phase_colormap_workflow.py
```

This produces:
- `phase_colormap.npy` — RGB phase image `(1320, 1140, 3)` float32
- `unique_spirals.npy` — spiral coordinates `(N, 3)` float32
- `vertex_colors.npy` — per-vertex RGBA colors for the phase map
- `interpolation_check.png` — visual sanity check (phase colors projected top-down onto the cortex outline)

Open `interpolation_check.png` to confirm alignment before rendering.

> Step B requires `isocortex.obj` from Step A.

---

### Step 2 — Map your data onto mesh vertices  *(alternative to notebook)*

**For the phase map:**
```bash
python scripts/02_phasemap_to_vertex_colors.py
```
Produces `vertex_colors.npy`.

**For the spiral density map:**
```bash
python scripts/02b_density_to_vertex_colors.py
```
Produces `vertex_colors_density.npy`.

> The scripts interpolate the 2D image onto each 3D mesh vertex using its
> (AP, ML) position in Allen CCF coordinates.  Vertices outside the image
> field of view are painted neutral gray.

---

### Step 3 — Render in Blender

Collect all files (`root.obj`, `isocortex.obj`, `vertex_colors.npy`) into one
folder.

1. Open Blender
2. Go to the **Scripting** tab (top menu bar)
3. Click **Open** and load the render script — or paste it into a new text block
4. Set `data_dir` at the top of the script to the folder containing your files
5. Click **▶ Run Script** (or press **Alt+P**)

The render is saved automatically as a PNG in `data_dir`.

**Choose the render style that fits your use case:**

| Script | Style | Best for |
|--------|-------|----------|
| `scripts/03_render_blender.py` | Metallic / iridescent | Journal covers, posters |
| `scripts/03b_render_matte.py` | Matte / flat-color | Data figures, supplementary |
| `scripts/03c_render_density_scatter.py` | Metallic + scatter dots | Spiral event locations |

> To switch between phase and density data in the matte render, change
> `VERTEX_COLORS_FILE` at the top of `03b_render_matte.py`.

---

### (Optional) Choose a custom camera angle

The render scripts each have a saved camera angle hardcoded near the bottom.
To capture a new angle:

1. Navigate to your desired view in the Blender **3D viewport**
2. Open `scripts/extract_camera_params.py` in the Scripting tab
3. Set `MODE = 'viewport'` and run the script
4. The printed `cam_obj.location` and `cam_obj.rotation_euler` lines are saved
   to a **CameraParams** text block in the Text Editor
5. Paste those two lines into the camera section of your render script

> **macOS tip:** Launch Blender from Terminal to see `print()` output:
> ```bash
> /Applications/Blender.app/Contents/MacOS/Blender
> ```

---

## How the resampling works

The 3D brain mesh vertices are stored in **Allen CCF µm coordinates**:

```
axis 0 = AP   (0 – 13 200 µm)   ←→   image rows
axis 1 = DV   (0 –  5 350 µm)   ←→   depth (not used for 2D lookup)
axis 2 = ML   (0 – 11 400 µm)   ←→   image columns
```

For each vertex, its `(axis 0, axis 2)` position is used to look up the
corresponding pixel in the 2D phase/density image via bilinear interpolation
(`scipy.interpolate.RegularGridInterpolator`).  Because the image is already
registered to the same CCF coordinate space, no additional alignment is needed.

---

## File reference

```
rotating-wave-brain-render/
├── notebooks/
│   └── phase_colormap_workflow.py   # Full pipeline from .mat files to vertex colors
├── scripts/
│   ├── 01_export_brain_meshes.py    # Download atlas and export .obj meshes
│   ├── 02_phasemap_to_vertex_colors.py   # Phase RGB image → vertex_colors.npy
│   ├── 02b_density_to_vertex_colors.py  # Spiral density → vertex_colors_density.npy
│   ├── 03_render_blender.py         # Blender: metallic/iridescent, phase map
│   ├── 03b_render_matte.py          # Blender: matte/scientific style
│   ├── 03c_render_density_scatter.py # Blender: scatter dots on iridescent brain
│   └── extract_camera_params.py     # Blender: capture viewport or scene camera angle
├── requirements.txt
└── README.md
```

---

## Troubleshooting

**Colors look misaligned on the brain**
→ Open `interpolation_check.png` (produced by the notebook workflow).  The
colored region should match the dorsal cortex outline.  If not, check that
`phase_colormap.mat` is registered to the Allen CCF 25 µm dorsal projection.

**"No module named bpy" error**
→ The Blender scripts (`03_*.py`, `extract_camera_params.py`) must be run
*inside* Blender, not from the terminal.

**Atlas download fails**
→ Check your internet connection.  The atlas is cached after the first download
in `~/.brainglobe/`.  Delete that folder to force a re-download.

**Blender renders a black or gray cortex**
→ Make sure `vertex_colors.npy` exists in `data_dir` and that the path is set
correctly at the top of the render script.
