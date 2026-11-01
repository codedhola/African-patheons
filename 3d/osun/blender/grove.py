"""The grove: a sandy bank on a bend of the Ọ̀ṣun, under high forest, in the morning.

UNESCO describes a meandering river in primary high forest, and this follows the layout of
stage 01 in this repo. No real place in the grove is copied, and its sculptures are left out:
they are the works of named artists.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

import materials as mats
from common import TEX, obj_from_arrays
from dress import smoothstep
from procedural import Noise, rock_mesh, sweep

Z_WATER = -0.14
SUN = Vector((-0.40, 0.60, 0.69)).normalized()      # toward the sun: high, over the river, behind her right shoulder

# river centre line: x, y, half width
RIVER = np.array([(-90, 24, 11), (-55, 15, 9.5), (-30, 9.8, 7.8), (-14, 8.7, 7.2), (-3, 8.5, 6.6), (6, 10.5, 6.2), (12.5, 16, 5.8),
                  (14, 24, 5.4), (10.5, 33, 5.0), (6, 42, 4.7), (6.5, 53, 4.4), (11, 64, 4.2), (14, 80, 4.0), (10, 110, 4.0)], float)


def densify(points, n=600):
    t = np.linspace(0, len(points) - 1, n)
    i = np.clip(t.astype(int), 0, len(points) - 2)
    f = (t - i)[:, None]
    f = f * f * (3 - 2 * f)
    p = points[i] * (1 - f) + points[i + 1] * f
    for _ in range(40):
        p[1:-1] = (p[:-2] + p[1:-1] * 2 + p[2:]) / 4
    return p


LINE = densify(RIVER)


BAY = (-5.4, -0.5, 4.5, 3.5)      # a shallow bay on the near bank: centre, then radii


def bank_distance(x, y):
    """Distance from the water's edge: positive on land, negative in the river."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    flat_x, flat_y = x.ravel(), y.ravel()
    res = np.empty(flat_x.shape)
    for start in range(0, len(flat_x), 40000):
        a, b = flat_x[start:start + 40000], flat_y[start:start + 40000]
        d = np.hypot(a[:, None] - LINE[:, 0], b[:, None] - LINE[:, 1]) - LINE[:, 2]
        res[start:start + 40000] = d.min(1)
    # the bay runs into the river without a seam
    cx, cy, rx, ry = BAY
    bay = (np.hypot((flat_x - cx) / rx, (flat_y - cy) / ry) - 1) * min(rx, ry)
    k = 1.4
    blend = np.clip(0.5 + 0.5 * (bay - res) / k, 0, 1)
    res = bay + (res - bay) * blend - k * blend * (1 - blend)
    return res.reshape(x.shape)


def height_field(x, y, e=None):
    """Ground height: a long sand beach rising to the forest floor, the river bed falling away."""
    e = bank_distance(x, y) if e is None else e
    n1 = Noise(7)
    p = np.stack([x, y, np.zeros_like(x)], -1)
    beach = Z_WATER + 0.105 * e - 0.0034 * np.maximum(e, 0) ** 2
    beach = np.minimum(beach, 0.0 + 0.040 * np.maximum(e - 2.0, 0))
    far = (0.22 * smoothstep(e, 3, 9) + 0.55 * smoothstep(e, 8, 24)) * (0.3 + 0.7 * smoothstep(y, -3, 5))
    h = np.where(e > 0, beach + far, Z_WATER + 0.24 * e)
    h = np.maximum(h, -1.6)
    h = h + 0.018 * n1.fbm(p * 1.3, 3) * smoothstep(e, -0.4, 1.5) + 0.26 * n1.fbm(p * 0.17, 3) * smoothstep(e, 4, 14)
    # she stands on level sand
    d = np.hypot(x - 0.15, y + 0.05)
    keep = smoothstep(d, 0.8, 2.2)
    return h * keep


def fast_mesh(name, verts, quads, col, attrs=None, material=None):
    """Mesh from big arrays of quads, without going through Python lists."""
    verts = np.asarray(verts, np.float32)
    quads = np.asarray(quads, np.int32)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts))
    me.vertices.foreach_set('co', verts.ravel())
    me.loops.add(len(quads) * 4)
    me.polygons.add(len(quads))
    me.loops.foreach_set('vertex_index', quads.ravel())
    me.polygons.foreach_set('loop_start', np.arange(len(quads)) * 4)
    me.update(calc_edges=True)
    me.polygons.foreach_set('use_smooth', np.ones(len(quads), bool))
    for key, values in (attrs or {}).items():
        a = me.attributes.new(key, 'FLOAT', 'POINT')
        a.data.foreach_set('value', np.asarray(values, np.float32).ravel())
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    if material:
        me.materials.append(material)
    return ob


def grid_quads(nx, ny):
    i, j = np.mgrid[0:nx - 1, 0:ny - 1]
    a = i * ny + j
    return np.stack([a, a + ny, a + ny + 1, a + 1], -1).reshape(-1, 4)


# ----- materials ------------------------------------------------------------

