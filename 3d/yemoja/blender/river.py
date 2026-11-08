"""The river: the shallows of the Ògùn in the late afternoon, granite domes beyond.

She is the patron of the Ògùn River, with a major cult centre at Abẹ́òkúta (Wikipedia:
Yemọja), the city named for the granite of Olúmọ Rock (stage 09's notes in this repo). Her
name joins the words for mother, child and fish, so fish swim round her feet. This bend of
the river and its domes are invented; Olúmọ Rock itself is not copied.

She stands at the origin facing -Y, ankle-deep. The river runs along X behind her, the near
bank is in front of her, toward the camera.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

import materials as mats
from common import obj_from_arrays
from dress import smoothstep
from procedural import Noise, merged, sweep

WATER_Z = 0.085
SUN = Vector((-0.62, -0.66, 0.42)).normalized()      # toward the sun: low, in front of her and to her right
HAZE = (0.52, 0.62, 0.76)


def bed_height(x, y):
    """The river bed and banks: dry sand toward the camera, her shallows, the channel, the far bank."""
    n = Noise(5)
    p = np.stack([x, y, np.zeros_like(x)], -1)
    h = np.where(y < -1.6, 0.085 + 0.045 * (-1.6 - y), 0.0)
    h = np.where((y >= -1.6) & (y < -0.9), 0.085 * (-0.9 - y) / 0.7, h)
    deep = smoothstep(y, 0.7, 9.0) * -0.95 + smoothstep(y, 19.0, 27.0) * 1.35
    h = np.where(y >= 0.7, deep, h)
    h = h + 0.012 * n.fbm(p * 1.4, 3) + 0.004 * n.fbm(p * 9.0, 2)
    # sand ripples across the current
    h = h + 0.006 * np.sin(x * 9.0 + 2.0 * n.fbm(p * 0.6, 2)) * smoothstep(y, -1.2, 0.0) * (1 - smoothstep(y, 6, 9))
    keep = smoothstep(np.hypot(x, y), 0.45, 0.9)          # level where she stands
    return h * keep


def grid_mesh(name, xs, ys, height, col):
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    Z = height(X, Y)
    verts = np.stack([X, Y, Z], -1).reshape(-1, 3)
    ny = len(ys)
    faces = [(i * ny + j, (i + 1) * ny + j, (i + 1) * ny + j + 1, i * ny + j + 1) for i in range(len(xs) - 1) for j in range(ny - 1)]
    return obj_from_arrays(name, verts, faces, col), X, Y, Z


def haze(g, colour):
    """Blend toward the sky with distance, as air does over a few hundred metres."""
    dist = g.node('CameraData').outputs['View Distance']
    f = g.math('SUBTRACT', 1.0, g.math('EXPONENT', g.math('DIVIDE', dist, -1600.0)))
    return g.mix(f, colour, HAZE)


def sand_material():
    g = mats.Graph('RiverSand')
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=3, Detail=6).outputs['Fac']
    fine = g.node('TexNoise', Vector=obj, Scale=140, Detail=6, Roughness=0.7).outputs['Fac']
    grains = g.node('TexVoronoi', Vector=obj, Scale=900, Randomness=1.0).outputs['Distance']
    wet = g.node('Attribute', attribute_name='wet', attribute_type='GEOMETRY').outputs['Fac']
    grass = g.node('Attribute', attribute_name='grass', attribute_type='GEOMETRY').outputs['Fac']
    col = g.ramp(n, [(0.3, (0.30, 0.22, 0.14)), (0.7, (0.42, 0.32, 0.21))])
    col = g.mix(g.math('MULTIPLY', fine, 0.35), col, (0.20, 0.15, 0.10))
    col = g.mix(wet, col, (0.19, 0.14, 0.09))
    blades = g.node('TexNoise', Vector=g.node('Mapping', Vector=obj, Scale=(40.0, 40.0, 4.0)).outputs[0], Scale=20, Detail=4).outputs['Fac']
    col = g.mix(grass, col, g.ramp(blades, [(0.3, (0.025, 0.055, 0.012)), (0.7, (0.10, 0.13, 0.035))]))
    normal = g.bump(g.math('ADD', g.math('MULTIPLY', fine, 0.6), g.math('ADD', g.math('MULTIPLY', grains, 0.4), g.math('MULTIPLY', g.math('MULTIPLY', blades, grass), 2.0))), 0.5, 0.0015)
    bsdf = g.node('BsdfPrincipled', Base_Color=haze(g, col), Roughness=g.mix(wet, 0.85, 0.35), Normal=normal)
    return g.finish(bsdf.outputs[0])


def water_material():
    """River water: clear on top, a green-brown that deepens with depth below."""
    g = mats.Graph('RiverWater')
    obj = g.node('TexCoord').outputs['Object']
    flow = g.node('Mapping', Vector=obj, Scale=(0.6, 1.6, 1.0)).outputs[0]
    waves = g.node('TexNoise', Vector=flow, Scale=6.0, Detail=6, Roughness=0.6).outputs['Fac']
    small = g.node('TexNoise', Vector=g.node('Mapping', Vector=obj, Scale=(1.0, 2.5, 1.0)).outputs[0], Scale=32, Detail=3).outputs['Fac']
    rings = g.node('Attribute', attribute_name='rings', attribute_type='GEOMETRY').outputs['Fac']
    h = g.math('ADD', g.math('MULTIPLY', waves, 0.7), g.math('MULTIPLY', small, 0.35))
    # in the shallows by the bank the water lies calm, broken only by the rings from her ankles
    xy = g.node('SeparateXYZ', Vector=obj).outputs
    near = g.math('SQRT', g.math('ADD', g.math('POWER', xy[0], 2.0), g.math('POWER', g.math('ADD', xy[1], 0.4), 2.0)))
    calm = g.math('ADD', 0.22, g.math('MULTIPLY', g.math('MULTIPLY', g.math('SUBTRACT', near, 0.8), 0.45, clamp=True), 0.78))
    h = g.math('ADD', g.math('MULTIPLY', h, calm), g.math('MULTIPLY', rings, 0.5))
    bsdf = g.node('BsdfPrincipled', Base_Color=(1, 1, 1, 1), Roughness=0.025, Normal=g.bump(h, 1.0, 0.016))
    bsdf.inputs['Transmission Weight'].default_value = 1.0
    bsdf.inputs['IOR'].default_value = 1.333
    # sunlight reaches the bed through the surface: shadow rays pass it, as the caustics it makes would average out
    shadow = g.node('LightPath').outputs['Is Shadow Ray']
    clear = g.node('BsdfTransparent')
    surface = g.node('MixShader', Fac=shadow)
    g.link(bsdf.outputs[0], surface.inputs[1])
    g.link(clear.outputs[0], surface.inputs[2])
    absorb = g.t.nodes.new('ShaderNodeVolumeAbsorption')
    absorb.inputs['Color'].default_value = (0.70, 0.72, 0.52, 1)
    absorb.inputs['Density'].default_value = 1.3
    g.t.links.new(absorb.outputs[0], g.out.inputs['Volume'])
    return g.finish(surface.outputs[0])


def granite_material():
    g = mats.Graph('Granite')
    obj = g.node('TexCoord').outputs['Object']
    big = g.node('TexNoise', Vector=obj, Scale=0.03, Detail=6, Roughness=0.6).outputs['Fac']
    streak_v = g.node('Mapping', Vector=obj, Scale=(0.15, 0.15, 0.012)).outputs[0]
    streaks = g.node('TexNoise', Vector=streak_v, Scale=6, Detail=4).outputs['Fac']
    fine = g.node('TexNoise', Vector=obj, Scale=2.5, Detail=8).outputs['Fac']
    col = g.ramp(big, [(0.3, (0.14, 0.12, 0.11)), (0.6, (0.22, 0.19, 0.17)), (0.8, (0.30, 0.26, 0.22))])
    col = g.mix(g.math('MULTIPLY', g.math('SUBTRACT', streaks, 0.45), 2.5, clamp=True), col, (0.06, 0.055, 0.05))
    col = g.mix(g.math('MULTIPLY', g.math('SUBTRACT', fine, 0.6), 3.0, clamp=True), col, (0.16, 0.18, 0.11))
    bsdf = g.node('BsdfPrincipled', Base_Color=haze(g, col), Roughness=0.8, Normal=g.bump(fine, 0.6, 0.5))
    return g.finish(bsdf.outputs[0])


def foliage_material(name='Foliage', low=(0.012, 0.040, 0.008), high=(0.075, 0.150, 0.025)):
    g = mats.Graph(name)
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=3.0, Detail=6).outputs['Fac']
    leafy = g.node('TexVoronoi', Vector=obj, Scale=9.0, Randomness=1.0).outputs['Distance']
    col = g.ramp(n, [(0.3, low), (0.7, high)])
    col = g.mix(g.math('MULTIPLY', leafy, 0.8), col, (0.005, 0.015, 0.004))
    bsdf = g.node('BsdfPrincipled', Base_Color=haze(g, col), Roughness=0.7, Normal=g.bump(leafy, 1.0, 0.3))
    return g.finish(bsdf.outputs[0])


def bark_material():
    g = mats.Graph('Bark')
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=g.node('Mapping', Vector=obj, Scale=(8, 8, 1)).outputs[0], Scale=4, Detail=5).outputs['Fac']
    col = g.ramp(n, [(0.3, (0.05, 0.04, 0.03)), (0.7, (0.14, 0.11, 0.08))])
    bsdf = g.node('BsdfPrincipled', Base_Color=haze(g, col), Roughness=0.85, Normal=g.bump(n, 0.6, 0.02))
    return g.finish(bsdf.outputs[0])


def fish_material():
    """Tilapia: olive-grey on the back, silver below, with faint dark bars."""
    g = mats.Graph('Fish')
    obj = g.node('TexCoord').outputs['Object']
    sep = g.node('SeparateXYZ', Vector=obj).outputs
    back = g.math('MULTIPLY', g.math('ADD', sep[2], 0.03), 16.0, clamp=True)
    bars = g.math('MULTIPLY', g.math('ADD', g.math('SINE', g.math('MULTIPLY', sep[0], 90.0)), 1.0), 0.5)
    scales = g.node('TexVoronoi', Vector=obj, Scale=600).outputs['Distance']
    col = g.mix(back, (0.30, 0.31, 0.28), (0.07, 0.085, 0.06))
    col = g.mix(g.math('MULTIPLY', bars, 0.25), col, (0.03, 0.035, 0.03))
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Metallic=0.35, Roughness=0.3, Normal=g.bump(scales, 0.3, 0.0004))
    return g.finish(bsdf.outputs[0])


# ----- the parts ----------------------------------------------------------

def make_bed(col):
    xs = np.concatenate([np.linspace(-90, -8, 60), np.linspace(-8, 8, 330)[1:-1], np.linspace(8, 90, 60)])
    ys = np.concatenate([np.linspace(-12, -3, 40), np.linspace(-3, 6, 300)[1:-1], np.linspace(6, 60, 90)])
    ob, X, Y, Z = grid_mesh('RiverBed', xs, ys, bed_height, col)
    wet = np.clip((WATER_Z + 0.03 - Z) / 0.03, 0, 1)
    ob.data.attributes.new('wet', 'FLOAT', 'POINT').data.foreach_set('value', wet.ravel().astype(np.float32))
    grass = smoothstep(Y, 20.5, 25.0) * smoothstep(Z, WATER_Z + 0.02, WATER_Z + 0.10) + smoothstep(-Y, 6.0, 9.0)
    ob.data.attributes.new('grass', 'FLOAT', 'POINT').data.foreach_set('value', np.clip(grass, 0, 1).ravel().astype(np.float32))
    ob.data.materials.append(sand_material())
    return ob


def make_water(col, feet):
    """A closed slab of water from the surface down past the bed, rings spreading from her ankles."""
    xs = np.linspace(-90, 90, 361)
    ys = np.linspace(-1.75, 60, 300)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    top = np.stack([X, Y, np.full_like(X, WATER_Z)], -1).reshape(-1, 3)
    rings = np.zeros(X.shape)
    for fx, fy in feet:
        r = np.hypot(X - fx, Y - fy)
        rings += np.sin(r * 120) * np.exp(-r / 0.12) * smoothstep(r, 0.04, 0.07)
    nx, ny = len(xs), len(ys)
    faces = [(i * ny + j, (i + 1) * ny + j, (i + 1) * ny + j + 1, i * ny + j + 1) for i in range(nx - 1) for j in range(ny - 1)]
    # close it: walls down from the grid's edge to a ring below the bed, and a floor across that ring
    loop = [i * ny for i in range(nx)] + [(nx - 1) * ny + j for j in range(1, ny)] + \
           [i * ny + ny - 1 for i in range(nx - 2, -1, -1)] + [j for j in range(ny - 2, 0, -1)]
    base = len(top)
    ring = top[loop] * np.array([1, 1, 0]) + np.array([0, 0, -1.6])
    verts = np.vstack([top, ring])
    m = len(loop)
    for k in range(m):
        a, b = loop[k], loop[(k + 1) % m]
        faces.append((b, a, base + k, base + (k + 1) % m))
    faces.append(tuple(base + k for k in range(m - 1, -1, -1)))
    ob = obj_from_arrays('RiverWater', verts, faces, col, smooth=False)
    ob.data.attributes.new('rings', 'FLOAT', 'POINT').data.foreach_set('value', np.concatenate([rings.ravel(), np.zeros(m)]).astype(np.float32))
    ob.data.materials.append(water_material())
    return ob


def fish_mesh(length, seed):
    """A tilapia's body: deep and flat-sided, a forked dorsal fin, a broad tail. Along +X, head forward."""
    n = Noise(seed)
    rows, cols = 26, 18
    verts = []
    for i in range(rows):
        t = i / (rows - 1)
        x = (0.5 - t) * length
        hgt = length * 0.21 * math.sin(math.pi * min(t * 1.08, 1)) ** 0.75 + 0.002
        wid = length * 0.065 * math.sin(math.pi * min(t * 1.1, 1)) ** 0.9 + 0.001
        for j in range(cols):
            a = 2 * math.pi * j / cols
            verts.append((x, math.cos(a) * wid, math.sin(a) * hgt * (1 + 0.04 * float(n(np.array([t * 4, a, seed * 1.0]))))))
    faces = [(i * cols + j, i * cols + (j + 1) % cols, (i + 1) * cols + (j + 1) % cols, (i + 1) * cols + j) for i in range(rows - 1) for j in range(cols)]
    body = (np.array(verts), faces)
    tail_x = -0.5 * length
    tail = (np.array([(tail_x + 0.004, 0, 0.012), (tail_x - length * 0.22, 0, 0.040), (tail_x - length * 0.17, 0, 0.0),
                      (tail_x - length * 0.22, 0, -0.040), (tail_x + 0.004, 0, -0.012)]) * np.array([1, 1, length / 0.14]), [(0, 1, 2), (0, 2, 4), (2, 3, 4)])
    dorsal = (np.array([(length * 0.25, 0, length * 0.19), (-length * 0.35, 0, length * 0.17), (-length * 0.30, 0, length * 0.27), (length * 0.18, 0, length * 0.25)]),
              [(0, 1, 2, 3)])
    return merged([body, tail, dorsal])


