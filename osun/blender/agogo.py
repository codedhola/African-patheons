"""The Àgògo: cornrows rising from the hairline into a tall disc of concentric braids.

Akintunde Akinleye's photographs of Ọ̀ṣun devotees at the 2014 festival show how it goes:
tight rows climb the sides of the head and feed a crest like a cockscomb, set toward the
back, its braids running round it in rings, white along its rim, a red ìkódẹ feather in
front. Each braid here is three strands crossing, and each strand is a bundle of hair curves.
"""
import math

import bpy
import numpy as np
from mathutils import Vector

import dress
import materials as mats
from common import obj_from_arrays

FRONT = math.radians(270)       # azimuth of her face: rest pose looks down -Y


def hair_material():
    """Black hair with a little warmth, the highlight running along each strand."""
    g = mats.Graph('BraidHair')
    bsdf = g.t.nodes.new('ShaderNodeBsdfHairPrincipled')
    bsdf.parametrization = 'MELANIN'
    bsdf.inputs['Melanin'].default_value = 0.88
    bsdf.inputs['Melanin Redness'].default_value = 0.55
    bsdf.inputs['Roughness'].default_value = 0.40
    bsdf.inputs['Radial Roughness'].default_value = 0.55
    bsdf.inputs['Coat'].default_value = 0.08
    return g.finish(bsdf.outputs[0])


def hairline(az):
    """Elevation of the hairline around the head, as seen from the head's centre."""
    c = np.cos(az - FRONT)
    return np.radians(-2.0 + 38.5 * c - 5.5 * c * c)


def scalp_points(tree, centre, az, el, reach=0.30):
    """Project directions onto the scalp. Returns points and outward normals."""
    d = np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)], -1)
    pts, nor = np.zeros_like(d), np.zeros_like(d)
    last_r = 0.1
    for i in np.ndindex(az.shape):
        ray = Vector(d[i])
        hit = tree.ray_cast(Vector(centre) + ray * reach, -ray, reach)
        if hit[0] is not None:
            pts[i] = hit[0]
            nor[i] = hit[1]
            last_r = (hit[0] - Vector(centre)).length
        else:
            pts[i] = np.array(centre) + d[i] * last_r
            nor[i] = d[i]
    return pts, nor


CREST_Y = 0.036                 # where the disc is centred, forward of the head's centre is negative
CREST_Z = 0.083
CREST_R = 0.094                 # to the rim
CREST_W = 0.031                 # half its thickness
SWEEP = (-0.04, 1.24)           # how far round the disc the braids run, in half turns


def crest_point(s, phi, centre, swell=0.0):
    """A point on the crest's skin. s runs round the disc from front to back; phi round its section, 0 on the rim."""
    th = np.pi * (SWEEP[0] + (SWEEP[1] - SWEEP[0]) * s)
    h = CREST_R * 0.47
    rc = CREST_R - h
    radial = rc + h * np.cos(phi) + swell
    side = np.sin(phi)
    lateral = (CREST_W + swell) * np.sign(side) * np.abs(side) ** 0.62
    return np.stack([centre[0] + lateral,
                     centre[1] + CREST_Y - radial * np.cos(th),
                     centre[2] + CREST_Z + radial * np.sin(th)], -1)


