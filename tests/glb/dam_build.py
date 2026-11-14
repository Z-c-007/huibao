# -*- coding: utf-8 -*-
"""
High-detail concrete arch-gravity dam, built procedurally in Blender 5.1.
Scene units: meters. Crest +180 m, foundation to -25 m, crest length ~380 m.
Run: blender --background --factory-startup --python dam_build.py
"""
import bpy
import bmesh
import math
import random
import os

from mathutils import Vector

OUT_DIR = r"D:\GIS_learn\tests\glb"
BLEND_PATH = os.path.join(OUT_DIR, "dam_arch.blend")
GLB_PATH = os.path.join(OUT_DIR, "dam_arch.glb")

# ----------------------------------------------------------------------------
# Scene reset
# ----------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = "DamScene"
scene.unit_settings.system = 'METRIC'
scene.unit_settings.length_unit = 'METERS'

# ----------------------------------------------------------------------------
# Global design constants
# ----------------------------------------------------------------------------
CREST_Z = 180.0
SILL_Z = 168.0
RES_Z = 176.0
TAIL_Z = 13.0
ARCH_R = 300.0
ARCH_HALF = math.radians(32.0)
CREST_T = 13.0
SPILL_X0 = 1.0
SPILL_X1 = 86.0
NOTCH_IN0, NOTCH_IN1 = 9.0, 78.0
DAM_HALF_X = ARCH_R * math.sin(ARCH_HALF)

RNG = random.Random(20261107)


# ----------------------------------------------------------------------------
# Math helpers
# ----------------------------------------------------------------------------
def clamp(v, a, b):
    return a if v < a else (b if v > b else v)


