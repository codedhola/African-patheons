"""His iron: the àdá, the chain of small tools across his chest, and the bangles.

Iron is Ògún's first emblem, and his followers wear chains of iron implements (Wikipedia:
Ogun). The forms here are this study's: hand-forged pieces, black with fire scale, worn
bright where they are handled or sharpened, rusting a little in their hollows.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

import dress
import materials as mats
from common import obj_from_arrays, verts_world
from procedural import Noise

BLADE_START = 0.070      # from the grip's centre to where the blade leaves the ferrule
BLADE_LONG = 0.445
HANDLE_HALF = 0.064


def iron_material(name='Iron', honed=False):
    """Forged iron: a coat of black scale, bright steel where it is worn, rust in the hollows.

    honed: an 'edge' point attribute gives the distance in metres from a cutting edge, and a
    band along it is ground bright with fine scratches running along the blade.
    """
    g = mats.Graph(name)
    tc = g.node('TexCoord')
    obj = tc.outputs['Object']
    geo = g.node('NewGeometry')
    scale_n = g.node('TexNoise', Vector=obj, Scale=38, Detail=6, Roughness=0.62).outputs['Fac']
    fine = g.node('TexNoise', Vector=obj, Scale=420, Detail=4, Roughness=0.6).outputs['Fac']
    pits = g.node('TexVoronoi', Vector=obj, Scale=260, Randomness=1.0).outputs['Distance']
    peen = g.node('TexVoronoi', Vector=obj, Scale=55, Randomness=0.9).outputs['Distance']
    ao = g.node('AmbientOcclusion', Distance=0.012, samples=8).outputs['AO']

    # worn: edges and high spots where hands and use rub through the scale
    worn = g.math('ADD', g.math('MULTIPLY', g.math('SUBTRACT', geo.outputs['Pointiness'], 0.56), 3.5), g.math('MULTIPLY', g.math('SUBTRACT', scale_n, 0.66), 2.0), clamp=True)
    # rust: in the hollows, broken up by noise
    rust = g.math('MULTIPLY', g.math('SUBTRACT', 1.0, ao), 1.6)
    rust = g.math('MULTIPLY', rust, g.math('ADD', g.math('MULTIPLY', fine, 1.4), -0.35), clamp=True)

    scale_col = g.ramp(scale_n, [(0.35, (0.016, 0.016, 0.018)), (0.55, (0.032, 0.030, 0.030)), (0.75, (0.050, 0.044, 0.040))])
    steel_col = (0.30, 0.295, 0.285)
    rust_col = g.ramp(fine, [(0.3, (0.10, 0.035, 0.015)), (0.7, (0.24, 0.085, 0.030))])
    col = g.mix(worn, scale_col, steel_col)
    col = g.mix(rust, col, rust_col)
    metal = g.math('ADD', g.math('MULTIPLY', worn, 0.65), 0.30)
    metal = g.math('MULTIPLY', metal, g.math('SUBTRACT', 1.0, rust), clamp=True)
    rough = g.math('ADD', g.math('MULTIPLY', worn, -0.24), g.math('ADD', 0.58, g.math('MULTIPLY', fine, 0.12)))
    rough = g.mix(rust, rough, 0.88)
    height = g.math('ADD', g.math('MULTIPLY', peen, 0.55), g.math('MULTIPLY', pits, 0.25))
    height = g.math('ADD', height, g.math('MULTIPLY', rust, 0.4))

    if honed:
        edge = g.node('Attribute', attribute_name='edge', attribute_type='GEOMETRY').outputs['Fac']
        band = g.math('LESS_THAN', edge, 0.0065)
        # the grinding leaves a wavering line, not a ruled one
        wav = g.node('TexNoise', Vector=obj, Scale=70, Detail=3).outputs['Fac']
        band = g.math('LESS_THAN', edge, g.math('ADD', 0.0042, g.math('MULTIPLY', wav, 0.0045)))
        stretched = g.node('Mapping', Vector=obj, Scale=(1.0, 1.0, 0.004)).outputs[0]
        scratch = g.node('TexNoise', Vector=stretched, Scale=900, Detail=2).outputs['Fac']
        col = g.mix(band, col, g.ramp(scratch, [(0.35, (0.50, 0.50, 0.49)), (0.65, (0.68, 0.67, 0.65))]))
        metal = g.mix(band, metal, 1.0)
        rough = g.mix(band, rough, g.math('ADD', 0.16, g.math('MULTIPLY', scratch, 0.12)))
        height = g.mix(band, height, g.math('MULTIPLY', scratch, 0.3))
    normal = g.bump(height, 0.35, 0.0006)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Metallic=metal, Roughness=rough, Normal=normal)
    return g.finish(bsdf.outputs[0])


def wood_material(name='HandleWood'):
    """A hardwood handle, darkened and polished by years of a hand's oil."""
    g = mats.Graph(name)
    obj = g.node('TexCoord').outputs['Object']
    stretched = g.node('Mapping', Vector=obj, Scale=(9.0, 9.0, 0.7)).outputs[0]
    grain = g.node('TexWave', Vector=stretched, Scale=6.0, Distortion=6.0, Detail=4, wave_type='RINGS').outputs['Fac']
    grime = g.node('TexNoise', Vector=obj, Scale=60, Detail=5).outputs['Fac']
    col = g.ramp(grain, [(0.2, (0.050, 0.022, 0.010)), (0.6, (0.110, 0.052, 0.022)), (1.0, (0.150, 0.075, 0.034))])
    col = g.mix(g.math('MULTIPLY', grime, 0.5), col, (0.030, 0.016, 0.009))
    normal = g.bump(grain, 0.08, 0.0004)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=g.math('ADD', 0.36, g.math('MULTIPLY', grime, 0.2)), Normal=normal)
    bsdf.inputs['Coat Weight'].default_value = 0.25
    bsdf.inputs['Coat Roughness'].default_value = 0.35
    return g.finish(bsdf.outputs[0])


