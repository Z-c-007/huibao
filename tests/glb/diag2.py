import bpy
for ob in bpy.data.objects:
    if ob.type == "MESH":
        me = ob.data
        print("OBJ", ob.name, len(me.vertices), len(me.polygons))
    elif ob.type in {"CAMERA","LIGHT"}:
        print("RIG", ob.name, ob.type)