def make_fish(col, rng, count=7):
    """Her children: tilapia turning in the shallows round her feet."""
    parts = []
    material = fish_material()
    for k in range(count):
        # in the clear water in front of her, where the shallows are calm
        x = -0.45 + 0.95 * (k + rng.uniform(0.1, 0.9)) / count
        y = rng.uniform(-0.95, -0.32)
        ang = math.atan2(y + 0.1, x)
        depth = float(WATER_Z - 0.038 - rng.uniform(0.0, 0.010))
        L = rng.uniform(0.14, 0.19)
        v, f = fish_mesh(L, int(rng.integers(1, 999)))
        heading = ang + math.pi / 2 * (1 if rng.random() < 0.5 else -1) + rng.normal(0, 0.4)
        R = np.array(Matrix.Rotation(heading, 3, 'Z')) @ np.array(Matrix.Rotation(rng.normal(0, 0.08), 3, 'X'))
        parts.append(((R @ v.T).T + np.array([x, y, depth]), f))
    v, f = merged(parts)
    ob = obj_from_arrays('Fish', v, f, col)
    ob.data.materials.append(material)
    return ob


def dome_mesh(seed, rx, ry, h, rows=60, cols=120):
    """A granite inselberg: a bald dome with sheets peeling off its flanks."""
    n = Noise(seed)
    verts = []
    for i in range(rows):
        el = (math.pi / 2) * i / (rows - 1)
        for j in range(cols):
            az = 2 * math.pi * j / cols
            d = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
            sheet = 0.035 * math.floor((1 - math.sin(el)) * 6 + 0.8 * float(n(d * 2 + seed))) / 6
            r = 1 + 0.10 * float(n.fbm(d * 2.4 + seed, 4)) + sheet
            verts.append((d[0] * rx * r, d[1] * ry * r, d[2] * h * r ** 1.3 - 6))
    faces = [(i * cols + j, i * cols + (j + 1) % cols, (i + 1) * cols + (j + 1) % cols, (i + 1) * cols + j) for i in range(rows - 1) for j in range(cols)]
    return np.array(verts), faces


