import bpy
import numpy as np
import os
import mathutils
import math

# ============================================================================
# DENSITY SCATTER RENDER
# ============================================================================
# Renders the iridescent-metallic brain with detected spiral events overlaid
# as 3D scatter spheres colored by a 'hot' colormap (black→red→yellow→white).
#
# Input:  unique_spirals.npy  — shape (N, 3): [AP_um, ML_um, density_count]
# Output: render_density_scatter.png
#
# Run inside Blender (Scripting tab → Run Script, or Alt+P).
# Requires root.obj and unique_spirals.npy in data_dir.
# ============================================================================

# --- Data directory (EDIT THIS) ---
data_dir = "."

SPIRALS_FILE = "unique_spirals.npy"   # (N, 3): [AP_um, ML_um, density]

# ============================================================================
# PARAMETERS
# ============================================================================

# -- BRAIN (iridescent metallic) --
BRAIN_ALPHA      = 0.30
BRAIN_ROUGHNESS  = 0.20
BRAIN_IOR        = 2.5
BRAIN_METALLIC   = 0.65
IRID_COLOR_WARM  = (0.85, 0.65, 0.90, 1)
IRID_COLOR_COOL  = (0.55, 0.70, 0.95, 1)
IRID_BLEND       = 0.5

# -- SCATTER SPHERES --
N_COLOR_BINS       = 64       # number of quantized color levels
SCATTER_RADIUS     = 0.03     # sphere radius in Blender units (after 0.001 scale)
SCATTER_EMISSION   = 2.0      # emission strength for glow
SCATTER_ROUGHNESS  = 0.4
SCATTER_SUBDIVISIONS = 2      # icosphere subdivisions (2 = smooth, fast)
SCATTER_Z_OFFSET   = 0.0      # dorsal offset if points need lifting off surface

# -- OUTLINE --
HULL_THICKNESS_BRAIN = 80
HULL_MASK_START_Z    = 0.0
HULL_MASK_END_Z      = 2.0
ENABLE_BRAIN_OUTLINE = True

# -- LIGHTING (dramatic directional) --
OVERHEAD_ENERGY         = 250
OVERHEAD_LOCATION       = (0, 0, -15)
OVERHEAD_SIZE           = 8.0
OVERHEAD_COLOR          = (1.0, 0.98, 0.95)

ACCENT1_ENERGY          = 100
ACCENT1_LOCATION        = (-4, 3, -8)
ACCENT1_SIZE            = 6.0
ACCENT1_COLOR           = (1.0, 0.90, 0.85)

ACCENT2_ENERGY          = 100
ACCENT2_LOCATION        = (-4, -3, -8)
ACCENT2_SIZE            = 6.0
ACCENT2_COLOR           = (0.85, 0.88, 1.0)

RIM_ENERGY              = 80
RIM_LOCATION            = (-6, -4, -2)
RIM_SIZE                = 3.0
RIM_COLOR               = (1.0, 0.95, 0.90)

RIM_LEFT_ENERGY         = 80
RIM_LEFT_LOCATION       = (6, -4, -2)
RIM_LEFT_SIZE           = 3.0
RIM_LEFT_COLOR          = (0.90, 0.95, 1.0)

RIM_BACK_LEFT_ENERGY    = 60
RIM_BACK_LEFT_LOCATION  = (6, 4, -2)
RIM_BACK_LEFT_SIZE      = 5.0
RIM_BACK_LEFT_COLOR     = (0.88, 0.85, 1.0)

RIM_BACK_RIGHT_ENERGY   = 60
RIM_BACK_RIGHT_LOCATION = (-6, 4, -2)
RIM_BACK_RIGHT_SIZE     = 5.0
RIM_BACK_RIGHT_COLOR    = (1.0, 0.88, 0.85)

RIM_BACK_CENTER_ENERGY   = 120
RIM_BACK_CENTER_LOCATION = (8, 0, -4)
RIM_BACK_CENTER_SIZE     = 8.0
RIM_BACK_CENTER_COLOR    = (0.95, 0.93, 1.0)

# -- CAMERA --
CAM_TYPE         = 'PERSP'
CAM_FOCAL_LENGTH = 28