def blade_section(width, thick, edge_w, n_face=14, n_spine=6):
    """Closed cross-section of a flat-ground blade, from the edge (y = 0) to the spine (y = width).

    Returns points (x, y) round the loop and each point's distance from the edge.
    """
    ys = np.concatenate([np.linspace(0, edge_w, n_face // 2, endpoint=False), np.linspace(edge_w, width, n_face - n_face // 2)])
    half = np.where(ys < edge_w, 0.0002 + (thick / 2 - 0.0002) * (ys / edge_w) ** 1.15, thick / 2)
    left = np.stack([half, ys], 1)
    a = np.linspace(0, np.pi, n_spine + 2)[1:-1]
    spine = np.stack([thick / 2 * np.cos(a), width + thick / 2 * 0.6 * np.sin(a)], 1)
    right = np.stack([-half[::-1], ys[::-1]], 1)
    pts = np.vstack([left, spine, right])
    return pts, pts[:, 1]


def make_machete(col):
    """The àdá along +Z from the middle of its grip, cutting edge toward -Y.

    About 58 cm overall. The blade is a smith's: widening toward a rounded point, the spine
    straight, the flats left black from the fire and the edge ground bright.
    """
    noise = Noise(41)
    stations = 150
    t = np.linspace(0, 1, stations)
    z = BLADE_START + t * BLADE_LONG
    # widening from the ferrule, rounding into the point over the last eighth
    w = 0.040 + 0.024 * np.clip(t / 0.82, 0, 1) ** 0.9
    tipzone = np.clip((t - 0.86) / 0.14, 0, 1)
    w = w * np.sqrt(np.clip(1 - tipzone ** 2.2, 0, 1)) + 0.0015
    thick = 0.0042 - 0.0018 * t
    # the spine stays straight; the edge drops as the blade widens, and the whole blade sweeps a little up
    sweep = 0.010 * t ** 2.2
    verts, edge_d = [], []
    nsec = None
    for i in range(stations):
        sec, d = blade_section(w[i], thick[i], min(0.016, w[i] * 0.42))
        nsec = len(sec)
        hammer = 0.00012 * noise(np.array([z[i] * 60, 0.5, 0.0]))
        y = 0.016 - w[i] + sec[:, 1] + sweep[i]
        verts.append(np.stack([sec[:, 0] + hammer, y, np.full(nsec, z[i])], 1))
        edge_d.append(d)
    verts = np.vstack(verts)
    edge_d = np.concatenate(edge_d)
    faces = []
    for i in range(stations - 1):
        for j in range(nsec):
            k = (j + 1) % nsec
            faces.append((i * nsec + j, i * nsec + k, (i + 1) * nsec + k, (i + 1) * nsec + j))
    faces.append(tuple(range(nsec))[::-1])
    faces.append(tuple(range((stations - 1) * nsec, stations * nsec)))
    blade = obj_from_arrays('Ada', verts, faces, col)
    blade.data.attributes.new('edge', 'FLOAT', 'POINT').data.foreach_set('value', edge_d.astype(np.float32))
    blade.data.materials.append(iron_material('AdaIron', honed=True))

    # the handle: oval, swelling to the butt, a forged ferrule at the blade and two rivets
    hz = np.linspace(-HANDLE_HALF, HANDLE_HALF, 60)
    s = (hz + HANDLE_HALF) / (2 * HANDLE_HALF)
    rx = 0.0118 + 0.0022 * (1 - s) ** 2 + 0.0012 * np.sin(np.pi * s)
    ry = 0.0150 + 0.0030 * (1 - s) ** 2 + 0.0010 * np.sin(np.pi * s)
    a = np.linspace(0, 2 * np.pi, 28, endpoint=False)
    hv = np.stack([np.outer(rx, np.cos(a)), np.outer(ry, np.sin(a)) + 0.001, np.tile(hz[:, None], (1, len(a)))], -1).reshape(-1, 3)
    hf = [(i * 28 + j, i * 28 + (j + 1) % 28, (i + 1) * 28 + (j + 1) % 28, (i + 1) * 28 + j) for i in range(59) for j in range(28)]
    hf.append(tuple(range(28))[::-1])
    hf.append(tuple(range(59 * 28, 60 * 28)))
    handle = obj_from_arrays('AdaHandle', hv, hf, col)
    handle.data.materials.append(wood_material())
    sub = handle.modifiers.new('Smooth', 'SUBSURF')
    sub.levels = sub.render_levels = 1

    # ferrule and rivets
    fz = np.linspace(HANDLE_HALF - 0.004, BLADE_START + 0.002, 8)
    fr = np.interp(fz, [fz[0], fz[-1]], [1.06, 0.92])
    fv = np.stack([np.outer(fr * 0.0128, np.cos(a)), np.outer(fr * 0.0165, np.sin(a)) + 0.001, np.tile(fz[:, None], (1, len(a)))], -1).reshape(-1, 3)
    ff = [(i * 28 + j, i * 28 + (j + 1) % 28, (i + 1) * 28 + (j + 1) % 28, (i + 1) * 28 + j) for i in range(7) for j in range(28)]
    parts = [(fv, ff)]
    for rz in (-0.028, 0.022):
        r_here = float(np.interp(rz, hz, rx))
        for side in (1, -1):
            v, f = dress.sphere(0.0034, 8, 12)[:2]
            # a domed head pressed flat against the wood
            parts.append((v * np.array([0.4, 1, 1]) + np.array([side * (r_here - 0.0004), 0.001, rz]), f))
    from procedural import merged
    v, f = merged(parts)
    fittings = obj_from_arrays('AdaFittings', v, f, col)
    fittings.data.materials.append(bpy.data.materials.get('Iron') or iron_material())
    for ob in (handle, fittings):
        ob.parent = blade
    return blade


# ----- the chain of tools -------------------------------------------------

LINK_INNER = 0.0255      # inner length of a link, which is also the chain's pitch
LINK_WIDE = 0.0128       # inner width
WIRE = 0.0039            # radius of the rod the links are bent from


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


def baldric(points, shoulder, hip):
    """Where a chain worn from one shoulder to the other hip lies: the torso's section in that plane, pulled taut.

    A chain under the pull of its tools bridges the hollows it crosses, so the section is its
    convex hull. Returns the loop in 3D, its outward normals, and the plane's two axes.
    """
    d = (hip - shoulder) / np.linalg.norm(hip - shoulder)
    y = np.array([0, 1.0, 0])
    y = y - y.dot(d) * d
    y /= np.linalg.norm(y)
    n = np.cross(d, y)
    near = np.abs((points - shoulder) @ n) < 0.010
    uv = np.stack([(points[near] - shoulder) @ d, (points[near] - shoulder) @ y], 1)
    hull = hull_2d(uv)
    loop, length = resample_closed(hull, 0.004)
    for _ in range(4):
        loop = (loop + np.roll(loop, 1, 0) + np.roll(loop, -1, 0)) / 3
    tan = np.roll(loop, -1, 0) - np.roll(loop, 1, 0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    out2 = np.stack([tan[:, 1], -tan[:, 0]], 1)          # counter-clockwise hull: outward is to the right
    loop3 = shoulder + loop[:, :1] * d + loop[:, 1:] * y
    out3 = out2[:, :1] * d + out2[:, 1:] * y
    return loop3, out3, length


def link_mesh(seed, rows=40, sides=10):
    """One hand-forged oval link lying in the XY plane, long along X, a little out of true."""
    n = Noise(seed)
    a = LINK_WIDE / 2 + WIRE
    straight = LINK_INNER - LINK_WIDE
    cum = []
    pts = []
    per = 2 * straight + 2 * np.pi * a
    for i in range(rows):
        s = i / rows * per
        if s < straight:
            p = (-straight / 2 + s, -a)
        elif s < straight + np.pi * a:
            t = (s - straight) / a
            p = (straight / 2 + a * math.sin(t), -a * math.cos(t))
        elif s < 2 * straight + np.pi * a:
            p = (straight / 2 - (s - straight - np.pi * a), a)
        else:
            t = (s - 2 * straight - np.pi * a) / a
            p = (-straight / 2 - a * math.sin(t), a * math.cos(t))
        pts.append(p)
    pts = np.array(pts)
    verts = []
    for i, (x, y) in enumerate(pts):
        j = (i + 1) % rows
        tx, ty = pts[j] - pts[i - 1]
        L = math.hypot(tx, ty)
        nx, ny = ty / L, -tx / L
        wob = 1 + 0.06 * float(n(np.array([x * 90, y * 90, seed * 1.3])))
        for k in range(sides):
            b = 2 * math.pi * k / sides
            r = WIRE * wob
            verts.append((x + nx * r * math.cos(b), y + ny * r * math.cos(b), r * math.sin(b)))
    faces = [(i * sides + k, i * sides + (k + 1) % sides, ((i + 1) % rows) * sides + (k + 1) % sides, ((i + 1) % rows) * sides + k)
             for i in range(rows) for k in range(sides)]
    return np.array(verts, np.float32), faces


def frame(x_axis, normal):
    """Rotation whose X runs along x_axis and whose Z is as near normal as it can be."""
    x = x_axis / np.linalg.norm(x_axis)
    z = normal - normal.dot(x) * x
    z /= np.linalg.norm(z)
    return np.stack([x, np.cross(z, x), z], 1)


def tool_parts(kind, rng):
    """A miniature tool hanging from the origin along -Z, its flat face toward -Y. Mesh parts."""
    from procedural import sweep
    parts = []

    def plate(outline, thick, z_round=0.0):
        """A flat plate from a closed 2D outline in XZ, thick along Y, edges softened."""
        o = np.asarray(outline, float)
        k = len(o)
        front = np.stack([o[:, 0], np.full(k, -thick / 2), o[:, 1]], 1)
        back = np.stack([o[:, 0], np.full(k, thick / 2), o[:, 1]], 1)
        c = o.mean(0)
        cf = np.array([[c[0], -thick / 2 - z_round, c[1]]])
        cb = np.array([[c[0], thick / 2 + z_round, c[1]]])
        v = np.vstack([front, back, cf, cb])
        f = [(i, (i + 1) % k, k + (i + 1) % k, k + i) for i in range(k)]
        f += [(2 * k, (i + 1) % k, i) for i in range(k)]
        f += [(2 * k + 1, k + i, k + (i + 1) % k) for i in range(k)]
        return v, f

    def eye(z, r=0.0055):
        a = np.linspace(0, 2 * np.pi, 24)
        return sweep(np.stack([r * np.sin(a), np.zeros(24), z - r + r * np.cos(a)], 1), 0.0016, sides=6)

    if kind == 'hoe':
        # a broad blade with sloping shoulders and a curved edge, on a narrow neck
        a = np.linspace(0, np.pi, 13)
        o = [(-0.006, -0.018), (0.006, -0.018), (0.024, -0.026), (0.032, -0.047)] + [(0.032 * math.cos(t), -0.047 - 0.010 * math.sin(t)) for t in a[1:-1]] + [(-0.032, -0.047), (-0.024, -0.026)]
        parts.append(plate(o, 0.0022, 0.0004))
        parts.append(sweep(np.array([(0, 0, -0.004), (0, 0, -0.019)]), 0.0024, sides=8))
        parts.append(eye(0.0))
    elif kind == 'hammer':
        parts.append(sweep(np.array([(0, 0, -0.005), (0, 0, -0.058)]), 0.0028, sides=8))
        head = np.array([(-0.024, 0, -0.064), (0.020, 0, -0.064)])
        parts.append(sweep(head, np.array([0.0062, 0.0075]), sides=4))
        parts.append(eye(0.0))
    elif kind == 'ada':
        s = np.linspace(0, 1, 16)
        w = 0.0085 + 0.006 * s - 0.010 * np.clip((s - 0.82) / 0.18, 0, 1) ** 2
        spine = np.stack([np.full(16, 0.004), -0.014 - s * 0.072], 1)
        edge = np.stack([0.004 - w * 2, -0.014 - s * 0.072], 1)
        o = np.vstack([spine, edge[::-1]])
        parts.append(plate(o, 0.0022, 0.0004))
        parts.append(sweep(np.array([(0, 0, -0.004), (0, 0, -0.015)]), 0.0032, sides=8))
        parts.append(eye(0.0))
    elif kind == 'tongs':
        for sign in (1, -1):
            arm = np.array([(sign * 0.003, 0, -0.006), (sign * 0.007, 0, -0.030), (-sign * 0.004, 0, -0.050), (-sign * 0.010, 0, -0.074), (-sign * 0.007, 0, -0.080)])
            parts.append(sweep(arm, 0.0021, sides=6))
        parts.append(sweep(np.array([(0, -0.004, -0.042), (0, 0.004, -0.042)]), 0.0030, sides=8))
        parts.append(eye(0.0, 0.0062))
    elif kind == 'spear':
        s = np.linspace(0, 1, 18)
        half = 0.012 * np.sin(np.pi * np.clip(s * 1.05, 0, 1)) ** 0.8 * (1 - s) ** 0.35 + 0.0005
        z = -0.024 - s * 0.056
        o = np.vstack([np.stack([half, z], 1), np.stack([-half[::-1], z[::-1]], 1)])
        parts.append(plate(o, 0.0024, 0.0012))
        parts.append(sweep(np.array([(0, 0, -0.004), (0, 0, -0.026)]), np.array([0.0030, 0.0046]), sides=10))
        parts.append(eye(0.0))
    elif kind == 'ring':
        a = np.linspace(0, 2 * np.pi, 48)
        parts.append(sweep(np.stack([0.019 * np.sin(a), np.zeros(48), -0.020 + 0.019 * np.cos(a)], 1), 0.0029, sides=8))
    return parts


TOOLS = ('hoe', 'hammer', 'ada', 'tongs', 'spear', 'ring')
TOOL_SCALE = 1.35        # as on the gallery figure


def posed_verts(body):
    """The posed body's own vertices, one per base vertex: masking and smoothing switched off while reading them."""
    saved = [(m, m.show_viewport) for m in body.modifiers if m.type in ('MASK', 'SUBSURF')]
    for m, _ in saved:
        m.show_viewport = False
    co = verts_world(body)
    for m, on in saved:
        m.show_viewport = on
    return co


def make_chain(body, cloth_obs, rig, col, material, cord_top):
    """The chain over his left shoulder to his right side, with six small tools hung from it."""
    from procedural import merged
    from cloth import arm_weight
    co = posed_verts(body)
    keep = arm_weight(body) < 0.15
    pts = [co[keep]]
    for ob in cloth_obs:
        pts.append(verts_world(ob))
    pts = np.vstack(pts)
    P = rig.pose.bones
    shoulder = np.array(P['shoulder01.L'].head) + np.array([-0.012, 0.0, 0.0])
    hip = np.array([float(P['pelvis.R'].tail.x) - 0.06, float(P['pelvis.R'].tail.y), cord_top + 0.055])
    loop, out, length = baldric(pts, shoulder, hip)
    # lay links along it: each lies along the loop, every other one turned on its edge
    closed = np.vstack([loop, loop[:1]])
    cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(closed, axis=0), axis=1))])
    nlinks = int(cum[-1] / LINK_INNER)
    pitch = cum[-1] / nlinks
    rng = np.random.default_rng(61)
    parts, centres = [], []
    for i in range(nlinks):
        s = i * pitch
        c = np.array([np.interp(s, cum, closed[:, k]) for k in range(3)])
        c2 = np.array([np.interp(s + 0.003, cum, closed[:, k]) for k in range(3)])
        o = np.array([np.interp(s, cum, np.vstack([out, out[:1]])[:, k]) for k in range(3)])
        o /= np.linalg.norm(o)
        flat = i % 2 == 0
        lift = WIRE + 0.0007 if flat else LINK_WIDE / 2 + WIRE + 0.0007
        R = frame(c2 - c, o if flat else np.cross(c2 - c, o))
        v, f = link_mesh(100 + i)
        parts.append(((R @ v.T).T + c + o * lift, f))
        centres.append((s, c + o * lift, o, c2 - c))
    print('chain links', nlinks, 'pitch', round(pitch, 4), 'length', round(cum[-1], 3), flush=True)

    # the tools hang from the front of the chain, between the chest and the hip
    front = [k for k, (s, c, o, t) in enumerate(centres) if o[1] < -0.35 and shoulder[2] - 0.07 > c[2] > cord_top + 0.07]
    front.sort(key=lambda k: -centres[k][1][2])
    # spread along the run from the collarbone to the hip, a link's gap at each end
    picks = np.linspace(0.6, len(front) - 1.6, len(TOOLS)).round().astype(int)
    tree = surface_tree(body, cloth_obs)
    hung = 0
    for kind, j in zip(TOOLS, picks):
        s, c, o, t = centres[front[j]]
        top = c - np.array([0, 0, LINK_WIDE / 2 + WIRE * 0.5])
        # a little ring through the link carries each tool
        a = np.linspace(0, 2 * np.pi, 20)
        across = np.cross(t / np.linalg.norm(t), (0, 0, 1.0))
        across /= np.linalg.norm(across)
        ring = top + np.outer(np.cos(a), across) * 0.0055 + np.outer(np.sin(a), (0, 0, 1.0)) * 0.0055 - np.array([0, 0, 0.0045])
        parts.append(sweep_ring(ring))
        hang = top - np.array([0, 0, 0.0110])
        tp = tool_parts(kind, rng)
        tv, tf = merged(tp)
        tv = tv * TOOL_SCALE
        length_t = float(-tv[:, 2].min())
        # hang straight down unless the body below is further out, then rest on it
        down = np.array([0, 0, -1.0])
        foot = hang + down * length_t
        start = Vector(foot + o * 0.25)
        hit = tree.ray_cast(start, Vector(-o), 0.5)
        if hit[0] is not None:
            surf = np.array(hit[0]) + np.array(hit[1]) * 0.003
            if (surf - foot) @ o > 0:
                down = surf - hang
                down /= np.linalg.norm(down)
        z = -down
        yv = -(o - o.dot(z) * z)
        yv /= np.linalg.norm(yv)
        xv = np.cross(yv, z)
        R = np.stack([xv, yv, z], 1) @ np.array(Matrix.Rotation(rng.normal(0, 0.12), 3, 'Z'))
        parts.append(((R @ tv.T).T + hang, tf))
        hung += 1
    v, f = merged(parts)
    ob = obj_from_arrays('Chain', v, f, col)
    ob.data.materials.append(material)
    print('tools', hung, flush=True)
    return ob