def smoothstep(e0, e1, x):
    t = clamp((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def _hash2(i, j, seed):
    n = (i * 374761393 + j * 668265263 + seed * 1442695040888963407) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFFFF) / float(0xFFFFFF)


def vnoise(x, y, seed=0):
    i, j = math.floor(x), math.floor(y)
    fx, fy = x - i, y - j
    u = fx * fx * (3.0 - 2.0 * fx)
    v = fy * fy * (3.0 - 2.0 * fy)
    a = _hash2(i, j, seed)
    b = _hash2(i + 1, j, seed)
    c = _hash2(i, j + 1, seed)
    d = _hash2(i + 1, j + 1, seed)
    return lerp(lerp(a, b, u), lerp(c, d, u), v)


def fbm(x, y, octaves=4, seed=0):
    s = 0.0
    amp = 0.5
    f = 1.0
    for k in range(octaves):
        s += amp * vnoise(x * f, y * f, seed + k)
        amp *= 0.5
        f *= 2.0
    return s


# ----------------------------------------------------------------------------
# Dam axis helpers
# ----------------------------------------------------------------------------
def arc_xy(t):
    return ARCH_R * math.sin(t), ARCH_R * (1.0 - math.cos(t))


def arc_normal(t):
    return -math.sin(t), math.cos(t)


def t_of_x(x):
    return math.asin(clamp(x / ARCH_R, -0.999999, 0.999999))


def crest_z_at_x(x):
    d = max(SPILL_X0 - x, x - SPILL_X1, 0.0)
    return lerp(SILL_Z, CREST_Z, smoothstep(0.0, 7.0, d))


# ----------------------------------------------------------------------------
# Terrain
# ----------------------------------------------------------------------------
ROAD_A = (DAM_HALF_X + 4.0, 38.0)
ROAD_B = (256.0, 38.0)
POWER_BENCH = (-100.0, -0.0, 52.0, 122.0)


def seg_dist(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    ll = vx * vx + vy * vy
    t = clamp((wx * vx + wy * vy) / ll, 0.0, 1.0)
    dx, dy = px - (ax + vx * t), py - (ay + vy * t)
    return math.hypot(dx, dy)


def terrain_raw(x, y):
    # canyon meanders away from the dam, stays symmetric at the structure
    meander = (52.0 * math.sin(y * 0.0034) + 17.0 * math.sin(y * 0.0092 + 1.1)) \
        * smoothstep(90.0, 330.0, abs(y))
    ax = abs(x - meander)
    wall = smoothstep(34.0, 208.0, ax)
    open_valley = 1.0 - 0.55 * smoothstep(60.0, 300.0, y)
    base = 3.0 + 0.02 * max(y, 0.0) - 11.0 * math.exp(-((x - meander) / 62.0) ** 2)
    z = base + 216.0 * (wall ** 1.30) * open_valley
    z += max(0.0, ax - 208.0) * 0.64
    n1 = fbm(x * 0.0042, y * 0.0042, 4, 11) - 0.5
    n2 = fbm(x * 0.021, y * 0.021, 3, 31) - 0.5
    z += n1 * 96.0 * wall * open_valley
    z += n2 * 15.0 * (0.22 + wall)
    z += abs(fbm(x * 0.010, y * 0.010, 3, 77) - 0.5) * 40.0 * wall
    z += (1.0 - abs(fbm(x * 0.014, y * 0.014, 4, 71) * 2.0 - 1.0)) * 34.0 * wall
    z += (fbm(x * 0.048, y * 0.048, 4, 103) - 0.5) * 26.0 * wall
    z += (fbm(x * 0.092, y * 0.092, 3, 131) - 0.5) * 8.0 * wall
    z += (fbm(x * 0.075, y * 0.075, 3, 151) - 0.5) * 3.4 * wall
    z += 2.6 * math.sin(z * 0.14)
    # upstream headland: closes the reservoir sightline with a rocky spur
    spur = math.exp(-(((y + 430.0) / 165.0) ** 2)) \
        * (1.0 - smoothstep(110.0, 300.0, abs(x - meander)))
    z += 225.0 * spur * (0.72 + 0.55 * fbm(x * 0.018, y * 0.018, 3, 320))
    # distant ridge closing the valley; wavy front makes a scalloped shoreline
    shore_off = 120.0 * fbm(x * 0.0035, 0.0, 3, 240)
    closure = smoothstep(640.0 + shore_off, 940.0 + shore_off, -y)
    if closure > 0.0:
        ridge = (250.0 + 120.0 * fbm(x * 0.0032, y * 0.0032, 3, 211)
                 + 95.0 * (1.0 - abs(fbm(x * 0.011, y * 0.011, 3, 260) * 2.0 - 1.0)))
        z += ridge * closure
    if y < 20.0:
        z = max(z, -26.0)
    return z


def terrain_h(x, y):
    z = terrain_raw(x, y)

    # access road bench cut into the right bank
    d = seg_dist(x, y, ROAD_A[0], ROAD_A[1], ROAD_B[0], ROAD_B[1])
    m = 1.0 - smoothstep(10.0, 26.0, d)
    z = lerp(z, 179.6, m)

    # powerhouse / tailrace bench
    px0, px1, py0, py1 = POWER_BENCH
    dx = max(px0 - x, 0.0, x - px1)
    dy = max(py0 - y, 0.0, y - py1)
    dd = math.hypot(dx, dy)
    m2 = 1.0 - smoothstep(2.0, 20.0, dd)
    z = lerp(z, 5.0, m2)
    return z


# ----------------------------------------------------------------------------
# Mesh helpers
# ----------------------------------------------------------------------------
class MB:
    """Small merged-mesh builder (vertices + faces)."""

    def __init__(self):
        self.v = []
        self.f = []

    def add(self, verts, faces):
        o = len(self.v)
        self.v.extend(verts)
        self.f.extend([[i + o for i in f] for f in faces])

    def box(self, cx, cy, cz, sx, sy, sz, rz=0.0):
        hx, hy, hz = sx * 0.5, sy * 0.5, sz * 0.5
        c, s = math.cos(rz), math.sin(rz)
        local = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
                 (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
        vs = [(cx + p[0] * c - p[1] * s, cy + p[0] * s + p[1] * c, cz + p[2]) for p in local]
        fs = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
        self.add(vs, fs)

    def box_mm(self, x0, x1, y0, y1, z0, z1):
        self.box((x0 + x1) * .5, (y0 + y1) * .5, (z0 + z1) * .5,
                 abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))

    def cyl(self, p0, p1, radius, sides=12, cap=True):
        p0, p1 = Vector(p0), Vector(p1)
        d = (p1 - p0)
        ln = d.length
        if ln < 1e-6:
            return
        d.normalize()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.92 else Vector((1, 0, 0))
        u = d.cross(up)
        u.normalize()
        w = d.cross(u)
        verts = []
        for p, _ in ((p0, 0), (p1, 1)):
            for i in range(sides):
                a = 2.0 * math.pi * i / sides
                verts.append(tuple(p + u * (radius * math.cos(a)) + w * (radius * math.sin(a))))
        self.add(verts, [])
        base = len(self.v) - 2 * sides
        for i in range(sides):
            j = (i + 1) % sides
            self.f.append([base + i, base + j, base + sides + j, base + sides + i])
        if cap:
            self.f.append([base + i for i in range(sides)][::-1])
            self.f.append([base + sides + i for i in range(sides)])

    def tube(self, points, radius, sides=12, cap=True):
        pts = [Vector(p) for p in points]
        rings = []
        for i, p in enumerate(pts):
            if i == 0:
                d = (pts[1] - pts[0])
            elif i == len(pts) - 1:
                d = (pts[-1] - pts[-2])
            else:
                d = (pts[i + 1] - pts[i - 1])
            d = d.normalized()
            up = Vector((0, 0, 1)) if abs(d.z) < 0.92 else Vector((1, 0, 0))
            u = d.cross(up).normalized()
            w = d.cross(u).normalized()
            rings.append((p, u, w))
        base0 = len(self.v)
        for p, u, w in rings:
            for i in range(sides):
                a = 2.0 * math.pi * i / sides
                self.v.append(tuple(p + u * (radius * math.cos(a)) + w * (radius * math.sin(a))))
        for r in range(len(pts) - 1):
            for i in range(sides):
                j = (i + 1) % sides
                a = base0 + r * sides
                b = base0 + (r + 1) * sides
                self.f.append([a + i, a + j, b + j, b + i])
        if cap:
            self.f.append([base0 + i for i in range(sides)][::-1])
            last = base0 + (len(pts) - 1) * sides
            self.f.append([last + i for i in range(sides)])


def make_obj(name, mb, mat, coll, smooth=False, bevel=0.0, bevel_seg=2,
             recalc=True, bevel_angle=30.0):
    if isinstance(mb, tuple):
        verts, faces = mb
    else:
        verts, faces = mb.v, mb.f
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate(verbose=False)
    if recalc:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    if bevel > 0.0:
        mod = ob.modifiers.new("Bevel", 'BEVEL')
        mod.width = bevel
        mod.segments = bevel_seg
        mod.limit_method = 'ANGLE'
        mod.angle_limit = math.radians(bevel_angle)
        mod.harden_normals = False
    return ob


def loft(rings, closed=True, cap_start=True, cap_end=True):
    """rings: list of list[Vector]; returns (verts, faces)."""
    verts = [tuple(p) for r in rings for p in r]
    n = len(rings[0])
    faces = []
    for i in range(len(rings) - 1):
        a = i * n
        b = (i + 1) * n
        for j in range(n if closed else n - 1):
            k = (j + 1) % n
            faces.append([a + j, a + k, b + k, b + j])
    if closed and cap_start:
        faces.append(list(range(n))[::-1])
    if closed and cap_end:
        a = (len(rings) - 1) * n
        faces.append([a + j for j in range(n)])
    return verts, faces


def chaikin(pts, iterations=3):
    pts = [Vector(p) for p in pts]
    for _ in range(iterations):
        new = [pts[0]]
        for i in range(len(pts) - 1):
            p, q = pts[i], pts[i + 1]
            new.append(p * 0.75 + q * 0.25)
            new.append(p * 0.25 + q * 0.75)
        new.append(pts[-1])
        pts = new
    return pts


# ----------------------------------------------------------------------------
# Materials
# ----------------------------------------------------------------------------
def principled(mat):
    return mat.node_tree.nodes.get("Principled BSDF")


def set_in(node, name, value):
    sock = node.inputs.get(name)
    if sock is not None:
        sock.default_value = value


def make_material(name, base, rough=0.8, metal=0.0, ior=1.45,
                  noise_scale=0.02, noise_strength=0.35, bump=0.15,
                  color2=None, coat=0.0, emission=None, noise_detail=8.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = principled(mat)
    set_in(bsdf, "Base Color", (*base, 1.0))
    set_in(bsdf, "Roughness", rough)
    set_in(bsdf, "Metallic", metal)
    set_in(bsdf, "IOR", ior)
    set_in(bsdf, "Coat Weight", coat)
    if emission is not None:
        set_in(bsdf, "Emission Color", (*emission[0], 1.0))
        set_in(bsdf, "Emission Strength", emission[1])
    mat.diffuse_color = (*base, 1.0)
    mat["base_rgb"] = list(base)

    # Object coordinates are metric here (all objects sit at world origin with
    # scale 1), so noise scale is directly "features per metre".
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-980, 0)
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.location = (-760, 120)
    tex.inputs["Scale"].default_value = noise_scale
    tex.inputs["Detail"].default_value = noise_detail
    tex.inputs["Roughness"].default_value = 0.62
    nt.links.new(tc.outputs["Object"], tex.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-540, 200)
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[1].position = 0.72
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.location = (-300, 220)
    mix.blend_type = 'MIX'
    mix.inputs["Color1"].default_value = (*base, 1.0)
    c2 = color2 if color2 is not None else tuple(min(1.0, c * 1.32 + 0.02) for c in base)
    mix.inputs["Color2"].default_value = (*c2, 1.0)
    mix.inputs["Fac"].default_value = 0.55
    nt.links.new(ramp.outputs["Color"], mix.inputs["Fac"])
    nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])

    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.location = (-300, -120)
    bmp.inputs["Strength"].default_value = bump
    bmp.inputs["Distance"].default_value = 0.35
    nt.links.new(ramp.outputs["Color"], bmp.inputs["Height"])
    nt.links.new(bmp.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


MAT_CONCRETE = make_material("MAT_Concrete", (0.310, 0.304, 0.289), rough=0.88,
                             noise_scale=0.035, bump=0.45,
                             color2=(0.268, 0.262, 0.250))
MAT_CONCRETE_DARK = make_material("MAT_Concrete_Weathered", (0.265, 0.258, 0.246), rough=0.92,
                                  noise_scale=0.06, bump=0.5,
                                  color2=(0.170, 0.165, 0.157))
MAT_STEEL = make_material("MAT_Steel", (0.175, 0.185, 0.200), rough=0.48, metal=0.85,
                          noise_scale=1.1, bump=0.06, color2=(0.255, 0.265, 0.280),
                          noise_detail=3.0)
MAT_STEEL_PEN = make_material("MAT_Steel_Penstock", (0.145, 0.152, 0.160), rough=0.58, metal=0.7,
                              noise_scale=0.45, bump=0.12, color2=(0.235, 0.242, 0.250),
                              noise_detail=4.0)
MAT_STEEL_RUST = make_material("MAT_Steel_Rusted", (0.285, 0.180, 0.105), rough=0.78, metal=0.45,
                               noise_scale=2.2, bump=0.12, color2=(0.40, 0.295, 0.19),
                               noise_detail=4.0)
MAT_WATER = make_material("MAT_Water", (0.011, 0.040, 0.046), rough=0.055, metal=0.0,
                          ior=1.333, noise_scale=0.10, bump=0.40,
                          color2=(0.023, 0.068, 0.072), coat=0.7,
                          noise_detail=5.0)
MAT_ROCK = make_material("MAT_Rock", (0.105, 0.098, 0.088), rough=0.96,
                         noise_scale=0.0055, bump=0.55, color2=(0.235, 0.220, 0.195),
                         noise_detail=6.0)
MAT_ASPHALT = make_material("MAT_Asphalt", (0.052, 0.054, 0.057), rough=0.9,
                            noise_scale=1.8, bump=0.08, color2=(0.082, 0.084, 0.088))
MAT_FOLIAGE = make_material("MAT_Foliage", (0.035, 0.078, 0.032), rough=0.88,
                            noise_scale=1.3, bump=0.15, color2=(0.062, 0.118, 0.046),
                            noise_detail=4.0)
MAT_TRUNK = make_material("MAT_Trunk", (0.078, 0.054, 0.036), rough=0.9,
                          noise_scale=1.6, bump=0.15, color2=(0.125, 0.088, 0.058),
                          noise_detail=4.0)
MAT_DARK = make_material("MAT_Dark_Recess", (0.012, 0.014, 0.016), rough=0.68,
                         noise_scale=1.4, bump=0.02, color2=(0.03, 0.033, 0.036),
                         noise_detail=3.0)
MAT_GLASS = make_material("MAT_Glass_Dark", (0.025, 0.045, 0.055), rough=0.14, metal=0.35,
                          noise_scale=0.7, bump=0.0, color2=(0.05, 0.08, 0.09),
                          noise_detail=3.0)
MAT_YELLOW = make_material("MAT_Steel_Yellow", (0.55, 0.36, 0.045), rough=0.55, metal=0.3,
                           noise_scale=0.8, bump=0.04, color2=(0.66, 0.47, 0.10),
                           noise_detail=3.0)
MAT_LAMP = make_material("MAT_Lamp", (0.9, 0.85, 0.7), rough=0.4, metal=0.0,
                         noise_scale=1.0, bump=0.0, color2=(1.0, 0.95, 0.8),
                         emission=((1.0, 0.86, 0.62), 6.0), noise_detail=2.0)


def add_streaks(mat, amount=0.55, lateral=0.42, vertical=0.022,
                ramp_lo=0.38, ramp_hi=0.62):
    """Rain/weathering streaks: high lateral frequency, very low vertical."""
    nt = mat.node_tree
    bsdf = principled(mat)
    if bsdf is None or not bsdf.inputs["Base Color"].is_linked:
        return
    src = bsdf.inputs["Base Color"].links[0].from_socket
    nt.links.remove(bsdf.inputs["Base Color"].links[0])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (lateral, lateral, vertical)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 1.7
    nz.inputs["Detail"].default_value = 6.0
    nz.inputs["Roughness"].default_value = 0.68
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    rmp = nt.nodes.new("ShaderNodeValToRGB")
    rmp.color_ramp.elements[0].position = ramp_lo
    rmp.color_ramp.elements[1].position = ramp_hi
    rmp.color_ramp.elements[0].color = (0.52, 0.51, 0.49, 1.0)
    rmp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    nt.links.new(nz.outputs["Fac"], rmp.inputs["Fac"])
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.blend_type = 'MULTIPLY'
    mix.inputs["Fac"].default_value = amount
    mix.inputs["Color1"].default_value = (1.0, 1.0, 1.0, 1.0)
    nt.links.new(src, mix.inputs["Color1"])
    nt.links.new(rmp.outputs["Color"], mix.inputs["Color2"])
    nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])


