import bpy, time
s = bpy.context.scene
s.render.engine = 'BLENDER_EEVEE'
s.render.resolution_x = 320
s.render.resolution_y = 180
s.eevee.taa_render_samples = 1
s.render.filepath = r"D:\GIS_learn\tests\glb\test_eevee_cube.png"
t = time.time()
bpy.ops.render.render(write_still=True)
print("EEVEE_CUBE_DONE", round(time.time()-t,1))
