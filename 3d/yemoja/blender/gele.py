"""Her gèlè: a light-blue head tie, wrapped close and rising behind into a pleated fan.

The gallery figure wears a light-blue gèlè, her colour; its shape is this study's. The wrap is
a surface lifted off the skull with its pleats running to a knot at the nape, worked out in
spherical coordinates round the knot as Ahiajoku's ichafu was, but standing further off the
head, as a stiff gèlè cloth does. From the crown a fan of nine accordion folds rises and leans
back; where its foot meets the wrap it is pushed out onto it.
"""
import math

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import dress
from cloth import U_PERIOD, V_PERIOD
from common import obj_from_arrays
from procedural import Noise, add_curves

KNOT = np.array([0.0, 0.92, -0.20])       # behind, at the nape
PLEATS = 15
RINGS, SPOKES = 140, 360
FAN_FOLDS = 9
FAN_TILT = math.radians(24)               # how much more the back of the band leans back
FAN_SPAN = math.radians(135)              # each way round from straight behind


def centre_of(body):
    info = eval(body['eyes'])
    e = (np.array(info['L']['centre']) + np.array(info['R']['centre'])) / 2
    return np.array([0.0, e[1] + 0.107, e[2] + 0.030])


def edge_elevation(az):
    """Height of the wrap's lower edge on the head: the hairline in front, above the ears, the nape behind."""
    c = np.cos(az - np.radians(270))
    return np.radians(9.0 + 14.0 * c - 6.0 * (2 * c * c - 1))


def saw(x, peak=0.80):
    f = x - np.floor(x)
    return dress.smoothstep(f, 0, peak) * (1 - dress.smoothstep(f, peak, 0.985))


def wrap_surface(tree, centre):
    az = np.linspace(0, 2 * np.pi, SPOKES, endpoint=False)
    t = np.linspace(0, 1, RINGS) ** 0.85
    AZ, T = np.meshgrid(az, t, indexing='ij')
    EL = edge_elevation(AZ) * (1 - T) + np.radians(89.5) * T
    d = np.stack([np.cos(EL) * np.cos(AZ), np.cos(EL) * np.sin(AZ), np.sin(EL)], -1)
    radius = np.zeros(AZ.shape)
    for idx in np.ndindex(AZ.shape):
        ray = Vector(d[idx])
        hit = tree.ray_cast(Vector(centre) + ray * 0.3, -ray, 0.3)
        radius[idx] = 0.3 - hit[3] if hit[0] is not None else np.nan
    filler = np.nanmedian(radius, axis=1, keepdims=True)
    radius = np.where(np.isnan(radius), filler, radius)
    for _ in range(16):
        radius = (radius + np.roll(radius, 1, 0) + np.roll(radius, -1, 0)) / 3
        radius[:, 1:-1] = (radius[:, 1:-1] + radius[:, :-2] + radius[:, 2:]) / 3

    k = KNOT / np.linalg.norm(KNOT)
    e1 = np.cross(k, (0, 0, 1))
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(k, e1)
    theta = np.arccos(np.clip(d @ k, -1, 1))
    lam = np.arctan2(d @ e2, d @ e1)
    n1, n2 = Noise(14), Noise(19)
    warp = n1.fbm(d * 1.6, 2) * 0.22
    phase = lam / (2 * np.pi) * PLEATS + warp + 0.40 * theta
    rng = np.random.default_rng(16)
    amp = rng.uniform(0.5, 1.0, PLEATS + 8)[np.floor(phase).astype(int) % (PLEATS + 8)]
    pleat = saw(phase) * amp * (0.0050 + 0.0140 * np.exp(-(theta / 1.6) ** 2))
    fine = n2.fbm(np.stack([lam * 5, theta * 2.5, d[..., 2]], -1), 3) * 0.0014
    # stiff cloth stands off the head: more on the crown and most behind, where the fan's foot is wrapped in
    bulk = 0.010 + 0.016 * dress.smoothstep(T, 0, 0.40) + 0.010 * np.clip(d[..., 2], 0, 1) ** 2
    behind = np.clip(d @ np.array([0.0, 0.80, 0.60]), 0, 1)
    bulk = bulk + 0.024 * behind ** 2.0
    fold = dress.smoothstep(T, 0.14, 0.10) * 0.0036
    tuck = dress.smoothstep(T, 0.022, 0.0) * 0.0120
    hug = dress.smoothstep(T, 0.03, 0.26)
    h = bulk + pleat * hug + fine + fold - tuck
    return d, radius + h, lam, theta


