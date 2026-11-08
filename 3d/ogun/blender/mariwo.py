"""His màrìwò: young palm fronds split into strips, tied round his waist and his head.

Màrìwò are young, unwilted palm fronds, tied round the body by Ògún's worshippers at festivals
such as Ọlọ́jọ́ (Wiktionary), and the palm frond is one of his symbols (Wikipedia: Ogun). As on
the gallery figure, they hang in a long fringe over the trousers from a cord at the waist and
rise from a band round the head. How the fronds are split, folded and tied is this study's.

Each strip of the fringe leaves the cord over its top, as a leaflet folded across it would,
then falls. A fringe hangs from the hips like a skirt, so below its widest it may spread but
never draws in; within that, the strips gather in loose bunches, twist and part, and their
ends lift a little where the leaflet's own spring curls them.
"""
import math

import numpy as np
from mathutils import Vector

import materials as mats
from common import obj_from_arrays, verts_world
from dress import head_matrix, head_tree, smoothstep
from procedural import Noise, sweep

STRIPS = 280
LAYERS = 4
LAYER_GAP = 0.0026
CORD_R = 0.0085          # the twisted cord at the waist
SAMPLES = 64


def palm_material(name='Mariwo'):
    """A young frond: pale yellow-green, waxy on top, with fine veins down its length; light comes through it."""
    g = mats.Graph(name)
    uv = g.node('TexCoord').outputs['UV']
    sep = g.node('SeparateXYZ', Vector=uv).outputs
    along, across = sep[0], sep[1]          # metres down and across the strip
    tint = g.node('Attribute', attribute_name='tint', attribute_type='GEOMETRY').outputs['Fac']
    rib = g.node('Attribute', attribute_name='rib', attribute_type='GEOMETRY').outputs['Fac']
    tip = g.node('Attribute', attribute_name='tip', attribute_type='GEOMETRY').outputs['Fac']
    base = g.ramp(tint, [(0.0, (0.20, 0.30, 0.070)), (0.35, (0.30, 0.38, 0.10)), (0.7, (0.42, 0.44, 0.16)), (1.0, (0.50, 0.49, 0.22))])
    veins = g.math('MULTIPLY', g.math('SINE', g.math('MULTIPLY', across, 2 * math.pi / 0.0011)), 0.5)
    veins = g.math('ADD', veins, 0.5)
    mottle = g.node('TexNoise', Vector=g.node('CombineXYZ', X=g.math('MULTIPLY', along, 2.0), Y=g.math('MULTIPLY', across, 30.0), Z=tint).outputs[0],
                    Scale=9.0, Detail=4).outputs['Fac']
    col = g.mix(g.math('MULTIPLY', veins, 0.10), base, (0.20, 0.25, 0.05))
    col = g.mix(g.math('MULTIPLY', mottle, 0.25), col, (0.40, 0.40, 0.16))
    # the midrib, where a strip kept one: a paler, raised line down its middle
    mid = g.math('MULTIPLY', rib, g.math('LESS_THAN', g.math('ABSOLUTE', across), 0.0011))
    col = g.mix(g.math('MULTIPLY', mid, 0.7), col, (0.56, 0.54, 0.28))
    # cut ends dry and brown first
    col = g.mix(g.math('MULTIPLY', tip, 0.55), col, (0.30, 0.20, 0.06))
    height = g.math('ADD', g.math('MULTIPLY', veins, 0.3), g.math('MULTIPLY', mid, 1.0))
    normal = g.bump(height, 0.25, 0.0002)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=g.math('ADD', 0.34, g.math('MULTIPLY', mottle, 0.16)), Normal=normal)
    bsdf.inputs['Specular IOR Level'].default_value = 0.55
    bsdf.inputs['Sheen Weight'].default_value = 0.15
    translucent = g.node('BsdfTranslucent', Color=g.mix(0.5, col, (0.55, 0.60, 0.10)), Normal=normal)
    both = g.node('MixShader', Fac=0.32)
    g.link(bsdf.outputs[0], both.inputs[1])
    g.link(translucent.outputs[0], both.inputs[2])
    return g.finish(both.outputs[0])


def wearing_points(body, sokoto):
    """What the fringe falls over: the skin below the chest, without the arms, and the trousers."""
    from cloth import arm_weight
    co = verts_world(body)
    co = co[(arm_weight(body) < 0.2) & (co[:, 2] < 1.25)]
    return np.vstack([co, verts_world(sokoto)])


