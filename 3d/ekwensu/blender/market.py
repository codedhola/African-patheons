"""The market at dusk: the day's trading over, lamps lit, a crescent moon over the trees.

Ekwensu is invoked in difficult bargains, and he was once honoured among the benevolent lunar
deities (Wikipedia: Ekwensu), so he stands in an Igbo market square as it empties at dusk, under a
young moon. The place, its stalls and its wares are this study's: thatched stalls on poles,
baskets, pots and produce left on the tables, clay lamps, and the bush beyond.

He stands at the origin facing -Y. The sun has set behind the stalls at his back, and the moon
hangs in the glow above them.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

import materials as mats
from common import obj_from_arrays
from dress import smoothstep
from procedural import Noise, add_curves, merged, rock_mesh, sweep

SUN = Vector((0.30, 0.95, -0.035)).normalized()       # toward the sun: just set, behind him and to his left
MOON = Vector((-0.20, 0.945, 0.26)).normalized()      # a young moon follows the sun down, 15 degrees up, over his right shoulder
HAZE = (0.30, 0.27, 0.32)


def haze(g, colour, distance=700.0):
    dist = g.node('CameraData').outputs['View Distance']
    f = g.math('SUBTRACT', 1.0, g.math('EXPONENT', g.math('DIVIDE', dist, -distance)))
    return g.mix(f, colour, HAZE)


def earth_material():
    """The square: red earth beaten hard by feet, dusty, scattered with husks and leaves."""
    g = mats.Graph('MarketEarth')
    obj = g.node('TexCoord').outputs['Object']
    big = g.node('TexNoise', Vector=obj, Scale=0.6, Detail=6).outputs['Fac']
    mid = g.node('TexNoise', Vector=obj, Scale=6.0, Detail=8, Roughness=0.62).outputs['Fac']
    fine = g.node('TexNoise', Vector=obj, Scale=90, Detail=6, Roughness=0.7).outputs['Fac']
    grit = g.node('TexVoronoi', Vector=obj, Scale=240, Randomness=1.0).outputs['Distance']
    prints = g.node('TexVoronoi', Vector=g.node('Mapping', Vector=obj, Scale=(1.0, 2.6, 1.0)).outputs[0], Scale=5.0).outputs['Distance']
    col = g.ramp(big, [(0.25, (0.16, 0.075, 0.040)), (0.55, (0.24, 0.12, 0.065)), (0.8, (0.30, 0.17, 0.10))])
    col = g.mix(g.math('MULTIPLY', mid, 0.45), col, (0.12, 0.065, 0.040))
    h = g.math('ADD', g.math('MULTIPLY', mid, 0.7), g.math('ADD', g.math('MULTIPLY', fine, 0.4), g.math('ADD', g.math('MULTIPLY', grit, 0.25), g.math('MULTIPLY', prints, 0.3))))
    bsdf = g.node('BsdfPrincipled', Base_Color=haze(g, col), Roughness=g.math('ADD', 0.80, g.math('MULTIPLY', fine, 0.12)), Normal=g.bump(h, 0.6, 0.005))
    return g.finish(bsdf.outputs[0])


def wood_material(name='Poles'):
    g = mats.Graph(name)
    obj = g.node('TexCoord').outputs['Object']
    grain = g.node('TexWave', Vector=g.node('Mapping', Vector=obj, Scale=(7, 7, 0.4)).outputs[0], Scale=4.0, Distortion=8.0, Detail=5, wave_type='RINGS').outputs['Fac']
    col = g.ramp(grain, [(0.2, (0.045, 0.030, 0.018)), (0.7, (0.12, 0.085, 0.050)), (1.0, (0.17, 0.12, 0.07))])
    bsdf = g.node('BsdfPrincipled', Base_Color=haze(g, col), Roughness=0.8, Normal=g.bump(grain, 0.5, 0.004))
    return g.finish(bsdf.outputs[0])


def thatch_material():
    """Layered dry palm fronds: straw and grey-brown, ragged along the fronds."""
    g = mats.Graph('Thatch')
    obj = g.node('TexCoord').outputs['Object']
    lines = g.node('TexNoise', Vector=g.node('Mapping', Vector=obj, Scale=(1.0, 30.0, 1.0)).outputs[0], Scale=3.0, Detail=6).outputs['Fac']
    patch = g.node('TexNoise', Vector=obj, Scale=1.5, Detail=4).outputs['Fac']
    col = g.ramp(g.math('ADD', g.math('MULTIPLY', lines, 0.6), g.math('MULTIPLY', patch, 0.4)),
                 [(0.3, (0.10, 0.075, 0.045)), (0.6, (0.24, 0.18, 0.10)), (0.85, (0.36, 0.28, 0.16))])
    bsdf = g.node('BsdfPrincipled', Base_Color=haze(g, col), Roughness=0.9, Normal=g.bump(lines, 0.9, 0.012))
    return g.finish(bsdf.outputs[0])


def basket_material():
    """Coiled grass baskets: ridges of coil round the basket, the stitches that bind them, straw going grey."""
    g = mats.Graph('Basket')
    obj = g.node('TexCoord').outputs['Object']
    z = g.node('SeparateXYZ', Vector=obj).outputs[2]
    coil = g.math('ABSOLUTE', g.math('SINE', g.math('MULTIPLY', z, 2 * math.pi / 0.014)))
    stitch = g.node('TexVoronoi', Vector=g.node('Mapping', Vector=obj, Scale=(1.0, 1.0, 3.0)).outputs[0], Scale=90, feature='F1').outputs['Distance']
    stitch = g.math('LESS_THAN', stitch, 0.18)
    n = g.node('TexNoise', Vector=obj, Scale=30, Detail=4).outputs['Fac']
    col = g.ramp(n, [(0.3, (0.17, 0.11, 0.05)), (0.7, (0.36, 0.25, 0.12))])
    col = g.mix(g.math('MULTIPLY', g.math('SUBTRACT', 1.0, coil), 0.5), col, (0.08, 0.05, 0.025))
    col = g.mix(g.math('MULTIPLY', stitch, 0.6), col, (0.10, 0.06, 0.03))
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.75, Normal=g.bump(g.math('ADD', coil, g.math('MULTIPLY', stitch, 0.4)), 0.7, 0.002))
    return g.finish(bsdf.outputs[0])


def clay_material():
    g = mats.Graph('PotClay')
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=14, Detail=6).outputs['Fac']
    col = g.ramp(n, [(0.3, (0.20, 0.09, 0.045)), (0.7, (0.32, 0.15, 0.075))])
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.7, Normal=g.bump(n, 0.3, 0.002))
    return g.finish(bsdf.outputs[0])


def produce_material(name, low, high, rough=0.45):
    g = mats.Graph(name)
    obj = g.node('TexCoord').outputs['Object']
    pick = g.node('Attribute', attribute_name='bead', attribute_type='GEOMETRY').outputs['Fac']
    n = g.node('TexNoise', Vector=obj, Scale=120, Detail=3).outputs['Fac']
    col = g.mix(pick, low, high)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=g.math('ADD', rough, g.math('MULTIPLY', n, 0.15)), Normal=g.bump(n, 0.2, 0.0008))
    return g.finish(bsdf.outputs[0])


def foliage_material(name='Foliage', low=(0.010, 0.030, 0.008), high=(0.055, 0.095, 0.022)):
    g = mats.Graph(name)
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=3.0, Detail=6).outputs['Fac']
    col = g.ramp(n, [(0.3, low), (0.7, high)])
    bsdf = g.node('BsdfPrincipled', Base_Color=haze(g, col), Roughness=0.7)
    return g.finish(bsdf.outputs[0])


def lathe(profile, sides=40):
    pts = np.array(profile, float)
    a = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    verts = np.stack([np.outer(pts[:, 0], np.cos(a)), np.outer(pts[:, 0], np.sin(a)), np.tile(pts[:, 1:2], (1, sides))], -1).reshape(-1, 3)
    rows = len(pts)
    faces = [(i * sides + j, i * sides + (j + 1) % sides, (i + 1) * sides + (j + 1) % sides, (i + 1) * sides + j) for i in range(rows - 1) for j in range(sides)]
    return verts, faces


# ----- the parts ----------------------------------------------------------

def make_ground(col):
    n = Noise(3)
    xs, ys = np.linspace(-60, 60, 240), np.linspace(-30, 90, 240)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    p = np.stack([X, Y, np.zeros_like(X)], -1)
    Z = 0.012 * n.fbm(p * 0.6, 3) + 0.004 * n.fbm(p * 6, 2)
    Z = Z * smoothstep(np.hypot(X, Y), 0.4, 1.0) + 0.6 * smoothstep(Y, 25, 80) * (0.5 + 0.5 * n.fbm(p * 0.05, 2))
    verts = np.stack([X, Y, Z], -1).reshape(-1, 3)
    ny = len(ys)
    faces = [(i * ny + j, (i + 1) * ny + j, (i + 1) * ny + j + 1, i * ny + j + 1) for i in range(len(xs) - 1) for j in range(ny - 1)]
    ob = obj_from_arrays('Ground', verts, faces, col)
    ob.data.materials.append(earth_material())
    return ob


def make_litter(col, rng):
    """Husks, dry leaves and scraps of the day, kicked about the square."""
    parts = []
    for _ in range(700):
        r = abs(rng.normal(0, 3.0)) + 0.35
        a = rng.uniform(0, 2 * np.pi)
        x, y = math.cos(a) * r, math.sin(a) * r * 0.9 + 0.6
        if abs(x) < 0.32 and abs(y + 0.05) < 0.25 or math.hypot(x - 0.34, y + 0.40) < 0.25:      # his feet, and the tortoise
            continue
        L, W = rng.uniform(0.02, 0.07), rng.uniform(0.008, 0.03)
        ang = rng.uniform(0, 6.28)
        c, s = math.cos(ang), math.sin(ang)
        q = np.array([(-L, -W), (L, -W * 0.6), (L * 1.1, W * 0.4), (-L * 0.8, W)]) / 2
        v = np.stack([x + q[:, 0] * c - q[:, 1] * s, y + q[:, 0] * s + q[:, 1] * c, np.full(4, 0.003) + rng.uniform(0, 0.004, 4)], 1)
        parts.append((v, [(0, 1, 2, 3)]))
    v, f = merged(parts)
    ob = obj_from_arrays('Litter', v, f, col)
    g = mats.Graph('Litter')
    n = g.node('TexNoise', Vector=g.node('TexCoord').outputs['Object'], Scale=8, Detail=3).outputs['Fac']
    bsdf = g.node('BsdfPrincipled', Base_Color=g.ramp(n, [(0.3, (0.10, 0.06, 0.03)), (0.7, (0.30, 0.20, 0.09))]), Roughness=0.8)
    ob.data.materials.append(g.finish(bsdf.outputs[0]))
    return ob


LAYOUT = [   # centre, yaw, and which front corner of the table holds a lamp: +1 its right, -1 its left, 0 none
    ((-2.45, 2.9), 12, 1), ((2.60, 3.3), -14, -1),           # either side of him, leaving the way open behind
    ((-5.9, 0.6), 42, 1), ((6.4, 0.0), -46, -1),             # at the sides of the square, turned in to it
    ((-1.0, 9.2), 3, 1), ((2.8, 10.4), -5, -1),              # across the square, behind him
    ((-4.8, 8.4), 10, 0), ((6.2, 7.6), -20, 0),
]


def eave(rng, e0, e1, sdir, spacing, reach):
    """Thatch at one edge of a roof: strands lying on it, over the edge, and hanging ragged below."""
    e0, e1 = np.asarray(e0, float), np.asarray(e1, float)
    sdir = np.asarray(sdir, float) / np.linalg.norm(sdir)
    n = int(np.linalg.norm(e1 - e0) / spacing)
    strands = []
    t = np.linspace(0, 1, 8)
    for k in range(n):
        p = e0 + (e1 - e0) * rng.uniform(0, 1)
        a, b = rng.uniform(0.10, 0.26), rng.uniform(0.01, 0.07)
        h = rng.uniform(0.04, reach) * (0.35 if rng.random() < 0.25 else 1.0)
        p0 = p - sdir * a + np.array([0, 0, 0.012])
        p1 = p + sdir * b + np.array([0, 0, 0.004])
        p2 = p + sdir * (b + rng.uniform(0.0, 0.05)) + np.array([0, 0, -h])
        # a quadratic from on the roof, over the edge and down, with a little sideways stray
        q = (1 - t)[:, None] ** 2 * p0 + 2 * ((1 - t) * t)[:, None] * p1 + (t ** 2)[:, None] * p2
        q += rng.normal(0, 0.006, 3) * (t ** 2)[:, None]
        strands.append(q)
    return strands


def stall(rng, at, yaw, lamp_side, wares):
    """A market stall: four poles, a roof of thatch sloping down to the square with its eaves hanging ragged,
    a table of laid sticks, and the day's goods left on it."""
    parts_wood, parts_thatch = [], []
    w, d = rng.uniform(1.9, 2.4), rng.uniform(1.4, 1.7)
    hf, hb = rng.uniform(1.80, 1.92), rng.uniform(2.05, 2.22)          # low at the front, high at the back
    for x, y, h in ((-w / 2, -d / 2, hf), (w / 2, -d / 2, hf), (w / 2, d / 2, hb), (-w / 2, d / 2, hb)):
        parts_wood.append(sweep(np.array([(x, y, -0.05), (x + rng.normal(0, 0.02), y + rng.normal(0, 0.02), h * 0.5), (x, y, h + 0.03)]), 0.045, sides=8))
    for y, h in ((-d / 2, hf), (d / 2, hb)):
        parts_wood.append(sweep(np.array([(-w / 2 - 0.15, y, h), (w / 2 + 0.15, y, h)]), 0.035, sides=6))
    ext = 0.32                                                         # the roof overhangs its frame
    roof_z = lambda y: hf + (hb - hf) * (y + d / 2) / d + 0.085
    for x in np.linspace(-w / 2 + 0.05, w / 2 - 0.05, int(w / 0.42) + 1):     # rafters, front to back
        parts_wood.append(sweep(np.array([(x, -d / 2 - ext + 0.05, roof_z(-d / 2 - ext + 0.05) - 0.03),
                                          (x + rng.normal(0, 0.015), d / 2 + ext - 0.05, roof_z(d / 2 + ext - 0.05) - 0.03)]), 0.02, sides=5))
    n = Noise(int(rng.integers(1, 999)))
    us, vs = np.linspace(-w / 2 - ext, w / 2 + ext, 30), np.linspace(-d / 2 - ext, d / 2 + ext, 16)
    U, V = np.meshgrid(us, vs, indexing='ij')
    Z = roof_z(V) + 0.008 * n.fbm(np.stack([U, V, np.zeros_like(U)], -1) * 2, 2)
    tv = np.stack([U, V, Z], -1).reshape(-1, 3)
    nv = len(vs)
    tf = [(i * nv + j, (i + 1) * nv + j, (i + 1) * nv + j + 1, i * nv + j + 1) for i in range(len(us) - 1) for j in range(nv - 1)]
    parts_thatch.append((tv, tf))
    # the eaves: along the low front, and down both sides
    fy, by = -d / 2 - ext, d / 2 + ext
    fl = np.array([-w / 2 - ext, fy, roof_z(fy)])
    fr = np.array([w / 2 + ext, fy, roof_z(fy)])
    slope = np.array([0, -1.0, -(hb - hf) / d])
    strands = eave(rng, fl, fr, slope, 0.0032, 0.30)
    for sx in (-1, 1):
        x = sx * (w / 2 + ext)
        strands += eave(rng, (x, fy + 0.05, roof_z(fy + 0.05)), (x, by, roof_z(by)), (sx, 0, -0.18), 0.0045, 0.20)
    # the table: a frame and a top of laid sticks
    th = 0.78
    for x in (-w / 2 + 0.15, w / 2 - 0.15):
        for y in (-d / 2 + 0.25, d / 2 - 0.35):
            parts_wood.append(sweep(np.array([(x, y, 0.0), (x, y, th)]), 0.025, sides=6))
    for k in range(18):
        y = -d / 2 + 0.22 + k * (d - 0.55) / 17
        parts_wood.append(sweep(np.array([(-w / 2 + 0.1, y, th + 0.02), (w / 2 - 0.1, y + rng.normal(0, 0.01), th + 0.02)]), 0.018, sides=5))
    M = np.array(Matrix.Translation(Vector((*at, 0.0))) @ Matrix.Rotation(math.radians(yaw), 4, 'Z'))

    def tf_(v):
        return np.asarray(v) @ M[:3, :3].T + M[:3, 3]
    out = []
    v, f = merged(parts_wood)
    out.append((tf_(v), f, 'Poles'))
    v, f = merged(parts_thatch)
    out.append((tf_(v), f, 'Thatch'))
    for v, f, m in wares(rng, w, d, th, lamp_side):
        out.append((tf_(v), f, m))
    spot = None
    if lamp_side:
        spot = tuple(tf_(np.array([[lamp_side * (w / 2 - 0.30), -d / 2 + 0.32, th + 0.036]]))[0])
    return out, [tf_(q) for q in strands], spot