def make_domes(col):
    parts = []
    for seed, (x, y, rx, ry, h) in enumerate(((-75, 210, 95, 80, 58), (95, 330, 150, 120, 80), (250, 260, 80, 70, 42), (-280, 420, 150, 110, 66))):
        v, f = dome_mesh(seed + 3, rx, ry, h)
        parts.append((v + np.array([x, y, 0]), f))
    v, f = merged(parts)
    ob = obj_from_arrays('Domes', v, f, col)
    ob.data.materials.append(granite_material())
    return ob


def crown_mesh(seed, radius, leaves=9000):
    """A crown of leaves: small cards scattered through a few lumps of the crown's volume, thickest at its skin."""
    rng = np.random.default_rng(seed)
    lumps = [rng.normal(0, radius * 0.32, 3) * np.array([1, 1, 0.55]) for _ in range(6)]
    verts, faces = [], []
    for k in range(leaves):
        c = lumps[k % len(lumps)]
        d = rng.normal(0, 1, 3)
        d /= np.linalg.norm(d)
        p = c + d * radius * 0.62 * rng.uniform(0.55, 1.0) ** 0.35 * np.array([1, 1, 0.75])
        size = rng.uniform(0.14, 0.26)
        a = rng.normal(0, 1, 3)
        a -= a.dot(d) * d
        a /= np.linalg.norm(a)
        b = np.cross(d, a)
        q = [p - a * size * 0.5, p + b * size * 0.35, p + a * size * 0.5, p - b * size * 0.35]
        base = len(verts)
        verts += q
        faces.append((base, base + 1, base + 2, base + 3))
    return np.array(verts), faces