# -- RENDER --
RENDER_ENGINE    = 'BLENDER_EEVEE'
TRANSPARENT_BG   = True
RENDER_SAMPLES   = 64
RESOLUTION_X     = 1500
RESOLUTION_Y     = 1800
WORLD_STRENGTH   = 0.25
WORLD_COLOR      = (0.015, 0.01, 0.025)

SAVE_RENDER   = True
RENDER_OUTPUT = os.path.join(data_dir, "render_density_scatter.png")

# ============================================================================
# HELPERS
# ============================================================================

def safe_set_input(node, names, value):
    if isinstance(names, str):
        names = [names]
    for name in names:
        if name in node.inputs:
            node.inputs[name].default_value = value
            return

def hot_colormap(t):
    """Piecewise approximation of matplotlib's 'hot' colormap."""
    t = max(0.0, min(1.0, t))
    if t < 1 / 3:
        return (t * 3.0, 0.0, 0.0)
    elif t < 2 / 3:
        return (1.0, (t - 1 / 3) * 3.0, 0.0)
    else:
        return (1.0, 1.0, (t - 2 / 3) * 3.0)

def create_hull_material(name, z_start, z_end):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = True
    mat.show_transparent_back = False
    if hasattr(mat, 'blend_method'):
        mat.blend_method = 'BLEND'
    if hasattr(mat, 'shadow_method'):
        mat.shadow_method = 'NONE'
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out         = nodes.new('ShaderNodeOutputMaterial')
    mix         = nodes.new('ShaderNodeMixShader')
    emission    = nodes.new('ShaderNodeEmission')
    transparent = nodes.new('ShaderNodeBsdfTransparent')
    emission.inputs['Color'].default_value = (0, 0, 0, 1)
    sep        = nodes.new('ShaderNodeSeparateXYZ')
    geom       = nodes.new('ShaderNodeNewGeometry')
    map_range  = nodes.new('ShaderNodeMapRange')
    links.new(geom.outputs['Position'],    sep.inputs['Vector'])
    map_range.inputs['From Min'].default_value = z_start
    map_range.inputs['From Max'].default_value = z_end
    map_range.inputs['To Min'].default_value   = 0.0
    map_range.inputs['To Max'].default_value   = 1.0
    map_range.clamp = True
    links.new(sep.outputs['Z'],             map_range.inputs['Value'])
    links.new(map_range.outputs['Result'],  mix.inputs['Fac'])
    links.new(emission.outputs['Emission'], mix.inputs[1])
    links.new(transparent.outputs['BSDF'], mix.inputs[2])
    links.new(mix.outputs['Shader'],        out.inputs['Surface'])
    return mat

def add_hull_modifier(obj, material_index, thickness):
    mod = obj.modifiers.new(name="Outline_Hull", type='SOLIDIFY')
    mod.thickness         = thickness
    mod.offset            = 1.0
    mod.use_flip_normals  = True
    mod.material_offset   = material_index
    mod.use_rim           = False
    mod.use_even_offset   = True
    mod.use_quality_normals = True
    mod.shell_vertex_group  = ""

def create_scatter_material(name, rgb, emission_strength):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out        = nodes.new('ShaderNodeOutputMaterial')
    emission   = nodes.new('ShaderNodeEmission')
    bsdf       = nodes.new('ShaderNodeBsdfPrincipled')
    mix_shader = nodes.new('ShaderNodeMixShader')
    emission.inputs['Color'].default_value    = (*rgb, 1.0)
    emission.inputs['Strength'].default_value = emission_strength
    bsdf.inputs['Base Color'].default_value   = (*rgb, 1.0)
    safe_set_input(bsdf, 'Roughness',  SCATTER_ROUGHNESS)
    safe_set_input(bsdf, ['Metallic'], 0.3)
    mix_shader.inputs['Fac'].default_value = 0.7
    links.new(bsdf.outputs['BSDF'],         mix_shader.inputs[1])
    links.new(emission.outputs['Emission'], mix_shader.inputs[2])
    links.new(mix_shader.outputs['Shader'], out.inputs['Surface'])
    return mat

