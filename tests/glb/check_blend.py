import bpy
sc = bpy.context.scene
print("BLEND_SCENE", sc.name, len(sc.objects), [o.name for o in sc.objects if o.type == 'CAMERA'])
cam = bpy.data.objects.get("CAM_Power")
print("CAM_POWER", tuple(round(v,1) for v in cam.location), cam.data.lens)
m = bpy.data.materials["MAT_Concrete"]
print("MAT_LINKED", m.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].is_linked)
