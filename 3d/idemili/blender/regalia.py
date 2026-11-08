"""Her clay pot, her coral and her ivory.

Large coral beads are worn round the neck and on the wrists, and ivory ornaments, odu, were
the insignia of the Otu Odu society of Igbo women, worn on the wrists and ankles (Wikipedia:
Igbo regalia and headdresses). Her gallery figure wears three strands of coral and two ivory
bangles on her right wrist, and carries a clay pot. The forms are this study's.
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

POT_SCALE = 0.80          # about the gallery figure's pot: 24 cm tall, 22 cm across
POT_HALF = 0.148 * POT_SCALE          # half the pot's height: its origin is at its middle


def lathe(profile, sides=72):
    pts = np.array(profile, float)
    a = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    verts = np.stack([np.outer(pts[:, 0], np.cos(a)), np.outer(pts[:, 0], np.sin(a)), np.tile(pts[:, 1:2], (1, sides))], -1).reshape(-1, 3)
    rows = len(pts)
    faces = [(i * sides + j, i * sides + (j + 1) % sides, (i + 1) * sides + (j + 1) % sides, (i + 1) * sides + j) for i in range(rows - 1) for j in range(sides)]
    return verts, faces


def smooth_profile(points, n=140):
    p = np.array(points, float)
    t = np.linspace(0, 1, len(p))
    s = np.linspace(0, 1, n)
    out = np.stack([np.interp(s, t, p[:, 0]), np.interp(s, t, p[:, 1])], 1)
    for _ in range(5):
        out[1:-1] = (out[:-2] + out[1:-1] * 2 + out[2:]) / 4
    return out


def pot_material():
    """Open-fired clay, burnished: red-brown with the dark clouds of the fire on it, and dark where river water has soaked in."""
    g = mats.Graph('ClayPot')
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=7, Detail=6, Roughness=0.6).outputs['Fac']
    clouds = g.node('TexNoise', Vector=obj, Scale=3.2, Detail=4, Roughness=0.55).outputs['Fac']
    fine = g.node('TexNoise', Vector=obj, Scale=220, Detail=4).outputs['Fac']
    z = g.node('SeparateXYZ', Vector=obj).outputs[2]
    col = g.ramp(n, [(0.3, (0.20, 0.085, 0.040)), (0.7, (0.30, 0.135, 0.065))])
    smoke = g.math('MULTIPLY', g.math('SUBTRACT', clouds, 0.58), 4.0, clamp=True)
    col = g.mix(smoke, col, (0.040, 0.028, 0.022))
    soaked = g.math('MULTIPLY', g.math('SUBTRACT', -0.08, z), 9.0, clamp=True)
    col = g.mix(g.math('MULTIPLY', soaked, 0.6), col, (0.11, 0.050, 0.028))
    # burnished with a stone: smooth and a little glossy, with the strokes still faintly there
    strokes = g.node('TexNoise', Vector=g.node('Mapping', Vector=obj, Scale=(30.0, 30.0, 3.0)).outputs[0], Scale=4.0, Detail=3).outputs['Fac']
    rough = g.math('ADD', 0.34, g.math('ADD', g.math('MULTIPLY', strokes, 0.18), g.math('MULTIPLY', smoke, 0.15)))
    normal = g.bump(g.math('ADD', g.math('MULTIPLY', fine, 0.3), g.math('MULTIPLY', strokes, 0.2)), 0.25, 0.0012)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=rough, Normal=normal)
    bsdf.inputs['Coat Weight'].default_value = 0.15
    bsdf.inputs['Coat Roughness'].default_value = 0.35
    return g.finish(bsdf.outputs[0])


POT_OUTER = [(0.0, 0.0), (0.050, 0.0), (0.092, 0.020), (0.128, 0.072), (0.138, 0.128), (0.130, 0.182), (0.102, 0.226),
             (0.070, 0.250), (0.062, 0.264), (0.070, 0.282), (0.084, 0.293), (0.086, 0.298)]


def pot_radius(h):
    """The pot's outer radius at height h above its middle."""
    prof = smooth_profile(POT_OUTER) * POT_SCALE
    return float(np.interp(h + POT_HALF, prof[:, 1], prof[:, 0]))


def make_pot(col):
    """A clay water pot about 24 cm tall, round-bellied with a short neck and an everted rim, origin at its middle."""
    outer = smooth_profile(POT_OUTER)
    inner = smooth_profile([(0.080, 0.298), (0.075, 0.292), (0.062, 0.282), (0.055, 0.266), (0.060, 0.250), (0.093, 0.226), (0.122, 0.185),
                            (0.130, 0.130), (0.118, 0.070), (0.082, 0.022), (0.0, 0.010)], 100)
    prof = np.vstack([outer, inner]) * POT_SCALE
    prof[:, 1] -= POT_HALF
    v, f = lathe(prof)
    n = Noise(29)
    v = v * (1 + 0.007 * n.fbm(v * 12, 3))[:, None]           # built up by hand, not turned true
    ob = obj_from_arrays('ClayPot', v, f, col)
    ob.data.materials.append(pot_material())
    sub = ob.modifiers.new('Smooth', 'SUBSURF')
    sub.levels = sub.render_levels = 1
    return ob


