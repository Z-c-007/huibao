# -*- coding: utf-8 -*-
import bpy
import os

OUT = r"D:\GIS_learn\tests\glb"
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 16
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.04
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 4
scene.cycles.diffuse_bounces = 2
scene.cycles.glossy_bounces = 2
scene.cycles.transmission_bounces = 2
scene.render.resolution_x = 960
scene.render.resolution_y = 540
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
try:
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = 0.0
except Exception:
    pass

views = [("CAM_Hero", "dam_hero.png"),
         ("CAM_Detail", "dam_detail.png"),
         ("CAM_Aerial", "dam_aerial.png"),
         ("CAM_Power", "dam_power.png")]
for cam_name, fname in views:
    cam = bpy.data.objects.get(cam_name)
    if cam is None:
        continue
    scene.camera = cam
    print("RENDERING", cam_name, [round(v, 1) for v in cam.location], cam.data.lens)
    scene.render.filepath = os.path.join(OUT, fname)
    bpy.ops.render.render(write_still=True)
    print("RENDER_DONE", scene.render.filepath)