def sand_material():
    """Pale river sand, darkened and shining where the water has been, leaf mould back from the bank."""
    g = mats.Graph('Sand')
    obj = g.node('TexCoord').outputs['Object']
    bank = g.node('Attribute', attribute_name='bank', attribute_type='GEOMETRY').outputs['Fac']
    wet = g.ramp(bank, [(0.0, (1, 1, 1)), (0.055, (0.62, 0.62, 0.62)), (0.135, (0, 0, 0))])
    wet_f = g.node('SeparateColor', Color=wet).outputs[0]
    forest = g.ramp(bank, [(0.30, (0, 0, 0)), (0.62, (1, 1, 1))])
    forest_f = g.node('SeparateColor', Color=forest).outputs[0]

    big = g.node('TexNoise', Vector=obj, Scale=1.7, Detail=6, Roughness=0.55).outputs['Fac']
    fine = g.node('TexNoise', Vector=obj, Scale=340, Detail=7, Roughness=0.7).outputs['Fac']
    grain = g.node('TexVoronoi', Vector=obj, Scale=1400, Randomness=1.0).outputs['Color']
    grain_v = g.node('SeparateColor', Color=grain).outputs[0]
    warped = g.node('TexNoise', Vector=obj, Scale=2.0, Detail=3).outputs['Color']
    across = g.node('Mapping', Vector=obj, Rotation=(0, 0, 0.5)).outputs[0]
    ripple_pos = g.node('VectorMath', operation='ADD', Vector=across)
    g.link(g.node('VectorMath', operation='SCALE', Vector=warped, Scale=0.34).outputs[0], ripple_pos.inputs[1])
    ripple = g.node('TexWave', Vector=ripple_pos.outputs[0], Scale=7.5, Distortion=0.0, wave_type='BANDS', bands_direction='Y').outputs['Fac']

    col = g.ramp(big, [(0.30, (0.25, 0.18, 0.11)), (0.55, (0.34, 0.25, 0.155)), (0.75, (0.44, 0.34, 0.22))])
    speck = g.ramp(grain_v, [(0.02, (1, 1, 1)), (0.06, (0, 0, 0))])
    col = g.mix(g.math('MULTIPLY', fine, 0.42), col, (0.22, 0.16, 0.10))
    col = g.mix(g.math('MULTIPLY', g.node('SeparateColor', Color=speck).outputs[0], 0.55), col, (0.10, 0.07, 0.05))
    damp = g.mix(0.6, col, (0.11, 0.075, 0.047), 'MULTIPLY')
    col = g.mix(wet_f, col, damp)
    mould = g.ramp(g.node('TexNoise', Vector=obj, Scale=7, Detail=7, Roughness=0.66).outputs['Fac'], [(0.3, (0.014, 0.011, 0.007)), (0.7, (0.075, 0.053, 0.028))])
    col = g.mix(forest_f, col, mould)

    h = g.math('ADD', g.math('MULTIPLY', ripple, 0.75), g.math('MULTIPLY', fine, 0.55))
    h = g.math('MULTIPLY', h, g.math('SUBTRACT', 1.0, g.math('MULTIPLY', wet_f, 0.6)))
    normal = g.bump(h, 1.0, 0.0085)
    rough = g.math('ADD', 0.86, g.math('MULTIPLY', wet_f, -0.66))
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=rough, Normal=normal)
    bsdf.inputs['Specular IOR Level'].default_value = 0.34
    return g.finish(bsdf.outputs[0])


def water_material():
    g = mats.Graph('River')
    obj = g.node('TexCoord').outputs['Object']
    depth = g.node('Attribute', attribute_name='depth', attribute_type='GEOMETRY').outputs['Fac']
    col = g.ramp(depth, [(0.0, (0.20, 0.145, 0.085)), (0.05, (0.095, 0.105, 0.060)), (0.20, (0.018, 0.055, 0.040)), (0.7, (0.006, 0.026, 0.022))])
    stretch = g.node('Mapping', Vector=obj, Scale=(0.30, 1.0, 1.0)).outputs[0]
    n1 = g.node('TexNoise', Vector=stretch, Scale=2.3, Detail=5, Roughness=0.55).outputs['Fac']
    n2 = g.node('TexNoise', Vector=stretch, Scale=11, Detail=4, Roughness=0.5).outputs['Fac']
    h = g.math('ADD', n1, g.math('MULTIPLY', n2, 0.32))
    normal = g.bump(h, 0.55, 0.012)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.035, IOR=1.33, Normal=normal)
    return g.finish(bsdf.outputs[0])


def bark_material():
    g = mats.Graph('Bark')
    obj = g.node('TexCoord').outputs['Object']
    tall = g.node('Mapping', Vector=obj, Scale=(1, 1, 0.18)).outputs[0]
    n = g.node('TexNoise', Vector=tall, Scale=7, Detail=7, Roughness=0.62).outputs['Fac']
    fine = g.node('TexNoise', Vector=tall, Scale=44, Detail=5).outputs['Fac']
    col = g.ramp(n, [(0.3, (0.075, 0.062, 0.050)), (0.52, (0.22, 0.185, 0.145)), (0.72, (0.37, 0.32, 0.26))])
    moss_mask = g.ramp(g.node('TexNoise', Vector=obj, Scale=1.1, Detail=6, Roughness=0.62).outputs['Fac'], [(0.46, (0, 0, 0)), (0.60, (1, 1, 1))])
    moss = g.ramp(fine, [(0.3, (0.035, 0.055, 0.012)), (0.7, (0.10, 0.14, 0.03))])
    col = g.mix(g.node('SeparateColor', Color=moss_mask).outputs[0], col, moss)
    normal = g.bump(g.math('ADD', n, g.math('MULTIPLY', fine, 0.4)), 1.0, 0.018)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.8, Normal=normal)
    return g.finish(bsdf.outputs[0])