def make_wrap(body, rig, col, material):
    M = np.array(dress.head_matrix(rig))
    centre = centre_of(body)
    tree = dress.head_tree(body)
    d, r, lam, theta = wrap_surface(tree, centre)
    pts = centre + d * r[..., None]
    nrows, ncols = SPOKES, RINGS
    idx = lambda i, j: (i % nrows) * ncols + j
    faces = [(idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)) for i in range(nrows) for j in range(ncols - 1)]
    ob = obj_from_arrays('GeleWrap', pts.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3], faces, col)
    me = ob.data
    layer = me.uv_layers.new(name='UVMap')
    loops = np.zeros(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', loops)
    l = lam.ravel()[loops]
    uv = np.stack([theta.ravel()[loops] * 0.12 / U_PERIOD, l / (2 * np.pi) * 0.80 / V_PERIOD + 0.2], 1)
    start = np.zeros(len(me.polygons), np.int32)
    me.polygons.foreach_get('loop_start', start)
    for s in start:
        q = l[s:s + 4]
        if q.max() - q.min() > np.pi:
            fixed = np.where(q < 0, q + 2 * np.pi, q)
            uv[s:s + 4, 1] = fixed / (2 * np.pi) * 0.80 / V_PERIOD + 0.2
    layer.data.foreach_set('uv', uv.astype(np.float32).ravel())
    me.materials.append(material)
    sol = ob.modifiers.new('Thickness', 'SOLIDIFY')
    sol.thickness = 0.0014
    sol.offset = -1
    return ob, centre, M


def make_fan(wrap, centre, M, col, material):
    """The crest: a band of pleats standing round the back and sides of the crown, opening outward, tallest behind."""
    rows, cols = 40, 720
    rho = np.linspace(0, 1, rows)
    alpha = np.linspace(-FAN_SPAN, FAN_SPAN, cols)          # round the head, 0 straight behind
    A, R = np.meshgrid(alpha, rho, indexing='ij')
    n = Noise(27)
    radial = np.stack([np.sin(A), np.cos(A), np.zeros_like(A)], -1)       # out from the head's axis
    up = np.array([0.0, 0.0, 1.0])
    # its foot is a ring on the crown, a little behind the top of the head
    foot_c = centre + np.array([0.0, 0.020, 0.060])
    foot = foot_c + radial * 0.050
    lean = np.radians(22) + np.radians(14) * np.abs(np.sin(A)) + FAN_TILT * 0.5 * np.clip(np.cos(A), 0, 1)
    out = radial * np.sin(lean)[..., None] + up * np.cos(lean)[..., None]
    height = (0.060 + 0.070 * np.clip(np.cos(A * 0.8), 0, 1) ** 1.3) * (1 + 0.06 * n.fbm(np.stack([A * 2, np.zeros_like(A), np.ones_like(A)], -1), 2))
    x = A / (2 * FAN_SPAN) * FAN_FOLDS * 2 + 0.06 * n.fbm(np.stack([R * 2, A, np.zeros_like(A)], -1), 2)
    rounded = 0.5 - 0.5 * np.cos(2 * np.pi * x)          # cloth folds round over, they do not crease like paper
    depth = 0.028 * (0.75 + 0.25 * np.sin(np.floor(x) * 2.3)) * R ** 0.8
    rim = 0.008 * dress.smoothstep(R, 0.8, 1.0)            # the edge curls out a little
    pts = foot + out * (R * height)[..., None] + radial * ((rounded - 0.5) * depth + rim)[..., None]
    pts = pts.reshape(-1, 3)
    # where the band's foot falls inside the wrap, push it out onto it
    wv = (np.array([v.co for v in wrap.data.vertices]) - M[:3, 3]) @ np.linalg.inv(M[:3, :3]).T
    tree = BVHTree.FromPolygons([Vector(q) for q in wv], [tuple(p.vertices) for p in wrap.data.polygons])
    for i, q in enumerate(pts):
        hit, normal, _, _ = tree.find_nearest(Vector(q))
        if hit is not None and (Vector(q) - hit).dot(normal) < 0.003:
            pts[i] = np.array(hit + normal * 0.003)
    idx = lambda i, j: i * rows + j
    faces = [(idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)) for i in range(cols - 1) for j in range(rows - 1)]
    uv = np.stack([(A * 0.09).ravel() / U_PERIOD + 0.3, (R * height).ravel() / V_PERIOD + 0.1], 1)
    ob = obj_from_arrays('GeleFan', pts @ M[:3, :3].T + M[:3, 3], faces, col, uv=uv)
    ob.data.materials.append(material)
    sol = ob.modifiers.new('Thickness', 'SOLIDIFY')
    sol.thickness = 0.0016
    sol.offset = 0
    return ob


