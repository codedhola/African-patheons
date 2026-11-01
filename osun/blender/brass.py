"""Her brass: the abẹ̀bẹ̀ fan, the ààjà bell and the bangles.

The fan follows the layout of the High Museum's Fan for Osun: a round embossed disc on a
short handle, 35.6 by 22.2 cm, ribs radiating under a pair of relief figures, a rim of small
coils. Birds on that fan become two fish here, as on the gallery figure.
"""
import math

import numpy as np

import dress
import materials as mats
from common import TEX, obj_from_arrays

FAN_RADIUS = 0.111
HANDLE_LENGTH = 0.135


def brass_material(name='Brass'):
    """Cast brass, rubbed bright on the high spots and dark in the hollows."""
    g = mats.Graph(name)
    obj = g.node('TexCoord').outputs['Object']
    hammered = g.node('TexVoronoi', Vector=obj, Scale=170, Randomness=1.0).outputs['Distance']
    grime = g.node('TexNoise', Vector=obj, Scale=90, Detail=6, Roughness=0.62).outputs['Fac']
    fine = g.node('TexNoise', Vector=obj, Scale=900, Detail=4).outputs['Fac']
    col = g.ramp(grime, [(0.30, (0.42, 0.24, 0.075)), (0.55, (0.80, 0.56, 0.21)), (0.72, (0.95, 0.74, 0.34))])
    rough = g.ramp(grime, [(0.3, (0.46, 0.46, 0.46)), (0.7, (0.23, 0.23, 0.23))])
    normal = g.bump(g.math('ADD', g.math('MULTIPLY', hammered, 0.5), g.math('MULTIPLY', fine, 0.25)), 0.32, 0.0008)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Metallic=1.0, Roughness=rough, Normal=normal)
    return g.finish(bsdf.outputs[0])


def fan_relief(n=1400):
    """Height of the repoussé, on a square map of the disc from -1 to 1."""
    y, x = np.mgrid[0:n, 0:n] / (n - 1) * 2 - 1
    r = np.hypot(x, y)
    th = np.arctan2(y, x)
    h = np.zeros_like(r)

    # a raised outer lip, then a band of small coils
    h += 0.75 * dress.smoothstep(r, 0.955, 0.975)
    band = dress.smoothstep(r, 0.79, 0.81) * dress.smoothstep(r, 0.945, 0.925)
    coils = 44
    a = (th / (2 * np.pi) * coils) % 1 - 0.5
    rho = np.hypot(a / coils * 2 * np.pi * 0.87, r - 0.87)
    phi = np.arctan2(r - 0.87, a / coils * 2 * np.pi * 0.87)
    coil = np.sin(rho / 0.055 * 2 * np.pi * 2.0 - phi) * dress.smoothstep(rho, 0.062, 0.05)
    h += band * (0.28 + 0.30 * coil)
    h += 0.55 * np.exp(-((r - 0.785) / 0.012) ** 2)

    # ribs radiating from below the middle, as on the museum fan
    fy = y + 0.46
    fr = np.hypot(x, fy)
    ft = np.arctan2(x, fy)
    ribs = (0.5 + 0.5 * np.cos(ft * 46)) ** 0.7
    h += 0.30 * ribs * dress.smoothstep(fr, 0.26, 0.32) * dress.smoothstep(r, 0.78, 0.74) * dress.smoothstep(np.abs(ft), 1.75, 1.55)

    # two fish, nose to nose: a tapered body, a tail, scales
    for sign in (-1, 1):
        px = x * sign
        s = (y - 0.02) * 0.92 + (px - 0.33) * 0.38
        t = (px - 0.33) * 0.92 - (y - 0.02) * 0.38
        along = (s + 0.56) / 1.12
        half = 0.205 * np.sin(np.clip(along, 0, 1) * np.pi) ** 0.62
        body_mask = dress.smoothstep(np.abs(t) / np.maximum(half, 1e-3), 1.0, 0.82) * (along > 0) * (along < 1)
        dome = np.sqrt(np.clip(1 - (t / np.maximum(half, 1e-3)) ** 2, 0, 1))
        scales = 0.08 * np.sin((s * 26 + np.abs(t) * 20)) * np.sin((s * 26 - np.abs(t) * 20))
        fish = body_mask * (0.72 * dome + scales)
        tail = dress.smoothstep(np.abs(t), 0.16 * np.clip((-0.56 - s) / 0.2, 0, 1) + 1e-3, 0.0) * (s < -0.5) * (s > -0.78)
        h = np.maximum(h, fish)
        h = np.maximum(h, 0.5 * tail)
        eye = dress.smoothstep(np.hypot(s - 0.34, t + 0.05), 0.04, 0.025)
        h = h + 0.25 * eye
    return np.clip(h, 0, 1.2).astype(np.float32)