def crest_normal(s, phi):
    th = np.pi * (SWEEP[0] + (SWEEP[1] - SWEEP[0]) * s)
    nx = np.sin(phi) / CREST_W
    nr = np.cos(phi) / (CREST_R * 0.47)
    n = np.stack([nx, -nr * np.cos(th), nr * np.sin(th)], -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def braid_fibres(path, normal, width, rng, fibres=18, period=0.0064, height=0.30, fibre_spread=1.0):
    """Hair fibres for one three-strand braid along a path.

    path and normal are N x 3, width is the braid's width along it (N). Returns a list of arrays.
    """
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    length = cum[-1]
    n = max(int(length / period * 9), 40)
    s = np.linspace(0, length, n)
    p = np.stack([np.interp(s, cum, path[:, i]) for i in range(3)], 1)
    up = np.stack([np.interp(s, cum, normal[:, i]) for i in range(3)], 1)
    w = np.interp(s, cum, width)
    tan = np.gradient(p, axis=0)
    tan /= np.maximum(np.linalg.norm(tan, axis=1, keepdims=True), 1e-9)
    up = up - (up * tan).sum(1, keepdims=True) * tan
    up /= np.maximum(np.linalg.norm(up, axis=1, keepdims=True), 1e-9)
    side = np.cross(tan, up)
    phase = 2 * np.pi * s / period
    out = []
    for k in range(3):
        a = phase + k * 2 * np.pi / 3
        lateral = 0.31 * w * np.sin(a)
        rise = (0.50 + 0.50 * np.sin(2 * a)) * height * w * 0.5 + 0.17 * w
        centre = p + side * lateral[:, None] + up * rise[:, None]
        strand_r = 0.19 * w
        for f in range(fibres):
            r = math.sqrt(rng.random()) * fibre_spread
            start = rng.uniform(0, 6.283)
            spin = rng.uniform(0.7, 1.3)
            b = start + phase * 0.14 * spin
            wander = rng.normal(0, 0.05, n).cumsum() / math.sqrt(n)
            offset = (side * np.cos(b)[:, None] + up * np.sin(b)[:, None]) * (strand_r * (r + 0.12 * wander))[:, None]
            out.append((centre + offset).astype(np.float32))
    return out


def add_varied_curves(name, fibres, radius_root, radius_tip, col, material):
    """Hair curves object from arrays of any length."""
    sizes = [len(f) for f in fibres]
    hc = bpy.data.hair_curves.new(name)
    hc.add_curves(sizes)
    hc.position_data.foreach_set('vector', np.concatenate(fibres).ravel())
    t = np.concatenate([np.linspace(0, 1, m) for m in sizes])
    rad = hc.attributes.get('radius') or hc.attributes.new('radius', 'FLOAT', 'POINT')
    edge = np.minimum(t, 1 - t)
    rad.data.foreach_set('value', (radius_tip + (radius_root - radius_tip) * np.clip(edge / 0.02, 0, 1)).astype(np.float32))
    ob = bpy.data.objects.new(name, hc)
    col.objects.link(ob)
    hc.materials.append(material)
    return ob, sum(sizes)


def make_under(col, centre, M, material):
    """A dark form under the crest, so the braids lie on something."""
    rows, cols = 110, 44
    S, PH = np.meshgrid(np.linspace(0.0, 1.0, rows), np.linspace(0, 2 * np.pi, cols, endpoint=False), indexing='ij')
    pts = crest_point(S, PH, centre, -0.005)
    verts = pts.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
    idx = lambda i, j: i * cols + (j % cols)
    faces = [(idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)) for i in range(rows - 1) for j in range(cols)]
    ob = obj_from_arrays('CrestForm', verts, faces, col)
    ob.data.materials.append(material)
    return ob


def slerp(a, b, t):
    w = math.acos(float(np.clip(a @ b, -1, 1)))
    if w < 1e-4:
        return np.outer(1 - t, a) + np.outer(t, b)
    return np.outer(np.sin((1 - t) * w), a) / math.sin(w) + np.outer(np.sin(t * w), b) / math.sin(w)


def make(body, rig, col, material, under_material, row_spacing=0.0175):
    """Cornrows all round the head, and long braids round the crest."""
    M = np.array(dress.head_matrix(rig))
    me = body.data
    corners = np.array([me.vertices[i].co for f in dress.layer_faces('scalp_solid') for i in me.polygons[f].vertices])
    centre = (corners.max(0) + corners.min(0)) / 2
    centre[1] += 0.004
    centre[2] = corners[:, 2].max() - 0.098
    print('scalp centre', centre.round(3), 'top', round(float(corners[:, 2].max()), 3), flush=True)
    tree = dress.head_tree(body)
    rng = np.random.default_rng(29)

    az_grid = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    line = np.cos(hairline(az_grid)) * 0.098
    arc = np.concatenate([[0], np.cumsum(line * (az_grid[1] - az_grid[0]))])
    rows = int(arc[-1] / row_spacing)
    print('cornrows', rows, flush=True)

    fibres = []
    steps = 110
    for r in range(rows):
        az0 = float(np.interp((r + 0.5) / rows * arc[-1], arc, np.concatenate([az_grid, [2 * np.pi]])))
        el0 = float(hairline(np.array(az0)))
        start = np.array([math.cos(el0) * math.cos(az0), math.cos(el0) * math.sin(az0), math.sin(el0)])
        # the row lands on the flank of the disc, further back the further back it starts
        fb = (math.sin(az0) + 1) / 2             # 0 at the brow, 1 at the nape
        c = math.cos(az0)
        side = math.copysign(abs(c) ** 0.6, c if c != 0 else 1)
        land = np.array([side * CREST_W * 1.05, CREST_Y - 0.082 + 0.150 * fb ** 0.85, 0.090 + 0.012 * math.sin(fb * math.pi)])
        land = land / np.linalg.norm(land)
        t = np.linspace(0, 1, steps)
        d = slerp(start, land, t)
        el = np.arcsin(np.clip(d[:, 2], -1, 1))
        az = np.arctan2(d[:, 1], d[:, 0])
        pts, nor = scalp_points(tree, centre, az, el)
        width = (0.0078 + 0.0066 * dress.smoothstep(t, 0.0, 0.7)) * (0.32 + 0.68 * dress.smoothstep(t, 0.0, 0.06))
        fibres += braid_fibres(pts, nor, width, rng)

    # rings of thicker braid round the crest, on both faces and over the rim
    per_face = 6
    phis = [0.0] + [sign * (k + 0.75) / (per_face + 0.3) * math.radians(172) for k in range(per_face) for sign in (-1, 1)]
    for phi0 in phis:
        s = np.linspace(0.0, 1.0, 190)
        phi = np.full_like(s, phi0)
        pts = crest_point(s, phi, centre)
        nor = crest_normal(s, phi)
        width = np.full_like(s, 0.0158) * (0.92 + 0.16 * rng.random())
        fibres += braid_fibres(pts, nor, width, rng, fibres=26, period=0.0170, height=0.5)

    fibres = [(f @ M[:3, :3].T + M[:3, 3]).astype(np.float32) for f in fibres]
    ob, points = add_varied_curves('Agogo', fibres, 0.00029, 0.00014, col, material)
    make_under(col, centre, M, under_material)
    print('braid fibres', len(fibres), 'points', points, flush=True)
    return ob, centre


