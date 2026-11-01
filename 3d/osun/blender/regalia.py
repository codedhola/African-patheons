"""Her beads and brass: coral and amber strands, the Àrẹ́mọ́rùn choker, earrings and bangles."""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

import dress
import materials as mats
from common import WORK, obj_from_arrays, verts_world
from procedural import add_curves


def amber_material():
    """Amber, lit from within where the light comes through it."""
    g = mats.Graph('Amber')
    obj = g.node('TexCoord').outputs['Object']
    pick = g.node('Attribute', attribute_name='bead', attribute_type='GEOMETRY').outputs['Fac']
    base = g.ramp(pick, [(0.0, (0.62, 0.24, 0.018)), (0.5, (0.80, 0.40, 0.030)), (1.0, (0.92, 0.56, 0.075))])
    cloud = g.node('TexNoise', Vector=obj, Scale=160, Detail=5).outputs['Fac']
    col = g.mix(g.math('MULTIPLY', cloud, 0.45), base, (0.40, 0.12, 0.012))
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.17,
                  Subsurface_Weight=1.0, Subsurface_Scale=0.006)
    bsdf.inputs['Subsurface Radius'].default_value = (1.0, 0.52, 0.12)
    return g.finish(bsdf.outputs[0])


def wearing_tree(body, *cloths):
    """What beads rest on: the posed skin below the chin, and the cloth over it."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    verts = [ev.matrix_world @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons if all(verts[i].z < 1.45 for i in p.vertices)]
    ev.to_mesh_clear()
    for ob in cloths:
        base = len(verts)
        verts += [ob.matrix_world @ v.co for v in ob.data.vertices]
        polys += [tuple(i + base for i in p.vertices) for p in ob.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def string_beads(curve, rng, bead_l, bead_r, shapes=(('barrel', 0.8), ('round', 0.2))):
    """Beads laid end to end along a closed curve. Returns mesh parts."""
    closed = np.vstack([curve, curve[:1]])
    seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    parts = []
    s = 0.0
    while s < cum[-1] - bead_l * 0.6:
        if rng.random() < shapes[0][1]:
            L, r, shape = bead_l * rng.uniform(0.9, 1.25), bead_r * rng.uniform(0.92, 1.06), shapes[0][0]
        else:
            L, r, shape = bead_l * rng.uniform(0.55, 0.7), bead_r * rng.uniform(0.88, 0.98), shapes[1][0]
        mid = s + L / 2
        q = np.array([np.interp(mid, cum, closed[:, i]) for i in range(3)])
        q2 = np.array([np.interp(mid + 0.002, cum, closed[:, i]) for i in range(3)])
        v, f = dress.bead_mesh(L, r, int(rng.integers(1, 9999)), shape)
        parts.append((dress.place(v, q, q2 - q, rng.uniform(0, 6.28)), f))
        s += L + 0.0004
    return parts


def ring_at(tree_pts, centre, axis, offset, n=56):
    """A closed ring round a limb or the neck: the limb's outline at a plane, stood off by offset."""
    axis = np.array(axis, float)
    axis /= np.linalg.norm(axis)
    w = tree_pts - centre
    h = w @ axis
    rad = w - h[:, None] * axis
    near = (np.abs(h) < 0.010) & (np.linalg.norm(rad, axis=1) < 0.085)
    x = np.cross(axis, (0, 1.0, 0.0))
    x /= np.linalg.norm(x)
    y = np.cross(axis, x)
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    dirs = np.cos(a)[:, None] * x + np.sin(a)[:, None] * y
    reach = (rad[near] @ dirs.T).max(0)
    for _ in range(3):
        reach = (reach + np.roll(reach, 1) + np.roll(reach, -1)) / 3
    return centre + dirs * (reach + offset)[:, None]


def make_brows(body, rig, col, material):
    """Fine, arched brows, lifted at the outer end. Sources are silent on these: they suit the smile."""
    M = dress.head_matrix(rig)
    tree = dress.head_tree(body)
    info = eval(body['eyes'])
    rng = np.random.default_rng(12)
    strands = []
    for side, sign in (('L', 1), ('R', -1)):
        e = info[side]['centre']
        for _ in range(800):
            t = rng.beta(1.3, 1.35)
            x = 0.0130 + t * 0.0480
            z = e[2] + 0.0196 + 0.0056 * math.sin(math.pi * min(t * 1.18, 1) ** 0.85) + 0.0012 * t
            z += rng.uniform(-1, 1) * (0.0026 * (1 - t) ** 0.8 + 0.0007)
            hit, normal, _, _ = tree.ray_cast(Vector((sign * x, -0.4, z)), Vector((0, 1, 0)))
            if hit is None:
                continue
            angle = math.radians(70 * (1 - t) ** 1.7 - 12 * t + rng.normal(0, 7))
            d = Vector((sign * math.cos(angle), 0, math.sin(angle)))
            d = (d - d.dot(normal) * normal).normalized()
            L = rng.uniform(0.0048, 0.0072) * (1 - 0.25 * t)
            pts = [hit + normal * (0.0006 * (1 + 2.4 * s) * (1 - s) + 0.00012) + d * (L * s) for s in np.linspace(0, 1, 5)]
            strands.append([M @ p for p in pts])
    return add_curves('Brows', np.array(strands, np.float32), 0.000036, 0.000011, col, material)