def skirt_support(points, centre, zs, nphi=240, band=0.010):
    """Support distance by angle at each height: below its widest a hanging fringe may spread but never draws in."""
    phi = np.linspace(0, 2 * np.pi, nphi, endpoint=False)
    dirs = np.stack([np.cos(phi), np.sin(phi)], 1)
    sup = np.zeros((len(zs), nphi))
    for i, z in enumerate(zs):
        slab = points[np.abs(points[:, 2] - z) < band, :2] - centre
        sup[i] = (slab @ dirs.T).max(0) if len(slab) else sup[i - 1]
    for i in range(1, len(zs)):
        sup[i] = np.maximum(sup[i], sup[i - 1])
    for _ in range(3):
        sup = (sup + np.roll(sup, 1, 1) + np.roll(sup, -1, 1)) / 3
    k = np.hanning(9)
    k /= k.sum()
    pad = np.pad(sup, ((4, 4), (0, 0)), mode='edge')
    sup = np.stack([np.convolve(pad[:, j], k, 'valid') for j in range(nphi)], 1)
    return phi, sup


def sample_support(phi, zs, sup, a, z):
    a = np.asarray(a) % (2 * np.pi)
    zi = np.clip((zs[0] - np.asarray(z)) / (zs[0] - zs[-1]) * (len(zs) - 1), 0, len(zs) - 1.001)
    i0 = zi.astype(int)
    f = zi - i0
    ai = a / (2 * np.pi) * len(phi)
    j0 = ai.astype(int) % len(phi)
    j1 = (j0 + 1) % len(phi)
    g = ai - np.floor(ai)
    s0 = sup[i0, j0] * (1 - g) + sup[i0, j1] * g
    s1 = sup[i0 + 1, j0] * (1 - g) + sup[i0 + 1, j1] * g
    return s0 * (1 - f) + s1 * f