def palm_mesh(seed, height):
    """An oil palm: a leaning trunk and a crown of arching fronds, each a rachis with leaflets."""
    rng = np.random.default_rng(seed)
    lean = rng.normal(0, 0.06, 2)
    t = np.linspace(0, 1, 16)
    trunk = np.stack([lean[0] * height * t ** 1.5, lean[1] * height * t ** 1.5, height * t], 1)
    parts = [sweep(trunk, np.linspace(0.30, 0.22, 16), sides=10)]
    top = trunk[-1]
    fronds = []
    for k in range(14):
        az = 2 * math.pi * k / 14 + rng.normal(0, 0.1)
        rise = rng.uniform(-0.1, 0.7)
        L = rng.uniform(4.5, 6.0)
        s = np.linspace(0, 1, 18)
        out = np.array([math.cos(az), math.sin(az), 0])
        path = top + out[None] * (L * s)[:, None] + np.array([0, 0, 1.0])[None] * (L * (rise * s - 0.55 * s ** 2))[:, None]
        side = np.cross(out, (0, 0, 1.0))
        for i in range(2, 17):
            for sgn in (1, -1):
                a = path[i]
                b = a + side * sgn * 0.95 * (1 - s[i]) ** 0.4 + np.array([0, 0, -0.40]) + out * 0.30
                fronds.append(np.array([a, b, b + out * 0.16, a + out * 0.16]))
        parts.append(sweep(path, 0.05, sides=4))
    fv = np.concatenate(fronds)
    ff = [(4 * i, 4 * i + 1, 4 * i + 2, 4 * i + 3) for i in range(len(fronds))]
    trunk_parts = merged(parts)
    return trunk_parts, (fv, ff)