def make_stalls(col, rng):
    mats_by = dict(Poles=wood_material(), Thatch=thatch_material(), Basket=basket_material(), Clay=clay_material(),
                   Peppers=produce_material('Peppers', (0.30, 0.02, 0.01), (0.45, 0.08, 0.02), 0.3),
                   Kola=produce_material('Kola', (0.22, 0.06, 0.05), (0.40, 0.25, 0.16), 0.4),
                   Yams=produce_material('YamSkin', (0.08, 0.05, 0.03), (0.16, 0.10, 0.06), 0.85))

    def wares(rng, w, d, th, lamp_side):
        items = []
        for k in range(int(rng.integers(3, 6))):
            x = rng.uniform(-w / 2 + 0.3, w / 2 - 0.3)
            y = rng.uniform(-d / 2 + 0.35, d / 2 - 0.45)
            if lamp_side and x * lamp_side > w / 2 - 0.65 and y < -d / 2 + 0.65:        # that corner is kept for the lamp
                continue
            kind = rng.random()
            if kind < 0.35:          # a round basket, heaped
                r = rng.uniform(0.16, 0.24)
                v, f = lathe([(r * 0.7, 0.0), (r, 0.12), (r * 1.03, 0.14)], 30)
                items.append((v + np.array([x, y, th + 0.04]), f, 'Basket'))
                heap = []
                for _ in range(60):
                    rr = r * 0.85 * math.sqrt(rng.random())
                    a = rng.uniform(0, 6.28)
                    bv, bf = rock_mesh(int(rng.integers(1, 9999)))
                    s = rng.uniform(0.015, 0.025)
                    heap.append((bv * s + np.array([x + math.cos(a) * rr, y + math.sin(a) * rr, th + 0.14 + 0.06 * (1 - rr / r) + rng.uniform(0, 0.02)]), bf))
                hv, hf = merged(heap)
                items.append((hv, hf, 'Peppers' if rng.random() < 0.5 else 'Kola'))
            elif kind < 0.65:        # a clay pot
                v, f = lathe([(0.0, 0.0), (0.10, 0.02), (0.15, 0.12), (0.14, 0.22), (0.08, 0.28), (0.09, 0.31), (0.075, 0.31)], 30)
                items.append((v * rng.uniform(0.8, 1.15) + np.array([x, y, th + 0.04]), f, 'Clay'))
            else:                    # yams laid side by side
                for j in range(int(rng.integers(3, 6))):
                    bv, bf = rock_mesh(int(rng.integers(1, 9999)))
                    s = np.array([rng.uniform(0.16, 0.24), rng.uniform(0.055, 0.075), rng.uniform(0.05, 0.07)])
                    items.append((bv * s + np.array([x + j * 0.02, y + j * 0.13 - 0.2, th + 0.09]), bf, 'Yams'))
        return items

    placed, strands, spots = [], [], []
    for at, yaw, lamp_side in LAYOUT:
        parts, eaves, spot = stall(rng, at, yaw, lamp_side, wares)
        placed += parts
        strands += eaves
        if spot:
            spots.append(spot)
    by_mat = {}
    for v, f, m in placed:
        by_mat.setdefault(m, []).append((v, f))
    for name, parts in by_mat.items():
        v, f = merged(parts)
        ob = obj_from_arrays(f'Stalls.{name}', v, f, col)
        ob.data.materials.append(mats_by[name])
    # the hanging thatch, all the stalls' eaves in one set of curves, each strand its own shade of dry palm
    g = mats.Graph('ThatchStraw')
    tint = g.node('Attribute', attribute_name='tint', attribute_type='GEOMETRY').outputs['Fac']
    col_ = g.ramp(tint, [(0.0, (0.07, 0.05, 0.03)), (0.5, (0.17, 0.12, 0.065)), (1.0, (0.30, 0.22, 0.12))])
    bsdf = g.node('BsdfPrincipled', Base_Color=haze(g, col_), Roughness=0.8)
    straw = add_curves('ThatchEaves', np.array(strands, np.float32), 0.0016, 0.0007, col, g.finish(bsdf.outputs[0]))
    attr = straw.data.attributes.new('tint', 'FLOAT', 'CURVE')
    attr.data.foreach_set('value', rng.random(len(strands)).astype(np.float32))
    print('thatch strands', len(strands), flush=True)
    return len(placed), spots


