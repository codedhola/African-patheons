"""The ichafu: a head tie of the same Akwete, tied flat on the head.

The surface is a dome lifted off the skull. Cloth pulled to a knot makes folds
that radiate from the knot, so the pleats are worked out in spherical coordinates
around the knot rather than around the head. Two short ends hang from the knot.
"""
import numpy as np
from mathutils import Vector

import dress
from cloth import U_PERIOD, V_PERIOD
from common import obj_from_arrays
from procedural import Noise

CENTRE = np.array([0.0, -0.022, 1.562])
KNOT = np.array([0.60, 0.60, 0.53])              # her left, behind, high
PLEATS = 17
RINGS, SPOKES = 150, 400


def edge_elevation(az):
    """Height of the tie's lower edge on the head: hairline in front, above the ears, nape behind."""
    c = np.cos(az - np.radians(270))
    return np.radians(5.0 + 17.0 * c - 6.5 * (2 * c * c - 1))


def saw(x, peak=0.82):
    """One asymmetric pleat: a long rise and a sharp fall into the tuck."""
    f = x - np.floor(x)
    return dress.smoothstep(f, 0, peak) * (1 - dress.smoothstep(f, peak, 0.985))


def surface(tree):
    """Radial distance to the skull over a grid of directions, then the cloth's height over it."""
    az = np.linspace(0, 2 * np.pi, SPOKES, endpoint=False)
    t = np.linspace(0, 1, RINGS) ** 0.85
    AZ, T = np.meshgrid(az, t, indexing='ij')
    EL = edge_elevation(AZ) * (1 - T) + np.radians(89.5) * T
    d = np.stack([np.cos(EL) * np.cos(AZ), np.cos(EL) * np.sin(AZ), np.sin(EL)], -1)

    radius = np.zeros(AZ.shape)
    for idx in np.ndindex(AZ.shape):
        ray = Vector(d[idx])
        hit = tree.ray_cast(Vector(CENTRE) + ray * 0.3, -ray, 0.3)
        radius[idx] = 0.3 - hit[3] if hit[0] is not None else np.nan
    filler = np.nanmedian(radius, axis=1, keepdims=True)
    radius = np.where(np.isnan(radius), filler, radius)
    for _ in range(14):                # ears and the like should not print through
        radius = (radius + np.roll(radius, 1, 0) + np.roll(radius, -1, 0)) / 3
        radius[:, 1:-1] = (radius[:, 1:-1] + radius[:, :-2] + radius[:, 2:]) / 3

    k = KNOT / np.linalg.norm(KNOT)
    e1 = np.cross(k, (0, 0, 1))
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(k, e1)
    theta = np.arccos(np.clip(d @ k, -1, 1))
    lam = np.arctan2(d @ e2, d @ e1)

    n1, n2 = Noise(4), Noise(9)
    warp = n1.fbm(d * 1.6, 2) * 0.22        # small, or the pleats close into rings instead of running to the knot
    phase = lam / (2 * np.pi) * PLEATS + warp + 0.42 * theta
    rng = np.random.default_rng(6)
    amp = rng.uniform(0.45, 1.0, PLEATS + 8)[np.floor(phase).astype(int) % (PLEATS + 8)]
    pleat = saw(phase) * amp * (0.0042 + 0.0125 * np.exp(-(theta / 1.5) ** 2))
    broad = saw(lam / (2 * np.pi) * 5 + n2.fbm(d * 1.4, 2) * 0.16 + 0.2) * 0.0082 * np.clip(theta / 0.7, 0, 1)
    fine = n2.fbm(np.stack([lam * 5, theta * 2.5, d[..., 2]], -1), 3) * 0.0012
    drawn = saw(lam / (2 * np.pi) * 41 + n1.fbm(d * 1.8, 2) * 0.45) * 0.0015 * np.exp(-(theta / 1.9) ** 2)   # small pulls toward the knot

    bulk = 0.0062 + 0.0125 * dress.smoothstep(T, 0, 0.36) + 0.006 * d[..., 2] ** 2
    behind = np.clip(d @ np.array([0.0, 0.86, 0.5]), 0, 1)
    bulk = bulk + 0.018 * behind ** 2.2
    fold = dress.smoothstep(T, 0.145, 0.105) * 0.0034          # the edge is turned under once
    tuck = dress.smoothstep(T, 0.022, 0.0) * 0.0108        # and it is drawn in against the skin
    hug = dress.smoothstep(T, 0.03, 0.26)                      # folds ease out where the edge is drawn tight
    h = bulk + (pleat + broad + drawn) * hug + fine + fold - tuck
    return d, radius + h, lam, theta