add_streaks(MAT_CONCRETE, amount=0.42, lateral=0.30, vertical=0.018)
add_streaks(MAT_CONCRETE_DARK, amount=0.45, lateral=0.38, vertical=0.025)


def add_rock_detail(mat):
    """Horizontal sedimentary strata + large scale tonal patches."""
    nt = mat.node_tree
    bsdf = principled(mat)
    if bsdf is None or not bsdf.inputs["Base Color"].is_linked:
        return
    src = bsdf.inputs["Base Color"].links[0].from_socket
    nt.links.remove(bsdf.inputs["Base Color"].links[0])

    tc = nt.nodes.new("ShaderNodeTexCoord")
    # --- strata bands (object space, waves along Z)
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'Z'
    wave.inputs["Scale"].default_value = 0.055
    wave.inputs["Distortion"].default_value = 3.2
    wave.inputs["Detail"].default_value = 3.0
    wave.inputs["Detail Scale"].default_value = 2.2
    nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
    wrmp = nt.nodes.new("ShaderNodeValToRGB")
    wrmp.color_ramp.elements[0].position = 0.0
    wrmp.color_ramp.elements[0].color = (0.55, 0.54, 0.52, 1.0)
    wrmp.color_ramp.elements[1].position = 0.16
    wrmp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    nt.links.new(wave.outputs["Fac"], wrmp.inputs["Fac"])
    wmix = nt.nodes.new("ShaderNodeMixRGB")
    wmix.blend_type = 'MULTIPLY'
    wmix.inputs["Fac"].default_value = 0.5
    nt.links.new(src, wmix.inputs["Color1"])
    nt.links.new(wrmp.outputs["Color"], wmix.inputs["Color2"])

    # --- broad tonal patches
    big = nt.nodes.new("ShaderNodeTexNoise")
    big.inputs["Scale"].default_value = 0.0018
    big.inputs["Detail"].default_value = 3.0
    big.inputs["Roughness"].default_value = 0.55
    nt.links.new(tc.outputs["Object"], big.inputs["Vector"])
    brmp = nt.nodes.new("ShaderNodeValToRGB")
    brmp.color_ramp.elements[0].position = 0.38
    brmp.color_ramp.elements[0].color = (0.72, 0.72, 0.72, 1.0)
    brmp.color_ramp.elements[1].position = 0.66
    brmp.color_ramp.elements[1].color = (1.12, 1.10, 1.06, 1.0)
    nt.links.new(big.outputs["Fac"], brmp.inputs["Fac"])
    bmix = nt.nodes.new("ShaderNodeMixRGB")
    bmix.blend_type = 'MULTIPLY'
    bmix.inputs["Fac"].default_value = 0.55
    nt.links.new(wmix.outputs["Color"], bmix.inputs["Color1"])
    nt.links.new(brmp.outputs["Color"], bmix.inputs["Color2"])
    nt.links.new(bmix.outputs["Color"], bsdf.inputs["Base Color"])


add_rock_detail(MAT_ROCK)


def add_bands(mat, scale, axis, amount, lo, hi, distort=1.4):
    """Thin darker bands (construction joints / lift lines) over base colour."""
    mnt = mat.node_tree
    bsdf = mnt.nodes.get("Principled BSDF")
    if bsdf is None or not bsdf.inputs["Base Color"].is_linked:
        return
    src = bsdf.inputs["Base Color"].links[0].from_socket
    mnt.links.remove(bsdf.inputs["Base Color"].links[0])
    wave = mnt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = 'BANDS'
    wave.bands_direction = axis
    wave.inputs["Scale"].default_value = scale
    wave.inputs["Distortion"].default_value = distort
    wave.inputs["Detail"].default_value = 2.0
    wave.inputs["Detail Scale"].default_value = 1.5
    tcb = mnt.nodes.new("ShaderNodeTexCoord")
    mnt.links.new(tcb.outputs["Object"], wave.inputs["Vector"])
    rmp = mnt.nodes.new("ShaderNodeValToRGB")
    rmp.color_ramp.elements[0].position = lo
    rmp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    rmp.color_ramp.elements[1].position = hi
    rmp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    mnt.links.new(wave.outputs["Fac"], rmp.inputs["Fac"])
    mix = mnt.nodes.new("ShaderNodeMixRGB")
    mix.blend_type = 'MULTIPLY'
    mix.inputs["Fac"].default_value = amount
    mnt.links.new(src, mix.inputs["Color1"])
    mnt.links.new(rmp.outputs["Color"], mix.inputs["Color2"])
    mnt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])


add_bands(MAT_CONCRETE, 0.060, "X", 0.20, 0.01, 0.05, 1.1)
add_bands(MAT_CONCRETE, 0.090, "Z", 0.14, 0.01, 0.055, 1.0)
add_bands(MAT_CONCRETE_DARK, 0.070, "X", 0.16, 0.01, 0.05, 1.0)