def cowrie_mesh():
    """A small white cowrie, its slit along its length. Built along +X, back up +Z."""
    rows, cols = 16, 20
    verts = []
    for i in range(rows):
        a = math.pi * (i + 0.5) / rows
        for j in range(cols):
            b = 2 * math.pi * j / cols
            x, y, z = math.cos(a), math.sin(a) * math.cos(b), math.sin(a) * math.sin(b)
            slit = math.exp(-((y) / 0.16) ** 2) * (z < 0)
            teeth = 0.10 * slit * math.sin(x * 26)
            z = z * (0.82 if z < 0 else 1.0) * (1 - 0.34 * slit) + teeth * 0.2
            verts.append((x * 0.0088, y * 0.0060, z * 0.0052))
    faces = [(i * cols + j, i * cols + (j + 1) % cols, (i + 1) * cols + (j + 1) % cols, (i + 1) * cols + j) for i in range(rows - 1) for j in range(cols)]
    faces.append(tuple(range(cols))[::-1])
    faces.append(tuple(range((rows - 1) * cols, rows * cols)))
    return np.array(verts, np.float32), faces


def make_cowries(rig, centre, col, material, count=19):
    """White along the rim of the crest."""
    M = np.array(dress.head_matrix(rig))
    v, f = cowrie_mesh()
    verts, faces, base = [], [], 0
    for k in range(count):
        th = (k + 0.5) / count * 1.06 + 0.02
        s = (th - SWEEP[0]) / (SWEEP[1] - SWEEP[0])
        p = crest_point(np.array(s), np.array(0.0), centre, 0.0062)
        n = crest_normal(np.array(s), np.array(0.0))
        along = np.array([0.0, math.sin(th * math.pi), math.cos(th * math.pi)])
        side = np.cross(n, along)
        m = np.stack([along, side, -n], 1)                 # slit outward, back against the hair
        verts.append(v @ m.T + p)
        faces += [tuple(i + base for i in q) for q in f]
        base += len(v)
    all_v = np.concatenate(verts) @ M[:3, :3].T + M[:3, 3]
    ob = obj_from_arrays('Cowries', all_v, faces, col)
    ob.data.materials.append(material)
    print('cowries', count, flush=True)
    return ob


def feather_parts(base, direction, width_dir, length, width, rng, barbs=150):
    """One red tail feather: a rachis and two vanes of barbs, as polylines."""
    n = 8
    rachis = []
    d = direction / np.linalg.norm(direction)
    w = width_dir / np.linalg.norm(width_dir)
    bow = np.cross(d, w)
    curve = rng.uniform(0.10, 0.22)
    for t in np.linspace(0, 1, n):
        rachis.append(base + d * length * t + bow * length * curve * t * t)
    rachis = np.array(rachis)
    strands = [rachis]
    for side in (-1, 1):
        for i in range(barbs):
            t = 0.10 + 0.90 * (i + rng.random() * 0.6) / barbs
            a = t * (n - 1)
            k = min(int(a), n - 2)
            p = rachis[k] + (rachis[k + 1] - rachis[k]) * (a - k)
            shape = math.sin(min(t * 1.08, 1) * math.pi) ** 0.5 * (1 - 0.15 * t)
            L = width * shape * (0.92 + 0.14 * rng.random())
            f = np.linspace(0, 1, 8)[:, None]
            strands.append(p + (w * side * 0.92 + d * 0.38) * f * L + bow * f * f * L * rng.uniform(0.05, 0.25))
    return strands


def make_feathers(rig, centre, col, material):
    """Ìkódẹ: a red parrot tail feather set at the front of the crest, pointing forward."""
    M = np.array(dress.head_matrix(rig))
    rng = np.random.default_rng(51)
    strands = []
    base = crest_point(np.array(0.135), np.array(0.0), centre) + np.array([0.0, 0.012, -0.030])
    for lean, up, length in ((-0.05, 0.62, 0.122), (0.07, 0.46, 0.104)):
        strands += feather_parts(base, np.array([lean, -1.0, up]), np.array([1.0, 0.05, 0.15]), length, 0.0115, rng)
    strands = [(f @ M[:3, :3].T + M[:3, 3]).astype(np.float32) for f in strands]
    ob, _ = add_varied_curves('Ikode', strands, 0.00024, 0.00012, col, material)
    print('feather strands', len(strands), flush=True)
    return ob