def ribbon(path, widths, normals0, twist, crease, across=5):
    """Vertices of a strip along a path: its width turned by twist about the path, folded along its middle."""
    tan = np.gradient(path, axis=0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    n = normals0 - (normals0 * tan).sum(1, keepdims=True) * tan
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    b = np.cross(tan, n)
    c, s = np.cos(twist)[:, None], np.sin(twist)[:, None]
    wdir = b * c + n * s
    ndir = n * c - b * s
    xs = np.linspace(-0.5, 0.5, across)
    v = path[:, None] + wdir[:, None] * (widths[:, None, None] * xs[None, :, None]) \
        + ndir[:, None] * (crease[:, None, None] * (1 - 2 * np.abs(xs))[None, :, None])
    uv_across = widths[:, None] * xs[None, :]
    return v, uv_across


def strip_faces(rows, across, base):
    return [(base + i * across + j, base + i * across + j + 1, base + (i + 1) * across + j + 1, base + (i + 1) * across + j)
            for i in range(rows - 1) for j in range(across - 1)]


def make_fringe(body, sokoto, col, material, waist_z):
    rng = np.random.default_rng(7)
    noise = Noise(19)
    pts = wearing_points(body, sokoto)
    band_z = waist_z - 0.012
    slab = pts[np.abs(pts[:, 2] - band_z) < 0.012, :2]
    centre = (slab.max(0) + slab.min(0)) / 2
    zs = np.linspace(band_z + 0.02, 0.20, 180)
    phi, sup = skirt_support(pts, centre, zs)

    # the cord: a little lower at the front, where the belly carries it
    cord_a = np.linspace(0, 2 * np.pi, 360, endpoint=False)
    front = np.clip(-np.sin(cord_a), 0, 1)
    cord_z = band_z - 0.010 * front
    cord_r = sample_support(phi, zs, sup, cord_a, cord_z) + CORD_R + 0.002
    cord = np.stack([centre[0] + np.cos(cord_a) * cord_r, centre[1] + np.sin(cord_a) * cord_r, cord_z], 1)

    # bunches: strips gather round a few dozen centres, more strongly further down
    bunch_at = np.sort(rng.uniform(0, 2 * np.pi, 44))
    verts, faces, uvs, tint, rib, tipv = [], [], [], [], [], []
    base = 0
    theta0 = np.sort((np.arange(STRIPS) + rng.uniform(-0.4, 0.4, STRIPS)) / STRIPS * 2 * np.pi)
    for k in range(STRIPS):
        th = theta0[k]
        layer = int(rng.integers(0, LAYERS))
        width = rng.uniform(0.007, 0.0145)
        length = rng.uniform(0.50, 0.64) * (0.92 if layer == 0 else 1.0)
        d_b = (bunch_at - th + np.pi) % (2 * np.pi) - np.pi
        pull = d_b[np.argmin(np.abs(d_b))]
        s = np.linspace(0, 1, SAMPLES)
        down = smoothstep(s, 0.05, 0.6)
        a = th + pull * 0.55 * down + 0.035 * noise.fbm(np.stack([s * 2.5, np.full(SAMPLES, k * 0.37), np.zeros(SAMPLES)], 1), 3) * s
        cz = float(np.interp(th % (2 * np.pi), cord_a, cord_z))
        cr = float(np.interp(th % (2 * np.pi), cord_a, cord_r))
        z = cz - CORD_R * 0.6 - s * length
        gap = 0.0015 + layer * LAYER_GAP
        # it hangs from the outside of the cord, and comes no further in than that unless the body is wider
        r = np.maximum(sample_support(phi, zs, sup, a, z), cr + CORD_R) + gap
        r += rng.uniform(0.0, 0.016) * s ** 2.2 + 0.010 * smoothstep(s, 0.88, 1.0) * rng.uniform(0.2, 1.0)
        path = np.stack([centre[0] + np.cos(a) * r, centre[1] + np.sin(a) * r, z], 1)
        # over the top of the cord first, as a leaflet folded across it
        over, over_n = [], []
        radial = np.array([math.cos(th), math.sin(th), 0.0])
        for ang in np.radians((150, 120, 90, 55, 25)):
            out = radial * math.cos(ang) + np.array([0, 0, 1.0]) * math.sin(ang)
            over.append(np.array([centre[0] + math.cos(th) * cr, centre[1] + math.sin(th) * cr, cz]) + out * (CORD_R + 0.0012 + layer * 0.0008))
            over_n.append(out)
        path = np.vstack([np.array(over), path])
        rows = len(path)
        ss = np.concatenate([np.zeros(5), s])
        radial0 = np.vstack([np.array(over_n), np.stack([np.cos(a), np.sin(a), np.zeros(SAMPLES)], 1)])
        twist = rng.normal(0, 0.22) + rng.normal(0, 1.1) * ss * length + 0.25 * noise(np.stack([ss * 3, np.full(rows, k * 0.11), np.ones(rows)], 1))
        twist = np.clip(twist, -1.25, 1.25)
        w = np.full(rows, width) * (1 - 0.35 * smoothstep(ss, 0.93, 1.0))
        crease = w * rng.uniform(0.05, 0.12)
        v, across = ribbon(path, w, radial0, twist, crease)
        verts.append(v.reshape(-1, 3))
        faces += strip_faces(rows, 5, base)
        arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
        uvs.append(np.stack([np.repeat(arc, 5), across.ravel()], 1))
        tint.append(np.full(rows * 5, rng.random()))
        rib.append(np.full(rows * 5, float(rng.random() < 0.3)))
        tipv.append(np.repeat(smoothstep(ss, 0.90, 1.0) * rng.uniform(0.2, 1.0), 5))
        base += rows * 5
    ob = obj_from_arrays('Mariwo', np.concatenate(verts), faces, col, uv=np.concatenate(uvs))
    for name, data in (('tint', tint), ('rib', rib), ('tip', tipv)):
        ob.data.attributes.new(name, 'FLOAT', 'POINT').data.foreach_set('value', np.concatenate(data).astype(np.float32))
    ob.data.materials.append(material)
    sol = ob.modifiers.new('Thickness', 'SOLIDIFY')
    sol.thickness = 0.0004
    sol.offset = 0
    print('fringe strips', STRIPS, 'vertices', base, flush=True)

    # the cord itself: two plies of twisted leaflet round the waist
    parts = []
    closed = np.vstack([cord, cord[:1]])
    tan = np.gradient(closed, axis=0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    up = np.array([0, 0, 1.0])
    side = np.cross(tan, up)
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    arcl = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(closed, axis=0), axis=1))])
    for ply in (0, 1):
        ang = arcl / 0.022 * 2 * np.pi + ply * np.pi
        p = closed + (side * np.cos(ang)[:, None] + np.cross(side, tan) * np.sin(ang)[:, None]) * (CORD_R * 0.45)
        parts.append(sweep(p, CORD_R * 0.58, sides=8))
    from procedural import merged
    v, f = merged(parts)
    cord_ob = obj_from_arrays('MariwoCord', v, f, col)
    n = len(v)
    for name, val in (('tint', 0.55), ('rib', 0.0), ('tip', 0.15)):
        cord_ob.data.attributes.new(name, 'FLOAT', 'POINT').data.foreach_set('value', np.full(n, val, np.float32))
    cord_ob.data.uv_layers.new(name='UVMap')
    cord_ob.data.materials.append(material)
    return ob, cord_ob