# fine grain bump on rock
_nt = MAT_ROCK.node_tree
_bsdf = principled(MAT_ROCK)
_n2 = _nt.nodes.new("ShaderNodeTexNoise")
_n2.inputs["Scale"].default_value = 0.38
_n2.inputs["Detail"].default_value = 10.0
_n2.inputs["Roughness"].default_value = 0.7
_b2 = _nt.nodes.new("ShaderNodeBump")
_b2.inputs["Strength"].default_value = 0.85
_b2.inputs["Distance"].default_value = 0.8
_nt.links.new(_n2.outputs["Fac"], _b2.inputs["Height"])
_prev = _bsdf.inputs["Normal"].links[0].from_node if _bsdf.inputs["Normal"].is_linked else None
if _prev is not None:
    _nt.links.new(_prev.outputs["Normal"], _b2.inputs["Normal"])
_nt.links.new(_b2.outputs["Normal"], _bsdf.inputs["Normal"])

# ----------------------------------------------------------------------------
# Collections
# ----------------------------------------------------------------------------
COL_STRUCT = bpy.data.collections.new("COL_Dam_Structure")
COL_HYDRO = bpy.data.collections.new("COL_Hydro_Plant")
COL_ENV = bpy.data.collections.new("COL_Environment")
COL_VERN = bpy.data.collections.new("COL_Vegetation")
COL_RIG = bpy.data.collections.new("COL_Lighting_Cameras")
for c in (COL_STRUCT, COL_HYDRO, COL_ENV, COL_VERN, COL_RIG):
    scene.collection.children.link(c)


# ----------------------------------------------------------------------------
# Terrain mesh
# ----------------------------------------------------------------------------
def build_terrain():
    n = 400
    x0, x1 = -700.0, 700.0
    y0, y1 = -1250.0, 820.0
    verts = []
    for j in range(n + 1):
        y = lerp(y0, y1, j / n)
        for i in range(n + 1):
            x = lerp(x0, x1, i / n)
            verts.append((x, y, terrain_h(x, y)))
    faces = []
    row = n + 1
    for j in range(n):
        for i in range(n):
            a = j * row + i
            faces.append([a, a + 1, a + 1 + row, a + row])
    return verts, faces


terrain = make_obj("SM_Terrain_Canyon", build_terrain(), MAT_ROCK, COL_ENV,
                   smooth=True, recalc=False)
terrain.data.materials[0] = MAT_ROCK

# ----------------------------------------------------------------------------
# Water surfaces
# ----------------------------------------------------------------------------
def reservoir_water():
    cols = 300
    rows = 32
    verts = []
    x0, x1 = -620.0, 620.0
    y0 = -1180.0
    for j in range(rows + 1):
        for i in range(cols + 1):
            x = lerp(x0, x1, i / cols)
            if abs(x) < DAM_HALF_X - 0.5:
                ymax = ARCH_R - math.sqrt(max(0.0, ARCH_R * ARCH_R - x * x)) - 1.2
            else:
                ymax = 62.0
            ymax = max(ymax, y0 + 1.0)
            y = lerp(y0, ymax, j / rows)
            verts.append((x, y, RES_Z - 0.06 * fbm(x * 0.02, y * 0.02, 2, 5)))
    faces = []
    row = cols + 1
    for j in range(rows):
        for i in range(cols):
            a = j * row + i
            faces.append([a, a + 1, a + 1 + row, a + row])
    return verts, faces


make_obj("SM_Reservoir_Water", reservoir_water(), MAT_WATER, COL_ENV,
         smooth=True, recalc=False)


def tailwater():
    n = 96
    x0, x1 = -420.0, 420.0
    y0, y1 = 52.0, 760.0
    verts = []
    for j in range(n + 1):
        y = lerp(y0, y1, j / n)
        for i in range(n + 1):
            x = lerp(x0, x1, i / n)
            verts.append((x, y, TAIL_Z + 0.05 * fbm(x * 0.03, y * 0.03, 2, 9)))
    faces = []
    row = n + 1
    for j in range(n):
        for i in range(n):
            a = j * row + i
            faces.append([a, a + 1, a + 1 + row, a + row])
    return verts, faces


make_obj("SM_Tailwater", tailwater(), MAT_WATER, COL_ENV,
         smooth=True, recalc=False)

# ----------------------------------------------------------------------------
# Dam body
# ----------------------------------------------------------------------------
def thick_at(z, base, crest, tbase):
    h = max(crest - base, 1.0)
    f = clamp((crest - z) / h, 0.0, 1.0)
    return CREST_T + (tbase - CREST_T) * (f ** 0.88)


def dam_base(t):
    x, y = arc_xy(t)
    return min(terrain_raw(x, y) - 18.0, CREST_Z - 16.0)


def dam_profile(t):
    x, y = arc_xy(t)
    crest = crest_z_at_x(x)
    base = dam_base(t)
    h = crest - base
    tbase = CREST_T + 0.30 * h
    pts = [(-4.0, base), (0.0, base), (0.0, crest), (CREST_T, crest)]
    for f in (0.94, 0.83, 0.70, 0.55, 0.40, 0.26, 0.13):
        z = base + f * h
        pts.append((thick_at(z, base, crest, tbase), z))
    pts.append((tbase, base))
    return base, crest, pts


def build_dam_body():
    n = 180
    rings = []
    for i in range(n + 1):
        t = -ARCH_HALF + 2.0 * ARCH_HALF * i / n
        x, y = arc_xy(t)
        nx, ny = arc_normal(t)
        base, crest, prof = dam_profile(t)
        rings.append([Vector((x + nx * d, y + ny * d, z)) for d, z in prof])
    return loft(rings, closed=True, cap_start=True, cap_end=True)


dam_obj = make_obj("SM_Dam_Body", build_dam_body(), MAT_CONCRETE, COL_STRUCT,
                   smooth=False, bevel=0.22, bevel_seg=2)


def build_gallery_outlets():
    """Rows of small dark drainage outlets; strong scale cue on the face."""
    mb = MB()
    for z in (104.0, 72.0, 40.0):
        for k in range(-13, 14):
            xx = k * 12.5 + 6.0
            if SPILL_X0 - 4.0 < xx < SPILL_X1 + 4.0:
                continue
            if abs(xx) > DAM_HALF_X - 6.0:
                continue
            t = t_of_x(xx)
            x, y = arc_xy(t)
            nx, ny = arc_normal(t)
            tx_, ty_ = math.cos(t), math.sin(t)
            base, crest, _ = dam_profile(t)
            tbase = CREST_T + 0.30 * (crest - base)
            hw, hh = 0.85, 0.75
            for zz, sy in ((z - hh, -1.0), (z + hh, 1.0)):
                dd = thick_at(zz, base, crest, tbase) + 0.10
                cx, cy = x + nx * dd, y + ny * dd
                for sx in (-1.0, 1.0):
                    mb.v.append((cx + tx_ * hw * sx, cy + ty_ * hw * sx, z + hh * sy))
            o = len(mb.v) - 4
            mb.f.append([o, o + 1, o + 3, o + 2])
    return mb


make_obj("SM_Drainage_Outlets", build_gallery_outlets(), MAT_DARK, COL_STRUCT,
         recalc=True)

# ----------------------------------------------------------------------------
# Crest roadway, parapets, railings, lamps
# ----------------------------------------------------------------------------
ROAD_D0, ROAD_D1 = 1.2, 8.6
RAIL_D = (1.55, 8.95)

rail_mb = MB()
lamp_mb = MB()
lamp_glow = MB()

