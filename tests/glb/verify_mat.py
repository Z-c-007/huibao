import json, struct
p = r"D:\GIS_learn\tests\glb\dam_arch.glb"
data = open(p, 'rb').read()
clen, ctype = struct.unpack_from('<II', data, 12)
g = json.loads(data[20:20+clen].decode('utf-8'))
for m in g["materials"]:
    pbr = m.get("pbrMetallicRoughness", {})
    print(m.get("name"), pbr.get("baseColorFactor"), "metal", pbr.get("metallicFactor"), "rough", pbr.get("roughnessFactor"))
