"""Close-cut coiled hair where the ichafu leaves the scalp showing: behind the ears and at the nape."""
import math

import numpy as np
from mathutils import Vector

import dress
import headtie
from yam import add_curves


def make(body, rig, col, material, per_face=34):
    M = dress.head_matrix(rig)
    me = body.data
    rng = np.random.default_rng(17)
    strands = []
    for f in dress.layer_faces('scalp_solid'):
        poly = me.polygons[f]
        vs = [me.vertices[i].co for i in poly.vertices]
        n = poly.normal
        for _ in range(per_face):
            w = rng.dirichlet((1, 1, 1, 1)[:len(vs)])
            p = sum((v * a for v, a in zip(vs, w)), Vector((0, 0, 0)))
            d = p - Vector(headtie.CENTRE)
            az = math.atan2(d.y, d.x) % (2 * math.pi)
            el = math.asin(d.z / d.length)
            # under the tie it cannot be seen: leave a little overlap beneath the edge
            if el > float(headtie.edge_elevation(az)) + math.radians(4):
                continue
            # the face keeps a clean hairline: nothing in front of the ears
            if d.y < -0.012:
                continue
            L = rng.uniform(0.0022, 0.0042)
            ph, turns = rng.uniform(0, 6.28), rng.uniform(1.2, 2.2)
            t1 = n.orthogonal().normalized()
            t2 = n.cross(t1)
            pts = []
            for s in np.linspace(0, 1, 7):
                a = ph + s * turns * 6.28
                pts.append(M @ (p + n * (L * s) + (t1 * math.cos(a) + t2 * math.sin(a)) * (0.0008 * math.sin(math.pi * min(s * 1.2, 1)))))
            strands.append(pts)
    ob = add_curves('EdgeHair', np.array(strands, np.float32), 0.00007, 0.00003, col, material)
    print('edge hair curves', len(strands), flush=True)
    return ob