n_road = 220
road_rings = []
par_rings_l = []
par_rings_r = []
for i in range(n_road + 1):
    t = -ARCH_HALF + 2.0 * ARCH_HALF * i / n_road
    x, y = arc_xy(t)
    nx, ny = arc_normal(t)

    def P(d, z):
        return Vector((x + nx * d, y + ny * d, z))

    road_rings.append([P(ROAD_D0, 179.55), P(ROAD_D1, 179.55),
                       P(ROAD_D1, 180.28), P(ROAD_D0, 180.28)])
    par_rings_l.append([P(0.55, 180.28), P(1.35, 180.28),
                        P(1.35, 181.55), P(0.55, 181.55)])
    par_rings_r.append([P(8.55, 180.28), P(9.35, 180.28),
                        P(9.35, 181.55), P(8.55, 181.55)])
make_obj("SM_Crest_Road", loft(road_rings), MAT_ASPHALT, COL_STRUCT,
         recalc=True)
make_obj("SM_Parapet_Upstream", loft(par_rings_l), MAT_CONCRETE, COL_STRUCT,
         bevel=0.06)
make_obj("SM_Parapet_Downstream", loft(par_rings_r), MAT_CONCRETE, COL_STRUCT,
         bevel=0.06)

# railing posts + lamp standards
for i in range(78):
    t = -ARCH_HALF + 2.0 * ARCH_HALF * (i + 0.5) / 78.0
    x, y = arc_xy(t)
    nx, ny = arc_normal(t)
    for d in RAIL_D:
        cx, cy = x + nx * d, y + ny * d
        rail_mb.box(cx, cy, 182.15, 0.10, 0.10, 0.75, rz=t)
    if i % 6 == 0:
        t2 = -ARCH_HALF + 2.0 * ARCH_HALF * (i + 1.0) / 78.0
        x2, y2 = arc_xy(t2)
        nx2, ny2 = arc_normal(t2)
        cx, cy = x2 + nx2 * 5.0, y2 + ny2 * 5.0
        lamp_mb.cyl((cx, cy, 180.28), (cx, cy, 187.6), 0.15, 8)
        lamp_mb.box(cx, cy, 187.75, 1.45, 0.38, 0.26, rz=t2)
        lamp_glow.box(cx, cy, 187.55, 1.15, 0.26, 0.09, rz=t2)

# continuous horizontal rails
for i in range(78):
    for t_ofs in (0.0, 0.5):
        t0 = -ARCH_HALF + 2.0 * ARCH_HALF * (i + t_ofs) / 78.0
        t1 = -ARCH_HALF + 2.0 * ARCH_HALF * (i + t_ofs + 1.0) / 78.0
        xa, ya = arc_xy(t0)
        xb, yb = arc_xy(t1)
        nxa, nya = arc_normal(t0)
        nxb, nyb = arc_normal(t1)
        for d in RAIL_D:
            pa = Vector((xa + nxa * d, ya + nya * d, 182.52))
            pb = Vector((xb + nxb * d, yb + nyb * d, 182.52))
            mid = (pa + pb) * 0.5
            ln = (pb - pa).length
            ang = math.atan2((pb - pa).y, (pb - pa).x)
            rail_mb.box(mid.x, mid.y, mid.z, ln + 0.1, 0.065, 0.065, rz=ang)

make_obj("SM_Crest_Railing", rail_mb, MAT_STEEL, COL_STRUCT, bevel=0.0)
make_obj("SM_Lamp_Posts", lamp_mb, MAT_STEEL, COL_STRUCT)
make_obj("SM_Lamp_Glow", lamp_glow, MAT_LAMP, COL_STRUCT)

# ----------------------------------------------------------------------------
# Spillway piers, gates, hoist houses
# ----------------------------------------------------------------------------
PIER_X = [2.25 + 16.5 * i for i in range(6)]
BAY_CENTERS = [10.5 + 16.5 * i for i in range(5)]
BAY_W = 14.0

pier_mb = MB()
house_mb = MB()
house_roof = MB()
house_door = MB()
gate_mb = MB()
gate_rib_mb = MB()
gate_arm_mb = MB()

for px in PIER_X:
    t = t_of_x(px)
    x, y = arc_xy(t)
    nx, ny = arc_normal(t)
    cx, cy = x + nx * 6.0, y + ny * 6.0
    pier_mb.box(cx, cy, (166.5 + 179.55) * 0.5, 2.5, 20.0, 179.55 - 166.5, rz=t)
    pier_mb.cyl((x - nx * 3.9, y - ny * 3.9, 172.0),
                (x - nx * 3.9, y - ny * 3.9, 175.5), 1.25, 12)
    hx, hy = x + nx * 12.9, y + ny * 12.9
    house_mb.box(hx, hy, 183.1, 4.8, 4.6, 6.2, rz=t)
    house_roof.box(hx, hy, 186.45, 5.5, 5.3, 0.4, rz=t)
    house_door.box(hx + nx * 2.35, hy + ny * 2.35, 182.8, 2.5, 0.35, 3.6, rz=t)

for bx in BAY_CENTERS:
    t = t_of_x(bx)
    x, y = arc_xy(t)
    nx, ny = arc_normal(t)
    tx_, ty_ = math.cos(t), math.sin(t)

    def G(d, z):
        return Vector((x + nx * d, y + ny * d, z))

    prof = []
    for k in range(13):
        a = k / 12.0
        z = 167.4 + a * 11.8
        d = 0.7 + 6.5 * a - 1.25 * math.sin(math.pi * a)
        prof.append(G(d, z))

    # gate leaf: extruded curved plate (solidified afterwards)
    verts = []
    for p in prof:
        verts.append((p.x - tx_ * 7.0, p.y - ty_ * 7.0, p.z))
        verts.append((p.x + tx_ * 7.0, p.y + ty_ * 7.0, p.z))
    faces = []
    for k in range(12):
        a = k * 2
        faces.append([a, a + 1, a + 3, a + 2])
    gate_mb.add(verts, faces)

    for k in range(1, 12):
        p = prof[k]
        gate_rib_mb.box(p.x, p.y, p.z, 14.0, 0.5, 0.55, rz=t)

    p_trun = G(12.2, 175.2)
    for zz in (171.6, 175.2):
        a = (zz - 167.4) / 11.8
        d = 0.7 + 6.5 * a - 1.25 * math.sin(math.pi * a)
        p_leaf = G(d, zz)
        mid = (p_leaf + p_trun) * 0.5
        dv = p_trun - p_leaf
        ln = dv.length
        ang = math.atan2(dv.y, dv.x)
        gate_arm_mb.box(mid.x, mid.y, mid.z, ln, 0.45, 0.45, rz=ang)
    gate_arm_mb.box(p_trun.x, p_trun.y, p_trun.z, 1.5, 1.5, 1.5, rz=t)

make_obj("SM_Spillway_Piers", pier_mb, MAT_CONCRETE, COL_STRUCT, bevel=0.12)
make_obj("SM_Hoist_Houses", house_mb, MAT_CONCRETE_DARK, COL_STRUCT, bevel=0.08)
make_obj("SM_Hoist_Roofs", house_roof, MAT_STEEL_RUST, COL_STRUCT, bevel=0.04)
make_obj("SM_Hoist_Doors", house_door, MAT_DARK, COL_STRUCT)
gate_obj = make_obj("SM_Radial_Gates", gate_mb, MAT_STEEL, COL_STRUCT, smooth=True)
sol = gate_obj.modifiers.new("Solidify", 'SOLIDIFY')
sol.thickness = 0.55
sol.offset = 0.0
make_obj("SM_Gate_Stiffeners", gate_rib_mb, MAT_STEEL_RUST, COL_STRUCT)
make_obj("SM_Gate_Arms", gate_arm_mb, MAT_STEEL, COL_STRUCT)

# ----------------------------------------------------------------------------
# Spillway chute (ogee face + flip bucket) and training walls
# ----------------------------------------------------------------------------
CHUTE_ZS = [166.5, 159.0, 151.0, 142.0, 132.0, 121.0, 109.0, 96.0,
            83.0, 70.0, 58.0, 47.0, 40.0]
FLIP = [(8.0, 35.0), (15.0, 31.0), (22.0, 29.5), (28.0, 32.0), (32.0, 36.5)]