def make(body, rig, col, material):
    M = np.array(dress.head_matrix(rig))
    tree = dress.head_tree(body)
    d, r, lam, theta = surface(tree)
    pts = CENTRE + d * r[..., None]
    verts = pts.reshape(-1, 3)

    nrows, ncols = SPOKES, RINGS
    idx = lambda i, j: (i % nrows) * ncols + j
    faces = [(idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)) for i in range(nrows) for j in range(ncols - 1)]
    verts = verts @ M[:3, :3].T + M[:3, 3]
    ob = obj_from_arrays('Ichafu', verts, faces, col)

    # cloth rows run along the folds, so a band of motifs follows each pleat toward the knot
    me = ob.data
    layer = me.uv_layers.new(name='UVMap')
    loops = np.zeros(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', loops)
    l = lam.ravel()[loops]
    uv = np.stack([theta.ravel()[loops] * 0.115 / U_PERIOD, (l / (2 * np.pi) * 0.74) * 0.72 / V_PERIOD * 1.15 + 0.30], 1)
    start = np.zeros(len(me.polygons), np.int32)
    me.polygons.foreach_get('loop_start', start)
    # keep one face on one side of the seam at lam = +-pi
    for s in start:
        q = l[s:s + 4]
        if q.max() - q.min() > np.pi:
            fixed = np.where(q < 0, q + 2 * np.pi, q)
            uv[s:s + 4, 1] = (fixed / (2 * np.pi) * 0.74) * 0.72 / V_PERIOD * 1.15 + 0.30
    layer.data.foreach_set('uv', uv.astype(np.float32).ravel())
    me.materials.append(material)
    sol = ob.modifiers.new('Thickness', 'SOLIDIFY')
    sol.thickness = 0.0012
    sol.offset = -1

    make_knot(d, r, M, col, material)
    make_ends(d, r, M, col, material)
    return ob


def knot_point(d, r):
    k = KNOT / np.linalg.norm(KNOT)
    i = np.unravel_index(np.argmax(d @ k), d.shape[:2])
    return CENTRE + d[i] * r[i], k


def make_knot(d, r, M, col, material):
    """A squat wrung knot: a ball of cloth with folds wound round it."""
    at, k = knot_point(d, r)
    x = np.cross(k, (0, 0, 1.0))
    x /= np.linalg.norm(x)
    y = np.cross(k, x)
    n = Noise(21)
    na, nb = 120, 60
    a = np.linspace(0, 2 * np.pi, na, endpoint=False)
    b = np.linspace(0.01, np.pi - 0.01, nb)
    A, B = np.meshgrid(a, b, indexing='ij')
    u = np.stack([np.sin(B) * np.cos(A), np.sin(B) * np.sin(A), np.cos(B)], -1)
    wind = saw((A / (2 * np.pi) * 6 + B * 1.1 + n.fbm(u * 1.5, 2) * 0.5)) * 0.0066
    rr = 1 + wind / 0.024
    p = u * np.array([0.033, 0.024, 0.021])[None, None] * rr[..., None]
    world = at + k * 0.012 + p[..., 0, None] * x + p[..., 1, None] * y + p[..., 2, None] * k
    verts = world.reshape(-1, 3)
    verts = verts @ M[:3, :3].T + M[:3, 3]
    idx = lambda i, j: (i % na) * nb + j
    faces = [(idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)) for i in range(na) for j in range(nb - 1)]
    uv = np.stack([A.ravel() * 0.03 / U_PERIOD, B.ravel() * 0.03 / V_PERIOD + 0.18], 1)
    ob = obj_from_arrays('IchafuKnot', verts, faces, col, uv=uv)
    ob.data.materials.append(material)
    return ob


def make_ends(d, r, M, col, material):
    """Two short ends: narrow at the knot, fanning out and falling behind the ear."""
    at, k = knot_point(d, r)
    R = M[:3, :3]
    made = []
    for name, side_lean, length, flare, seed in (('IchafuEndA', 0.85, 0.150, 0.082, 31), ('IchafuEndB', -0.55, 0.115, 0.070, 32)):
        n1 = Noise(seed)
        rows, cols = 70, 36
        s = np.linspace(0, 1, rows)
        out = k.copy()
        lean = np.cross(k, (0, 0, 1.0))
        lean /= np.linalg.norm(lean)
        # the centre line leaves the knot, then gravity takes it down
        c = np.zeros((rows, 3))
        v = (out * 0.8 + lean * side_lean * 0.8 + np.array([0, 0, 0.55]))
        v /= np.linalg.norm(v)
        p = at + k * 0.012
        step = length / rows
        for i in range(rows):
            c[i] = p
            v = v + np.array([0, 0, -1.0]) * (0.075 + 0.06 * s[i]) + k * 0.004
            v /= np.linalg.norm(v)
            p = p + v * step
        tan = np.gradient(c, axis=0)
        tan /= np.linalg.norm(tan, axis=1, keepdims=True)
        side = np.cross(tan, k + np.array([0, 0.0, 0.3]))
        side /= np.linalg.norm(side, axis=1, keepdims=True)
        nor = np.cross(side, tan)
        w = np.linspace(-1, 1, cols)
        S, W = np.meshgrid(s, w, indexing='ij')
        half = 0.012 + (flare / 2 - 0.012) * dress.smoothstep(S, 0.0, 0.8)
        ripple = np.sin(W * 7.5 + 1.3 * seed + S * 2) * 0.0058 * dress.smoothstep(S, 0.05, 0.75)
        ripple += n1.fbm(np.stack([W * 2.2, S * 4, np.full_like(S, seed)], -1), 3) * 0.0032
        pos = c[:, None] + side[:, None] * (half * W)[..., None] + nor[:, None] * ripple[..., None]
        pos = pos.reshape(-1, 3) @ R.T + M[:3, 3]
        idx = lambda i, j: i * cols + j
        faces = [(idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)) for i in range(rows - 1) for j in range(cols - 1)]
        uv = np.stack([(S.ravel() * length) / U_PERIOD + 0.1, (half.ravel() * W.ravel() + 0.042) / V_PERIOD + 0.006], 1)
        ob = obj_from_arrays(name, pos, faces, col, uv=uv)
        ob.data.materials.append(material)
        sol = ob.modifiers.new('Thickness', 'SOLIDIFY')
        sol.thickness = 0.0016
        made.append(ob)
    return made
