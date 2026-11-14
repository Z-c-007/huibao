# -*- coding: utf-8 -*-
"""Lookdev pass: world gradient, lighting balance, shading detail, cameras."""
import bpy
import math
import os

OUT = r"D:\GIS_learn\tests\glb"
scene = bpy.context.scene

# ---------------------------------------------------------------- world
world = scene.world
nt = world.node_tree
for n in list(nt.nodes):
    if n.type != 'OUTPUT_WORLD':
        nt.nodes.remove(n)
out = next(n for n in nt.nodes if n.type == 'OUTPUT_WORLD')
bg = nt.nodes.new("ShaderNodeBackground")
tc = nt.nodes.new("ShaderNodeTexCoord")
mr = nt.nodes.new("ShaderNodeMapRange")
mr.inputs["From Min"].default_value = -0.05
mr.inputs["From Max"].default_value = 0.85
mr.inputs["To Min"].default_value = 0.0
mr.inputs["To Max"].default_value = 1.0
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
ramp = nt.nodes.new("ShaderNodeValToRGB")
cr = ramp.color_ramp
cr.elements[0].position = 0.0
cr.elements[0].color = (0.42, 0.47, 0.52, 1.0)
cr.elements[1].position = 0.55
cr.elements[1].color = (0.13, 0.24, 0.42, 1.0)
e = cr.elements.new(1.0)
e.color = (0.045, 0.10, 0.22, 1.0)
nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 0.32
nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

# ---------------------------------------------------------------- lights
key = bpy.data.lights.get("LGT_Sun_Key")
key.energy = 2.6
key.color = (1.0, 0.94, 0.85)
key.angle = math.radians(1.6)
fill = bpy.data.lights.get("LGT_Sun_Fill")
fill.energy = 0.55
fill.color = (0.58, 0.72, 1.0)

scene.view_settings.exposure = 0.0

# ---------------------------------------------------------------- joint lines
def add_bands(mat, scale, axis="Z", amount=0.35, lo=0.015, hi=0.075, distort=1.6):
    mnt = mat.node_tree
    bsdf = mnt.nodes.get("Principled BSDF")
    if bsdf is None or not bsdf.inputs["Base Color"].is_linked:
        return
    src_sock = bsdf.inputs["Base Color"].links[0].from_socket
    mnt.links.remove(bsdf.inputs["Base Color"].links[0])
    wave = mnt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = 'BANDS'
    wave.bands_direction = axis
    wave.inputs["Scale"].default_value = scale
    wave.inputs["Distortion"].default_value = distort
    wave.inputs["Detail"].default_value = 2.0
    wave.inputs["Detail Scale"].default_value = 1.5
    rmp = mnt.nodes.new("ShaderNodeValToRGB")
    rmp.color_ramp.elements[0].position = lo
    rmp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    rmp.color_ramp.elements[1].position = hi
    rmp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    mnt.links.new(wave.outputs["Fac"], rmp.inputs["Fac"])
    mix = mnt.nodes.new("ShaderNodeMixRGB")
    mix.blend_type = 'MULTIPLY'
    mix.inputs["Fac"].default_value = amount
    mnt.links.new(src_sock, mix.inputs["Color1"])
    mnt.links.new(rmp.outputs["Color"], mix.inputs["Color2"])
    mnt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])


con = bpy.data.materials.get("MAT_Concrete")
if con:
    bsdf = con.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.50, 0.485, 0.455, 1.0)
    add_bands(con, 44.0, "X", 0.30, 0.01, 0.055, 1.2)
    add_bands(con, 26.0, "Z", 0.22, 0.01, 0.05, 1.0)

rock = bpy.data.materials.get("MAT_Rock")
if rock:
    bsdf = rock.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.225, 0.20, 0.17, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.96
    add_bands(rock, 16.0, "Z", 0.35, 0.0, 0.16, 3.0)

weathered = bpy.data.materials.get("MAT_Concrete_Weathered")
if weathered:
    weathered.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.33, 0.315, 0.29, 1.0)

# ---------------------------------------------------------------- cameras
hero = bpy.data.objects.get("CAM_Hero")
hero.location = (10.0, 735.0, 300.0)
hero.data.lens = 52.0
from mathutils import Vector
d = Vector((0.0, 30.0, 88.0)) - hero.location
hero.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

aerial = bpy.data.objects.get("CAM_Aerial")
aerial.location = (430.0, 790.0, 540.0)
aerial.data.lens = 38.0
d2 = Vector((0.0, 10.0, 60.0)) - aerial.location
aerial.rotation_euler = d2.to_track_quat('-Z', 'Y').to_euler()

# ---------------------------------------------------------------- render
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 960
scene.render.resolution_y = 540
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
try:
    scene.eevee.taa_render_samples = 32
except Exception:
    pass
try:
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    pass

for cam_name, fname in (("CAM_Hero", "look_hero.png"), ("CAM_Aerial", "look_aerial.png")):
    scene.camera = bpy.data.objects[cam_name]
    scene.render.filepath = os.path.join(OUT, fname)
    bpy.ops.render.render(write_still=True)
    print("RENDER_DONE", fname)