def chute_stations():
    n = 64
    return [t_of_x(lerp(SPILL_X0 - 0.5, SPILL_X1 + 0.5, i / n)) for i in range(n + 1)]


def chute_surface_samples(t):
    x, y = arc_xy(t)
    nx, ny = arc_normal(t)
    base, crest, _ = dam_profile(t)
    tbase = CREST_T + 0.30 * (crest - base)
    samples = []
    for z in CHUTE_ZS:
        d = thick_at(z, base, crest, tbase) + 1.15
        samples.append((d, z))
    d0 = thick_at(40.0, base, crest, tbase) + 1.15
    for extra, zz in FLIP:
        samples.append((d0 + extra, zz))
    return [(x + nx * d, y + ny * d, z) for d, z in samples]


def build_chute():
    top = [chute_surface_samples(t) for t in chute_stations()]
    nz = len(top[0])
    verts = [tuple(p) for row in top for p in row]
    nv = len(verts)
    for row in top:
        for p in row:
            verts.append((p[0], p[1], p[2] - 2.2))
    faces = []
    for i in range(len(top) - 1):
        for j in range(nz - 1):
            a = i * nz + j
            faces.append([a, a + 1, a + 1 + nz, a + nz])
            b = nv + a
            faces.append([b, b + nz, b + 1 + nz, b + 1])
    last = (len(top) - 1) * nz
    for j in range(nz - 1):
        faces.append([j, nv + j, nv + j + 1, j + 1])
        faces.append([last + j, last + j + 1, nv + last + j + 1, nv + last + j])
    for i in range(len(top) - 1):
        a = i * nz
        faces.append([a, a + nz, nv + a + nz, nv + a])
        b = a + nz - 1
        faces.append([b, nv + b, nv + b + nz, b + nz])
    return verts, faces


make_obj("SM_Spillway_Chute", build_chute(), MAT_CONCRETE_DARK, COL_STRUCT,
         smooth=False, bevel=0.08)


def build_chute_joints():
    """Thin raised contraction joints every ~13 m of drop."""
    verts, faces = [], []
    n = 56
    for z in (154.0, 141.0, 128.0, 115.0, 102.0, 89.0, 76.0, 63.0, 50.0):
        row = []
        for i in range(n + 1):
            xx = lerp(SPILL_X0 + 0.4, SPILL_X1 - 0.4, i / n)
            t = t_of_x(xx)
            xa, ya = arc_xy(t)
            nx, ny = arc_normal(t)
            base, crest, _ = dam_profile(t)
            tbase = CREST_T + 0.30 * (crest - base)
            d = thick_at(z, base, crest, tbase) + 1.23
            row.append(Vector((xa + nx * d, ya + ny * d, z)))
        o = len(verts)
        for p in row:
            verts.append((p.x, p.y, p.z - 0.26))
        for p in row:
            verts.append((p.x, p.y, p.z + 0.26))
        for i in range(n):
            faces.append([o + i, o + i + 1, o + n + 2 + i, o + n + 1 + i])
    return verts, faces


make_obj("SM_Chute_Contraction_Joints", build_chute_joints(), MAT_CONCRETE_DARK,
         COL_STRUCT, recalc=True)


def build_training_walls():
    stations = chute_stations()
    all_v, all_f = [], []
    for idx in (0, len(stations) - 1):
        t = stations[idx]
        x, y = arc_xy(t)
        nx, ny = arc_normal(t)
        tx_, ty_ = math.cos(t), math.sin(t)
        samples = chute_surface_samples(t)
        rings = []
        for (px, py, pz) in samples:
            rings.append([Vector((px + tx_ * 0.7, py + ty_ * 0.7, pz)),
                          Vector((px + tx_ * 0.7, py + ty_ * 0.7, pz + 4.4)),
                          Vector((px - tx_ * 0.7, py - ty_ * 0.7, pz + 4.4)),
                          Vector((px - tx_ * 0.7, py - ty_ * 0.7, pz))])
        v, f = loft(rings, closed=True, cap_start=True, cap_end=True)
        off = len(all_v)
        all_v.extend(v)
        all_f.extend([[i + off for i in fc] for fc in f])
    return all_v, all_f


make_obj("SM_Spillway_Training_Walls", build_training_walls(), MAT_CONCRETE,
         COL_STRUCT, bevel=0.08)

# ----------------------------------------------------------------------------
# Powerhouse
# ----------------------------------------------------------------------------
PH_X0, PH_X1 = -76.0, -8.0
PH_Y0, PH_Y1 = 70.0, 104.0
PH_Z0, PH_Z1 = 5.0, 40.0

ph_mb = MB()
ph_win = MB()
ph_roof = MB()
ph_accent = MB()
ph_trim = MB()
ph_vents = MB()

ph_mb.box_mm(PH_X0, PH_X1, PH_Y0, PH_Y1, PH_Z0, PH_Z1)
ph_mb.box_mm(PH_X0 - 2.0, PH_X1 + 2.0, PH_Y0 - 2.0, PH_Y1 + 2.0, PH_Z0 - 1.5, PH_Z0 + 1.2)
# parapet
ph_roof.box_mm(PH_X0 - 1.0, PH_X1 + 1.0, PH_Y0 - 1.0, PH_Y1 + 1.0, PH_Z1, PH_Z1 + 1.1)
ph_roof.box_mm(PH_X0, PH_X1, PH_Y0, PH_Y1, PH_Z1 - 0.4, PH_Z1)
# window bands on downstream face
for k in range(5):
    x = PH_X0 + 8.0 + k * 13.0
    ph_win.box_mm(x, x + 8.5, PH_Y1 - 0.35, PH_Y1 + 0.15, 12.0, 33.0)
    for j in (1, 2):
        mx = x + 8.5 * j / 3.0
        ph_trim.box_mm(mx - 0.09, mx + 0.09, PH_Y1 - 0.2, PH_Y1 + 0.32, 12.0, 33.0)
    ph_trim.box_mm(x - 0.2, x + 8.7, PH_Y1 - 0.3, PH_Y1 + 0.38, 11.6, 12.1)
    ph_trim.box_mm(x - 0.2, x + 8.7, PH_Y1 - 0.3, PH_Y1 + 0.38, 32.9, 33.4)
# doors + canopies
for k in range(2):
    x = PH_X0 + 14.0 + k * 34.0
    ph_win.box_mm(x, x + 9.0, PH_Y1 - 0.4, PH_Y1 + 0.2, 1.2, 12.0)
    ph_trim.box_mm(x - 1.0, x + 10.0, PH_Y1 + 0.2, PH_Y1 + 2.4, 12.0, 12.5)
# roof vents
for k in range(3):
    x = PH_X0 + 14.0 + k * 19.0
    ph_vents.box_mm(x, x + 4.2, PH_Y0 + 10.0, PH_Y0 + 22.0, PH_Z1, PH_Z1 + 2.2)
# roof crane rails + travelling gantry
for y in (PH_Y0 + 6.0, PH_Y1 - 6.0):
    ph_accent.box_mm(PH_X0 + 2.0, PH_X1 - 2.0, y - 0.35, y + 0.35, PH_Z1 + 0.05, PH_Z1 + 0.75)
gx = PH_X0 + 40.0
ph_accent.box_mm(gx, gx + 2.6, PH_Y0 + 3.0, PH_Y1 - 3.0, PH_Z1 + 2.6, PH_Z1 + 3.6)
ph_accent.box_mm(gx - 0.5, gx + 3.1, PH_Y0 + 3.2, PH_Y0 + 5.0, PH_Z1 + 0.6, PH_Z1 + 2.6)
ph_accent.box_mm(gx - 0.5, gx + 3.1, PH_Y1 - 5.0, PH_Y1 - 3.2, PH_Z1 + 0.6, PH_Z1 + 2.6)
# tailrace apron and training walls
ph_mb.box_mm(PH_X0 - 8.0, PH_X1 + 8.0, PH_Y1, PH_Y1 + 34.0, 2.5, 6.0)
ph_mb.box_mm(PH_X0 - 8.0, PH_X0 - 4.0, PH_Y1, PH_Y1 + 34.0, 2.5, 9.0)
ph_mb.box_mm(PH_X1 + 4.0, PH_X1 + 8.0, PH_Y1, PH_Y1 + 34.0, 2.5, 9.0)
# transformer yard on left
for k in range(3):
    x = PH_X0 - 30.0 + k * 9.0
    ph_accent.box_mm(x, x + 6.0, PH_Y0 + 6.0, PH_Y0 + 12.0, 5.0, 13.0)
    ph_accent.box_mm(x - 0.8, x + 6.8, PH_Y0 + 5.2, PH_Y0 + 12.8, 4.2, 5.0)

