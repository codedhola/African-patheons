"""Ọrun àti ọfà: his bow and arrow, the quiver on his back and its strap.

The bow and arrow are his main symbols (Wikipedia: Oshosi). His gallery figure draws a wooden bow
with an iron-tipped arrow on the string and carries a leather quiver on his back. The forms are
this study's: a self bow of dark hardwood about 1.35 m along its curve, its handle bound in
leather; reed arrows with leaf-shaped iron heads, fletched with two feathers of guinea fowl, a
bird offered to him in Candomblé (Wikipedia: Oshosi); a quiver of hide on a strap over his right
shoulder.

The bow is built drawn, in its own frame: the handle at the origin, standing up +Z, its back
toward the mark along +Y, the limbs bent back toward him in arcs, as far as a string of fixed
length lets them come.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

import materials as mats
from common import obj_from_arrays, verts_world
from procedural import merged, sweep

GRIP_HALF = 0.050      # the handle, half its length
LIMB = 0.625           # each limb along its curve, from the handle to the string's loop
STRING = 1.260         # the string, loop to loop
ARROW_LONG = 0.740     # the shaft; the head adds 6.8 cm
HEAD_LONG = 0.068
SHAFT_R = 0.0044
QUIVER_LONG = 0.580
QUIVER_R = 0.041
NOCK_OUT = 0.240       # how far each arrow's nock stands out of the quiver's mouth


# ----- materials ---------------------------------------------------------------

def wood_material(name='BowWood', dark=(0.030, 0.016, 0.009), light=(0.085, 0.048, 0.026)):
    """Dark hardwood, oiled and rubbed smooth, its grain running the length of the limb."""
    g = mats.Graph(name)
    obj = g.node('TexCoord').outputs['Object']
    long_grain = g.node('Mapping', Vector=obj, Scale=(60.0, 60.0, 2.0)).outputs[0]
    grain = g.node('TexWave', Vector=long_grain, Scale=1.0, Distortion=7.0, Detail=5, bands_direction='X').outputs['Fac']
    n = g.node('TexNoise', Vector=obj, Scale=40, Detail=4).outputs['Fac']
    col = g.ramp(grain, [(0.3, dark), (0.75, light)])
    rough = g.math('ADD', 0.30, g.math('MULTIPLY', n, 0.16))
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=rough, Normal=g.bump(grain, 0.12, 0.0004))
    bsdf.inputs['Coat Weight'].default_value = 0.25
    bsdf.inputs['Coat Roughness'].default_value = 0.25
    return g.finish(bsdf.outputs[0])


def fibre_material(name='String', base=(0.42, 0.33, 0.20)):
    """Twisted fibre: a fine diagonal lay, a little paler on the ridges."""
    g = mats.Graph(name)
    obj = g.node('TexCoord').outputs['Object']
    lay = g.node('TexWave', Vector=g.node('Mapping', Vector=obj, Scale=(700.0, 700.0, 700.0)).outputs[0], Scale=1.0,
                 wave_type='BANDS', bands_direction='DIAGONAL').outputs['Fac']
    col = g.mix(g.math('MULTIPLY', lay, 0.3), base, tuple(c * 0.6 for c in base))
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.7, Normal=g.bump(lay, 0.3, 0.0002))
    return g.finish(bsdf.outputs[0])


def reed_material():
    """Dry reed: straw-coloured and glossy, darker at the nodes."""
    g = mats.Graph('Reed')
    node = g.node('Attribute', attribute_name='node', attribute_type='GEOMETRY').outputs['Fac']
    obj = g.node('TexCoord').outputs['Object']
    streak = g.node('TexNoise', Vector=g.node('Mapping', Vector=obj, Scale=(300.0, 300.0, 300.0)).outputs[0], Scale=1.0, Detail=3).outputs['Fac']
    col = g.ramp(streak, [(0.3, (0.30, 0.21, 0.09)), (0.7, (0.46, 0.34, 0.15))])
    col = g.mix(node, col, (0.10, 0.065, 0.03))
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.36, Normal=g.bump(g.math('ADD', node, g.math('MULTIPLY', streak, 0.2)), 0.4, 0.0005))
    return g.finish(bsdf.outputs[0])


def feather_material():
    """Guinea-fowl feathers: slate grey spotted all over with small white dots, a little translucent."""
    g = mats.Graph('GuineaFowl')
    uv = g.node('TexCoord').outputs['UV']
    dots = g.node('TexVoronoi', Vector=g.node('Mapping', Vector=uv, Scale=(30.0, 6.0, 1.0)).outputs[0], Randomness=0.55).outputs['Distance']
    spot = g.math('LESS_THAN', dots, 0.24)
    barbs = g.node('TexWave', Vector=g.node('Mapping', Vector=uv, Scale=(1.0, 1.0, 1.0), Rotation=(0, 0, 0.5)).outputs[0],
                   Scale=90.0, wave_type='BANDS', bands_direction='X').outputs['Fac']
    col = g.mix(spot, (0.028, 0.030, 0.034), (0.62, 0.62, 0.60))
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.62, Normal=g.bump(barbs, 0.25, 0.0002))
    bsdf.inputs['Sheen Weight'].default_value = 0.5
    translucent = g.node('BsdfTranslucent', Color=col)
    both = g.node('MixShader', Fac=0.2)
    g.link(bsdf.outputs[0], both.inputs[1])
    g.link(translucent.outputs[0], both.inputs[2])
    return g.finish(both.outputs[0])


def iron_material(name='ArrowIron'):
    """Hand-forged iron: dark scale, with the edges filed bright."""
    g = mats.Graph(name)
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=160, Detail=5).outputs['Fac']
    edge = g.node('Attribute', attribute_name='edge', attribute_type='GEOMETRY').outputs['Fac']
    col = g.ramp(n, [(0.3, (0.018, 0.017, 0.017)), (0.7, (0.050, 0.045, 0.042))])
    col = g.mix(edge, col, (0.42, 0.42, 0.41))
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Metallic=g.math('ADD', 0.55, g.math('MULTIPLY', edge, 0.45)),
                  Roughness=g.math('SUBTRACT', 0.62, g.math('MULTIPLY', edge, 0.30)), Normal=g.bump(n, 0.3, 0.0003))
    return g.finish(bsdf.outputs[0])


def leather_material(name='Leather', base=(0.090, 0.045, 0.020)):
    """Worn hide: a fine pebbled grain, darker and smoother where it has been handled."""
    g = mats.Graph(name)
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=60, Detail=5).outputs['Fac']
    grain = g.node('TexVoronoi', Vector=obj, Scale=1100, feature='DISTANCE_TO_EDGE').outputs['Distance']
    col = g.ramp(n, [(0.3, tuple(c * 0.72 for c in base)), (0.7, base)])
    normal = g.bump(g.math('ADD', g.math('MINIMUM', g.math('MULTIPLY', grain, 8.0), 1.0), g.math('MULTIPLY', n, 0.4)), 0.10, 0.0003)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=g.math('ADD', 0.42, g.math('MULTIPLY', n, 0.18)), Normal=normal)
    bsdf.inputs['Sheen Weight'].default_value = 0.2
    return g.finish(bsdf.outputs[0])


def quiver_material():
    """The quiver's hide: brown, mottled and creased with use, and a band of zigzags burned in below the mouth."""
    g = mats.Graph('QuiverHide')
    obj = g.node('TexCoord').outputs['Object']
    along = g.node('Attribute', attribute_name='along', attribute_type='GEOMETRY').outputs['Fac']
    angle = g.math('ARCTAN2', g.node('Attribute', attribute_name='sina', attribute_type='GEOMETRY').outputs['Fac'],
                   g.node('Attribute', attribute_name='cosa', attribute_type='GEOMETRY').outputs['Fac'])
    blotch = g.node('TexNoise', Vector=obj, Scale=9, Detail=6, Roughness=0.6).outputs['Fac']
    crease = g.node('TexNoise', Vector=g.node('Mapping', Vector=obj, Scale=(3.0, 3.0, 1.0)).outputs[0], Scale=30, Detail=6, Roughness=0.65).outputs['Fac']
    grain = g.node('TexVoronoi', Vector=obj, Scale=900, feature='DISTANCE_TO_EDGE').outputs['Distance']
    col = g.ramp(blotch, [(0.25, (0.032, 0.014, 0.005)), (0.55, (0.070, 0.034, 0.013)), (0.80, (0.110, 0.058, 0.022))])
    # eight teeth round the quiver, between two burned lines, a hand below the mouth
    tooth = g.math('MULTIPLY', g.math('ABSOLUTE', g.math('SUBTRACT', g.math('FRACT', g.math('MULTIPLY', angle, 8 / (2 * math.pi))), 0.5)), 2.0)
    t = g.math('DIVIDE', g.math('SUBTRACT', along, 0.855), 0.07)
    inband = g.math('MULTIPLY', g.math('GREATER_THAN', t, 0.0), g.math('LESS_THAN', t, 1.0))
    teeth = g.math('MULTIPLY', g.math('LESS_THAN', t, tooth), inband)
    lines = g.math('ADD', g.math('LESS_THAN', g.math('ABSOLUTE', g.math('SUBTRACT', along, 0.849)), 0.003),
                   g.math('LESS_THAN', g.math('ABSOLUTE', g.math('SUBTRACT', along, 0.931)), 0.003))
    burned = g.math('MINIMUM', g.math('ADD', teeth, lines), 1.0)
    col = g.mix(burned, col, (0.012, 0.007, 0.004))
    h = g.math('ADD', g.math('MULTIPLY', crease, 0.6), g.math('MINIMUM', g.math('MULTIPLY', grain, 8.0), 1.0))
    h = g.math('SUBTRACT', h, g.math('MULTIPLY', burned, 0.5))
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=g.math('ADD', 0.58, g.math('MULTIPLY', blotch, 0.2)), Normal=g.bump(h, 0.35, 0.0006))
    bsdf.inputs['Sheen Weight'].default_value = 0.1
    return g.finish(bsdf.outputs[0])