def add_light(name, energy, loc, size, color, shadows=True):
    data = bpy.data.lights.new(name=name, type='AREA')
    data.energy = energy
    data.color  = color
    data.size   = size
    if not shadows:
        data.use_shadow = False
    obj = bpy.data.objects.new(name, data)
    lights_coll.objects.link(obj)
    obj.location = loc
    con = obj.constraints.new(type='TRACK_TO')
    con.target     = brain_pivot
    con.track_axis = 'TRACK_NEGATIVE_Z'
    con.up_axis    = 'UP_Y'
    return obj

# ============================================================================
# 1. CLEANUP
# ============================================================================
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for block in [bpy.data.meshes, bpy.data.materials, bpy.data.lights,
              bpy.data.cameras, bpy.data.collections, bpy.data.linestyles]:
    for item in block:
        try: block.remove(item)
        except: pass

# ============================================================================
# 2. COLLECTIONS
# ============================================================================
main_coll    = bpy.context.scene.collection
brain_coll   = bpy.data.collections.new("Brain_Collection")
scatter_coll = bpy.data.collections.new("Scatter_Collection")
lights_coll  = bpy.data.collections.new("Lights_Collection")
main_coll.children.link(brain_coll)
main_coll.children.link(scatter_coll)
main_coll.children.link(lights_coll)

brain_pivot = bpy.data.objects.new("Brain_Pivot", None)
main_coll.objects.link(brain_pivot)
brain_pivot.location = (0, 0, 0)

# ============================================================================
# 3. IMPORT BRAIN MESH
# ============================================================================
imported_objects = {}
full_path = os.path.join(data_dir, "root.obj")
if not os.path.exists(full_path):
    print(f"WARNING: {full_path} not found.")
else:
    bpy.ops.wm.obj_import(filepath=full_path)
    for obj in bpy.context.selected_objects:
        obj.name = "Brain"
        for coll in obj.users_collection:
            coll.objects.unlink(obj)
        brain_coll.objects.link(obj)
        obj.scale  = (0.001, 0.001, 0.001)
        obj.parent = brain_pivot
        bpy.ops.object.shade_smooth()
        weld = obj.modifiers.new(name="Weld_Geometry", type='WELD')
        weld.merge_threshold = 0.01
        if hasattr(obj.data, 'use_auto_smooth'):
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = math.radians(60)
        else:
            try:
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.modifier_add(type='SMOOTH_BY_ANGLE')
            except: pass
        imported_objects["Brain"] = obj

# ============================================================================
# 4. BRAIN MATERIAL (iridescent metallic)
# ============================================================================
hull_mat = create_hull_material("Hull_Ink",
                                z_start=HULL_MASK_START_Z,
                                z_end=HULL_MASK_END_Z)

if "Brain" in imported_objects:
    obj = imported_objects["Brain"]
    mat = bpy.data.materials.new("BrainMat_Iridescent")
    mat.use_nodes = True
    mat.use_backface_culling = False
    if hasattr(mat, 'blend_method'):
        mat.blend_method = 'BLEND'
    if hasattr(mat, 'shadow_method'):
        mat.shadow_method = 'NONE'
    mat.show_transparent_back = False
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out          = nodes.new('ShaderNodeOutputMaterial')
    bsdf         = nodes.new('ShaderNodeBsdfPrincipled')
    layer_weight = nodes.new('ShaderNodeLayerWeight')
    color_mix    = nodes.new('ShaderNodeMixRGB')
    fresnel2     = nodes.new('ShaderNodeFresnel')
    mix_final    = nodes.new('ShaderNodeMixShader')
    transparent  = nodes.new('ShaderNodeBsdfTransparent')

    layer_weight.inputs['Blend'].default_value = IRID_BLEND
    color_mix.blend_type                        = 'MIX'
    color_mix.inputs[1].default_value           = IRID_COLOR_COOL
    color_mix.inputs[2].default_value           = IRID_COLOR_WARM
    fresnel2.inputs['IOR'].default_value        = 1.8
    transparent.inputs['Color'].default_value   = (0.85, 0.88, 0.95, 1)
    mix_final.inputs['Fac'].default_value       = 0.35

    links.new(layer_weight.outputs['Fresnel'], color_mix.inputs['Fac'])
    links.new(color_mix.outputs['Color'],      bsdf.inputs['Base Color'])
    safe_set_input(bsdf, ['Metallic'],  BRAIN_METALLIC)
    safe_set_input(bsdf, 'Roughness',   BRAIN_ROUGHNESS)
    safe_set_input(bsdf, 'IOR',         BRAIN_IOR)
    safe_set_input(bsdf, 'Alpha',       BRAIN_ALPHA)
    links.new(transparent.outputs['BSDF'], mix_final.inputs[1])
    links.new(bsdf.outputs['BSDF'],        mix_final.inputs[2])
    links.new(mix_final.outputs['Shader'], out.inputs['Surface'])

    obj.data.materials.append(mat)
    if ENABLE_BRAIN_OUTLINE:
        obj.data.materials.append(hull_mat)
        add_hull_modifier(obj, 1, HULL_THICKNESS_BRAIN)