make_obj("SM_Powerhouse", ph_mb, MAT_CONCRETE, COL_HYDRO, bevel=0.12)
make_obj("SM_Powerhouse_Windows", ph_win, MAT_GLASS, COL_HYDRO)
make_obj("SM_Powerhouse_Roof", ph_roof, MAT_CONCRETE_DARK, COL_HYDRO, bevel=0.06)
make_obj("SM_Powerhouse_Gantry", ph_accent, MAT_YELLOW, COL_HYDRO, bevel=0.03)
make_obj("SM_Powerhouse_Trim", ph_trim, MAT_STEEL, COL_HYDRO, bevel=0.02)
make_obj("SM_Powerhouse_Roof_Vents", ph_vents, MAT_STEEL_RUST, COL_HYDRO, bevel=0.03)

# ----------------------------------------------------------------------------
# Penstocks and intakes
# ----------------------------------------------------------------------------
PEN_X = [-66.0, -50.0, -34.0, -18.0]
pen_mb = MB()
saddle_mb = MB()
intake_mb = MB()
rack_mb = MB()

for px in PEN_X:
    t = t_of_x(px)
    x, y = arc_xy(t)
    nx, ny = arc_normal(t)
    tx_, ty_ = math.cos(t), math.sin(t)
    base, crest, _ = dam_profile(t)
    h = crest - base
    tbase = CREST_T + 0.30 * h
    face_d = thick_at(126.0, base, crest, tbase)

    ix, iy = x + nx * (face_d + 4.8), y + ny * (face_d + 4.8)
    intake_mb.box(ix, iy, 124.0, 9.6, 9.6, 15.0, rz=t)
    intake_mb.cyl((x + nx * face_d, y + ny * face_d, 121.5),
                  (x + nx * (face_d + 9.6), y + ny * (face_d + 9.6), 121.5), 3.7, 16)
    for k in range(7):
        off = (k - 3) * 1.28
        rax = x + nx * (face_d + 0.15) + tx_ * off
        ray = y + ny * (face_d + 0.15) + ty_ * off
        rack_mb.box(rax, ray, 123.5, 0.18, 0.55, 11.5, rz=t)

    def ds_at(z):
        return thick_at(z, base, crest, tbase) + 4.6

    pts = [
        (x + nx * (face_d + 4.8), y + ny * (face_d + 4.8), 126.0),
        (x + nx * ds_at(112.0), y + ny * ds_at(112.0), 112.0),
        (x + nx * ds_at(92.0), y + ny * ds_at(92.0), 92.0),
        (x + nx * ds_at(70.0), y + ny * ds_at(70.0), 70.0),
        (x + nx * ds_at(48.0), y + ny * ds_at(48.0), 48.0),
        (x + nx * 72.0, y + ny * 72.0, 26.0),
        (x + nx * 80.0, y + ny * 80.0, 15.0),
        (x + nx * 88.0, y + ny * 88.0, 13.0),
    ]
    sm = chaikin(pts, 3)
    pen_mb.tube(sm, 3.1, 24)
    # ring girders / flanges every ~8 stations
    for k in range(1, len(sm) - 2, 8):
        p = sm[k]
        d = (sm[k + 1] - sm[k - 1]).normalized()
        pen_mb.cyl(tuple(p - d * 0.30), tuple(p + d * 0.30), 3.36, 24)
    # small support brackets kept fully below the pipe (no collars)
    for k in range(4, len(sm) - 3, 9):
        p = sm[k]
        saddle_mb.box(p.x, p.y, p.z - 4.15, 3.4, 1.4, 1.5)

make_obj("SM_Penstock_Intakes", intake_mb, MAT_CONCRETE, COL_HYDRO, bevel=0.1)
make_obj("SM_Penstock_TrashRacks", rack_mb, MAT_STEEL_RUST, COL_HYDRO)
make_obj("SM_Penstocks", pen_mb, MAT_STEEL_PEN, COL_HYDRO, smooth=True)
make_obj("SM_Penstock_Saddles", saddle_mb, MAT_CONCRETE_DARK, COL_HYDRO, bevel=0.06)

# ----------------------------------------------------------------------------
# Access road + tunnel portal (right bank)
# ----------------------------------------------------------------------------
road2 = MB()
road2.box_mm(ROAD_A[0], ROAD_B[0] + 1.5, 32.5, 43.5, 180.15, 180.6)
make_obj("SM_Access_Road", road2, MAT_ASPHALT, COL_STRUCT)

portal = MB()
PX = ROAD_B[0] + 1.0
portal.box_mm(PX, PX + 6.0, 29.0, 32.0, 180.0, 192.0)
portal.box_mm(PX, PX + 6.0, 44.0, 47.0, 180.0, 192.0)
portal.box_mm(PX, PX + 6.0, 29.0, 47.0, 192.0, 195.2)
make_obj("SM_Tunnel_Portal", portal, MAT_CONCRETE, COL_STRUCT, bevel=0.1)
hole = MB()
hole.box_mm(PX + 5.9, PX + 6.15, 32.0, 44.0, 180.0, 192.0)
make_obj("SM_Tunnel_Bore", hole, MAT_DARK, COL_STRUCT)

# ----------------------------------------------------------------------------
# Vegetation and rocks
# ----------------------------------------------------------------------------
def tree_mesh():
    trunk = MB()
    leaves = MB()
    count = 0
    for _ in range(7000):
        x = RNG.uniform(-640, 640)
        y = RNG.uniform(-1150, 740)
        z = terrain_h(x, y)
        if z < 12.0 or z > 215.0:
            continue
        if math.hypot(x, y * 0.6) < 130.0:
            continue
        if seg_dist(x, y, ROAD_A[0], ROAD_A[1], ROAD_B[0], ROAD_B[1]) < 30.0:
            continue
        dx = (terrain_h(x + 2, y) - terrain_h(x - 2, y)) / 4.0
        dy = (terrain_h(x, y + 2) - terrain_h(x, y - 2)) / 4.0
        if math.hypot(dx, dy) > 0.85:
            continue
        # clustered forest patches instead of an even sprinkle
        if fbm(x * 0.0055, y * 0.0055, 3, 301) < 0.42:
            continue
        h = RNG.uniform(14.0, 24.0)
        r = h * RNG.uniform(0.17, 0.23)
        trunk.cyl((x, y, z - 1.0), (x, y, z + h * 0.45), 0.35, 6)
        for tier in range(2):
            z0 = z + h * (0.28 + 0.26 * tier)
            z1 = z + h * (0.72 + 0.28 * tier)
            rr = r * (1.0 - 0.30 * tier)
            sides = 7
            ring = [(x + rr * math.cos(2.0 * math.pi * i / sides),
                     y + rr * math.sin(2.0 * math.pi * i / sides), z0) for i in range(sides)]
            apex = (x, y, z1)
            for i in range(sides):
                j = (i + 1) % sides
                leaves.add(list(ring) + [apex], [[i, j, sides]])
        count += 1
    return trunk, leaves


trunk_mb, leaves_mb = tree_mesh()
make_obj("SM_Tree_Trunks", trunk_mb, MAT_TRUNK, COL_VERN, smooth=True)
make_obj("SM_Forest", leaves_mb, MAT_FOLIAGE, COL_VERN, smooth=True, recalc=False)