def tube(path, radius, sides=12, caps=True):
    """A swept tube with its ends closed."""
    v, f = sweep(path, radius, sides=sides)
    f = list(f)
    if caps:
        n = len(path)
        f += [tuple(range(sides - 1, -1, -1)), tuple(range((n - 1) * sides, n * sides))]
    return v, f


# ----- the bow ---------------------------------------------------------------

def limb_points(kappa, n=60):
    """One limb from the end of the handle: an arc bending back toward him, as y falls."""
    t = np.linspace(0, LIMB, n)
    if kappa < 1e-6:
        return np.stack([np.zeros(n), np.zeros(n), GRIP_HALF + t], 1)
    return np.stack([np.zeros(n), -(1 - np.cos(kappa * t)) / kappa, GRIP_HALF + np.sin(kappa * t) / kappa], 1)


def drawn_shape(draw, over):
    """The limbs' curvature at full draw: as much bend as lets the string reach the nock."""
    nock = np.array([0.0, -draw, over])

    def reach(kappa):
        tip = limb_points(kappa)[-1]
        down = tip * np.array([1, 1, -1])
        return (np.linalg.norm(tip - nock) + np.linalg.norm(down - nock)) / 2

    lo, hi = 0.0, math.pi / LIMB
    for _ in range(60):
        mid = (lo + hi) / 2
        if reach(mid) > STRING / 2:
            lo = mid
        else:
            hi = mid
    kappa = (lo + hi) / 2
    print('bow bent', round(math.degrees(kappa * LIMB), 1), 'degrees at each tip; tips', round(-float(limb_points(kappa)[-1][1]), 3), 'm back', flush=True)
    return kappa


