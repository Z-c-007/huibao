import bpy
e = bpy.context.scene.eevee
names = [p for p in dir(e) if not p.startswith("_")]
print("EEVEE_PROPS", [n for n in names if any(k in n.lower() for k in ("ray","gtao","ao","shadow","sample","volum","fast_gi"))])