def foliage_material(name='Foliage', low=(0.014, 0.050, 0.008), mid=(0.035, 0.115, 0.014), high=(0.105, 0.185, 0.020), rough=0.38):
    """Waxy leaves with their colour set leaf by leaf, glowing where the sun comes through."""
    g = mats.Graph(name)
    pick = g.node('Attribute', attribute_name='tint', attribute_type='GEOMETRY').outputs['Fac']
    col = g.ramp(pick, [(0.0, low), (0.55, mid), (1.0, high)])
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=rough)
    bsdf.inputs['Specular IOR Level'].default_value = 0.55
    glow = g.mix(0.5, col, (0.75, 0.95, 0.18), 'MULTIPLY')
    trans = g.node('BsdfTranslucent', Color=glow)
    both = g.node('MixShader', Fac=0.42)
    g.link(bsdf.outputs[0], both.inputs[1])
    g.link(trans.outputs[0], both.inputs[2])
    return g.finish(both.outputs[0])


def stone_material():
    g = mats.Graph('RiverStone')
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=380, Detail=6, Roughness=0.62).outputs['Fac']
    pick = g.node('ObjectInfo').outputs['Random']
    tint = g.ramp(pick, [(0.0, (0.20, 0.15, 0.11)), (0.6, (0.33, 0.27, 0.20)), (1.0, (0.50, 0.45, 0.38))])
    col = g.mix(g.math('MULTIPLY', n, 0.6), tint, (0.07, 0.05, 0.04))
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.62, Normal=g.bump(n, 1.0, 0.0015))
    return g.finish(bsdf.outputs[0])


# ----- ground and water -----------------------------------------------------

NEAR = (-4.2, 5.0, -5.6, 3.6)


def ground_attrs(e):
    return {'bank': np.clip((e + 0.2) / 16.0, 0, 1)}


def make_ground(col):
    sand = sand_material()
    # the patch she stands on, fine enough for close-ups
    x0, x1, y0, y1 = NEAR
    nx, ny = int((x1 - x0) / 0.02), int((y1 - y0) / 0.02)
    X, Y = np.meshgrid(np.linspace(x0, x1, nx), np.linspace(y0, y1, ny), indexing='ij')
    e = bank_distance(X, Y)
    n2 = Noise(44)
    p = np.stack([X, Y, np.zeros_like(X)], -1)
    edge = np.minimum.reduce([X - x0, x1 - X, Y - y0, y1 - Y])
    detail = (0.0065 * n2.fbm(p * 5.5, 4, 0.55) + 0.0016 * n2.fbm(p * 34, 3, 0.55)) * np.clip(edge / 0.4, 0, 1)
    Z = height_field(X, Y, e) + detail
    near = fast_mesh('Sand', np.stack([X, Y, Z], -1).reshape(-1, 3), grid_quads(nx, ny), col, ground_attrs(e), sand)

    # the rest of the valley, coarser with distance
    n = 520
    u = np.sign(np.linspace(-1, 1, n)) * np.abs(np.linspace(-1, 1, n)) ** 2.4
    xs, ys = u * 170, u * 170 + 45
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    e = bank_distance(X, Y)
    Z = height_field(X, Y, e)
    inside = (X > x0 + 0.12) & (X < x1 - 0.12) & (Y > y0 + 0.12) & (Y < y1 - 0.12)
    Z = np.where(inside, Z - 0.05, Z)
    far = fast_mesh('Valley', np.stack([X, Y, Z], -1).reshape(-1, 3), grid_quads(n, n), col, ground_attrs(e), sand)

    # water: a grid just to carry depth, so colour can follow the bed
    n = 420
    u = np.sign(np.linspace(-1, 1, n)) * np.abs(np.linspace(-1, 1, n)) ** 1.8
    X, Y = np.meshgrid(u * 170, u * 170 + 45, indexing='ij')
    e = bank_distance(X, Y)
    depth = np.clip(-e / 7.0, 0, 1)
    fast_mesh('River', np.stack([X, Y, np.full_like(X, Z_WATER)], -1).reshape(-1, 3), grid_quads(n, n), col, {'depth': depth}, water_material())
    return near, far


def make_stones(col):
    stone = stone_material()
    rng = np.random.default_rng(21)
    src = []
    for s in range(6):
        v, f = rock_mesh(500 + s)
        r = obj_from_arrays(f'Pebble.{s}', v, f, col)
        r.data.materials.append(stone)
        sub = r.modifiers.new('Smooth', 'SUBSURF')
        sub.levels = sub.render_levels = 1
        r.hide_render = r.hide_viewport = True
        src.append(r)
    x0, x1, y0, y1 = NEAR
    count = 0
    for _ in range(620):
        x, y = rng.uniform(x0 + 0.5, x1 - 0.5), rng.uniform(y0 + 0.5, y1 - 0.5)
        if math.hypot(x, y) < 0.34:
            continue
        s = float(np.clip(rng.lognormal(math.log(0.0075), 0.75), 0.003, 0.055))
        ob = bpy.data.objects.new('Pebble', src[int(rng.integers(0, len(src)))].data)
        col.objects.link(ob)
        ob.modifiers.new('Smooth', 'SUBSURF').render_levels = 1
        ob.location = (x, y, float(height_field(np.array([x]), np.array([y]))[0]) + s * 0.2)
        ob.rotation_euler = tuple(rng.uniform(0, 6.28, 3))
        ob.scale = (s, s, s)
        count += 1
    return count


