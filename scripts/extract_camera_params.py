"""
Camera helper: capture a viewport angle for the render script.

Run this INSIDE Blender (Scripting tab -> Run Script, or Alt+P) to print the
current camera's location and rotation, ready to paste into section 9 of
03_render_blender.py.

Workflow for choosing a new saved angle:
    1. In the 3D viewport, navigate to the angle you want.
    2. Press Ctrl+Alt+Numpad 0  (View > Align View > Align Active Camera to View)
       to snap the scene camera to your current view.
    3. Run this script.
    4. Copy the printed cam_obj.location / cam_obj.rotation_euler lines over the
       existing ones in 03_render_blender.py.

On macOS, print() output only shows if Blender was launched from Terminal:
    /Applications/Blender.app/Contents/MacOS/Blender
Otherwise, the values are also written to a "CameraParams" text block you can
open in the Text Editor.
"""

import bpy
import math

cam_obj = bpy.context.scene.camera
if cam_obj is None:
    print("No active scene camera. Add one or run the render script first.")
else:
    cam_data = cam_obj.data
    loc = cam_obj.location
    rot = cam_obj.rotation_euler

    lines = [
        "# --- Paste into section 9 of 03_render_blender.py ---",
        f"cam_obj.location = ({loc.x:.4f}, {loc.y:.4f}, {loc.z:.4f})",
        f"cam_obj.rotation_euler = ({rot.x:.4f}, {rot.y:.4f}, {rot.z:.4f})",
        f"cam_data.type = '{cam_data.type}'",
        f"cam_data.lens = {cam_data.lens:.1f}",
        f"# rotation in degrees: "
        f"({math.degrees(rot.x):.1f}, {math.degrees(rot.y):.1f}, "
        f"{math.degrees(rot.z):.1f})",
    ]
    text = "\n".join(lines)
    print(text)

    # Also stash it in a text block (handy on macOS without a terminal).
    if "CameraParams" not in bpy.data.texts:
        bpy.data.texts.new("CameraParams")
    txt = bpy.data.texts["CameraParams"]
    txt.clear()
    txt.write(text + "\n")
