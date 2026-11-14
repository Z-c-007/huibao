import bpy
for m in bpy.data.materials:
    if not m.use_nodes: continue
    b = m.node_tree.nodes.get("Principled BSDF")
    if not b: continue
    bc = b.inputs["Base Color"].default_value[:3]
    linked = b.inputs["Base Color"].is_linked
    print("MAT", m.name, "base", [round(v,3) for v in bc], "linked", linked,
          "rough", round(b.inputs["Roughness"].default_value,3))
s = bpy.context.scene
print("EXPOSURE", s.view_settings.exposure, s.view_settings.view_transform, s.view_settings.look)
print("SUN", bpy.data.lights["LGT_Sun_Key"].energy, "WORLD", s.world.node_tree.nodes["Background"].inputs["Strength"].default_value)
print("ENGINE", s.render.engine)