def rocks_mesh():
    mb = MB()
    for _ in range(90):
        x = RNG.uniform(-520, 520)
        y = RNG.uniform(-650, 650)
        z = terrain_h(x, y)
        if z < 2.0:
            continue
        if math.hypot(x, y) < 90.0:
            continue
        rr = RNG.uniform(1.2, 4.2)
        sides, rings_n = 8, 5
        vs = []
        for j in range(rings_n + 1):
            phi = math.pi * j / rings_n
            for i in range(sides):
                th = 2.0 * math.pi * i / sides
                rad = rr * (0.72 + 0.5 * vnoise(i * 0.7 + x, j * 0.9 + y, 5))
                vs.append((x + rad * math.sin(phi) * math.cos(th),
                           y + rad * math.sin(phi) * math.sin(th),
                           z + rad * math.cos(phi) * 0.62))
        fs = []
        for j in range(rings_n):
            for i in range(sides):
                a = j * sides + i
                b = j * sides + (i + 1) % sides
                fs.append([a, b, b + sides, a + sides])
        off = len(mb.v)
        mb.v.extend(vs)
        mb.f.extend([[i + off for i in f] for f in fs])
    return mb


make_obj("SM_Rock_Outcrops", rocks_mesh(), MAT_ROCK, COL_ENV, smooth=True)

# ----------------------------------------------------------------------------
# World, lights, camera
# ----------------------------------------------------------------------------
world = bpy.data.worlds.new("WLD_Dam")
world.use_nodes = True
scene.world = world
wnt = world.node_tree
for n in list(wnt.nodes):
    if n.type != 'OUTPUT_WORLD':
        wnt.nodes.remove(n)
wout = next(n for n in wnt.nodes if n.type == 'OUTPUT_WORLD')
wbg = wnt.nodes.new("ShaderNodeBackground")
wtc = wnt.nodes.new("ShaderNodeTexCoord")
wsep = wnt.nodes.new("ShaderNodeSeparateXYZ")
wmr = wnt.nodes.new("ShaderNodeMapRange")
wmr.inputs["From Min"].default_value = -0.05
wmr.inputs["From Max"].default_value = 0.85
wramp = wnt.nodes.new("ShaderNodeValToRGB")
wcr = wramp.color_ramp
wcr.elements[0].position = 0.0
wcr.elements[0].color = (0.40, 0.45, 0.50, 1.0)
wcr.elements[1].position = 0.55
wcr.elements[1].color = (0.12, 0.23, 0.41, 1.0)
wcr.elements.new(1.0).color = (0.04, 0.09, 0.21, 1.0)
wnt.links.new(wtc.outputs["Generated"], wsep.inputs["Vector"])
wnt.links.new(wsep.outputs["Z"], wmr.inputs["Value"])
wnt.links.new(wmr.outputs["Result"], wramp.inputs["Fac"])
wnt.links.new(wramp.outputs["Color"], wbg.inputs["Color"])
wbg.inputs["Strength"].default_value = 0.38
wnt.links.new(wbg.outputs["Background"], wout.inputs["Surface"])

sun_data = bpy.data.lights.new("LGT_Sun_Key", 'SUN')
sun_data.energy = 3.3
sun_data.color = (1.0, 0.925, 0.82)
sun_data.angle = math.radians(1.2)
sun = bpy.data.objects.new("LGT_Sun_Key", sun_data)
COL_RIG.objects.link(sun)
sun.rotation_euler = (math.radians(58.0), 0.0, math.radians(154.0))

fill_data = bpy.data.lights.new("LGT_Sun_Fill", 'SUN')
fill_data.energy = 0.38
fill_data.color = (0.58, 0.72, 1.0)
fill_data.angle = math.radians(10.0)
fill = bpy.data.objects.new("LGT_Sun_Fill", fill_data)
COL_RIG.objects.link(fill)
fill.rotation_euler = (math.radians(64.0), 0.0, math.radians(-58.0))

cam_data = bpy.data.cameras.new("CAM_Hero")
cam_data.lens = 38.0
cam_data.sensor_width = 36.0
cam = bpy.data.objects.new("CAM_Hero", cam_data)
COL_RIG.objects.link(cam)
cam.location = (175.0, 545.0, 212.0)
target = Vector((0.0, 18.0, 80.0))
direction = target - cam.location
cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
scene.camera = cam

cam2_data = bpy.data.cameras.new("CAM_Aerial")
cam2_data.lens = 44.0
cam2 = bpy.data.objects.new("CAM_Aerial", cam2_data)
COL_RIG.objects.link(cam2)
cam2.location = (390.0, 600.0, 450.0)
d2 = Vector((0.0, 15.0, 35.0)) - cam2.location
cam2.rotation_euler = d2.to_track_quat('-Z', 'Y').to_euler()

cam3_data = bpy.data.cameras.new("CAM_Detail")
cam3_data.lens = 72.0
cam3 = bpy.data.objects.new("CAM_Detail", cam3_data)
COL_RIG.objects.link(cam3)
cam3.location = (-34.0, 148.0, 198.0)
d3 = Vector((14.0, 34.0, 172.0)) - cam3.location
cam3.rotation_euler = d3.to_track_quat('-Z', 'Y').to_euler()

cam4_data = bpy.data.cameras.new("CAM_Power")
cam4_data.lens = 40.0
cam4_data.sensor_width = 36.0
cam4 = bpy.data.objects.new("CAM_Power", cam4_data)
COL_RIG.objects.link(cam4)
cam4.location = (90.0, 380.0, 120.0)
d4 = Vector((-40.0, 80.0, 60.0)) - cam4.location
cam4.rotation_euler = d4.to_track_quat('-Z', 'Y').to_euler()

# ----------------------------------------------------------------------------
# Render settings
# ----------------------------------------------------------------------------
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
try:
    scene.eevee.taa_render_samples = 64
except Exception:
    pass
try:
    scene.eevee.use_raytracing = True
    scene.eevee.use_fast_gi = True
    scene.eevee.fast_gi_method = 'GLOBAL_ILLUMINATION'
    scene.eevee.ray_tracing_options.use_denoise = True
except Exception:
    pass
try:
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = 0.0
except Exception:
    pass

# ----------------------------------------------------------------------------
# Stats + save
# ----------------------------------------------------------------------------
dg = bpy.context.evaluated_depsgraph_get()
tris = 0
for ob in scene.objects:
    if ob.type == 'MESH':
        me = ob.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
        ob.evaluated_get(dg).to_mesh_clear()

print("DAM_BUILD_TRIS", tris)
print("DAM_BUILD_OBJECTS", len(scene.objects))
print("DAM_BUILD_BOUNDS", [round(v, 2) for v in (min(ob.location.x for ob in scene.objects), max(ob.location.x for ob in scene.objects))])

bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)

# glTF cannot carry the procedural shader networks. Flatten Base Color to the
# material's constant colour *after* saving the .blend, so the GLB keeps tints.
for _mat in bpy.data.materials:
    if not _mat.use_nodes:
        continue
    _nt = _mat.node_tree
    _bsdf = _nt.nodes.get("Principled BSDF")
    if _bsdf is None:
        continue
    _sock = _bsdf.inputs["Base Color"]
    if _sock.is_linked:
        _base = _mat.get("base_rgb", [0.5, 0.5, 0.5])
        for _lk in list(_sock.links):
            _nt.links.remove(_lk)
        _sock.default_value = (float(_base[0]), float(_base[1]), float(_base[2]), 1.0)

# select only meshes for GLB
for ob in bpy.context.selected_objects:
    ob.select_set(False)
for ob in scene.objects:
    if ob.type == 'MESH':
        ob.select_set(True)
bpy.context.view_layer.objects.active = dam_obj
bpy.ops.export_scene.gltf(
    filepath=GLB_PATH,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
    export_yup=True,
)
print("DAM_BUILD_DONE", BLEND_PATH, GLB_PATH)