# ============================================================================
# 5. DENSITY SCATTER POINTS
# ============================================================================
spirals_path = os.path.join(data_dir, SPIRALS_FILE)
if not os.path.exists(spirals_path):
    print(f"WARNING: {spirals_path} not found — no scatter points created.")
else:
    data = np.load(spirals_path)  # (N, 3): [AP_um, ML_um, density]
    xs        = data[:, 0]
    ys        = data[:, 1]
    densities = data[:, 2]

    d_min, d_max = densities.min(), densities.max()
    densities_norm = (densities - d_min) / (d_max - d_min + 1e-12)

    n_points = len(xs)
    print(f"Placing {n_points} scatter points in {N_COLOR_BINS} color bins …")

    # Pre-build color-bin materials
    scatter_materials = [
        create_scatter_material(
            f"ScatterMat_{i:03d}",
            hot_colormap(i / (N_COLOR_BINS - 1)),
            SCATTER_EMISSION,
        )
        for i in range(N_COLOR_BINS)
    ]

    # Template icosphere (hidden)
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=SCATTER_SUBDIVISIONS,
        radius=SCATTER_RADIUS,
        location=(0, 0, 0),
    )
    template_sphere       = bpy.context.active_object
    template_sphere.name  = "ScatterTemplate"
    template_mesh         = template_sphere.data
    template_sphere.hide_render   = True
    template_sphere.hide_viewport = True

    template_verts    = np.array([v.co for v in template_mesh.vertices])
    template_faces    = np.array([list(p.vertices) for p in template_mesh.polygons])
    n_template_verts  = len(template_verts)

    bin_indices = np.clip(
        (densities_norm * (N_COLOR_BINS - 1)).astype(int), 0, N_COLOR_BINS - 1
    )

    for bin_idx in range(N_COLOR_BINS):
        mask = bin_indices == bin_idx
        if not np.any(mask):
            continue
        bin_xs = xs[mask]
        bin_ys = ys[mask]
        n_bin  = len(bin_xs)

        all_verts  = []
        all_faces  = []
        vert_offset = 0
        for j in range(n_bin):
            # Scale from Allen CCF μm to Blender units: brain uses 0.001 scale
            px = bin_xs[j] * 0.001
            py = bin_ys[j] * 0.001
            pz = SCATTER_Z_OFFSET
            all_verts.append(template_verts + np.array([px, py, pz]))
            all_faces.append(template_faces + vert_offset)
            vert_offset += n_template_verts

        all_verts = np.vstack(all_verts)
        all_faces = np.vstack(all_faces)

        mesh_data = bpy.data.meshes.new(f"ScatterMesh_{bin_idx:03d}")
        mesh_data.from_pydata(all_verts.tolist(), [], all_faces.tolist())
        mesh_data.update()

        sobj = bpy.data.objects.new(f"ScatterBin_{bin_idx:03d}", mesh_data)
        scatter_coll.objects.link(sobj)
        sobj.parent = brain_pivot
        sobj.data.materials.append(scatter_materials[bin_idx])

    bpy.data.objects.remove(template_sphere, do_unlink=True)
    bpy.data.meshes.remove(template_mesh,    do_unlink=True)
    print(f"Scatter complete: {n_points} points.")