def bow_frame(centre, aim, up):
    x = up.cross(aim).normalized()            # his left as he looks along the shot
    y = (aim - aim.dot(up) * up).normalized()
    M = Matrix((x, y, up)).transposed().to_4x4()
    M.translation = centre
    return M


def make_bow(col, centre, aim, up, draw, over):
    """The bow at full draw, its handle at centre in his fist. Returns the bow, its grip, the string's two loops and the frame."""
    kappa = drawn_shape(draw, over)
    limb = limb_points(kappa)
    handle = np.stack([np.zeros(9), np.zeros(9), np.linspace(-GRIP_HALF, GRIP_HALF, 9)], 1)
    path = np.vstack([(limb * np.array([1, 1, -1]))[::-1], handle[1:-1], limb])
    t = np.clip((np.abs(path[:, 2]) - GRIP_HALF) / (np.abs(path[:, 2]).max() - GRIP_HALF), 0, 1)
    width = 0.032 * (1 - 0.58 * t ** 0.9)
    depth = 0.022 * (1 - 0.50 * t ** 0.9) + 0.006 * (t == 0)
    tan = np.gradient(path, axis=0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    side = np.tile(np.array([1.0, 0, 0]), (len(path), 1))
    nrm = np.cross(side, tan)
    m = 16
    a = np.linspace(0, 2 * np.pi, m, endpoint=False)
    # a D section: the back toward the mark nearly flat, the belly toward him rounded
    cy = np.sin(a)
    cy = np.where(cy > 0, np.abs(cy) ** 0.45, cy)
    verts = path[:, None] + side[:, None] * (np.cos(a)[None, :, None] * width[:, None, None] / 2) \
        - nrm[:, None] * (cy[None, :, None] * depth[:, None, None] / 2)
    verts = verts.reshape(-1, 3)
    rows = len(path)
    faces = [(i * m + j, (i + 1) * m + j, (i + 1) * m + (j + 1) % m, i * m + (j + 1) % m) for i in range(rows - 1) for j in range(m)]
    faces += [tuple(range(m - 1, -1, -1)), tuple(range((rows - 1) * m, rows * m))]
    bow = obj_from_arrays('Bow', verts, faces, col)
    bow.data.materials.append(wood_material())
    sub = bow.modifiers.new('Smooth', 'SUBSURF')
    sub.levels = sub.render_levels = 1
    grip = make_grip(col)
    M = bow_frame(centre, aim, up)
    for ob in (bow, grip):
        ob.matrix_world = M
    # the string's loops sit in notches a little short of each tip: bottom, then top
    loops = [M @ Vector(limb[-4] * np.array([1, 1, -1])), M @ Vector(limb[-4])]
    return bow, grip, loops, M


def make_grip(col):
    """The handle bound in a strip of hide, wound round with each turn overlapping the last."""
    rows, sides = 90, 28
    z = np.linspace(-GRIP_HALF - 0.008, GRIP_HALF + 0.008, rows)
    a = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    Z, A = np.meshgrid(z, a, indexing='ij')
    pitch = 0.013
    ridge = ((Z / pitch - A / (2 * np.pi)) % 1.0) ** 2           # each turn rises to its edge, then drops to the next
    taper = np.clip((GRIP_HALF + 0.008 - np.abs(Z)) / 0.004, 0, 1)
    r_x = (0.0168 + 0.0016 * ridge) * (0.85 + 0.15 * taper)
    r_y = (0.0148 + 0.0016 * ridge) * (0.85 + 0.15 * taper)
    verts = np.stack([np.cos(A) * r_x, np.sin(A) * r_y, Z], -1).reshape(-1, 3)
    faces = [(i * sides + j, i * sides + (j + 1) % sides, (i + 1) * sides + (j + 1) % sides, (i + 1) * sides + j) for i in range(rows - 1) for j in range(sides)]
    ob = obj_from_arrays('BowGrip', verts, faces, col)
    ob.data.materials.append(leather_material('GripLeather', (0.060, 0.030, 0.014)))
    return ob


def make_string(col, loops, through):
    """The string from loop to loop, drawn into the hooked fingers: through is its path across the hand, top to bottom."""
    pts = [np.array(loops[1])] + [np.array(p) for p in through] + [np.array(loops[0])]
    path = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        n = max(int(np.linalg.norm(b - a) / 0.01), 1)
        for k in range(1, n + 1):
            path.append(a + (b - a) * k / n)
    v, f = tube(np.array(path), 0.0013, sides=8)
    ob = obj_from_arrays('BowString', v, f, col)
    ob.data.materials.append(fibre_material())
    # the string is whipped thicker where it loops over each notch
    whips = []
    for end, nxt in ((pts[0], pts[1]), (pts[-1], pts[-2])):
        dvec = (nxt - end) / np.linalg.norm(nxt - end)
        whips.append(tube(np.array([end - dvec * 0.004, end + dvec * 0.016]), 0.0023, sides=8))
    v, f = merged(whips)
    whip = obj_from_arrays('StringLoops', v, f, col)
    whip.data.materials.append(fibre_material('Whipping', (0.20, 0.13, 0.06)))
    return ob


# ----- arrows ----------------------------------------------------------------

def arrow_parts(rng):
    """One arrow up +Z from its nock at the origin: a reed shaft with nodes, an iron head, two guinea-fowl feathers."""
    rows, sides = 150, 10
    z = np.linspace(0, ARROW_LONG, rows)
    node = np.zeros(rows)
    for k in range(1, 4):
        zk = ARROW_LONG * k / 4 + rng.normal(0, 0.012)
        node = np.maximum(node, np.exp(-((z - zk) / 0.0035) ** 2))
    r = SHAFT_R * (1 + 0.10 * node) * (1 - 0.06 * (z / ARROW_LONG))
    r[0] = SHAFT_R * 0.8                      # the nock end rounded off
    shaft = tube(np.stack([np.zeros(rows), np.zeros(rows), z], 1), r, sides=sides)
    shaft_node = np.repeat(node, sides)
    # the head: a leaf of iron with a ridge down its middle, its tang bound into the shaft
    hz = np.linspace(0, HEAD_LONG, 26)
    u = hz / HEAD_LONG
    w = 0.0108 * np.sin(np.pi * u ** 0.72) * (1 - 0.18 * u) + 0.0004
    hv, edge = [], []
    for i, zz in enumerate(hz):
        thick = 0.0019 * (1 - u[i]) + 0.0002
        for a in np.linspace(0, 2 * np.pi, 12, endpoint=False):
            ca, sa = math.cos(a), math.sin(a)
            hv.append((ca * w[i], sa * thick * (1 - 0.7 * abs(ca)) + sa * 0.0003, ARROW_LONG + 0.004 + zz))
            edge.append(1.0 if abs(sa) < 0.3 else 0.0)
    hf = [(i * 12 + j, (i + 1) * 12 + j, (i + 1) * 12 + (j + 1) % 12, i * 12 + (j + 1) % 12) for i in range(len(hz) - 1) for j in range(12)]
    hf.append(tuple(range(11, -1, -1)))
    binding = tube(np.array([[0, 0, ARROW_LONG - 0.026], [0, 0, ARROW_LONG - 0.020], [0, 0, ARROW_LONG + 0.006], [0, 0, ARROW_LONG + 0.010]]),
                   np.array([SHAFT_R * 0.98, SHAFT_R * 1.22, SHAFT_R * 1.22, SHAFT_R * 0.9]), sides=12)
    nock_wrap = tube(np.array([[0, 0, 0.004], [0, 0, 0.022]]), SHAFT_R * 1.10, sides=12)
    # fletching: two half-vanes, a little curved, opposite each other near the nock
    fv, ff, fuv = [], [], []
    for ang in (0.0, math.pi):
        rows_f, cols_f = 14, 6
        base = len(fv)
        for i in range(rows_f):
            uu = i / (rows_f - 1)
            zz = 0.032 + uu * 0.110
            height = 0.017 * math.sin(math.pi * min(uu * 1.08, 1.0)) ** 0.55 * (1 - 0.25 * uu) + 0.0015
            for j in range(cols_f):
                vv = j / (cols_f - 1)
                rr = SHAFT_R + vv * height
                bend = 0.0035 * vv * vv
                c, s_ = math.cos(ang), math.sin(ang)
                fv.append((c * rr - s_ * bend, s_ * rr + c * bend, zz - vv * 0.006))
                fuv.append((uu, vv))
        ff += [(base + i * cols_f + j, base + (i + 1) * cols_f + j, base + (i + 1) * cols_f + j + 1, base + i * cols_f + j + 1)
               for i in range(rows_f - 1) for j in range(cols_f - 1)]
    return shaft, shaft_node, (np.array(hv), hf, np.array(edge)), [binding, nock_wrap], (np.array(fv), ff, np.array(fuv))


def build_arrows(col, placements, rng, name='Arrow'):
    """Arrows stood on their lines: each placement matrix takes an arrow's +Z, nock first, onto its line."""
    shafts, nodes, heads, edges, binds, feathers, fuvs = [], [], [], [], [], [], []
    for M in placements:
        shaft, node, head, wraps, fl = arrow_parts(rng)
        R = np.array(M.to_3x3())
        T = np.array(M.translation)

        def tf(v):
            return np.asarray(v) @ R.T + T
        shafts.append((tf(shaft[0]), shaft[1]))
        nodes.append(node)
        heads.append((tf(head[0]), head[1]))
        edges.append(head[2])
        binds += [(tf(w[0]), w[1]) for w in wraps]
        feathers.append((tf(fl[0]), fl[1]))
        fuvs.append(fl[2])
    v, f = merged(shafts)
    shaft_ob = obj_from_arrays(f'{name}Shafts', v, f, col)
    shaft_ob.data.attributes.new('node', 'FLOAT', 'POINT').data.foreach_set('value', np.concatenate(nodes).astype(np.float32))
    shaft_ob.data.materials.append(bpy.data.materials.get('Reed') or reed_material())
    v, f = merged(heads)
    head_ob = obj_from_arrays(f'{name}Heads', v, f, col)
    head_ob.data.attributes.new('edge', 'FLOAT', 'POINT').data.foreach_set('value', np.concatenate(edges).astype(np.float32))
    head_ob.data.materials.append(bpy.data.materials.get('ArrowIron') or iron_material())
    v, f = merged(binds)
    bind_ob = obj_from_arrays(f'{name}Bindings', v, f, col)
    bind_ob.data.materials.append(bpy.data.materials.get('Binding') or fibre_material('Binding', (0.20, 0.13, 0.06)))
    v, f = merged(feathers)
    fl_ob = obj_from_arrays(f'{name}Feathers', v, f, col, uv=np.concatenate(fuvs))
    fl_ob.data.materials.append(bpy.data.materials.get('GuineaFowl') or feather_material())
    sol = fl_ob.modifiers.new('Thickness', 'SOLIDIFY')
    sol.thickness = 0.0004
    return [shaft_ob, head_ob, bind_ob, fl_ob]


def arrow_matrix(nock, toward, vanes_across):
    """Stand an arrow at nock pointing to toward, its two vanes lying along vanes_across."""
    d = (Vector(toward) - Vector(nock)).normalized()
    x = Vector(vanes_across)
    x = (x - x.dot(d) * d).normalized()
    M = Matrix((x, d.cross(x), d)).transposed().to_4x4()
    M.translation = Vector(nock)
    return M


def nocked_arrow(col, nock, rest, up):
    """The arrow on the string: nock in the drawing fingers, laid over the bow hand, its vanes square to the string."""
    d = (Vector(rest) - Vector(nock)).normalized()
    across = Vector(up).cross(d)
    return build_arrows(col, [arrow_matrix(nock, rest, across)], np.random.default_rng(3), 'Nocked')


# ----- the strap and the quiver on it ---------------------------------------------

def posed_verts(body):
    saved = [(m, m.show_viewport) for m in body.modifiers if m.type in ('MASK', 'SUBSURF')]
    for m, _ in saved:
        m.show_viewport = False
    co = verts_world(body)
    for m, on in saved:
        m.show_viewport = on
    return co


def group_weight(body, keys):
    groups = {g.index for g in body.vertex_groups if any(k in g.name for k in keys)}
    return np.array([sum(g.weight for g in v.groups if g.group in groups) for v in body.data.vertices])


def hull_2d(p):
    """Convex hull of 2D points, counter-clockwise (Andrew's monotone chain)."""
    pts = sorted(map(tuple, p))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for q in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], q) <= 0:
            lower.pop()
        lower.append(q)
    for q in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], q) <= 0:
            upper.pop()
        upper.append(q)
    return np.array(lower[:-1] + upper[:-1])


