import bpy, time
s = bpy.context.scene
s.render.resolution_x = 320
s.render.resolution_y = 180
s.eevee.taa_render_samples = 1
s.eevee.use_raytracing = False
s.eevee.use_fast_gi = False
s.eevee.use_shadows = False
s.render.filepath = r"D:\GIS_learn\tests\glb\test_small.png"
t=time.time()
bpy.ops.render.render(write_still=True)
print("SMALL_DONE", round(time.time()-t,1))