# ============================================================================
# 6. CENTERING
# ============================================================================
if "Brain" in imported_objects:
    brain_obj  = imported_objects["Brain"]
    depsgraph  = bpy.context.evaluated_depsgraph_get()
    brain_eval = brain_obj.evaluated_get(depsgraph)
    bbox_corners = [brain_obj.matrix_world @ mathutils.Vector(c)
                    for c in brain_eval.bound_box]
    bbox_center = sum(bbox_corners, mathutils.Vector((0, 0, 0))) / 8
    for child in brain_pivot.children:
        child.location = child.location - bbox_center

# ============================================================================
# 7. WORLD & LIGHTING
# ============================================================================
bpy.context.view_layer.use_freestyle = False

world = bpy.context.scene.world
if not world:
    world = bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes['Background']
bg.inputs['Color'].default_value    = (*WORLD_COLOR, 1)
bg.inputs['Strength'].default_value = WORLD_STRENGTH

add_light("Overhead",     OVERHEAD_ENERGY,       OVERHEAD_LOCATION,       OVERHEAD_SIZE,       OVERHEAD_COLOR,       shadows=True)
add_light("Accent_Left",  ACCENT1_ENERGY,        ACCENT1_LOCATION,        ACCENT1_SIZE,        ACCENT1_COLOR,        shadows=False)
add_light("Accent_Right", ACCENT2_ENERGY,        ACCENT2_LOCATION,        ACCENT2_SIZE,        ACCENT2_COLOR,        shadows=False)
add_light("Rim_Front_R",  RIM_ENERGY,            RIM_LOCATION,            RIM_SIZE,            RIM_COLOR,            shadows=False)
add_light("Rim_Front_L",  RIM_LEFT_ENERGY,       RIM_LEFT_LOCATION,       RIM_LEFT_SIZE,       RIM_LEFT_COLOR,       shadows=False)
add_light("Rim_Back_L",   RIM_BACK_LEFT_ENERGY,  RIM_BACK_LEFT_LOCATION,  RIM_BACK_LEFT_SIZE,  RIM_BACK_LEFT_COLOR,  shadows=False)
add_light("Rim_Back_R",   RIM_BACK_RIGHT_ENERGY, RIM_BACK_RIGHT_LOCATION, RIM_BACK_RIGHT_SIZE, RIM_BACK_RIGHT_COLOR, shadows=False)
add_light("Rim_Back_C",   RIM_BACK_CENTER_ENERGY,RIM_BACK_CENTER_LOCATION,RIM_BACK_CENTER_SIZE,RIM_BACK_CENTER_COLOR,shadows=False)

# ============================================================================
# 8. RENDER & CAMERA
# ============================================================================
scene = bpy.context.scene
scene.render.engine           = RENDER_ENGINE
scene.render.resolution_x     = RESOLUTION_X
scene.render.resolution_y     = RESOLUTION_Y
scene.render.film_transparent = TRANSPARENT_BG

if RENDER_ENGINE == 'BLENDER_EEVEE':
    if hasattr(scene.eevee, 'taa_render_samples'):
        scene.eevee.taa_render_samples = RENDER_SAMPLES
    if hasattr(scene.eevee, 'use_bloom'):
        scene.eevee.use_bloom = True
        scene.eevee.bloom_threshold = 0.7
        scene.eevee.bloom_intensity = 0.15
    if hasattr(scene.eevee, 'use_ssr'):
        scene.eevee.use_ssr = True
        scene.eevee.use_ssr_refraction = True

cam_data = bpy.data.cameras.new("Camera")
cam_obj  = bpy.data.objects.new("Camera", cam_data)
main_coll.objects.link(cam_obj)
scene.camera = cam_obj

# Saved angled view from the journal-cover render.
# Use extract_camera_params.py to capture a new viewport angle.
cam_obj.location       = (2.4583, -4.8708, -15.1973)
cam_obj.rotation_euler = (0.3491, 3.1416, 0.5515)
cam_data.type          = CAM_TYPE
cam_data.lens          = CAM_FOCAL_LENGTH

print("Density scatter scene ready.")

if SAVE_RENDER:
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_depth = '16'
    scene.render.filepath = RENDER_OUTPUT
    bpy.ops.render.render(write_still=True)
    print(f"Saved: {RENDER_OUTPUT}")
