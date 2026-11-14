import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"D:\GIS_learn\tests\glb\dam_arch.glb")
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
dg = bpy.context.evaluated_depsgraph_get()
tris = 0
for o in objs:
    me = o.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    tris += len(me.loop_triangles)
    o.evaluated_get(dg).to_mesh_clear()
print("IMPORT_CHECK objects", len(objs), "tris", tris, "materials", len(bpy.data.materials))
