"""His hair: close-cut coils on the scalp, and no beard.

No source describes his hair. A young hunter who moves quietly through the forest keeps it short;
the method is Ògún's. Each hair is a small coil standing off the skin, and under the hair the skin
is darkened, as hair shadows it, so the curves need not be as dense as real hair.
"""
import math

import numpy as np
from mathutils import Vector

import dress
import materials as mats
from procedural import add_curves


def hair_material(name='CoilHair'):
    """Black-brown hair, with the soft sheen tight coils have rather than a straight hair's highlight."""
    g = mats.Graph(name)
    bsdf = g.t.nodes.new('ShaderNodeBsdfHairPrincipled')
    bsdf.parametrization = 'MELANIN'
    bsdf.inputs['Melanin'].default_value = 0.96
    bsdf.inputs['Melanin Redness'].default_value = 0.42
    bsdf.inputs['Roughness'].default_value = 0.42
    bsdf.inputs['Radial Roughness'].default_value = 0.62
    bsdf.inputs['Coat'].default_value = 0.08
    bsdf.inputs['Random Roughness'].default_value = 0.25
    return g.finish(bsdf.outputs[0])


def face_frame(body):
    """Rest-pose landmarks of the face, from the eye helpers and the lips."""
    info = eval(body['eyes'])
    eye = (np.array(info['L']['centre']) + np.array(info['R']['centre'])) / 2
    me = body.data
    co = np.array([v.co for v in me.vertices])
    lips = sorted({i for f in dress.layer_faces('lips_solid') for i in me.polygons[f].vertices})
    lp = co[lips]
    return dict(eye=eye, lips=lp, lip_top=float(lp[:, 2].max()), lip_bottom=float(lp[:, 2].min()),
                mouth_w=float(lp[:, 0].max()), lip_y=float(lp[:, 1].min()))


def scalp_mask(body):
    """Where hair grows, as a 0 to 1 weight per vertex: MPFB's scalp, with a man's hairline drawn on it.

    MPFB's scalp reaches down the forehead to the brows, so the hairline is set here, in
    millimetres from the eye centres: across the brow a hand's width up, a little higher at the
    temples, then down past the temples to the sideburns in front of the ears.
    """
    me = body.data
    n = len(me.vertices)
    co = np.array([v.co for v in me.vertices])
    m = np.zeros(n)
    for f in dress.layer_faces('scalp_solid'):
        m[list(me.polygons[f].vertices)] = 1
    adj = [[] for _ in range(n)]
    for e in me.edges:
        a, b = e.vertices
        adj[a].append(b)
        adj[b].append(a)
    m = dress.soften(m, adj, 2, 0.5)
    e = face_frame(body)['eye']
    x, y, z = np.abs(co[:, 0]), co[:, 1] - e[1], co[:, 2] - e[2]
    hl = 0.080 + 0.012 * dress.smoothstep(x, 0.020, 0.046)
    # the brow's hairline only bounds the front of the head; behind it the scalp itself is the edge
    front = np.maximum(dress.smoothstep(z, hl - 0.003, hl + 0.004), dress.smoothstep(y, 0.03, 0.05))
    y_edge = np.where(z > 0.030, 0.045 - (z - 0.030) * 1.0, 0.045)
    side = dress.smoothstep(y, y_edge - 0.003, y_edge + 0.004) * dress.smoothstep(z, -0.030, -0.022)
    side = np.maximum(side, dress.smoothstep(y, 0.10, 0.12))           # behind the ears it runs down to the nape
    w = dress.smoothstep(x, 0.044, 0.058)
    m *= front * (1 - w) + np.maximum(front, side) * w
    return np.clip(m, 0, 1), adj


def sample_face(vs, rng, k):
    """k points spread evenly over a triangle or quad."""
    tris = [(vs[0], vs[1], vs[2])] + ([(vs[0], vs[2], vs[3])] if len(vs) == 4 else [])
    areas = np.array([((b - a).cross(c - a)).length / 2 for a, b, c in tris])
    out = []
    for _ in range(k):
        a, b, c = tris[int(rng.choice(len(tris), p=areas / areas.sum()))]
        r1, r2 = math.sqrt(rng.random()), rng.random()
        out.append(a * (1 - r1) + b * (r1 * (1 - r2)) + c * (r1 * r2))
    return out


def coils(faces, me, weight, rng, per_area, length, coil_r, comb=None, M=None, points=12):
    """Hair curves scattered evenly over faces in proportion to area and weight, each a small coil."""
    strands = []
    co = [v.co for v in me.vertices]
    for f in faces:
        poly = me.polygons[f]
        w = float(np.mean([weight[i] for i in poly.vertices]))
        if w < 0.05:
            continue
        count = rng.poisson(poly.area * per_area * w)
        if not count:
            continue
        vs = [co[i] for i in poly.vertices]
        n = poly.normal
        for p in sample_face(vs, rng, count):
            L = rng.uniform(*length) * (0.6 + 0.4 * w)
            lean = (comb(p) if comb else Vector((0, 0, 0))) + Vector(rng.normal(0, 0.25, 3))
            grow = (n + lean).normalized()
            t1 = grow.orthogonal().normalized()
            t2 = grow.cross(t1)
            ph, turns = rng.uniform(0, 6.28), rng.uniform(1.0, 1.8)
            r = coil_r * rng.uniform(0.7, 1.25)
            pts = []
            for s in np.linspace(0, 1, points):
                a = ph + s * turns * 6.28
                q = p + grow * (L * s) + (t1 * math.cos(a) + t2 * math.sin(a)) * (r * math.sin(math.pi * min(s * 1.5, 1) / 2))
                pts.append(M @ q)
            strands.append(pts)
    return np.array(strands, np.float32)


def make(body, rig, col):
    M = dress.head_matrix(rig)
    me = body.data
    rng = np.random.default_rng(41)
    material = hair_material()
    scalp, adj = scalp_mask(body)
    faces = [p.index for p in me.polygons if max(scalp[i] for i in p.vertices) > 0.05]
    strands = coils(faces, me, scalp, rng, per_area=1.1e6, length=(0.0028, 0.0048), coil_r=0.00065, M=M)
    hair = add_curves('Hair', strands, 0.000075, 0.00004, col, material)
    print('hair curves', len(strands), flush=True)

    return hair, scalp