def leaf_cards(n, rng, centres, spread, size, droop=0.5, tint_range=(0.0, 1.0)):
    """n leaves as two-quad folded cards. centres is k x 3: leaves scatter round them."""
    pick = rng.integers(0, len(centres), n)
    u = rng.normal(0, 1, (n, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    r = rng.random(n)[:, None] ** (1 / 3)
    spreads = np.broadcast_to(np.asarray(spread, float), (len(centres),))[pick][:, None]
    base = centres[pick] + u * r * spreads * np.array([1, 1, 0.62])
    heading = rng.uniform(0, 6.283, n)
    drop = rng.uniform(droop * 0.4, droop * 1.6, n)
    along = np.stack([np.cos(heading) * np.cos(drop), np.sin(heading) * np.cos(drop), -np.sin(drop)], 1)
    side = np.cross(along, (0, 0, 1))
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    up = np.cross(side, along)
    L = rng.uniform(0.7, 1.3, n)[:, None] * size
    W = L * 0.30
    p0 = base
    p1 = base + along * L * 0.45 + side * W + up * W * 0.25
    p2 = base + along * L * 0.45 - side * W + up * W * 0.25
    p3 = base + along * L * 0.45
    p4 = base + along * L
    verts = np.stack([p0, p1, p3, p2, p4], 1).reshape(-1, 3)
    i = np.arange(n)[:, None] * 5
    quads = np.concatenate([i + np.array([0, 2, 4, 1]), i + np.array([0, 3, 4, 2])])      # base, rib, tip, edge on each side
    tint = np.repeat(rng.uniform(tint_range[0], tint_range[1], n), 5)
    return verts, quads, tint


def tree_trunk(rng, height, radius, lean, nodes=46, sides=26):
    """A straight forest trunk with buttress roots flaring out at its foot."""
    t = np.linspace(0, 1, nodes) ** 1.4
    wander = rng.normal(0, 0.012, (nodes, 2)).cumsum(0) * height * 0.06
    axis = np.stack([wander[:, 0] + lean[0] * t * height, wander[:, 1] + lean[1] * t * height, t * height], 1)
    r = radius * (1 - 0.72 * t) + 0.04
    th = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    ribs = int(rng.integers(4, 7))
    phase = rng.uniform(0, 6.28)
    rough = Noise(int(rng.integers(1, 9999)))
    T, TH = np.meshgrid(np.arange(nodes), th, indexing='ij')
    fin = np.maximum(np.cos(TH * ribs + phase), 0) ** 5
    flare = 3.2 * np.exp(-(t[T] * height) / (height * 0.038 + 0.5)) * fin + 0.5 * np.exp(-(t[T] * height) / 2.0)
    bumps = 1 + 0.06 * rough(np.stack([np.cos(TH) * 2, np.sin(TH) * 2, t[T] * 9], -1))
    rad = r[T] * (1 + flare) * bumps
    verts = np.stack([axis[T, 0] + np.cos(TH) * rad, axis[T, 1] + np.sin(TH) * rad, axis[T, 2]], -1)
    i, j = np.mgrid[0:nodes - 1, 0:sides]
    a = i * sides + j
    b = i * sides + (j + 1) % sides
    quads = np.stack([a, b, b + sides, a + sides], -1).reshape(-1, 4)
    return verts.reshape(-1, 3), quads, axis


def forest_tree(name, seed, col, bark, leaves, height=30.0, radius=0.62, crown=9.0, leaf_count=15000, leaf_size=0.22):
    """One tall tree: trunk, limbs, and crowded leaf clusters. Used many times over."""
    rng = np.random.default_rng(seed)
    lean = rng.normal(0, 0.012, 2)
    v, q, axis = tree_trunk(rng, height, radius, lean)
    parts = [(v, q)]
    centres, spreads = [], []
    top = axis[-1]
    limbs = int(rng.integers(9, 14))
    for k in range(limbs):
        at = rng.uniform(0.60, 0.96)
        a = axis[int(at * (len(axis) - 1))]
        heading = rng.uniform(0, 6.283)
        reach = crown * rng.uniform(0.55, 1.05) * (1.15 - at * 0.5)
        rise = rng.uniform(0.15, 0.8)
        s = np.linspace(0, 1, 12)[:, None]
        d = np.array([math.cos(heading), math.sin(heading), 0])
        path = a + d * s * reach + np.array([0, 0, 1]) * (s * reach * rise - s * s * reach * 0.25)
        vv, ff = sweep(path, np.linspace(radius * 0.26, 0.03, 12), 7)
        parts.append((vv, np.array(ff)))
        for f in (0.45, 0.75, 1.0):
            centres.append(a + d * f * reach + np.array([0, 0, 1]) * (f * reach * rise - f * f * reach * 0.25 + 0.5))
            spreads.append(reach * 0.34 + 1.0)
    base = 0
    verts, quads = [], []
    for vv, qq in parts:
        verts.append(vv)
        quads.append(np.asarray(qq) + base)
        base += len(vv)
    trunk = fast_mesh(name + '.wood', np.concatenate(verts), np.concatenate(quads), col, material=bark)
    lv, lq, tint = leaf_cards(leaf_count, rng, np.array(centres), np.array(spreads), leaf_size)
    crown_ob = fast_mesh(name + '.crown', lv, lq, col, {'tint': tint}, leaves)
    for ob in (trunk, crown_ob):
        ob.hide_render = ob.hide_viewport = True
    return trunk, crown_ob


def shrub(name, seed, col, bark, leaves, height=4.5, spread=2.4, leaf_count=2600, leaf_size=0.20):
    """Understorey: a few thin stems and a loose head of big leaves."""
    rng = np.random.default_rng(seed)
    parts, centres = [], []
    for k in range(5):
        a = rng.uniform(0, 6.28)
        s = np.linspace(0, 1, 8)[:, None]
        tip = np.array([math.cos(a) * spread * 0.6, math.sin(a) * spread * 0.6, height * rng.uniform(0.7, 1.05)])
        path = np.array([0, 0, 0]) + tip * s + np.array([0, 0, 1]) * (-s * s * height * 0.1)
        vv, ff = sweep(path, np.linspace(0.05, 0.012, 8), 5)
        parts.append((vv, np.array(ff)))
        for f in (0.45, 0.7, 1.0):
            centres.append(tip * f)
    base = 0
    verts, quads = [], []
    for vv, qq in parts:
        verts.append(vv)
        quads.append(qq + base)
        base += len(vv)
    stem = fast_mesh(name + '.wood', np.concatenate(verts), np.concatenate(quads), col, material=bark)
    lv, lq, tint = leaf_cards(leaf_count, rng, np.array(centres), spread * 0.42, leaf_size, droop=0.8)
    head = fast_mesh(name + '.leaves', lv, lq, col, {'tint': tint}, leaves)
    for ob in (stem, head):
        ob.hide_render = ob.hide_viewport = True
    return stem, head


def reed_patch(name, seed, col, material, blades=2400, area=2.2, tall=0.85):
    """A patch of riverside grass, as tapering folded strips."""
    rng = np.random.default_rng(seed)
    segs = 5
    t = np.linspace(0, 1, segs + 1)
    base = np.stack([rng.uniform(-area, area, blades), rng.uniform(-area * 0.6, area * 0.6, blades), np.zeros(blades)], 1)
    a = rng.uniform(0, 6.283, blades)
    h = rng.uniform(0.45, 1.0, blades)[:, None, None] * tall
    bend = rng.uniform(0.2, 0.75, blades)[:, None, None] * tall
    dirv = np.stack([np.cos(a), np.sin(a), np.zeros(blades)], 1)[:, None]
    tt = t[None, :, None]
    spine = base[:, None] + np.array([0, 0, 1.0])[None, None] * h * tt + dirv * bend * tt ** 2.2
    side = np.stack([-np.sin(a), np.cos(a), np.zeros(blades)], 1)[:, None]
    w = (0.0075 * (1 - tt ** 1.5))
    left, right = spine + side * w, spine - side * w
    verts = np.stack([left, right], 2).reshape(-1, 3)
    i, j = np.mgrid[0:blades, 0:segs]
    a0 = i * (2 * (segs + 1)) + j * 2
    quads = np.stack([a0, a0 + 1, a0 + 3, a0 + 2], -1).reshape(-1, 4)
    tint = np.repeat(rng.random(blades), 2 * (segs + 1))
    ob = fast_mesh(name, verts, quads, col, {'tint': tint}, material)
    ob.hide_render = ob.hide_viewport = True
    return ob


def liana(rng, top, drop, wobble=0.6):
    n = 26
    s = np.linspace(0, 1, n)[:, None]
    path = top + np.array([0, 0, -1.0]) * s * drop + rng.normal(0, 1, (n, 3)).cumsum(0) * wobble * 0.03 * s
    return sweep(path, np.linspace(0.028, 0.009, n), 5)


def place(src, col, at, yaw, scale, z_scale=None):
    ob = bpy.data.objects.new(src.name.split('.')[0], src.data)
    col.objects.link(ob)
    ob.location = at
    ob.rotation_euler = (0, 0, yaw)
    ob.scale = (scale, scale, z_scale or scale)
    return ob


def clear_of_sun(x, y, height=24.0, radius=7.5):
    """True when a crown here leaves the sun's way down to her open."""
    t = height / SUN.z
    cx, cy = SUN.x * t, SUN.y * t
    return math.hypot(x - cx, y - cy) > radius


def make_forest(col):
    bark = bark_material()
    high = foliage_material('Canopy')
    low = foliage_material('Understorey', (0.012, 0.040, 0.012), (0.030, 0.095, 0.020), (0.095, 0.150, 0.030))
    reed_m = foliage_material('Reed', (0.040, 0.075, 0.012), (0.095, 0.150, 0.022), (0.24, 0.26, 0.055))
    rng = np.random.default_rng(77)

    tall = [forest_tree(f'Tall{k}', 300 + k, col, bark, high, height=rng.uniform(27, 36), radius=rng.uniform(0.55, 0.85),
                        crown=rng.uniform(8, 12)) for k in range(4)]
    mid = [forest_tree(f'Mid{k}', 340 + k, col, bark, high, height=rng.uniform(13, 18), radius=rng.uniform(0.22, 0.34),
                       crown=rng.uniform(4, 6), leaf_count=7000, leaf_size=0.20) for k in range(3)]
    bushes = [shrub(f'Bush{k}', 400 + k, col, bark, low, height=rng.uniform(3.2, 6.0), spread=rng.uniform(1.8, 3.2)) for k in range(4)]
    reeds = [reed_patch(f'Reed{k}', 440 + k, col, reed_m) for k in range(3)]

    placed = dict(tall=0, mid=0, bush=0, reed=0)
    tries = 0
    spots = []

    def far_enough(x, y, gap):
        return all(math.hypot(x - a, y - b) > gap for a, b in spots)

    while placed['tall'] < 110 and tries < 8000:
        tries += 1
        x, y = rng.uniform(-75, 75), rng.uniform(-30, 120)
        e = float(bank_distance(np.array([x]), np.array([y]))[0])
        if e < rng.uniform(2.5, 8) or (y < 2.0 and abs(x) < 16) or not clear_of_sun(x, y) or not far_enough(x, y, 7.5):
            continue
        spots.append((x, y))
        k = int(rng.integers(0, len(tall)))
        z = float(height_field(np.array([x]), np.array([y]))[0]) - 0.1
        yaw, sc = rng.uniform(0, 6.28), rng.uniform(0.85, 1.2)
        for part in tall[k]:
            place(part, col, (x, y, z), yaw, sc)
        placed['tall'] += 1

    tries = 0
    while placed['mid'] < 170 and tries < 8000:
        tries += 1
        x, y = rng.uniform(-60, 60), rng.uniform(-14, 100)
        e = float(bank_distance(np.array([x]), np.array([y]))[0])
        if e < rng.uniform(1.8, 5) or (y < 2.0 and abs(x) < 9) or not far_enough(x, y, 3.0):
            continue
        k = int(rng.integers(0, len(mid)))
        z = float(height_field(np.array([x]), np.array([y]))[0]) - 0.05
        yaw, sc = rng.uniform(0, 6.28), rng.uniform(0.8, 1.25)
        for part in mid[k]:
            place(part, col, (x, y, z), yaw, sc)
        placed['mid'] += 1

    tries = 0
    while placed['bush'] < 420 and tries < 20000:
        tries += 1
        x, y = rng.uniform(-48, 48), rng.uniform(-10, 90)
        e = float(bank_distance(np.array([x]), np.array([y]))[0])
        if e < rng.uniform(0.9, 2.4) or (y < 1.5 and abs(x) < 6.5):
            continue
        k = int(rng.integers(0, len(bushes)))
        z = float(height_field(np.array([x]), np.array([y]))[0]) - 0.03
        yaw, sc = rng.uniform(0, 6.28), rng.uniform(0.75, 1.3)
        for part in bushes[k]:
            place(part, col, (x, y, z), yaw, sc)
        placed['bush'] += 1

    tries = 0
    while placed['reed'] < 240 and tries < 30000:
        tries += 1
        x, y = rng.uniform(-44, 44), rng.uniform(-8, 80)
        e = float(bank_distance(np.array([x]), np.array([y]))[0])
        if e < 0.15 or e > 3.5 or (y < 3.5 and abs(x + 0.2) < 5.2):      # nothing between the camera and her
            continue
        z = float(height_field(np.array([x]), np.array([y]))[0])
        place(reeds[int(rng.integers(0, len(reeds)))], col, (x, y, z - 0.02), rng.uniform(0, 6.28), rng.uniform(0.7, 1.2))
        placed['reed'] += 1

    # lianas hanging into the gap above the banks
    parts = []
    for _ in range(46):
        x, y = rng.uniform(-22, 26), rng.uniform(1, 34)
        e = float(bank_distance(np.array([x]), np.array([y]))[0])
        if e < 0.5:
            continue
        parts.append(liana(rng, np.array([x, y, rng.uniform(13, 22)]), rng.uniform(7, 16)))
    base = 0
    verts, quads = [], []
    for vv, qq in parts:
        verts.append(vv)
        quads.append(np.array(qq) + base)
        base += len(vv)
    fast_mesh('Lianas', np.concatenate(verts), np.concatenate(quads), col, material=bark)
    print('forest', placed, flush=True)
    return high, low


def make_canopy(col, material, holes=((0.0, 0.0, 1.7), (-2.6, 5.5, 1.1), (3.4, 7.0, 1.5), (-6.5, 9.5, 1.6), (1.0, 12.5, 1.2), (6.5, 14.0, 1.4), (-2.5, 17.0, 1.5))):
    """A roof of leaves over the river, with gaps. The sun comes through as separate shafts.

    Each hole is given by where its light lands on the ground, and a radius.
    """
    rng = np.random.default_rng(66)
    cells = []
    for x in np.arange(-34, 28, 1.6):
        for y in np.arange(-9, 62, 1.6):
            z = rng.uniform(15.0, 25.0)
            px, py = x + rng.normal(0, 0.45), y + rng.normal(0, 0.45)
            t = z / SUN.z
            gx, gy = px - SUN.x * t, py - SUN.y * t
            if any(math.hypot(gx - a, gy - b) < r + 0.5 for a, b, r in holes) or rng.random() < 0.20:
                continue
            cells.append((px, py, z))
    v, q, tint = leaf_cards(len(cells) * 120, rng, np.array(cells), 1.25, 0.22)
    print('canopy cells', len(cells), flush=True)
    return fast_mesh('Canopy', v, q, col, {'tint': tint}, material)


SHAFTS = ((0.0, 0.0, 1.5), (-3.0, 6.0, 0.75), (2.6, 7.5, 1.0), (-7.0, 10.0, 1.1), (0.4, 12.5, 0.7), (5.5, 13.5, 0.9), (-3.4, 17.0, 1.2),
          (9.0, 21.0, 1.1), (-10.5, 18.0, 0.9), (2.0, 26.0, 1.3))


def make_sun_mask(col, holes=SHAFTS, z=23.0):
    """A sheet only the sun can see. Its gaps turn sunlight into shafts, and a scatter of small ones into dapples.

    The real canopy is too thin to do this on its own, and would cost far more to make dense enough.
    """
    step = 0.45
    xs = np.arange(-95, 75, step)
    ys = np.arange(-60, 140, step)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    t = z / SUN.z
    gx, gy = X - SUN.x * t, Y - SUN.y * t       # where sunlight through each cell lands
    n = Noise(12)
    p = np.stack([gx, gy, np.zeros_like(gx)], -1)
    wobble = 0.28 * n.fbm(p * 1.3, 3, 0.6)
    solid = np.ones(X.shape, bool)
    for a, b, r in holes:
        solid &= np.hypot(gx - a, gy - b) > r * (1 + wobble)
    dapple = n.fbm(p * 0.95, 3, 0.55) > 0.42
    solid &= ~dapple
    i, j = np.nonzero(solid)
    quads = np.arange(len(i) * 4).reshape(-1, 4)
    h = step / 2
    verts = np.empty((len(i) * 4, 3), np.float32)
    cx, cy = xs[i], ys[j]
    verts[0::4] = np.stack([cx - h, cy - h, np.full_like(cx, z)], 1)
    verts[1::4] = np.stack([cx + h, cy - h, np.full_like(cx, z)], 1)
    verts[2::4] = np.stack([cx + h, cy + h, np.full_like(cx, z)], 1)
    verts[3::4] = np.stack([cx - h, cy + h, np.full_like(cx, z)], 1)
    ob = fast_mesh('SunMask', verts, quads, col)
    ob.visible_camera = False
    ob.visible_diffuse = False
    ob.visible_glossy = False
    ob.visible_transmission = False
    ob.visible_volume_scatter = False
    print('sun mask quads', len(quads), flush=True)
    return ob


def leaf_blades(rng, centres, along, side, length, width, curl, tint, sections=10):
    """Fallen leaves as strips across the midrib: a stalk, a pointed blade, its two halves folded up, the whole curled."""
    n = len(centres)
    t = np.linspace(0, 1, sections)[None, :, None]
    half = np.sin(np.pi * np.clip((t - 0.10) / 0.90, 0, 1) ** 0.8) ** 0.8 + 0.04
    length, width, curl = (a[:, None, None] for a in (length, width, curl))
    up = np.array([0, 0, 1.0])
    mid = centres[:, None] + along[:, None] * length * (t - 0.5) + up * length * curl * (2 * t - 1) ** 2
    edge = side[:, None] * width * half
    left, right = (mid + sign * edge + up * width * half * rng.uniform(0.03, 0.32, (n, 1, 1)) for sign in (-1, 1))
    verts = np.stack([left, mid, right], 2).reshape(-1, 3)
    a = np.arange(sections - 1)[:, None] * 3 + np.array([0, 1])
    cell = np.stack([a, a + 1, a + 4, a + 3], -1).reshape(-1, 4)
    quads = (np.arange(n)[:, None, None] * (sections * 3) + cell).reshape(-1, 4)
    browned = np.repeat(tint, sections * 3) - np.tile((0.16, 0.0, 0.16), n * sections)
    return verts, quads, np.clip(browned, 0, 1)


def make_litter(col):
    """Fallen leaves and a few sticks on the sand."""
    rng = np.random.default_rng(38)
    x0, x1, y0, y1 = NEAR
    n = 900
    x, y = rng.uniform(x0 + 0.2, x1 - 0.2, n), rng.uniform(y0 + 0.2, y1 - 0.2, n)
    keep = (np.hypot(x, y) > 0.36) & (np.hypot(x - 0.66, y + 0.46) > 0.20) & (bank_distance(x, y) > 0.12)
    x, y = x[keep], y[keep]
    z = height_field(x, y)
    n = len(x)
    heading = rng.uniform(0, 6.283, n)
    along = np.stack([np.cos(heading), np.sin(heading), rng.normal(0, 0.05, n)], 1)
    side = np.cross(along, (0, 0, 1))
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    L = rng.uniform(0.045, 0.115, n)
    W = L * rng.uniform(0.17, 0.27, n)
    curl = rng.uniform(-0.03, 0.10, n)
    centres = np.stack([x, y, z + 0.004 + L * np.maximum(-curl, 0)], 1)
    verts, quads, tint = leaf_blades(np.random.default_rng(39), centres, along, side, L, W, curl, rng.random(n))
    leaf = foliage_material('Litter', (0.060, 0.026, 0.010), (0.18, 0.085, 0.020), (0.42, 0.24, 0.035), rough=0.72)
    fast_mesh('Litter', verts, quads, col, {'tint': tint}, leaf)
    parts = []
    for _ in range(26):
        a, b = rng.uniform(x0 + 0.4, x1 - 0.4), rng.uniform(y0 + 0.4, y1 - 0.4)
        if math.hypot(a, b) < 0.5:
            continue
        t = rng.uniform(0, 6.28)
        L = rng.uniform(0.12, 0.62)
        s = np.linspace(0, 1, 9)[:, None]
        p = np.array([a, b, 0.0]) + np.array([math.cos(t), math.sin(t), 0]) * s * L + rng.normal(0, 0.008, (9, 3)).cumsum(0)
        p[:, 2] = height_field(p[:, 0], p[:, 1]) + 0.006
        parts.append(sweep(p, np.linspace(0.0075, 0.0025, 9), 5))
    base = 0
    verts, quads = [], []
    for vv, qq in parts:
        verts.append(vv)
        quads.append(np.array(qq) + base)
        base += len(vv)
    fast_mesh('Sticks', np.concatenate(verts), np.concatenate(quads), col, material=bpy.data.materials['Bark'])


def make_framing(col, material, eye, target):
    """Out-of-focus leaves at the top corners of the hero picture."""
    rng = np.random.default_rng(90)
    eye = np.array(eye, float)
    look = np.array(target, float) - eye
    look /= np.linalg.norm(look)
    side = np.cross(look, (0, 0, 1))
    side /= np.linalg.norm(side)
    up = np.cross(side, look)
    centres, spreads = [], []
    for sx, sz, d, sp in ((-1.0, 0.86, 1.9, 0.32), (-0.68, 1.04, 2.1, 0.34), (-0.25, 1.16, 2.3, 0.28), (0.98, 0.84, 1.9, 0.30), (0.72, 1.04, 2.1, 0.32), (0.34, 1.16, 2.3, 0.26)):
        centres.append(eye + look * d + side * sx * d * 0.40 + up * sz * d * 0.50)
        spreads.append(sp)
    v, q, tint = leaf_cards(3200, rng, np.array(centres), np.array(spreads), 0.050, droop=0.7)
    return fast_mesh('NearLeaves', v, q, col, {'tint': tint}, material)


def make_sky():
    """A pale morning sky, brightest round the sun."""
    w = bpy.data.worlds.get('Morning') or bpy.data.worlds.new('Morning')
    w.use_nodes = True
    t = w.node_tree
    t.nodes.clear()
    out = t.nodes.new('ShaderNodeOutputWorld')
    bg = t.nodes.new('ShaderNodeBackground')
    coord = t.nodes.new('ShaderNodeTexCoord')
    norm = t.nodes.new('ShaderNodeVectorMath')
    norm.operation = 'NORMALIZE'
    t.links.new(coord.outputs['Generated'], norm.inputs[0])
    dot = t.nodes.new('ShaderNodeVectorMath')
    dot.operation = 'DOT_PRODUCT'
    dot.inputs[1].default_value = SUN
    t.links.new(norm.outputs[0], dot.inputs[0])
    ramp = t.nodes.new('ShaderNodeValToRGB')
    t.links.new(dot.outputs['Value'], ramp.inputs['Fac'])
    stops = [(0.0, (0.34, 0.44, 0.40)), (0.55, (0.46, 0.56, 0.46)), (0.86, (0.86, 0.80, 0.52)), (0.975, (1.9, 1.55, 0.80)), (1.0, (6.0, 4.6, 2.1))]
    cr = ramp.color_ramp
    while len(cr.elements) < len(stops):
        cr.elements.new(0)
    for el, (p, c) in zip(cr.elements, stops):
        el.position = p
        el.color = (*c, 1)
    t.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 0.95
    t.links.new(bg.outputs[0], out.inputs['Surface'])
    w.cycles.sampling_method = 'NONE'       # so that the sun mask, which only blocks light sampling, leaves the sky alone
    bpy.context.scene.world = w
    return w


def make_haze(col, density=0.013):
    """Morning haze under the trees, which is what makes the sun's shafts visible."""
    v = np.array([(x, y, z) for x in (-46, 46) for y in (-16, 90) for z in (-1.0, 34)], float)
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    ob = obj_from_arrays('Haze', v, f, col, smooth=False)
    g = mats.Graph('HazeVolume')
    t = g.t
    t.nodes.clear()
    out = t.nodes.new('ShaderNodeOutputMaterial')
    vol = t.nodes.new('ShaderNodeVolumePrincipled')
    vol.inputs['Color'].default_value = (0.98, 0.90, 0.70, 1)
    vol.inputs['Density'].default_value = density
    vol.inputs['Anisotropy'].default_value = 0.62
    t.links.new(vol.outputs[0], out.inputs['Volume'])
    ob.data.materials.append(g.mat)
    ob.visible_shadow = True
    return ob
