"""His iron and leather: the machete, the bangles, the strap and its pouch, and his beads.

The gallery figure carries a machete, iron bangles and a leather strap, and wears one strand
of black, white and red beads. Their forms are this study's: the machete broad with a clipped
point, the strap's pouch a small bag of the kind a man keeps his charms or his money in.
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
BLADE_LONG = 0.420
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
        band = g.math('LESS_THAN', edge, g.math('ADD', 0.0024, g.math('MULTIPLY', wav, 0.0026)))
        stretched = g.node('Mapping', Vector=obj, Scale=(1.0, 1.0, 0.004)).outputs[0]
        scratch = g.node('TexNoise', Vector=stretched, Scale=900, Detail=2).outputs['Fac']
        col = g.mix(band, col, g.ramp(scratch, [(0.35, (0.40, 0.40, 0.39)), (0.65, (0.55, 0.54, 0.52))]))
        metal = g.mix(band, metal, 1.0)
        rough = g.mix(band, rough, g.math('ADD', 0.34, g.math('MULTIPLY', scratch, 0.12)))
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
    """The machete along +Z from the middle of its grip, cutting edge toward -Y.

    About 55 cm overall: a broad blade whose spine drops to a clipped point, the flats dark and
    the edge bright from the stone. Its shape is this study's.
    """
    noise = Noise(41)
    stations = 150
    t = np.linspace(0, 1, stations)
    z = BLADE_START + t * BLADE_LONG
    # widening from the ferrule, rounding into the point over the last eighth
    w = 0.044 + 0.030 * np.clip(t / 0.78, 0, 1) ** 0.8
    tipzone = np.clip((t - 0.80) / 0.20, 0, 1)
    w = w * (1 - tipzone ** 1.6) + 0.0015
    thick = 0.0042 - 0.0018 * t
    # the spine stays straight; the edge drops as the blade widens, and the whole blade sweeps a little up
    sweep = -0.026 * np.clip((t - 0.78) / 0.22, 0, 1) ** 1.5     # the clip: the spine drops toward the point
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
    blade = obj_from_arrays('Mma', verts, faces, col)
    blade.data.attributes.new('edge', 'FLOAT', 'POINT').data.foreach_set('value', edge_d.astype(np.float32))
    blade.data.materials.append(iron_material('MmaIron', honed=True))

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
    handle = obj_from_arrays('MmaHandle', hv, hf, col)
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
    fittings = obj_from_arrays('MmaFittings', v, f, col)
    fittings.data.materials.append(bpy.data.materials.get('Iron') or iron_material())
    for ob in (handle, fittings):
        ob.parent = blade
    return blade


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


def baldric(points, shoulder, hip, band=0.010):
    """Where a chain worn from one shoulder to the other hip lies: the torso's section in that plane, pulled taut.

    A chain under the pull of its tools bridges the hollows it crosses, so the section is its
    convex hull. Returns the loop in 3D, its outward normals, and the plane's two axes.
    """
    d = (hip - shoulder) / np.linalg.norm(hip - shoulder)
    y = np.array([0, 1.0, 0])
    y = y - y.dot(d) * d
    y /= np.linalg.norm(y)
    n = np.cross(d, y)
    near = np.abs((points - shoulder) @ n) < band
    uv = np.stack([(points[near] - shoulder) @ d, (points[near] - shoulder) @ y], 1)
    hull = hull_2d(uv)
    loop, length = resample_closed(hull, 0.004)
    for _ in range(4):
        loop = (loop + np.roll(loop, 1, 0) + np.roll(loop, -1, 0)) / 3
    tan = np.roll(loop, -1, 0) - np.roll(loop, 1, 0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    out2 = np.stack([tan[:, 1], -tan[:, 0]], 1)          # counter-clockwise hull: outward is to the right
    for _ in range(12):                                   # a leather strap turns gradually round a corner, it does not crease
        out2 = (out2 + np.roll(out2, 1, 0) + np.roll(out2, -1, 0)) / 3
        out2 /= np.linalg.norm(out2, axis=1, keepdims=True)
    loop3 = shoulder + loop[:, :1] * d + loop[:, 1:] * y
    out3 = out2[:, :1] * d + out2[:, 1:] * y
    return loop3, out3, length


def posed_verts(body):
    """The posed body's own vertices, one per base vertex: masking and smoothing switched off while reading them."""
    saved = [(m, m.show_viewport) for m in body.modifiers if m.type in ('MASK', 'SUBSURF')]
    for m, _ in saved:
        m.show_viewport = False
    co = verts_world(body)
    for m, on in saved:
        m.show_viewport = on
    return co



