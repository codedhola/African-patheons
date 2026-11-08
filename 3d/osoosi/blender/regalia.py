"""His beads: three strands of blue glass, as on his gallery figure.

In Candomblé his garment and beads are blue (Wikipedia: Oshosi). Here the beads are a turquoise
glass, each its own shade; the strand lengths and bead sizes are this study's. The cowrie and the
turned profile are kept here for the offerings at the iroko in the forest.
"""
import math

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import dress
import materials as mats
from procedural import Noise


def lathe(profile, sides=72):
    pts = np.array(profile, float)
    a = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    verts = np.stack([np.outer(pts[:, 0], np.cos(a)), np.outer(pts[:, 0], np.sin(a)), np.tile(pts[:, 1:2], (1, sides))], -1).reshape(-1, 3)
    rows = len(pts)
    faces = [(i * sides + j, i * sides + (j + 1) % sides, (i + 1) * sides + (j + 1) % sides, (i + 1) * sides + j) for i in range(rows - 1) for j in range(sides)]
    return verts, faces


def glass_material(name, colour, transmission=1.0, rough=0.04):
    g = mats.Graph(name)
    obj = g.node('TexCoord').outputs['Object']
    seed = g.node('Attribute', attribute_name='bead', attribute_type='GEOMETRY').outputs['Fac']
    tint = g.ramp(seed, [(0.0, tuple(c * 0.70 for c in colour)), (0.5, colour), (1.0, tuple(min(c * 1.25, 1.0) for c in colour))])
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


def wearing_tree(body, *over):
    """What beads rest on: the posed skin below the chin, and what he wears over it.

    The skin is chosen by what moves it, not by height: everything but the head, and the forearms and
    hands. His body is tilted along the shot, so a cut by height leaves holes in his shoulders, and the
    drawing forearm passes over his right one.
    """
    rig = bpy.data.objects['Rig']
    head_bones = {'head'} | {b.name for b in rig.data.bones['head'].children_recursive}
    groups = {g.index for g in body.vertex_groups if any(k in g.name for k in ('lowerarm', 'wrist', 'finger', 'metacarpal')) or g.name in head_bones}
    fore = [sum(g.weight for g in v.groups if g.group in groups) for v in body.data.vertices]
    saved = [(m, m.show_viewport) for m in body.modifiers if m.type in ('MASK', 'SUBSURF')]
    for m, _ in saved:
        m.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    verts = [ev.matrix_world @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons if all(fore[i] < 0.3 for i in p.vertices)]
    ev.to_mesh_clear()
    for m, on in saved:
        m.show_viewport = on
    for ob in over:
        e = ob.evaluated_get(dg)
        m2 = e.to_mesh()
        base = len(verts)
        verts += [e.matrix_world @ v.co for v in m2.vertices]
        polys += [tuple(i + base for i in p.vertices) for p in m2.polygons]
        e.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys)


def bead_ball(radius, seed):
    v, f, _ = dress.sphere(radius, 8, 12)
    n = Noise(seed)
    v = v * (1 + 0.04 * n(v * 300 + seed))[:, None] * np.array([1.0, 1.0, 0.82])
    return v, f


def strand_parts(curve, rng, radius):
    """Round glass beads end to end round a closed curve."""
    closed = np.vstack([curve, curve[:1]])
    cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(closed, axis=0), axis=1))])
    parts = []
    s = 0.0
    while s < cum[-1] - radius * 1.6:
        r = radius * rng.uniform(0.90, 1.08)
        mid = s + r * 0.82
        q = np.array([np.interp(mid, cum, closed[:, i]) for i in range(3)])
        q2 = np.array([np.interp(mid + 0.002, cum, closed[:, i]) for i in range(3)])
        v, f = bead_ball(r, int(rng.integers(1, 9999)))
        parts.append((dress.place(v, q, q2 - q, rng.uniform(0, 6.28)), f))
        s += r * 1.64 + 0.0002
    return parts


def make_beads(body, rig, col, *over):
    """Three strands of turquoise glass, each hanging a little lower than the last."""
    tree = wearing_tree(body, *over)
    neck = rig.pose.bones['neck01'].head
    rng = np.random.default_rng(37)
    beads = []
    for half, drop, r in ((0.068, 0.062, 0.0042), (0.082, 0.098, 0.0046), (0.096, 0.136, 0.0050)):
        curve = dress.lay_strand(tree, float(neck.x), half, drop, r * 0.95)
        # the toolkit smooths the strand after its last push off the skin; push once more, so no bead sinks in
        for i in range(len(curve)):
            hit, normal, _, _ = tree.find_nearest(Vector(curve[i]))
            if hit is not None and (Vector(curve[i]) - hit).dot(normal) < r * 1.05:
                curve[i] = np.array(hit + normal * r * 1.05)
        beads += strand_parts(curve, rng, r)
    ob = dress.join_beads('BlueBeads', beads, col, glass_material('Turquoise', (0.10, 0.50, 0.62), 0.45, 0.10))
    print('beads', len(beads), flush=True)
    return ob
