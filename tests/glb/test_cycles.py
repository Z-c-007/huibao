import bpy, time
s = bpy.context.scene
s.render.engine = 'CYCLES'
s.cycles.device = 'CPU'
s.cycles.samples = 16
s.cycles.use_denoising = True
s.render.resolution_x = 640
s.render.resolution_y = 360
s.render.filepath = r"D:\GIS_learn\tests\glb\test_cycles.png"
t=time.time()
bpy.ops.render.render(write_still=True)
print("CYCLES_DONE", round(time.time()-t,1))
