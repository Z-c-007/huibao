import bpy
c = bpy.data.objects["CAM_Hero"]
print("CAM", [round(v,2) for v in c.location], c.data.lens)
print("SUN", bpy.data.lights["LGT_Sun_Key"].energy, [round(v,3) for v in bpy.data.objects["LGT_Sun_Key"].rotation_euler])
print("CON", bpy.data.materials["MAT_Concrete"].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value[:3])
print("TREES", len(bpy.data.objects["SM_Forest"].data.vertices))
print("EXPO", bpy.context.scene.view_settings.exposure)