def make_knot(centre, M, col, material):
    """A squat wrung knot at the nape, where the ends are tied and tucked."""
    k = KNOT / np.linalg.norm(KNOT)
    at = centre + k * 0.105
    x = np.cross(k, (0, 0, 1.0))
    x /= np.linalg.norm(x)
    y = np.cross(k, x)
    n = Noise(31)
    na, nb = 120, 60
    A, B = np.meshgrid(np.linspace(0, 2 * np.pi, na, endpoint=False), np.linspace(0.01, np.pi - 0.01, nb), indexing='ij')
    u = np.stack([np.sin(B) * np.cos(A), np.sin(B) * np.sin(A), np.cos(B)], -1)
    wind = saw(A / (2 * np.pi) * 6 + B * 1.1 + n.fbm(u * 1.5, 2) * 0.5) * 0.0068
    p = u * np.array([0.036, 0.026, 0.024])[None, None] * (1 + wind / 0.026)[..., None]
    world = at + k * 0.012 + p[..., 0, None] * x + p[..., 1, None] * y + p[..., 2, None] * k
    idx = lambda i, j: (i % na) * nb + j
    faces = [(idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)) for i in range(na) for j in range(nb - 1)]
    uv = np.stack([A.ravel() * 0.03 / U_PERIOD, B.ravel() * 0.03 / V_PERIOD + 0.18], 1)
    ob = obj_from_arrays('GeleKnot', world.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3], faces, col, uv=uv)
    ob.data.materials.append(material)
    return ob


def make_edge_hair(body, rig, col, material, centre, per_face=30):
    """Close-cut coiled hair where the gèlè leaves the scalp showing: at the temples, behind the ears and at the nape."""
    M = dress.head_matrix(rig)
    me = body.data
    rng = np.random.default_rng(17)
    strands = []
    for f in dress.layer_faces('scalp_solid'):
        poly = me.polygons[f]
        vs = [me.vertices[i].co for i in poly.vertices]
        nrm = poly.normal
        for _ in range(per_face):
            w = rng.dirichlet((1, 1, 1, 1)[:len(vs)])
            p = sum((v * a for v, a in zip(vs, w)), Vector((0, 0, 0)))
            d = p - Vector(centre)
            az = math.atan2(d.y, d.x) % (2 * math.pi)
            el = math.asin(d.z / d.length)
            if el > float(edge_elevation(az)) + math.radians(4):
                continue
            if d.y < -0.012 and el > math.radians(-5):          # a clean hairline: nothing on the brow
                continue
            L = rng.uniform(0.0022, 0.0042)
            ph, turns = rng.uniform(0, 6.28), rng.uniform(1.2, 2.2)
            t1 = nrm.orthogonal().normalized()
            t2 = nrm.cross(t1)
            pts = [M @ (p + nrm * (L * s) + (t1 * math.cos(ph + s * turns * 6.28) + t2 * math.sin(ph + s * turns * 6.28)) * (0.0008 * math.sin(math.pi * min(s * 1.2, 1))))
                   for s in np.linspace(0, 1, 7)]
            strands.append(pts)
    ob = add_curves('EdgeHair', np.array(strands, np.float32), 0.00007, 0.00003, col, material)
    print('edge hair curves', len(strands), flush=True)
    return ob


def make(body, rig, col, material, hair_material):
    wrap, centre, M = make_wrap(body, rig, col, material)
    fan = make_fan(wrap, centre, M, col, material)
    knot = make_knot(centre, M, col, material)
    hair = make_edge_hair(body, rig, col, hair_material, centre)
    return wrap, fan, knot, hair