# ----- coral and ivory -------------------------------------------------------

def posed_verts(body):
    """The posed body's own vertices, one per base vertex: masking and smoothing switched off while reading them."""
    saved = [(m, m.show_viewport) for m in body.modifiers if m.type in ('MASK', 'SUBSURF')]
    for m, _ in saved:
        m.show_viewport = False
    co = verts_world(body)
    for m, on in saved:
        m.show_viewport = on
    return co


def wearing_tree(body, *cloths):
    """What beads rest on: the posed skin below the chin, and the cloth over it."""
    saved = [(m, m.show_viewport) for m in body.modifiers if m.type in ('MASK', 'SUBSURF')]
    for m, _ in saved:
        m.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    verts = [ev.matrix_world @ v.co for v in me.vertices]
    neck_z = max(v.z for v in verts) * 0.86
    polys = [tuple(p.vertices) for p in me.polygons if all(verts[i].z < neck_z for i in p.vertices)]
    ev.to_mesh_clear()
    for m, on in saved:
        m.show_viewport = on
    for ob in cloths:
        base = len(verts)
        verts += [ob.matrix_world @ v.co for v in ob.data.vertices]
        polys += [tuple(i + base for i in p.vertices) for p in ob.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def coral_strand(curve, rng, radius, tree):
    """Barrel beads of coral end to end round a closed curve, each a little different in length and girth,
    each lifted onto the skin or the cloth where the curve dips into it, as at the sides of the neck."""
    closed = np.vstack([curve, curve[:1]])
    cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(closed, axis=0), axis=1))])
    parts = []
    s = 0.0
    while s < cum[-1] - radius * 2.2:
        length = radius * rng.uniform(1.5, 2.2)
        r = radius * rng.uniform(0.90, 1.08)
        mid = s + length / 2
        q = np.array([np.interp(mid, cum, closed[:, i]) for i in range(3)])
        q2 = np.array([np.interp(mid + 0.002, cum, closed[:, i]) for i in range(3)])
        loc, nrm, _, dist = tree.find_nearest(Vector(q))
        if loc is not None:
            off = (Vector(q) - loc).dot(nrm)
            if off < r + 0.0018:                   # the render's smoothing moves the skin a little: keep clear of it
                lift = np.array(nrm) * (r + 0.0018 - off)
                q, q2 = q + lift, q2 + lift
        v, f = dress.bead_mesh(length, r, int(rng.integers(1, 9999)))
        parts.append((dress.place(v, q, q2 - q, rng.uniform(0, 6.28)), f))
        s += length + 0.0006
    return parts


def make_beads(body, rig, wrapper, col):
    """Three strands of large coral beads at the base of her neck, the lowest lying on the top of her wrapper."""
    tree = wearing_tree(body, wrapper)
    neck = rig.pose.bones['neck01'].head
    rng = np.random.default_rng(43)
    parts = []
    for half, drop, r in ((0.060, 0.040, 0.0052), (0.074, 0.070, 0.0058), (0.088, 0.102, 0.0064)):
        curve = dress.lay_strand(tree, float(neck.x), half, drop, r * 1.05)
        parts += coral_strand(curve, rng, r, tree)
    ob = dress.join_beads('Coral', parts, col, mats.coral())
    print('coral beads', len(parts), flush=True)
    return ob


def limb_radius(co, centre, axis):
    w = co - centre
    h = w @ axis
    rad = np.linalg.norm(w - h[:, None] * axis, axis=1)
    near = (np.abs(h) < 0.008) & (rad < 0.085)
    return float(np.percentile(rad[near], 85)) if near.any() else 0.03


def make_bangles(rig, body, col, count=2):
    """Two heavy ivory bangles on the right wrist, as on her gallery figure, slid down against the hand."""
    co = posed_verts(body)
    P = rig.pose.bones
    rng = np.random.default_rng(8)
    ivory = mats.ivory()
    wrist = np.array(P['wrist.R'].head)
    elbow = np.array(P['lowerarm01.R'].head)
    axis = (wrist - elbow) / np.linalg.norm(wrist - elbow)
    for k in range(count):
        c = wrist - axis * (0.012 + 0.0175 * k)
        r_here = limb_radius(co, c, axis)
        inner = max(r_here + 0.004, 0.031)
        tilt = Matrix.Rotation(rng.normal(0, 0.07), 3, Vector(np.cross(axis, (0.3, 0.8, 0.2))))
        z = tilt @ Vector(axis)
        x = z.orthogonal().normalized()
        m = Matrix((x, z.cross(x), z)).transposed().to_4x4()
        m.translation = Vector(c)
        v, f = dress.ring_mesh(inner, inner + 0.0105, 0.0150, 500 + k)
        ob = obj_from_arrays(f'IvoryBangle.{k}', v, f, col)
        ob.matrix_world = m
        ob.data.materials.append(ivory)
    print('ivory bangles', count, flush=True)