def sweep_ring(ring):
    from procedural import sweep
    return sweep(np.vstack([ring, ring[:1]]), 0.0015, sides=6)


def surface_tree(body, others):
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys, base = [], [], 0
    for ob in [body] + list(others):
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        verts += [ev.matrix_world @ v.co for v in me.vertices]
        polys += [tuple(i + base for i in p.vertices) for p in me.polygons]
        base += len(me.vertices)
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys)


def limb_radius(co, centre, axis):
    w = co - centre
    h = w @ axis
    rad = np.linalg.norm(w - h[:, None] * axis, axis=1)
    near = (np.abs(h) < 0.008) & (rad < 0.085)
    return float(np.percentile(rad[near], 85)) if near.any() else 0.03


def make_bangles(rig, body, col, material, counts=(('L', 3), ('R', 2))):
    """Heavy forged rings, three on the left wrist and two on the right, as on the gallery figure.

    The arms hang, so the rings have slid down onto the heel of the hand and stack up the wrist.
    """
    co = posed_verts(body)
    P = rig.pose.bones
    rng = np.random.default_rng(9)
    made = 0
    for side, count in counts:
        wrist = np.array(P[f'wrist.{side}'].head)
        elbow = np.array(P[f'lowerarm01.{side}'].head)
        axis = (wrist - elbow) / np.linalg.norm(wrist - elbow)
        inner = 0.0355
        at = wrist - axis * 0.004
        for k in range(count):
            c = at - axis * (0.0118 * k)
            r_here = limb_radius(co, c, axis)
            # each ring rests against the arm on one side
            side_dir = np.cross(axis, (0, 1.0, 0))
            side_dir /= np.linalg.norm(side_dir)
            c = c + side_dir * max(inner - r_here, 0) * 0.6 * (1 if k % 2 else -1)
            tilt = Matrix.Rotation(rng.normal(0, 0.07), 3, Vector(np.cross(axis, (0.3, 0.8, 0.2))))
            z = tilt @ Vector(axis)
            x = z.orthogonal().normalized()
            m = Matrix((x, z.cross(x), z)).transposed().to_4x4()
            m.translation = Vector(c)
            v, f = dress.ring_mesh(inner, inner + 0.0085, 0.0098, 300 + k + (0 if side == 'L' else 10))
            ob = obj_from_arrays(f'IronBangle.{side}.{k}', v, f, col)
            ob.matrix_world = m
            ob.data.materials.append(material)
            made += 1
    print('iron bangles', made, flush=True)