# ----- the strap, its pouch, and the beads ------------------------------------

def leather_material(name='Leather', base=(0.060, 0.030, 0.014)):
    """Worn hide: a fine pebbled grain, darker and smoother where it has been handled."""
    g = mats.Graph(name)
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=60, Detail=5).outputs['Fac']
    grain = g.node('TexVoronoi', Vector=obj, Scale=1100, feature='DISTANCE_TO_EDGE').outputs['Distance']
    col = g.ramp(n, [(0.3, tuple(c * 0.72 for c in base)), (0.7, base)])
    normal = g.bump(g.math('ADD', g.math('MINIMUM', g.math('MULTIPLY', grain, 8.0), 1.0), g.math('MULTIPLY', n, 0.4)), 0.10, 0.0003)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=g.math('ADD', 0.40, g.math('MULTIPLY', n, 0.18)), Normal=normal)
    bsdf.inputs['Sheen Weight'].default_value = 0.2
    return g.finish(bsdf.outputs[0])


def make_strap(body, cloth_obs, rig, col, cord_top, width=0.044, thick=0.0035, over=()):
    """A leather strap over his left shoulder to his right side, lying where the chain lay on Ògún:
    the body's section in that plane, pulled taut. A small pouch hangs from it at his right hip."""
    co = posed_verts(body)
    from cloth import arm_weight
    # the arms are left out so the strap does not wrap round them, except at the shoulder, where the
    # deltoid is weighted to the arm but the strap still has to lie over it
    pts = [co[(arm_weight(body) < 0.15) | (co[:, 2] > 1.35)]] + [verts_world(ob) for ob in cloth_obs]
    pts = np.vstack(pts)
    P = rig.pose.bones
    shoulder = np.array(P['shoulder01.L'].head) + np.array([-0.010, 0.0, 0.0])
    # it crosses his right side above the gathered waistband, where there is room between the flank and the hanging arm
    hip = np.array([float(P['pelvis.R'].tail.x) - 0.07, float(P['pelvis.R'].tail.y), cord_top + 0.08])
    loop, out, length = baldric(pts, shoulder, hip, band=width / 2 + 0.008)
    n = len(loop)
    tan = np.roll(loop, -1, 0) - np.roll(loop, 1, 0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    side = np.cross(tan, out)
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    base = loop + out * (thick / 2 + 0.003)
    rings = []
    for k, (u, w) in enumerate(((-0.5, -1), (0.5, -1), (0.5, 1), (-0.5, 1))):
        rings.append(base + side * (u * width) + out * (w * thick / 2))
    verts = np.concatenate(rings)
    faces = []
    for k in range(4):
        a, b = k * n, ((k + 1) % 4) * n
        for i in range(n):
            j = (i + 1) % n
            faces.append((a + i, a + j, b + j, b + i))
    strap = obj_from_arrays('Strap', verts, faces, col)
    leather = leather_material()
    strap.data.materials.append(leather)
    # the pouch: a soft leather bag on the strap's front run, hanging in front of his right hip joint,
    # clear of the arm that hangs at his side
    hip_x, hip_y = float(P['upperleg01.R'].head.x), float(P['upperleg01.R'].head.y)
    front = (loop[:, 1] < hip_y - 0.04) & (loop[:, 2] < cord_top + 0.20)
    i = int(np.argmin(np.abs(loop[:, 0] - (hip_x - 0.01)) + 10.0 * ~front)) if front.any() else int(np.argmin(loop[:, 2]))
    top = base[i] + out[i] * 0.004
    # at the bottom of the loop the strap's outward normal points down: the bag hangs out from his side instead
    o = out[i] * np.array([1.0, 1.0, 0.0])
    o /= np.linalg.norm(o)
    sd = np.cross(np.array([0, 0, 1.0]), o)
    sd /= np.linalg.norm(sd)
    noise = Noise(51)
    rows, cols = 24, 40
    u = np.linspace(-1, 1, cols)
    v = np.linspace(0, 1, rows)
    U, V = np.meshgrid(u, v, indexing='ij')
    rounded = np.where(V > 0.68, np.sqrt(np.clip(1 - ((V - 0.68) / 0.32) ** 2, 0, 1)), 1.0)     # the bottom corners rounded
    half_w = 0.050 * (1 - 0.15 * V) * (0.42 + 0.58 * rounded)
    bulge = 0.022 * np.sqrt(np.clip(1 - U ** 2, 0, 1)) * np.sin(np.pi * np.clip(V * 1.05, 0, 1)) ** 0.7
    sag = 0.002 * noise.fbm(np.stack([U * 2, V * 3, np.zeros_like(U)], -1), 2)
    pos = top[None, None] + sd[None, None] * (U * half_w)[..., None] - np.array([0, 0, 1.0])[None, None] * (V * 0.115 + 0.012)[..., None] \
        + o[None, None] * (bulge + sag)[..., None]
    back = top[None, None] + sd[None, None] * (U * half_w)[..., None] - np.array([0, 0, 1.0])[None, None] * (V * 0.115 + 0.012)[..., None] - o[None, None] * 0.003
    if over:
        # it hangs on top of the fringe: each row stands out as far as the strands beneath it, and never comes back in
        under = np.vstack([verts_world(ob) for ob in over]) - top
        lateral, depth, outward = under @ sd, -under[:, 2], under @ o
        need = np.zeros(rows)
        for j in range(rows):
            near = (np.abs(lateral) < 0.058) & (np.abs(depth - (v[j] * 0.115 + 0.012)) < 0.010)
            if near.any():
                need[j] = outward[near].max() + 0.006
        need = np.maximum.accumulate(np.maximum(need, 0.0))
        pos = pos + o[None, None] * need[None, :, None]
        back = back + o[None, None] * need[None, :, None]
        print('pouch stands off the fringe by up to', round(float(need.max()), 3), flush=True)
    pv = np.vstack([pos.reshape(-1, 3), back.reshape(-1, 3)])
    idx = lambda s_, i_, j_: s_ * cols * rows + i_ * rows + j_
    pf = [(idx(0, i_, j_), idx(0, i_, j_ + 1), idx(0, i_ + 1, j_ + 1), idx(0, i_ + 1, j_)) for i_ in range(cols - 1) for j_ in range(rows - 1)]
    pf += [(idx(1, i_, j_), idx(1, i_ + 1, j_), idx(1, i_ + 1, j_ + 1), idx(1, i_, j_ + 1)) for i_ in range(cols - 1) for j_ in range(rows - 1)]
    for i_ in (0, cols - 1):
        pf += [(idx(0, i_, j_), idx(1, i_, j_), idx(1, i_, j_ + 1), idx(0, i_, j_ + 1)) for j_ in range(rows - 1)]
    pf += [(idx(0, i_, rows - 1), idx(0, i_ + 1, rows - 1), idx(1, i_ + 1, rows - 1), idx(1, i_, rows - 1)) for i_ in range(cols - 1)]
    pouch = obj_from_arrays('Pouch', pv, pf, col)
    pouch.data.materials.append(leather_material('PouchLeather', (0.085, 0.045, 0.020)))
    sub = pouch.modifiers.new('Smooth', 'SUBSURF')
    sub.levels = sub.render_levels = 1
    # the flap: over the top of the front, its lower edge curved and lowest in the middle, closed with a toggle
    vs = np.linspace(0, 1, rows)
    fl_rows = 10
    flap = np.zeros((cols, fl_rows, 3))
    for c in range(cols):
        reach = 0.36 + 0.10 * np.sqrt(np.clip(1 - u[c] ** 2, 0, 1))
        for r, t in enumerate(np.linspace(0, reach, fl_rows)):
            flap[c, r] = [np.interp(t, vs, pos[c, :, k]) for k in range(3)]
    flap = flap * 1.0 + o[None, None] * 0.0028 - np.array([0, 0, 1.0])[None, None] * 0.002
    fv = flap.reshape(-1, 3)
    ff = [(c * fl_rows + r, (c + 1) * fl_rows + r, (c + 1) * fl_rows + r + 1, c * fl_rows + r + 1) for c in range(cols - 1) for r in range(fl_rows - 1)]
    flap_ob = obj_from_arrays('PouchFlap', fv, ff, col)
    flap_ob.data.materials.append(leather_material('FlapLeather', (0.050, 0.025, 0.011)))
    sol = flap_ob.modifiers.new('Thickness', 'SOLIDIFY')
    sol.thickness = 0.0016
    sol.offset = -1
    tip = flap[cols // 2, fl_rows - 1]
    v, f, _ = dress.sphere(0.0055, 8, 12)
    toggle = obj_from_arrays('PouchToggle', v * np.array([1.0, 1.0, 1.6]) + tip + o * 0.004 + np.array([0, 0, 0.004]), f, col)
    horn = mats.Graph('Toggle')
    bsdf = horn.node('BsdfPrincipled', Base_Color=(0.030, 0.020, 0.014, 1), Roughness=0.35)
    toggle.data.materials.append(horn.finish(bsdf.outputs[0]))
    print('strap length', round(length, 3), flush=True)
    return strap, pouch


def make_necklace(body, rig, col, radius=0.0062):
    """One strand of black, white and red beads, the cap's colours, as on his gallery figure."""
    import dress
    from mathutils.bvhtree import BVHTree
    saved = [(m, m.show_viewport) for m in body.modifiers if m.type in ('MASK', 'SUBSURF')]
    for m, _ in saved:
        m.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    verts = [ev.matrix_world @ v.co for v in me.vertices]
    neck_z = float(rig.pose.bones['neck01'].head.z)
    polys = [tuple(p.vertices) for p in me.polygons if all(verts[i].z < neck_z + 0.02 for i in p.vertices)]
    tree = BVHTree.FromPolygons(verts, polys)
    ev.to_mesh_clear()
    for m, on in saved:
        m.show_viewport = on
    curve = dress.lay_strand(tree, float(rig.pose.bones['neck01'].head.x), 0.075, 0.075, radius * 0.95)
    closed = np.vstack([curve, curve[:1]])
    cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(closed, axis=0), axis=1))])
    rng = np.random.default_rng(71)
    parts = {0: [], 1: [], 2: []}
    s, k = 0.0, 0
    while s < cum[-1] - radius * 1.6:
        r = radius * rng.uniform(0.92, 1.06)
        mid = s + r * 0.85
        q = np.array([np.interp(mid, cum, closed[:, i]) for i in range(3)])
        q2 = np.array([np.interp(mid + 0.002, cum, closed[:, i]) for i in range(3)])
        v, f, _ = dress.sphere(r, 8, 12)
        v = v * np.array([1.0, 1.0, 0.85])
        parts[k % 3].append((dress.place(v, q, q2 - q, rng.uniform(0, 6.28)), f))
        s += r * 1.72
        k += 1
    obs = []
    for key, name, colour in ((0, 'BeadsBlack', (0.012, 0.011, 0.011)), (1, 'BeadsWhite', (0.80, 0.78, 0.72)), (2, 'BeadsRed', (0.42, 0.030, 0.020))):
        g = mats.Graph(name)
        bsdf = g.node('BsdfPrincipled', Base_Color=(*colour, 1), Roughness=0.22)
        bsdf.inputs['Coat Weight'].default_value = 0.4
        obs.append(dress.join_beads(name, parts[key], col, g.finish(bsdf.outputs[0])))
    print('necklace beads', k, flush=True)
    return obs


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


def make_bangles(rig, body, col, material, counts=(('L', 2), ('R', 2))):
    """Forged iron rings, two on each wrist, as on the gallery figure, slid down against the hand."""
    co = posed_verts(body)
    P = rig.pose.bones
    rng = np.random.default_rng(9)
    made = 0
    for side, count in counts:
        wrist = np.array(P[f'wrist.{side}'].head)
        elbow = np.array(P[f'lowerarm01.{side}'].head)
        axis = (wrist - elbow) / np.linalg.norm(wrist - elbow)
        inner = 0.0355
        at = wrist - axis * 0.014          # a centimetre up the forearm, off the swell at the base of the hand
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
