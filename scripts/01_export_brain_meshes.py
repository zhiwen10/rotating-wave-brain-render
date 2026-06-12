"""
Step 1: Export Allen CCF brain meshes as .obj files.

Produces:
    root.obj       -> whole-brain shell (for context / outline)
    isocortex.obj  -> dorsal cortical surface (this is what gets phase colors)
    (optional) thalamus.obj, striatum.obj for subcortical depth.

These .obj files are loaded directly by the Blender render script (step 3).

Run in a normal Python env (NOT inside Blender):
    pip install brainglobe-atlasapi
    python 01_export_brain_meshes.py

Note: the first call downloads the atlas (~hundreds of MB) and caches it
locally, so subsequent runs are fast.
"""

import os
from brainglobe_atlasapi import BrainGlobeAtlas

# ---- Output directory ----
OUT_DIR = "raw_data"
os.makedirs(OUT_DIR, exist_ok=True)

# 25um atlas is a good balance of detail vs mesh size.
# Use allen_mouse_10um for a denser cortical mesh if you want finer color.
atlas = BrainGlobeAtlas("allen_mouse_25um")

# Structures to export: (CCF acronym, output filename)
structures = [
    ("root", "root.obj"),            # whole brain shell
    ("Isocortex", "isocortex.obj"),  # dorsal cortex (phase map target)
    # ("TH", "thalamus.obj"),        # uncomment for subcortical context
    # ("STR", "striatum.obj"),
]

for acronym, fname in structures:
    mesh = atlas.mesh_from_structure(acronym)
    out_path = os.path.join(OUT_DIR, fname)
    mesh.write(out_path)
    print(f"wrote {out_path}")

print("done. root.obj and isocortex.obj are in raw_data/.")