def make_trees(col, rng):
    """Trees and oil palms along the far bank and up the land behind it."""
    bark, leaves, palm_leaves = bark_material(), foliage_material(), foliage_material('PalmLeaves', (0.020, 0.050, 0.010), (0.090, 0.150, 0.030))
    protos = []
    for seed in range(4):
        v, f = crown_mesh(seed + 2, rng.uniform(3.6, 5.6))
        crown = obj_from_arrays(f'CrownProto.{seed}', v, f, col)
        crown.data.materials.append(leaves)
        th = rng.uniform(3.5, 7.0)
        tv, tf = sweep(np.array([(0, 0, -0.5), (0.3, 0.1, th * 0.6), (0.2, -0.2, th)]), np.array([0.50, 0.32, 0.24]), sides=10)
        trunk = obj_from_arrays(f'TrunkProto.{seed}', tv, tf, col)
        trunk.data.materials.append(bark)
        protos.append(('tree', crown, trunk, th))
    for seed in range(3):
        (tv, tf), (fv, ff) = palm_mesh(seed + 20, rng.uniform(9, 14))
        trunk = obj_from_arrays(f'PalmTrunkProto.{seed}', tv, tf, col)
        trunk.data.materials.append(bark)
        fr = obj_from_arrays(f'PalmFrondProto.{seed}', fv, ff, col)
        fr.data.materials.append(palm_leaves)
        protos.append(('palm', fr, trunk, 0.0))
    for seed in range(3):
        v, f = crown_mesh(seed + 40, rng.uniform(0.9, 1.5), leaves=2600)
        shrub = obj_from_arrays(f'ShrubProto.{seed}', v, f, col)
        shrub.data.materials.append(leaves)
        protos.append(('shrub', shrub, None, 0.0))
    placed = 0
    for _ in range(170):
        kind, a, b, th = protos[-1 - int(rng.integers(0, 3))]
        x, y = rng.uniform(-150, 150), rng.uniform(22.5, 40)
        z = float(bed_height(np.array([x]), np.array([y]))[0])
        s = rng.uniform(0.7, 1.4)
        ob = bpy.data.objects.new('Shrub', a.data)
        col.objects.link(ob)
        ob.matrix_world = Matrix.Translation((x, y, z + 0.6 * s)) @ Matrix.Rotation(rng.uniform(0, 6.28), 4, 'Z') @ Matrix.Diagonal((s, s, s * 0.8, 1))
    trees = [p for p in protos if p[0] != 'shrub']
    for _ in range(300):
        x = rng.uniform(-170, 170)
        y = 34 + rng.exponential(30) if rng.random() < 0.9 else rng.uniform(-30, -10)
        if y > 170 or (y > 0 and rng.random() < 0.35):
            continue
        if abs(x) < 6 and y < 0:
            continue
        kind, a, b, th = trees[int(rng.integers(0, len(trees)))]
        z = float(bed_height(np.array([x]), np.array([y]))[0]) if y < 60 else 1.4
        s = rng.uniform(0.8, 1.3)
        for src in (a, b):
            ob = bpy.data.objects.new(src.name.replace('Proto', ''), src.data)
            col.objects.link(ob)
            ob.matrix_world = Matrix.Translation((x, y, z + (th if (kind == 'tree' and src is a) else 0))) @ Matrix.Rotation(rng.uniform(0, 6.28), 4, 'Z') @ Matrix.Diagonal((s, s, s, 1))
        placed += 1
    for kind, a, b, th in protos:
        for ob in (a, b):
            if ob is not None:
                bpy.data.objects.remove(ob)
    return placed