def crown_mesh(seed, radius, leaves=7000):
    rng = np.random.default_rng(seed)
    lumps = [rng.normal(0, radius * 0.32, 3) * np.array([1, 1, 0.55]) for _ in range(7)]
    verts, faces = [], []
    for k in range(leaves):
        c = lumps[k % len(lumps)]
        d = rng.normal(0, 1, 3)
        d /= np.linalg.norm(d)
        p = c + d * radius * 0.62 * rng.uniform(0.55, 1.0) ** 0.35 * np.array([1, 1, 0.7])
        size = rng.uniform(0.18, 0.32)
        a = rng.normal(0, 1, 3)
        a -= a.dot(d) * d
        a /= np.linalg.norm(a)
        b = np.cross(d, a)
        base = len(verts)
        verts += [p - a * size * 0.5, p + b * size * 0.35, p + a * size * 0.5, p - b * size * 0.35]
        faces.append((base, base + 1, base + 2, base + 3))
    return np.array(verts), faces


def make_trees(col, rng):
    """The bush behind the market: a band of trees low against the twilight, with a gap where the moon is."""
    leaves, bark = foliage_material(), wood_material('Bark')
    made = 0
    protos = []
    for seed in range(4):
        v, f = crown_mesh(seed + 10, rng.uniform(3.0, 5.0), 11000)
        c = obj_from_arrays(f'CrownProto.{seed}', v, f, col)
        c.data.materials.append(leaves)
        c['top'] = float(v[:, 2].max())
        th = rng.uniform(4, 8)
        tv, tf = sweep(np.array([(0, 0, -0.5), (0.2, 0.1, th * 0.6), (0.1, -0.1, th)]), np.array([0.35, 0.25, 0.18]), sides=8)
        t = obj_from_arrays(f'TrunkProto.{seed}', tv, tf, col)
        t.data.materials.append(bark)
        protos.append((c, t, th))
    for _ in range(140):
        x = rng.uniform(-70, 70)
        y = rng.uniform(14, 80)
        # keep the moon clear of the nearer crowns, as seen from the hero camera
        if y < 55 and abs(math.atan2(x + 0.1, y + 4.9) - math.atan2(MOON.x, MOON.y)) < math.radians(9):
            continue
        c, t, th = protos[int(rng.integers(0, len(protos)))]
        s = rng.uniform(0.8, 1.4)
        z = 0.6 * smoothstep(y, 25, 80)
        # from the hero camera no crown rises more than about eleven degrees: the sky stays open above them
        top = z + s * (th + c['top'])
        s *= min(1.0, (math.tan(math.radians(rng.uniform(8.5, 11.5))) * (y + 4.9) + 0.88 - z) / (top - z))
        if s < 0.55:
            continue
        for src, dz in ((c, th), (t, 0.0)):
            o = bpy.data.objects.new(src.name.replace('Proto', ''), src.data)
            col.objects.link(o)
            o.matrix_world = Matrix.Translation((x, y, z + dz * s)) @ Matrix.Rotation(rng.uniform(0, 6.28), 4, 'Z') @ Matrix.Diagonal((s, s, s, 1))
        made += 1
    for c, t, th in protos:
        bpy.data.objects.remove(c)
        bpy.data.objects.remove(t)
    return made


