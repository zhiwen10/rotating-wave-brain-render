# Rotating Wave Phase Map on a 3D Mouse Brain

Pipeline for rendering a 2D dorsal cortical phase map (rotating waves) overlaid
onto a 3D Allen CCF mouse brain in Blender, for journal covers, posters, and
figures.

The workflow has three stages: export brain meshes, convert the phase map to
per-vertex colors, then render in Blender from a saved camera angle.

```
phase_map.npy  ─┐
                ├─► 02 ─► vertex_colors.npy ─┐
isocortex.obj ──┘                            ├─► 03 (Blender) ─► render.png
root.obj  ───────────────────────────────────┘
   ▲
   01 (brainrender export)
```

## Files

| File | Where it runs | What it does |
|------|---------------|--------------|
| `scripts/01_export_brain_meshes.py` | normal Python | Exports `root.obj` (whole brain) and `isocortex.obj` (cortex) from the Allen CCF via brainglobe-atlasapi. |
| `scripts/02_phasemap_to_vertex_colors.py` | normal Python | Interpolates your 2D phase map onto the cortex vertices and writes `vertex_colors.npy`. |
| `scripts/03_render_blender.py` | inside Blender | Imports the meshes, applies the phase colors and metallic/iridescent materials, lights the scene, and renders the saved camera angle to a PNG. |
| `scripts/extract_camera_params.py` | inside Blender | Prints the current viewport camera location/rotation to paste back into step 3 when you want a new saved angle. |

## Requirements

Python side (steps 1 and 2):

```bash
pip install -r requirements.txt
```

Blender side (steps 3 and the camera helper): Blender 3.x or 4.x. The render
script uses numpy, which is bundled with Blender's Python. If it is missing:

```python
import subprocess, sys
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'numpy'])
```

## How to run

### 1. Export the meshes (normal Python)

```bash
cd scripts
python 01_export_brain_meshes.py
```

First run downloads and caches the atlas. Produces `root.obj` and
`isocortex.obj`.

### 2. Build the vertex colors (normal Python)

Put your registered phase map at `phase_map.npy` (2D, values in `[0, 2*pi]`),
then edit the AP/ML extents and axis indices at the top of the script to match
your own registration, and run:

```bash
python 02_phasemap_to_vertex_colors.py
```

Produces `vertex_colors.npy`.

### 3. Render in Blender

Collect `root.obj`, `isocortex.obj`, and `vertex_colors.npy` into one folder.
Open `scripts/03_render_blender.py`, set `data_dir` near the top to that
folder, then:

1. Open Blender, go to the **Scripting** tab.
2. Click **Open** and load `03_render_blender.py` (or paste it into a new text
   block).
3. Click **Run Script** (play icon) or press **Alt+P**.

With `SAVE_RENDER = True` (default) it writes `rotating_wave_render.png` into
`data_dir`. View colors live in the viewport by switching shading to
**Rendered** or **Material Preview** (the sphere icons, top-right of the
viewport).

### Choosing a new camera angle

The saved angle lives in section 9 of the render script as `cam_obj.location`
and `cam_obj.rotation_euler`. To capture a different one:

1. Frame the angle in the viewport.
2. Press **Ctrl+Alt+Numpad 0** to snap the camera to the view.
3. Run `extract_camera_params.py` and copy the printed values back into
   section 9.

On macOS, launch Blender from Terminal to see `print()` output:

```bash
/Applications/Blender.app/Contents/MacOS/Blender
```

## Notes

- The render script is the "metallic / iridescent" style (transparent brain
  shell with a Fresnel color shift, emissive phase cortex, dorsal outline hull).
  Material, lighting, and camera parameters are grouped at the top for tuning.
- `02_phasemap_to_vertex_colors.py` can be adapted to other scalar overlays
  (for example a spiral density map) by swapping the per-vertex value source
  before the colormap step.
- Coordinate conventions (which CCF axis is AP vs ML vs depth) must match your
  own registration. Verify before trusting the overlay alignment.