def add_tiroo(body):
    """Tìróò: a fine dark line of eye cosmetic along the lash roots."""
    data = np.load(WORK / 'lashes.npz')
    roots = []
    for key in ('upper_L', 'upper_R', 'lower_L', 'lower_R'):
        pos, quads, eye = data[key + '_co'], data[key + '_quads'], data[key + '_eye']
        for q in quads:
            p = pos[q]
            roots.append(p[np.argsort(np.linalg.norm(p - eye, axis=1))[:2]].mean(0))
    roots = np.array(roots)
    me = body.data
    n = len(me.vertices)
    co = np.array([v.co for v in me.vertices])
    near = np.nonzero(np.linalg.norm(co - roots.mean(0), axis=1) < 0.09)[0]
    d = np.linalg.norm(co[near, None] - roots[None], axis=2).min(1)
    ca = me.color_attributes['mask_b']
    a = np.zeros(n * 4, np.float32)
    ca.data.foreach_get('color', a)
    a = a.reshape(-1, 4)
    a[near, 3] = np.clip(np.exp(-(d / 0.0031) ** 2) * 1.1, 0, 0.92)
    ca.data.foreach_set('color', a.ravel())


def make_beads(body, rig, blouse, col):
    """Three long strands, the choker, earrings, and a strand on each wrist."""
    tree = wearing_tree(body, blouse)
    co = verts_world(body)
    P = rig.pose.bones
    rng = np.random.default_rng(31)
    coral, amber, counts = [], [], {}

    neck = P['neck01'].head
    x0 = float(neck.x)
    strands = [('coral', 0.070, 0.066, 0.0058, 0.0092), ('amber', 0.086, 0.112, 0.0074, 0.0118), ('coral', 0.104, 0.158, 0.0086, 0.0150)]
    for kind, half, drop, r, L in strands:
        curve = dress.lay_strand(tree, x0, half, drop, r * 0.95)
        beads = string_beads(curve, rng, L, r)
        (coral if kind == 'coral' else amber).extend(beads)
        counts[kind] = counts.get(kind, 0) + len(beads)

    # the choker sits close at the base of the neck
    a, b = P['neck02'].head, P['neck01'].head
    axis = np.array(a - b)
    centre = np.array(b) + axis * 0.95
    ring = ring_at(co, centre, axis, 0.0052)
    choker = string_beads(ring, rng, 0.0062, 0.0046, (('round', 0.62), ('barrel', 0.38)))
    coral.extend(choker)
    counts['choker'] = len(choker)

    earrings = dress.earring_parts(body, rig, rng)
    amber.extend(earrings[1::3])
    coral.extend(earrings[0::3] + earrings[2::3])

    for side in 'LR':
        tail = np.array(P[f'wrist.{side}'].head)
        axis = tail - np.array(P[f'lowerarm02.{side}'].head)
        axis /= np.linalg.norm(axis)
        coral.extend(string_beads(ring_at(co, tail - axis * 0.012, axis, 0.0055), rng, 0.0078, 0.0052))
    print('beads', counts, 'in all', len(coral) + len(amber), flush=True)
    dress.join_beads('Coral', coral, col, mats.coral())
    dress.join_beads('AmberBeads', amber, col, amber_material())


def limb_radius(co, centre, axis):
    w = co - centre
    h = w @ axis
    rad = np.linalg.norm(w - h[:, None] * axis, axis=1)
    near = (np.abs(h) < 0.008) & (rad < 0.085)
    return float(np.percentile(rad[near], 80)) if near.any() else 0.03


def make_bangles(rig, body, col, material, count=6):
    """Six thin brass bangles on each arm, lying where gravity and the arm's taper leave them."""
    co = verts_world(body)
    P = rig.pose.bones
    rng = np.random.default_rng(3)
    made = 0
    for side, seed in (('L', 80), ('R', 90)):
        wrist = np.array(P[f'wrist.{side}'].head)
        elbow = np.array(P[f'lowerarm01.{side}'].head)
        axis = wrist - elbow
        length = np.linalg.norm(axis)
        axis = axis / length
        inner = 0.0355
        # rings slide down the arm until it is too thick for them, then pile up from there
        down = 1 if axis[2] < 0 else -1
        ts = np.linspace(0.92, 0.38, 28) if down < 0 else np.linspace(0.92, 1.0, 5)
        stop = ts[-1]
        if down < 0:
            for t in ts:
                if limb_radius(co, elbow + axis * length * t, axis) > inner * 0.99:
                    stop = t
                    break
        at = elbow + axis * length * stop
        gravity = np.array([0, 0, -1.0]) - np.array([0, 0, -1.0]) @ axis * axis
        for k in range(count):
            step = -down * 0.0078 * k
            c = at + axis * step
            r_here = limb_radius(co, c, axis)
            c = c + gravity * max(inner - r_here, 0) * 0.92
            tilt = Matrix.Rotation(rng.normal(0, 0.05), 3, Vector(np.cross(axis, (0.2, 0.9, 0.3))))
            z = tilt @ Vector(axis)
            x = z.orthogonal().normalized()
            m = Matrix((x, z.cross(x), z)).transposed().to_4x4()
            m.translation = c
            v, f = dress.ring_mesh(inner, inner + 0.0058, 0.0066, seed + k)
            ob = obj_from_arrays(f'Bangle.{side}.{k}', v, f, col)
            ob.matrix_world = m
            ob.data.materials.append(material)
            made += 1
    print('bangles', made, flush=True)