def resample_closed(poly, step):
    closed = np.vstack([poly, poly[:1]])
    cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(closed, axis=0), axis=1))])
    n = max(int(cum[-1] / step), 8)
    s = np.linspace(0, cum[-1], n, endpoint=False)
    return np.stack([np.interp(s, cum, closed[:, i]) for i in range(poly.shape[1])], 1), cum[-1]


def strap_plane(rig):
    """The plane the strap lies in: through his right shoulder and his left side above the hip."""
    P = rig.pose.bones
    shoulder = np.array(P['shoulder01.R'].head) + np.array([0.004, 0.0, 0.0])
    hip = np.array([float(P['pelvis.L'].tail.x) + 0.06, float(P['pelvis.L'].tail.y), float(P['pelvis.L'].head.z) + 0.10])
    d = (hip - shoulder) / np.linalg.norm(hip - shoulder)
    y = np.array([0, 1.0, 0])
    y = y - y.dot(d) * d
    y /= np.linalg.norm(y)
    return shoulder, hip, d, y, np.cross(d, y)


def make_strap(body, tunic, rig, col, width=0.036, thick=0.0032):
    """The strap: the section of his body and tunic in its plane, pulled taut, so it bridges the hollows it crosses.

    The forearms and hands are left out, so it does not wrap round the drawing arm; the upper arm only
    near the shoulder, where the strap has to lie over the deltoid.
    """
    shoulder, hip, d, y, n = strap_plane(rig)
    P = rig.pose.bones
    co = posed_verts(body)
    fore = group_weight(body, ('lowerarm', 'wrist', 'finger', 'metacarpal'))
    upper = group_weight(body, ('upperarm',))
    joint = np.array(P['upperarm01.R'].head)
    keep = (fore < 0.1) & ((upper < 0.15) | (np.linalg.norm(co - joint, axis=1) < 0.09))
    pts = np.vstack([co[keep], verts_world(tunic)])
    near = np.abs((pts - shoulder) @ n) < width / 2 + 0.008
    uv = np.stack([(pts[near] - shoulder) @ d, (pts[near] - shoulder) @ y], 1)
    hull = hull_2d(uv)
    loop, total = resample_closed(hull, 0.004)
    for _ in range(4):
        loop = (loop + np.roll(loop, 1, 0) + np.roll(loop, -1, 0)) / 3
    tan = np.roll(loop, -1, 0) - np.roll(loop, 1, 0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    out2 = np.stack([tan[:, 1], -tan[:, 0]], 1)          # counter-clockwise: outward is to the right
    for _ in range(12):                                   # leather turns gradually round a corner, it does not crease
        out2 = (out2 + np.roll(out2, 1, 0) + np.roll(out2, -1, 0)) / 3
        out2 /= np.linalg.norm(out2, axis=1, keepdims=True)
    loop3 = shoulder + loop[:, :1] * d + loop[:, 1:] * y
    out3 = out2[:, :1] * d + out2[:, 1:] * y
    m = len(loop3)
    tan3 = np.roll(loop3, -1, 0) - np.roll(loop3, 1, 0)
    tan3 /= np.linalg.norm(tan3, axis=1, keepdims=True)
    sd = np.cross(tan3, out3)
    sd /= np.linalg.norm(sd, axis=1, keepdims=True)
    base = loop3 + out3 * (thick / 2 + 0.003)
    rings = [base + sd * (u * width) + out3 * (w * thick / 2) for u, w in ((-0.5, -1), (0.5, -1), (0.5, 1), (-0.5, 1))]
    verts = np.concatenate(rings)
    faces = []
    for k in range(4):
        a, b = k * m, ((k + 1) % 4) * m
        faces += [(a + i, a + (i + 1) % m, b + (i + 1) % m, b + i) for i in range(m)]
    strap = obj_from_arrays('QuiverStrap', verts, faces, col, smooth=False)      # flat-shaded, so its face reads flat and its edges square
    strap.data.materials.append(leather_material('StrapLeather', (0.070, 0.036, 0.016)))
    print('strap length', round(total, 3), 'm', flush=True)
    return strap, loop, (shoulder, d, y)


def make_quiver(col, loop, plane, thick=0.0032):
    """A quiver of hide laid on the strap's run across his back, its mouth behind his right shoulder,
    with six arrows standing in it, heads down, feathers out of the mouth."""
    shoulder, d, y = plane
    u0, u1 = 0.03, 0.03 + QUIVER_LONG
    back = loop[loop[:, 1] > 0.02]
    usable = back[(back[:, 0] > u0 - 0.06) & (back[:, 0] < u1)]

    def v_at(u):
        w = usable[np.abs(usable[:, 0] - u) < 0.02]
        return float(w[:, 1].max()) if len(w) else float(usable[:, 1].max())
    lo_u = min(u1, float(usable[:, 0].max()) - 0.02)
    slope = (v_at(lo_u) - v_at(u0)) / (lo_u - u0)
    lift = max(float((usable[:, 1] - (v_at(u0) + slope * (usable[:, 0] - u0))).max()), 0.0)
    clear = lift + thick + 0.004 + QUIVER_R
    top = shoulder + d * u0 + y * (v_at(u0) + clear)
    bottom = shoulder + d * u1 + y * (v_at(u0) + slope * (u1 - u0) + clear)
    axis = (top - bottom) / np.linalg.norm(top - bottom)
    mouth = bottom + axis * QUIVER_LONG
    rows, sides = 40, 28
    s = np.linspace(0, 1, rows)
    r = QUIVER_R * (0.82 + 0.18 * s) * (1 + 0.02 * np.sin(s * 23))
    # the foot is closed in a dome of hide, sewn up to a point
    phi = np.linspace(0, np.pi / 2, 7)[:-1]
    dome = -(r[0] * 0.55 * np.cos(phi))
    path = bottom[None] + axis[None] * np.concatenate([dome, s * QUIVER_LONG])[:, None]
    radius = np.concatenate([np.maximum(r[0] * np.sin(phi), 0.002), r])
    v, f = sweep(path, radius, sides=sides, up=tuple(y))
    f = list(f) + [tuple(range(sides - 1, -1, -1))]
    q = obj_from_arrays('Quiver', v, f, col)
    a = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    for name, values in (('along', np.repeat(np.concatenate([dome / QUIVER_LONG, s]), sides)),
                         ('cosa', np.tile(np.cos(a), len(path))), ('sina', np.tile(np.sin(a), len(path)))):
        q.data.attributes.new(name, 'FLOAT', 'POINT').data.foreach_set('value', values.astype(np.float32))
    q.data.materials.append(quiver_material())
    sol = q.modifiers.new('Thickness', 'SOLIDIFY')
    sol.thickness = 0.003
    sol.offset = -1
    # a rolled rim at the mouth and two bands of darker hide, where the strap is laced on
    bands = []
    for at, rr, wide in ((QUIVER_LONG - 0.004, 1.06, 0.010), (QUIVER_LONG - 0.07, 1.05, 0.016), (0.06, 1.06, 0.016)):
        c = bottom + axis * at
        k = float(np.interp(at / QUIVER_LONG, s, r))
        bands.append(sweep(np.array([c - axis * wide / 2, c + axis * wide / 2]), k * rr, sides=sides, up=tuple(y)))
    v, f = merged(bands)
    rim = obj_from_arrays('QuiverBands', v, f, col)
    rim.data.materials.append(leather_material('QuiverBand', (0.050, 0.026, 0.012)))
    # six arrows, heads down, fanned a little so their feathers part at the mouth
    rng = np.random.default_rng(17)
    side = np.cross(axis, y)
    side /= np.linalg.norm(side)
    out = np.cross(side, axis)
    placements = []
    for k in range(6):
        ang = k / 6 * 2 * math.pi + rng.uniform(-0.3, 0.3)
        radial = side * math.cos(ang) + out * math.sin(ang)
        at_mouth = mouth + radial * QUIVER_R * 0.55 * math.sqrt(rng.uniform(0.2, 1.0))
        dvec = axis + radial * rng.uniform(0.02, 0.06)
        dvec /= np.linalg.norm(dvec)
        nock = at_mouth + dvec * NOCK_OUT
        placements.append(arrow_matrix(nock, at_mouth, Vector(side) * math.cos(ang * 0.5) + Vector(out) * math.sin(ang * 0.5)))
    arrows = build_arrows(col, placements, rng, 'Quivered')
    print('quiver: mouth', tuple(np.round(mouth, 3)), 'foot', tuple(np.round(bottom, 3)), 'stands off', round(clear, 3), flush=True)
    return q, mouth, axis, arrows
