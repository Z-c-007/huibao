import json, struct, os
p = r"D:\GIS_learn\tests\glb\dam_arch.glb"
data = open(p, 'rb').read()
magic, ver, total = struct.unpack_from('<4sII', data, 0)
clen, ctype = struct.unpack_from('<II', data, 12)
gltf = json.loads(data[20:20+clen].decode('utf-8'))
print("GLB", magic, "v", ver, "bytes", total, "file", len(data))
print("MESHES", len(gltf.get("meshes", [])), "NODES", len(gltf.get("nodes", [])),
      "MATERIALS", len(gltf.get("materials", [])), "IMAGES", len(gltf.get("images", [])))
tris = 0
for m in gltf.get("meshes", []):
    for pr in m.get("primitives", []):
        if "indices" in pr:
            tris += gltf["accessors"][pr["indices"]]["count"] // 3
print("GLB_TRIS", tris)
mn = [1e9]*3; mx = [-1e9]*3
for a in gltf.get("accessors", []):
    if a.get("type") == "VEC3" and "min" in a and len(a["min"]) == 3 and a.get("componentType") == 5126:
        for i in range(3):
            mn[i] = min(mn[i], a["min"][i]); mx[i] = max(mx[i], a["max"][i])
print("GLB_BOUNDS", [round(v,1) for v in mn], [round(v,1) for v in mx])
print("SIZES", os.path.getsize(p), os.path.getsize(r"D:\GIS_learn\tests\glb\dam_arch.blend"))