def frond_mesh(rng, length, droop, leaflets=70):
    """One oil-palm frond: a stiff rachis arching out and down, with leaflets in pairs along it."""
    t = np.linspace(0, 1, 24)
    spine = np.stack([t * length, np.zeros_like(t), droop * length * (0.35 * t - t ** 2)], 1)
    tan = np.gradient(spine, axis=0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    verts, faces = [], []
    v, f = sweep(spine, np.linspace(0.05, 0.012, len(t)), sides=4)
    verts.append(v)
    faces += f
    base = len(v)
    for k in range(leaflets):
        u = 0.12 + 0.88 * k / leaflets
        i = min(int(u * (len(t) - 1)), len(t) - 2)
        f_ = u * (len(t) - 1) - i
        p = spine[i] * (1 - f_) + spine[i + 1] * f_
        d = tan[i]
        L = length * 0.24 * np.sin(np.pi * (0.25 + 0.75 * u)) * rng.uniform(0.85, 1.1)
        for side in (1, -1):
            # leaflets stand out from the rachis on both sides, angled forward, some up and some down
            out = np.array([0.0, side, 0.0]) * np.cos(0.55) + d * np.sin(0.55)
            out[2] += rng.uniform(-0.45, 0.25)
            out /= np.linalg.norm(out)
            tip = p + out * L + np.array([0, 0, -0.25 * L])
            wv = np.cross(out, (0, 0, 1.0))
            wv = wv / (np.linalg.norm(wv) + 1e-9) * 0.018
            verts.append(np.array([p - wv, p + wv, tip + wv * 0.3, tip - wv * 0.3]))
            faces.append((base, base + 1, base + 2, base + 3))
            base += 4
    return np.vstack(verts), faces


def make_palms(col, rng, count=26):
    """Oil palms standing out of the bush against the twilight, as they do all over Igboland."""
    fronds_m = foliage_material('PalmFronds', (0.010, 0.022, 0.008), (0.035, 0.060, 0.016))
    trunk_m = wood_material('PalmTrunk')
    protos = []
    for seed in range(3):
        prng = np.random.default_rng(100 + seed)
        parts = []
        for k in range(prng.integers(26, 34)):
            v, f = frond_mesh(prng, prng.uniform(3.6, 4.8), prng.uniform(0.25, 0.9))
            yaw, pitch = prng.uniform(0, 2 * np.pi), prng.uniform(-0.35, 0.75)
            R = np.array(Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(-pitch, 3, 'Y'))
            parts.append((v @ R.T, f))
        v, f = merged(parts)
        c = obj_from_arrays(f'PalmCrownProto.{seed}', v, f, col)
        c.data.materials.append(fronds_m)
        h = prng.uniform(11, 16)
        bend = prng.normal(0, 0.6, 2)
        path = np.array([(bend[0] * (z / h) ** 2, bend[1] * (z / h) ** 2, z) for z in np.linspace(-0.5, h, 12)])
        tv, tf = sweep(path, np.linspace(0.30, 0.22, 12), sides=10)
        tr = obj_from_arrays(f'PalmTrunkProto.{seed}', tv, tf, col)
        tr.data.materials.append(trunk_m)
        protos.append((c, tr, path[-1]))
    made, tries = 0, 0
    moon_az = math.atan2(MOON.x, MOON.y)
    while made < count and tries < 500:
        tries += 1
        x, y = rng.uniform(-55, 55), rng.uniform(16, 70)
        c, tr, top = protos[int(rng.integers(0, 3))]
        s = rng.uniform(0.8, 1.15)
        z = 0.6 * smoothstep(y, 25, 80)
        az = math.atan2(x + 0.15, y + 4.9)
        elev = math.degrees(math.atan2(z + s * (top[2] + 1.5) - 0.88, y + 4.9))
        # from the hero camera: none in front of the moon, and the ones behind him kept below its height
        if abs(az - moon_az) < math.radians(7) or (abs(az) < math.radians(24) and elev > 13.5) or elev > 24:
            continue
        rot = Matrix.Rotation(rng.uniform(0, 6.28), 4, 'Z')
        m = Matrix.Translation((x, y, z)) @ rot @ Matrix.Diagonal((s, s, s, 1))
        for src, off in ((tr, Vector((0, 0, 0))), (c, Vector(top))):
            o = bpy.data.objects.new(src.name.replace('Proto', ''), src.data)
            col.objects.link(o)
            o.matrix_world = m @ Matrix.Translation(off)
        made += 1
    for c, tr, _ in protos:
        bpy.data.objects.remove(c)
        bpy.data.objects.remove(tr)
    return made


def make_lamps(col, spots):
    """Clay lamps of palm oil on the stall tables nearest him: a bowl, a wick and its flame."""
    clay = clay_material()
    g = mats.Graph('Flame')
    tc = g.node('TexCoord').outputs['Object']
    z = g.node('SeparateXYZ', Vector=tc).outputs[2]
    hot = g.node('Blackbody', Temperature=1900)
    em = g.node('Emission', Color=hot.outputs[0], Strength=g.math('ADD', 30.0, g.math('MULTIPLY', z, -400.0)))
    flame_m = g.finish(em.outputs[0])
    obs = []
    for k, at in enumerate(spots):
        v, f = lathe([(0.0, 0.0), (0.045, 0.004), (0.055, 0.030), (0.050, 0.034), (0.040, 0.020), (0.0, 0.018)], 24)
        bowl = obj_from_arrays(f'Lamp.{k}', v + np.array(at), f, col)
        bowl.data.materials.append(clay)
        fv, ff = lathe([(0.0, 0.0), (0.006, 0.006), (0.007, 0.016), (0.004, 0.030), (0.0, 0.042)], 12)
        flame = obj_from_arrays(f'Flame.{k}', fv, ff, col)      # its origin at the wick, so the flame cools upward from there
        flame.location = Vector(at) + Vector((0.02, 0, 0.030))
        flame.data.materials.append(flame_m)
        flame.visible_shadow = False
        obs.append(flame)
    return obs


def paint_moon(n=512):
    """A young crescent, lit on the side toward the set sun, with the dark limb faintly lit by earthshine."""
    y, x = np.mgrid[0:n, 0:n] / (n - 1) * 2 - 1
    r = np.hypot(x, y)
    disc = smoothstep(r, 1.0, 0.985)
    # the terminator is half an ellipse from pole to pole; a moon three or four days old is lit about a fifth of the way across
    lit = smoothstep(-x - 0.62 * np.sqrt(np.clip(1 - y * y, 0, 1)), -0.012, 0.012) * disc
    noise = Noise(7)
    mare = 0.85 + 0.15 * noise.fbm(np.stack([x * 4, y * 4, np.zeros_like(x)], -1), 4)
    lum = lit * mare + disc * 0.012
    from common import TEX
    from weave import save
    save(TEX / 'moon_crescent.png', np.dstack([lum, lum * 0.97, lum * 0.90, disc]).astype(np.float32))


def make_moon(col, distance=900.0, size=30.0):
    """The crescent, about four times its true size so it reads, turned so its lit side faces the sun below the horizon.

    The twilight is scattered in the air between us and the moon, so the moon adds its light to
    the sky's and its dark part hides nothing: the quad lets everything through and only emits.
    """
    paint_moon()
    at = MOON * distance
    v = np.array([(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)], float) * size / 2
    ob = obj_from_arrays('Moon', v, [(0, 1, 2, 3)], col, smooth=False, uv=np.array([(0, 0), (1, 0), (1, 1), (0, 1)]))
    g = mats.Graph('Moon')
    uv = g.node('TexCoord').outputs['UV']
    img = g.image('moon_crescent.png', uv, 'sRGB', extension='CLIP')
    em = g.node('Emission', Color=img.outputs['Color'], Strength=6.0)
    clear = g.node('BsdfTransparent')
    both = g.node('AddShader')
    g.link(clear.outputs[0], both.inputs[0])
    g.link(em.outputs[0], both.inputs[1])
    ob.data.materials.append(g.finish(both.outputs[0]))
    face = -MOON
    rot = face.to_track_quat('-Y', 'Z').to_matrix().to_4x4()
    # the lit limb points down toward where the sun went
    toward_sun = (SUN - SUN.dot(MOON) * MOON).normalized()
    m = Matrix.Translation(at) @ rot
    right = (m.to_3x3() @ Vector((1, 0, 0))).normalized()
    up = (m.to_3x3() @ Vector((0, 0, 1))).normalized()
    ang = math.atan2(toward_sun.dot(up), toward_sun.dot(right))
    ob.matrix_world = m @ Matrix.Rotation(math.pi - ang, 4, 'Y')      # the lit limb starts on local -X
    ob.visible_shadow = False
    return ob


def make_sky():
    """Dusk from Blender's physical sky, the sun a degree or two below the horizon."""
    sc = bpy.context.scene
    world = bpy.data.worlds.get('Dusk') or bpy.data.worlds.new('Dusk')
    sc.world = world
    world.use_nodes = True
    t = world.node_tree
    t.nodes.clear()
    out = t.nodes.new('ShaderNodeOutputWorld')
    bg = t.nodes.new('ShaderNodeBackground')
    sky = t.nodes.new('ShaderNodeTexSky')
    sky.sky_type = 'NISHITA'
    sky.sun_disc = False
    sky.sun_elevation = math.asin(SUN.z)
    sky.sun_rotation = math.atan2(SUN.x, -SUN.y) % (2 * math.pi)
    sky.air_density = 1.0
    sky.dust_density = 1.5
    sky.ozone_density = 3.0          # the ozone layer's absorption is what turns twilight blue
    t.links.new(sky.outputs[0], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 3.0
    t.links.new(bg.outputs[0], out.inputs['Surface'])
    return world


def build(far, near):
    rng = np.random.default_rng(21)
    make_ground(near)
    make_litter(near, rng)
    count, spots = make_stalls(near, rng)
    print('stall parts', count, flush=True)
    print('trees', make_trees(far, rng), flush=True)
    print('palms', make_palms(far, rng), flush=True)
    make_moon(far)
    make_sky()
    # and one on the ground by his left foot, where a trader set it down
    return make_lamps(near, spots + [(0.80, -0.70, 0.0)])