def make_far_land(col):
    """The land behind the far bank, rising gently to the foot of the domes."""
    n = Noise(41)

    def h(X, Y):
        p = np.stack([X * 0.01, Y * 0.01, np.zeros_like(X)], -1)
        return 1.4 + 6.0 * smoothstep(Y, 60, 400) + 3.0 * n.fbm(p, 4)
    ob, X, Y, Z = grid_mesh('FarLand', np.linspace(-700, 700, 120), np.linspace(55, 700, 80), h, col)
    g = mats.Graph('FarLand')
    obj = g.node('TexCoord').outputs['Object']
    nz = g.node('TexNoise', Vector=obj, Scale=0.05, Detail=6).outputs['Fac']
    colr = g.ramp(nz, [(0.35, (0.03, 0.06, 0.015)), (0.65, (0.10, 0.12, 0.04))])
    bsdf = g.node('BsdfPrincipled', Base_Color=haze(g, colr), Roughness=0.9)
    ob.data.materials.append(g.finish(bsdf.outputs[0]))
    return ob


def make_reeds(col, rng):
    """Grass and reeds along the near bank's edge, short of the camera."""
    strands = []
    for _ in range(1600):
        x = rng.uniform(-9, 9)
        if abs(x) < 1.6:
            continue
        y = rng.uniform(-2.4, -1.5)
        base = np.array([x, y, float(bed_height(np.array([x]), np.array([y]))[0])])
        L = rng.uniform(0.25, 0.7)
        bend = rng.normal(0, 0.25, 2)
        s = np.linspace(0, 1, 6)
        strands.append(base + np.stack([bend[0] * s ** 2 * L, bend[1] * s ** 2 * L, s * L], 1))
    from procedural import add_curves
    g = mats.Graph('Reed')
    bsdf = g.node('BsdfPrincipled', Base_Color=(0.10, 0.12, 0.04, 1), Roughness=0.6)
    return add_curves('Reeds', np.array(strands, np.float32), 0.0016, 0.0003, col, g.finish(bsdf.outputs[0]))


