"""Her white pot, her beads and cowries, and her silver.

White jars and pitchers are among her shrine objects, her necklaces use crystalline beads,
and cowries stand for her wealth (Wikipedia: Yemọja). In Cuba her necklaces run seven blue
beads, then seven crystalline ones; her strands are strung so here. The forms are this
study's.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

import dress
import materials as mats
from common import obj_from_arrays, verts_world
from procedural import Noise, merged

POT_HALF = 0.148          # half the pot's height: its origin is at its middle


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
    """Fired clay under a white slip, rubbed thin on the belly and stained where water has run."""
    g = mats.Graph('WhitePot')
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=9, Detail=6, Roughness=0.6).outputs['Fac']
    fine = g.node('TexNoise', Vector=obj, Scale=180, Detail=4).outputs['Fac']
    z = g.node('SeparateXYZ', Vector=obj).outputs[2]
    runs = g.node('TexNoise', Vector=g.node('Mapping', Vector=obj, Scale=(40.0, 40.0, 2.0)).outputs[0], Scale=3.0, Detail=3).outputs['Fac']
    slip = g.ramp(n, [(0.3, (0.70, 0.68, 0.63)), (0.7, (0.84, 0.82, 0.77))])
    clay = (0.36, 0.20, 0.12)
    worn = g.math('MULTIPLY', g.math('SUBTRACT', fine, 0.72), 4.0, clamp=True)
    col = g.mix(worn, slip, clay)
    stain = g.math('MULTIPLY', g.math('SUBTRACT', runs, 0.55), 3.0, clamp=True)
    col = g.mix(g.math('MULTIPLY', stain, g.math('SUBTRACT', 0.4, g.math('MULTIPLY', z, 1.5), clamp=True)), col, (0.48, 0.42, 0.34))
    normal = g.bump(g.math('ADD', n, g.math('MULTIPLY', fine, 0.4)), 0.3, 0.0015)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=g.math('ADD', 0.55, g.math('MULTIPLY', fine, 0.2)), Normal=normal)
    return g.finish(bsdf.outputs[0])


def make_pot(col):
    """A white water jar about 30 cm tall, round-bellied with a short flared neck, origin at its middle."""
    outer = smooth_profile([(0.0, 0.0), (0.060, 0.0), (0.090, 0.022), (0.124, 0.075), (0.134, 0.130), (0.126, 0.185), (0.098, 0.228),
                            (0.066, 0.252), (0.060, 0.266), (0.068, 0.284), (0.079, 0.294), (0.080, 0.298)])
    inner = smooth_profile([(0.074, 0.298), (0.070, 0.292), (0.059, 0.282), (0.053, 0.266), (0.058, 0.250), (0.090, 0.226), (0.118, 0.185),
                            (0.126, 0.130), (0.115, 0.070), (0.080, 0.022), (0.0, 0.010)], 100)
    prof = np.vstack([outer, inner])
    prof[:, 1] -= POT_HALF
    v, f = lathe(prof)
    n = Noise(17)
    v = v * (1 + 0.006 * n.fbm(v * 14, 3))[:, None]           # thrown by hand, not turned true
    ob = obj_from_arrays('WhitePot', v, f, col)
    ob.data.materials.append(pot_material())
    sub = ob.modifiers.new('Smooth', 'SUBSURF')
    sub.levels = sub.render_levels = 1
    return ob


# ----- beads, cowries and silver -------------------------------------------

def glass_material(name, colour, transmission=1.0, rough=0.04):
    g = mats.Graph(name)
    obj = g.node('TexCoord').outputs['Object']
    seed = g.node('Attribute', attribute_name='bead', attribute_type='GEOMETRY').outputs['Fac']
    tint = g.mix(g.math('MULTIPLY', seed, 0.35), colour, (1.0, 1.0, 1.0))
    flaw = g.node('TexNoise', Vector=obj, Scale=900, Detail=2).outputs['Fac']
    bsdf = g.node('BsdfPrincipled', Base_Color=tint, Roughness=g.math('ADD', rough, g.math('MULTIPLY', flaw, 0.03)),
                  Normal=g.bump(flaw, 0.04, 0.0002))
    bsdf.inputs['Transmission Weight'].default_value = transmission
    bsdf.inputs['IOR'].default_value = 1.52
    return g.finish(bsdf.outputs[0])


def cowrie_material():
    g = mats.Graph('Cowrie')
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=300, Detail=4).outputs['Fac']
    col = g.ramp(n, [(0.3, (0.74, 0.70, 0.60)), (0.7, (0.86, 0.83, 0.74))])
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.18, Subsurface_Weight=0.3, Subsurface_Scale=0.002)
    bsdf.inputs['Coat Weight'].default_value = 0.5
    bsdf.inputs['Coat Roughness'].default_value = 0.08
    return g.finish(bsdf.outputs[0])


def silver_material():
    g = mats.Graph('Silver')
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=140, Detail=5).outputs['Fac']
    col = g.ramp(n, [(0.3, (0.55, 0.55, 0.56)), (0.7, (0.86, 0.86, 0.87))])
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Metallic=1.0, Roughness=g.math('ADD', 0.16, g.math('MULTIPLY', n, 0.14)),
                  Normal=g.bump(n, 0.15, 0.0004))
    return g.finish(bsdf.outputs[0])


def cowrie_mesh(length=0.021):
    """A money cowrie, toothed slit underneath: an egg flattened on its belly."""
    rows, cols = 22, 30
    verts = []
    for i in range(rows):
        t = i / (rows - 1)
        z = (t - 0.5) * length
        r = length * 0.36 * math.sin(math.pi * t) ** 0.75 + 0.0004
        for j in range(cols):
            a = 2 * math.pi * j / cols
            x, y = math.cos(a) * r, math.sin(a) * r * 0.78
            if y < 0:                                 # the flat belly, with the slit's teeth across it
                y *= 0.42
                if abs(x) < r * 0.16:
                    y += 0.0007 * (0.5 + 0.5 * math.cos(t * 2 * math.pi * 11))
            verts.append((x, y + r * 0.10, z))
    faces = [(i * cols + j, i * cols + (j + 1) % cols, (i + 1) * cols + (j + 1) % cols, (i + 1) * cols + j) for i in range(rows - 1) for j in range(cols)]
    return np.array(verts, np.float32), faces


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
    polys = [tuple(p.vertices) for p in me.polygons if all(verts[i].z < 1.42 for i in p.vertices)]
    ev.to_mesh_clear()
    for m, on in saved:
        m.show_viewport = on
    for ob in cloths:
        base = len(verts)
        verts += [ob.matrix_world @ v.co for v in ob.data.vertices]
        polys += [tuple(i + base for i in p.vertices) for p in ob.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def bead_ball(radius, seed):
    v, f, _ = dress.sphere(radius, 8, 12)
    n = Noise(seed)
    v = v * (1 + 0.04 * n(v * 300 + seed))[:, None] * np.array([1.0, 1.0, 0.82])
    return v, f


def strand_parts(curve, rng, radius, pattern):
    """Round glass beads end to end round a closed curve, coloured by a repeating pattern of 'b' and 'c'."""
    closed = np.vstack([curve, curve[:1]])
    cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(closed, axis=0), axis=1))])
    blue, crystal = [], []
    s, k = 0.0, 0
    while s < cum[-1] - radius * 1.6:
        r = radius * rng.uniform(0.92, 1.06)
        mid = s + r * 0.82
        q = np.array([np.interp(mid, cum, closed[:, i]) for i in range(3)])
        q2 = np.array([np.interp(mid + 0.002, cum, closed[:, i]) for i in range(3)])
        v, f = bead_ball(r, int(rng.integers(1, 9999)))
        part = (dress.place(v, q, q2 - q, rng.uniform(0, 6.28)), f)
        (blue if pattern[k % len(pattern)] == 'b' else crystal).append(part)
        s += r * 1.64 + 0.0002
        k += 1
    return blue, crystal


def make_beads(body, rig, blouse, col):
    """Four strands of light-blue and crystal glass, seven and seven, and a strand of cowries below them."""
    tree = wearing_tree(body, blouse)
    neck = rig.pose.bones['neck01'].head
    rng = np.random.default_rng(37)
    seven = 'b' * 7 + 'c' * 7
    blues, crystals = [], []
    for half, drop, r in ((0.064, 0.050, 0.0040), (0.078, 0.082, 0.0043), (0.092, 0.116, 0.0046), (0.106, 0.152, 0.0049)):
        curve = dress.lay_strand(tree, float(neck.x), half, drop, r * 0.95)
        b, c = strand_parts(curve, rng, r, seven)
        blues += b
        crystals += c
    blue_ob = dress.join_beads('BlueBeads', blues, col, glass_material('BlueGlass', (0.36, 0.66, 0.90), 0.55, 0.08))
    crystal_ob = dress.join_beads('CrystalBeads', crystals, col, glass_material('CrystalGlass', (0.93, 0.96, 1.0), 0.50, 0.10))
    # the cowries lie on their backs below the beads, slit outward, on a cord
    curve = dress.lay_strand(tree, float(neck.x), 0.120, 0.205, 0.0075)
    closed = np.vstack([curve, curve[:1]])
    cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(closed, axis=0), axis=1))])
    parts = []
    tree_n = tree
    count = 0
    s = 0.0
    while s < cum[-1] - 0.02:
        q = np.array([np.interp(s, cum, closed[:, i]) for i in range(3)])
        q2 = np.array([np.interp(s + 0.003, cum, closed[:, i]) for i in range(3)])
        hit = tree_n.find_nearest(Vector(q))
        nrm = np.array(hit[1]) if hit[0] is not None else np.array([0, -1.0, 0])
        v, f = cowrie_mesh(rng.uniform(0.016, 0.019))
        z = (q2 - q) / np.linalg.norm(q2 - q)
        y = -(nrm - nrm.dot(z) * z)          # the toothed slit faces out
        y /= np.linalg.norm(y)
        x = np.cross(y, z)
        R = np.stack([x, y, z], 1)
        parts.append(((R @ v.T).T + q + nrm * 0.0055, f))
        s += 0.0200
        count += 1
    v, f = merged(parts)
    cowries = obj_from_arrays('Cowries', v, f, col)
    cowries.data.materials.append(cowrie_material())
    print('beads', len(blues), 'blue', len(crystals), 'crystal; cowries', count, flush=True)
    return blue_ob, crystal_ob, cowries


def limb_radius(co, centre, axis):
    w = co - centre
    h = w @ axis
    rad = np.linalg.norm(w - h[:, None] * axis, axis=1)
    near = (np.abs(h) < 0.008) & (rad < 0.085)
    return float(np.percentile(rad[near], 85)) if near.any() else 0.03


def make_bangles(rig, body, col, count=3):
    """Three silver bangles on the right wrist, as on her gallery figure, slid down to the hand."""
    co = posed_verts(body)
    P = rig.pose.bones
    rng = np.random.default_rng(5)
    metal = silver_material()
    wrist = np.array(P['wrist.R'].head)
    elbow = np.array(P['lowerarm01.R'].head)
    axis = (wrist - elbow) / np.linalg.norm(wrist - elbow)
    inner = 0.0330
    for k in range(count):
        c = wrist - axis * (0.005 + 0.0068 * k)
        tilt = Matrix.Rotation(rng.normal(0, 0.06), 3, Vector(np.cross(axis, (0.3, 0.8, 0.2))))
        z = tilt @ Vector(axis)
        x = z.orthogonal().normalized()
        m = Matrix((x, z.cross(x), z)).transposed().to_4x4()
        m.translation = Vector(c)
        v, f = dress.ring_mesh(inner, inner + 0.0042, 0.0050, 400 + k)
        ob = obj_from_arrays(f'SilverBangle.{k}', v, f, col)
        ob.matrix_world = m
        ob.data.materials.append(metal)
    print('silver bangles', count, flush=True)
