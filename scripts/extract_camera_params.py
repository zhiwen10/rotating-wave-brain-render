"""
Camera parameter extractor — run INSIDE Blender (Scripting tab → Run Script).

Two modes:
  MODE = 'scene'    (default)
      Reads the active SCENE CAMERA set by the render scripts.
      Use after running 03_render_blender.py (or any 03_*.py) to confirm the
      current render angle, then navigate to a new angle in the viewport,
      snap the camera (Ctrl+Alt+Numpad 0), and run again.

  MODE = 'viewport'
      Reads the 3D VIEWPORT navigation directly — no scene camera required.
      Navigate the viewport to any angle, run this script, and you get values
      you can paste straight into a render script.

Workflow (recommended):
    1. In the 3D viewport, navigate to the angle you want.
    2. For 'scene' mode: press Ctrl+Alt+Numpad 0 to snap the scene camera
       to the viewport, then run with MODE = 'scene'.
       For 'viewport' mode: just run with MODE = 'viewport'.
    3. Paste the printed cam_obj.location / cam_obj.rotation_euler lines into
       the camera section of 03_render_blender.py (or 03b/03c variants).

On macOS, print() output only appears if Blender was launched from Terminal:
    /Applications/Blender.app/Contents/MacOS/Blender
Output is also written to a "CameraParams" text block accessible in the
Blender Text Editor (top menu → Text → Open / switch to CameraParams).
"""

import bpy
import math

# ---- EDIT THIS ----
MODE = 'scene'    # 'scene'  or  'viewport'
# -------------------

lines = []

if MODE == 'scene':
    cam_obj = bpy.context.scene.camera
    if cam_obj is None:
        print("No active scene camera. Run a render script first, or switch to MODE='viewport'.")
    else:
        cam_data = cam_obj.data
        loc = cam_obj.location
        rot = cam_obj.rotation_euler
        lines = [
            "# --- Paste into cam section of 03_render_blender.py ---",
            f"cam_obj.location = ({loc.x:.4f}, {loc.y:.4f}, {loc.z:.4f})",
            f"cam_obj.rotation_euler = ({rot.x:.4f}, {rot.y:.4f}, {rot.z:.4f})",
            f"cam_data.type = '{cam_data.type}'",
            f"cam_data.lens = {cam_data.lens:.1f}",
            f"# rotation in degrees: ({math.degrees(rot.x):.1f}, "
            f"{math.degrees(rot.y):.1f}, {math.degrees(rot.z):.1f})",
        ]

elif MODE == 'viewport':
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            r3d      = area.spaces[0].region_3d
            view_mat = r3d.view_matrix.inverted()
            loc      = view_mat.translation
            rot      = view_mat.to_euler()
            lines = [
                "# --- Paste into cam section of 03_render_blender.py ---",
                f"cam_obj.location = ({loc.x:.4f}, {loc.y:.4f}, {loc.z:.4f})",
                f"cam_obj.rotation_euler = ({rot.x:.4f}, {rot.y:.4f}, {rot.z:.4f})",
                f"# rotation in degrees: ({math.degrees(rot.x):.1f}, "
                f"{math.degrees(rot.y):.1f}, {math.degrees(rot.z):.1f})",
                f"# view distance: {r3d.view_distance:.4f}",
                f"# perspective: {r3d.view_perspective}",
            ]
            # Show Blender popup so you know it ran
            def show_popup(self, context):
                self.layout.label(text="Camera params saved to CameraParams text block.")
            bpy.context.window_manager.popup_menu(
                show_popup, title="Camera Params Exported", icon='CHECKMARK')
            break
    else:
        print("No 3D viewport found — open a 3D View area and try again.")

if lines:
    text = "\n".join(lines)
    print(text)
    if "CameraParams" not in bpy.data.texts:
        bpy.data.texts.new("CameraParams")
    txt = bpy.data.texts["CameraParams"]
    txt.clear()
    txt.write(text + "\n")