def make_sky(sun=SUN):
    """A clear late-afternoon sky from Blender's physical sky model, its sun put out: a lamp stands for it."""
    sc = bpy.context.scene
    world = bpy.data.worlds.get('Afternoon') or bpy.data.worlds.new('Afternoon')
    sc.world = world
    world.use_nodes = True
    t = world.node_tree
    t.nodes.clear()
    out = t.nodes.new('ShaderNodeOutputWorld')
    bg = t.nodes.new('ShaderNodeBackground')
    sky = t.nodes.new('ShaderNodeTexSky')
    sky.sky_type = 'NISHITA'
    sky.sun_disc = False
    sky.sun_elevation = math.asin(sun.z)
    sky.sun_rotation = math.atan2(sun.x, -sun.y) % (2 * math.pi)
    sky.air_density = 1.2
    sky.dust_density = 2.0
    t.links.new(sky.outputs[0], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 0.16
    t.links.new(bg.outputs[0], out.inputs['Surface'])
    return world


def build(far, near, feet):
    rng = np.random.default_rng(11)
    make_bed(near)
    make_water(near, feet)
    make_fish(near, rng)
    make_reeds(near, rng)
    make_far_land(far)
    make_domes(far)
    print('trees', make_trees(far, rng), flush=True)
    make_sky()