def make_headband(body, rig, col, material, hair_lift=0.004):
    """A band of twisted leaflet round the head, above the brows, with leaflet ends standing up from it."""
    M = head_matrix(rig)
    tree = head_tree(body)
    info = eval(body['eyes'])
    eye_z = (info['L']['centre'][2] + info['R']['centre'][2]) / 2
    eye_y = info['L']['centre'][1]
    rng = np.random.default_rng(29)
    noise = Noise(33)
    centre = Vector((0.0, eye_y + 0.085, eye_z + 0.05))
    ring = []
    for a in np.linspace(0, 2 * np.pi, 180, endpoint=False):
        # level across the brow, dipping toward the nape
        back = max(math.sin(a), 0.0)
        z = centre.z - 0.020 * back ** 1.5 + 0.004 * max(-math.sin(a), 0)
        d = Vector((math.cos(a), math.sin(a), 0))
        start = Vector((centre.x, centre.y, z)) + d * 0.25
        hit, normal, _, _ = tree.ray_cast(start, -d, 0.3)
        if hit is None:
            continue
        ring.append(hit + normal * (hair_lift + 0.0062))
    ring = np.array(ring)
    for _ in range(6):
        ring = (ring + np.roll(ring, 1, 0) + np.roll(ring, -1, 0)) / 3
    closed = np.vstack([ring, ring[:1]])
    tan = np.gradient(closed, axis=0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    out = closed - np.array(centre)
    out[:, 2] = 0
    out /= np.linalg.norm(out, axis=1, keepdims=True)
    arcl = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(closed, axis=0), axis=1))])
    parts = []
    for ply in (0, 1):
        ang = arcl / 0.018 * 2 * np.pi + ply * np.pi
        p = closed + (out * np.cos(ang)[:, None] + np.array([0, 0, 1.0]) * np.sin(ang)[:, None]) * 0.0030
        parts.append(sweep(p, 0.0038, sides=8))

    # leaflet ends rising from the band all round, shorter over the brow so the face stays clear
    verts, faces, uvs, tint, rib, tipv = [], [], [], [], [], []
    base = 0
    count = 40
    for k in range(count):
        t = (k + rng.uniform(-0.3, 0.3)) / count
        i = int(t * len(ring)) % len(ring)
        root = ring[i]
        o = out[i]
        a = math.atan2(o[1], o[0])
        frontness = max(-math.sin(a), 0)
        length = rng.uniform(0.085, 0.135) * (1 - 0.35 * frontness ** 2)
        lean = math.radians(rng.uniform(22, 42))
        s = np.linspace(0, 1, 22)
        # up and out, the tip bending over under its own weight
        bend = lean + math.radians(rng.uniform(18, 40)) * s ** 1.8
        dirs = np.stack([o[0] * np.sin(bend), o[1] * np.sin(bend), np.cos(bend)], 1)
        sway = 0.004 * noise.fbm(np.stack([s * 3, np.full(22, k * 0.7), np.zeros(22)], 1), 2)
        path = root + np.cumsum(dirs * (length / 21), axis=0) - dirs[0] * (length / 21)
        path += np.cross(o, (0, 0, 1.0))[None] * sway[:, None]
        w = rng.uniform(0.010, 0.016) * (1 - s ** 1.6) + 0.0006
        twist = rng.normal(0, 0.35) + rng.normal(0, 0.8) * s
        normals0 = np.tile(o, (22, 1))
        v, across = ribbon(path, w, normals0, twist, w * 0.10)
        verts.append(v.reshape(-1, 3))
        faces += strip_faces(22, 5, base)
        arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
        uvs.append(np.stack([np.repeat(arc, 5), across.ravel()], 1))
        tint.append(np.full(22 * 5, rng.random()))
        rib.append(np.full(22 * 5, float(rng.random() < 0.6)))
        tipv.append(np.repeat(smoothstep(s, 0.85, 1.0) * rng.uniform(0.2, 0.9), 5))
        base += 22 * 5
    from procedural import merged
    bv, bf = merged(parts)
    band = obj_from_arrays('HeadbandCord', bv, bf, col)
    tips = obj_from_arrays('HeadbandFronds', np.concatenate(verts), faces, col, uv=np.concatenate(uvs))
    for ob, data in ((band, None), (tips, (tint, rib, tipv))):
        n = len(ob.data.vertices)
        for j, name in enumerate(('tint', 'rib', 'tip')):
            vals = np.concatenate(data[j]) if data else np.full(n, (0.6, 0.0, 0.1)[j])
            ob.data.attributes.new(name, 'FLOAT', 'POINT').data.foreach_set('value', vals.astype(np.float32))
        if not ob.data.uv_layers:
            ob.data.uv_layers.new(name='UVMap')
        ob.data.materials.append(material)
        ob.matrix_world = M
    sol = tips.modifiers.new('Thickness', 'SOLIDIFY')
    sol.thickness = 0.0004
    sol.offset = 0
    print('head fronds', count, flush=True)
    return band, tips