def make_fan(col, material):
    """Disc and handle along +Z, facing -Y, with the grip's centre at the origin."""
    relief = fan_relief()
    n = relief.shape[0]
    rings, spokes = 260, 480
    rr = np.linspace(0, 1, rings) ** 0.8
    th = np.linspace(0, 2 * np.pi, spokes, endpoint=False)
    R, T = np.meshgrid(rr, th, indexing='ij')
    x, y = R * np.cos(T), R * np.sin(T)
    ix = np.clip(((x + 1) / 2 * (n - 1)).astype(int), 0, n - 1)
    iy = np.clip(((y + 1) / 2 * (n - 1)).astype(int), 0, n - 1)
    h = relief[iy, ix]
    # one sheet of metal: the front rises where the back would sink
    centre_z = HANDLE_LENGTH * 0.62 + FAN_RADIUS
    front = np.stack([x * FAN_RADIUS, -0.0035 - h * 0.0062 - 0.003 * (1 - R ** 2), y * FAN_RADIUS + centre_z], -1)
    back = front.copy()
    back[..., 1] = 0.0015 - 0.003 * (1 - R ** 2) - h * 0.003
    verts = np.vstack([front.reshape(-1, 3), back.reshape(-1, 3)])
    idx = lambda s, i, j: s * rings * spokes + i * spokes + (j % spokes)
    faces = []
    for j in range(spokes):
        for i in range(rings - 1):
            faces.append((idx(0, i, j), idx(0, i + 1, j), idx(0, i + 1, j + 1), idx(0, i, j + 1)))
            faces.append((idx(1, i, j), idx(1, i, j + 1), idx(1, i + 1, j + 1), idx(1, i + 1, j)))
        faces.append((idx(0, rings - 1, j), idx(1, rings - 1, j), idx(1, rings - 1, j + 1), idx(0, rings - 1, j + 1)))

    # the handle: a turned brass rod with collars, flattening into the disc
    profile = [(-0.050, 0.0060), (-0.046, 0.0118), (-0.040, 0.0118), (-0.036, 0.0098), (-0.020, 0.0105), (0.030, 0.0105),
               (0.040, 0.0098), (0.046, 0.0125), (0.054, 0.0125), (0.058, 0.0095), (HANDLE_LENGTH * 0.62 + 0.012, 0.0085)]
    zs = np.array([p[0] for p in profile])
    rs = np.array([p[1] for p in profile])
    hz = np.linspace(zs[0], zs[-1], 90)
    hr = np.interp(hz, zs, rs)
    a = np.linspace(0, 2 * np.pi, 20, endpoint=False)
    handle = (np.stack([np.cos(a)[None] * hr[:, None], np.sin(a)[None] * hr[:, None] * 0.92, np.tile(hz[:, None], (1, 20))], -1)).reshape(-1, 3)
    base = len(verts)
    verts = np.vstack([verts, handle])
    for i in range(89):
        for j in range(20):
            k = (j + 1) % 20
            faces.append((base + i * 20 + j, base + i * 20 + k, base + (i + 1) * 20 + k, base + (i + 1) * 20 + j))
    ob = obj_from_arrays('Abebe', verts, faces, col)
    ob.data.materials.append(material)
    return ob


def lathe(profile, sides=64):
    """Solid of revolution about Z from (radius, z) pairs, with the ends closed."""
    pts = np.array(profile, float)
    a = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    verts = np.stack([np.outer(pts[:, 0], np.cos(a)), np.outer(pts[:, 0], np.sin(a)), np.tile(pts[:, 1:2], (1, sides))], -1).reshape(-1, 3)
    rows = len(pts)
    faces = [(i * sides + j, (i + 1) * sides + j, (i + 1) * sides + (j + 1) % sides, i * sides + (j + 1) % sides) for i in range(rows - 1) for j in range(sides)]
    return verts, faces


def smooth_profile(points, n=120):
    p = np.array(points, float)
    t = np.linspace(0, 1, len(p))
    s = np.linspace(0, 1, n)
    out = np.stack([np.interp(s, t, p[:, 0]), np.interp(s, t, p[:, 1])], 1)
    for _ in range(4):
        out[1:-1] = (out[:-2] + out[1:-1] * 2 + out[2:]) / 4
    return out


def make_bell(col, material):
    """The ààjà: a flared brass bell hanging from a rod handle, grip centre at the origin, mouth down."""
    body = smooth_profile([(0.0032, -0.058), (0.0105, -0.062), (0.0150, -0.082), (0.0195, -0.112), (0.0255, -0.142), (0.0365, -0.170),
                           (0.0405, -0.177), (0.0370, -0.177), (0.0235, -0.144), (0.0170, -0.114), (0.0105, -0.080), (0.0001, -0.070)], 140)
    v, f = lathe(body)
    rod = smooth_profile([(0.0, 0.066), (0.0078, 0.064), (0.0092, 0.056), (0.0092, 0.046), (0.0072, 0.040), (0.0076, -0.030), (0.0092, -0.042),
                          (0.0092, -0.052), (0.0060, -0.060), (0.0, -0.064)], 90)
    v2, f2 = lathe(rod, 24)
    clap = smooth_profile([(0.0, -0.160), (0.0052, -0.154), (0.0052, -0.146), (0.0014, -0.136), (0.0014, -0.075), (0.0, -0.07)], 40)
    v3, f3 = lathe(clap, 16)
    base = len(v)
    faces = list(f) + [tuple(i + base for i in q) for q in f2]
    verts = np.vstack([v, v2])
    base = len(verts)
    faces += [tuple(i + base for i in q) for q in f3]
    verts = np.vstack([verts, v3])
    ob = obj_from_arrays('Aaja', verts, faces, col)
    ob.data.materials.append(material)
    return ob
