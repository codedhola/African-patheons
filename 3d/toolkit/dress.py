"""Skin regions, eyes, brows and lashes, and the jewellery.

Everything here is built on the posed figure at the end of the arm move.
"""
import gzip
import json
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

import materials as mats
from common import TEX, WORK, edge_adjacency, obj_from_arrays, verts_world
from procedural import Noise, add_curves


def head_matrix(rig):
    return rig.pose.bones['head'].matrix @ rig.data.bones['head'].matrix_local.inverted()


def bone_matrix(rig, name):
    return rig.pose.bones[name].matrix @ rig.data.bones[name].matrix_local.inverted()


def layer_faces(name):
    """Faces of a named region, from MPFB's UV layer files."""
    from common import load_mpfb
    root = os.environ.get('MPFB_DATA') or load_mpfb()[2].get_mpfb_data('uv_layers')
    with gzip.open(os.path.join(root, name + '.json.gz'), 'rt') as f:
        return [int(k) for k in json.load(f)]


def smoothstep(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def soften(v, adj, n=1, amount=0.5):
    out = v.copy()
    for _ in range(n):
        nb = np.array([out[a].mean() if a else out[i] for i, a in enumerate(adj)])
        out += (nb - out) * amount
    return out


def skin_masks(body, rig, scalp_shade=True, lip_erode=0):
    """Write two colour layers: lips, palm, crease and nails, lids, flush.

    scalp_shade darkens the scalp behind the ears, where close-cut hair stands.
    lip_erode pulls the lip colour in from the edge of MPFB's lip region, by rings of vertices.
    """
    me = body.data
    B = rig.data.bones
    n = len(me.vertices)
    co = np.array([v.co for v in me.vertices])
    nor = np.zeros(n * 3)
    me.vertices.foreach_get('normal', nor)
    nor = nor.reshape(-1, 3)
    adj = edge_adjacency(me)

    def from_faces(name):
        m = np.zeros(n, np.float32)
        for f in layer_faces(name):
            m[list(me.polygons[f].vertices)] = 1
        return m

    lips = from_faces('lips_solid')
    if lip_erode:
        inside = lips > 0.5
        for _ in range(lip_erode):
            inside = np.array([x and all(inside[j] for j in adj[i]) for i, x in enumerate(inside)])
        lips = inside.astype(np.float32)
    lips = soften(lips, adj, 1, 0.5 if lip_erode else 0.3)
    lids = soften(from_faces('eyelids_solid'), adj, 2) * 0.5

    gi = {g.index: g.name for g in body.vertex_groups}
    hand = {'L': np.zeros(n), 'R': np.zeros(n)}
    for v in me.vertices:
        for g in v.groups:
            nm = gi[g.group]
            if nm.startswith(('wrist', 'finger', 'metacarpal')) and nm[-2:] in ('.L', '.R'):
                hand[nm[-1]][v.index] += g.weight

    palm = np.zeros(n, np.float32)
    nails = np.zeros(n, np.float32)
    crease = np.zeros(n, np.float32)
    for side in 'LR':
        wrist = B[f'wrist.{side}'].head_local
        along = (B[f'finger3-1.{side}'].head_local - wrist).normalized()
        across = (B[f'finger5-1.{side}'].head_local - B[f'finger2-1.{side}'].head_local).normalized()
        pn = np.array(along.cross(across) if side == 'R' else across.cross(along))
        pn /= np.linalg.norm(pn)
        d = nor @ pn
        palm = np.maximum(palm, smoothstep(d, -0.05, 0.60) * np.clip(hand[side], 0, 1))
        for k in range(1, 6):
            tip = np.array(B[f'finger{k}-3.{side}'].tail_local)
            dist = np.linalg.norm(co - tip, axis=1)
            nails = np.maximum(nails, smoothstep(0.0125, 0.0095, dist) * smoothstep(d, -0.62, -0.75))
            for j in (1, 2, 3):
                knuckle = np.array(B[f'finger{k}-{j}.{side}'].head_local)
                dist = np.linalg.norm(co - knuckle, axis=1)
                crease = np.maximum(crease, smoothstep(0.012, 0.004, dist) * smoothstep(d, 0.1, -0.5) * 0.55)
        elbow = np.array(B[f'lowerarm01.{side}'].head_local)
        crease = np.maximum(crease, smoothstep(0.042, 0.012, np.linalg.norm(co - elbow, axis=1)) * 0.5)
        # soles and toe tips
        low = co[:, 2] < 0.05
        palm = np.maximum(palm, (smoothstep(-nor[:, 2], 0.25, 0.75) * low * (co[:, 0] * (1 if side == 'L' else -1) > 0)))
        for k in range(1, 6):
            name = f'toe{k}-3.{side}' if f'toe{k}-3.{side}' in B else f'toe{k}-2.{side}'
            tip = np.array(B[name].tail_local)
            dist = np.linalg.norm(co - tip, axis=1)
            radius = 0.0125 if k == 1 else 0.0075
            nails = np.maximum(nails, smoothstep(radius, radius * 0.72, dist) * smoothstep(nor[:, 2], 0.45, 0.8))

    flush = np.zeros(n, np.float32)
    for sx in (-1, 1):
        d = np.linalg.norm(co - np.array([0.050 * sx, -0.098, 1.515]), axis=1)
        flush = np.maximum(flush, np.exp(-(d / 0.027) ** 2) * 0.32)
    d = np.linalg.norm(co - np.array([0.0, -0.138, 1.517]), axis=1)
    flush = np.maximum(flush, np.exp(-(d / 0.014) ** 2) * 0.22)

    scalp = soften(from_faces('scalp_solid'), adj, 2) * smoothstep(co[:, 1], -0.03, 0.0)
    if not scalp_shade:
        scalp = scalp * 0
    a = np.dstack([lips, soften(palm, adj, 1), soften(crease, adj, 1), scalp])[0]
    b = np.dstack([soften(nails, adj, 1, 0.3), lids, flush, np.zeros(n)])[0]      # alpha is left for eye paint
    for name, data in (('mask_a', a), ('mask_b', b)):
        ca = me.color_attributes.new(name, 'FLOAT_COLOR', 'POINT')
        ca.data.foreach_set('color', data.astype(np.float32).ravel())


def hide_covered(body, covers):
    """Mask out skin under the cloth, so it costs nothing and can never show through."""
    verts, polys, base = [], [], 0
    for ob in covers:
        verts += [ob.matrix_world @ v.co for v in ob.data.vertices]
        polys += [tuple(i + base for i in p.vertices) for p in ob.data.polygons]
        base += len(ob.data.vertices)
    tree = BVHTree.FromPolygons(verts, polys)
    co = verts_world(body)
    adj = edge_adjacency(body.data)
    from cloth import arm_weight
    arms = arm_weight(body)
    covered = np.zeros(len(co), bool)
    round_ = [Vector((math.cos(a), math.sin(a), 0)) for a in np.linspace(0, 6.28, 8, endpoint=False)]
    for i, p in enumerate(co):
        if p[2] > 1.30 or p[2] < 0.20 or arms[i] > 0.05:
            continue
        covered[i] = sum(tree.ray_cast(Vector(p), d, 0.6)[0] is not None for d in round_) == 8
    print('skin under cloth before margin:', int(covered.sum()), flush=True)
    # keep a two-ring margin inside every cuff and hem
    for _ in range(2):
        covered = np.array([c and all(covered[j] for j in adj[i]) for i, c in enumerate(covered)])
    vg = body.vertex_groups.new(name='visible')
    vg.add(np.nonzero(~covered)[0].tolist(), 1.0, 'REPLACE')
    print('skin hidden under cloth:', int(covered.sum()), 'of', len(co), flush=True)


def paint_eye(iris_r=0.47, pupil_r=0.155, white=(0.37, 0.32, 0.275), inner=(0.100, 0.044, 0.016), outer=(0.018, 0.009, 0.006)):
    """Dark brown iris with radial fibres, in a front-on map of the eyeball."""
    rng = np.random.default_rng(5)
    n = 1024
    y, x = np.mgrid[0:n, 0:n] / (n - 1) * 2 - 1
    r = np.hypot(x, y)
    th = np.arctan2(y, x)

    fibres = np.zeros_like(r)
    for f in (23, 41, 67, 113, 181, 271):
        fibres += np.sin(th * f + rng.uniform(0, 6.28) + 2.5 * np.sin(r * 7 + rng.uniform(0, 6.28))) / np.sqrt(f)
    fibres = fibres / fibres.std()
    rr = (r - pupil_r) / (iris_r - pupil_r)
    inner, outer = np.array(inner), np.array(outer)
    iris = inner[None, None] * (1 - rr[..., None]) ** 2 + outer[None, None] * (1 - (1 - rr[..., None]) ** 2)
    iris = iris * (1 + 0.42 * fibres[..., None])

    streak = np.zeros_like(r)
    for _ in range(26):
        a, f = rng.uniform(0, 6.28), rng.uniform(5, 16)
        streak += np.exp(-((r - rng.uniform(0.55, 0.95)) / 0.2) ** 2) * np.maximum(np.sin(th * f + a), 0) ** 40
    sclera = np.array(white)[None, None] * np.ones_like(r[..., None])
    sclera = sclera * (1 - 0.36 * smoothstep(np.abs(x), 0.55, 1.0))[..., None]
    sclera = sclera + np.array([0.20, -0.20, -0.20])[None, None] * np.clip(streak * 0.12, 0, 0.5)[..., None]

    m = smoothstep(r, iris_r - 0.022, iris_r + 0.022)[..., None]
    col = iris * (1 - m) + sclera * m
    ring = np.exp(-((r - iris_r + 0.02) / 0.030) ** 2)[..., None]
    col = col * (1 - 0.72 * ring)
    pupil = smoothstep(r, pupil_r + 0.012, pupil_r - 0.012)[..., None]
    col = col * (1 - pupil) + 0.003 * pupil
    from weave import save
    rgba = np.dstack([np.clip(col, 0, 1) ** (1 / 2.2), np.ones_like(r)])
    save(TEX / 'eye_color.png', rgba)


def sphere(radius, rows=48, cols=64, bulge=None):
    """UV sphere with its pole forward along -Y, UV as a front-on projection."""
    verts, uvs = [(0, -radius, 0)], [(0.5, 0.5)]
    for i in range(1, rows):
        a = math.pi * i / rows
        for j in range(cols):
            b = 2 * math.pi * j / cols
            d = np.array([math.sin(a) * math.cos(b), -math.cos(a), math.sin(a) * math.sin(b)])
            r = radius * (bulge(a) if bulge else 1)
            verts.append(tuple(d * r))
            uvs.append((d[0] / 2 + 0.5, d[2] / 2 + 0.5))
    verts.append((0, radius, 0))
    uvs.append((0.5, 0.5))
    faces = []
    for j in range(cols):
        faces.append((0, 1 + j, 1 + (j + 1) % cols))
    for i in range(rows - 2):
        for j in range(cols):
            a = 1 + i * cols + j
            b = 1 + i * cols + (j + 1) % cols
            faces.append((a, a + cols, b + cols, b))
    last = len(verts) - 1
    for j in range(cols):
        faces.append((last, last - cols + (j + 1) % cols, last - cols + j))
    return np.array(verts), faces, np.array(uvs)


def make_eyes(body, rig, col, look_at, **paint):
    """Eyeballs with the cornea modelled as a bulge in one wet surface."""
    M = head_matrix(rig)
    info = eval(body['eyes'])
    paint_eye(**paint)
    eye_m = mats.eye()
    made = []
    for side in 'LR':
        c = M @ Vector(info[side]['centre'])
        R = info[side]['radius'] * 0.985
        v, f, uv = sphere(R, bulge=lambda a: 1 + 0.085 * math.exp(-(a / 0.50) ** 2))
        ball = obj_from_arrays(f'Eye.{side}', v, f, col, uv=uv)
        ball.data.materials.append(eye_m)
        fwd = (M.to_3x3() @ Vector((0, -1, 0))).normalized()
        want = (Vector(look_at) - c).normalized()
        q = fwd.rotation_difference(want)
        q = Quaternion(q.axis, min(q.angle, math.radians(14)))
        ball.matrix_world = Matrix.Translation(c) @ (q @ M.to_quaternion()).to_matrix().to_4x4()
        made.append(ball)
    return made


def head_tree(body):
    me = body.data
    return BVHTree.FromPolygons([v.co for v in me.vertices], [tuple(p.vertices) for p in me.polygons])


def make_brows(body, rig, col, material):
    """Curves laid along the brow ridge, combed up at the inner end and out along the tail."""
    M = head_matrix(rig)
    tree = head_tree(body)
    info = eval(body['eyes'])
    rng = np.random.default_rng(12)
    strands = []
    for side, sign in (('L', 1), ('R', -1)):
        e = info[side]['centre']
        for _ in range(1150):
            t = rng.beta(1.5, 1.45)
            x = 0.0125 + t * 0.0480
            z = e[2] + 0.0245 + 0.0060 * math.sin(math.pi * min(t * 1.25, 1) ** 0.8) - 0.0052 * t ** 2.4
            hh = 0.0036 * (1 - t) ** 0.7 + 0.0010
            z += rng.uniform(-1, 1) * hh
            hit, normal, _, _ = tree.ray_cast(Vector((sign * x, -0.4, z)), Vector((0, 1, 0)))
            if hit is None:
                continue
            angle = math.radians(74 * (1 - t) ** 1.6 - 15 * t + rng.normal(0, 7))
            d = Vector((sign * math.cos(angle), 0, math.sin(angle)))
            d = (d - d.dot(normal) * normal).normalized()
            L = rng.uniform(0.0055, 0.0085) * (1 - 0.22 * t)
            pts = [hit + normal * (0.0007 * (1 + 2.6 * s) * (1 - s) + 0.00015) + d * (L * s) for s in np.linspace(0, 1, 5)]
            strands.append([M @ p for p in pts])
    return add_curves('Brows', np.array(strands, np.float32), 0.000042, 0.000012, col, material)


def make_lashes(rig, col, material):
    M = head_matrix(rig)
    data = np.load(WORK / 'lashes.npz')
    rng = np.random.default_rng(3)
    strands = []
    for key, per_quad, scale, curl in (('upper_L', 3, 1.06, 0.8), ('upper_R', 3, 1.06, 0.8), ('lower_L', 2, 0.62, -0.3), ('lower_R', 2, 0.62, -0.3)):
        pos, quads, centre = data[key + '_co'], data[key + '_quads'], data[key + '_eye']
        for q in quads:
            p = pos[q]
            order = np.argsort(np.linalg.norm(p - centre, axis=1))
            root, tip = p[order[:2]], p[order[2:]]
            if np.dot(root[1] - root[0], tip[1] - tip[0]) < 0:
                tip = tip[::-1]
            for _ in range(per_quad):
                t = rng.random()
                a = root[0] + (root[1] - root[0]) * t
                b = tip[0] + (tip[1] - tip[0]) * t
                d = (b - a) * scale * rng.uniform(0.72, 1.05)
                lift = np.array([0, 0, 1.0]) * np.linalg.norm(d) * curl
                s = np.linspace(0, 1, 5)[:, None]
                pts = a + d * s + lift * s * s * 0.5
                strands.append([M @ Vector(x) for x in pts])
    return add_curves('Lashes', np.array(strands, np.float32), 0.00007, 0.000015, col, material)


def join_beads(name, parts, col, material):
    """One mesh from many beads, with a random value per bead for the coral's tint."""
    verts, faces, rand, base = [], [], [], 0
    rng = np.random.default_rng(23)
    for v, f in parts:
        verts.append(v)
        faces += [tuple(i + base for i in q) for q in f]
        rand.append(np.full(len(v), rng.random(), np.float32))
        base += len(v)
    ob = obj_from_arrays(name, np.concatenate(verts), faces, col)
    attr = ob.data.attributes.new('bead', 'FLOAT', 'POINT')
    attr.data.foreach_set('value', np.concatenate(rand))
    ob.data.materials.append(material)
    sub = ob.modifiers.new('Smooth', 'SUBSURF')
    sub.levels = 1
    sub.render_levels = 2
    return ob


def bead_mesh(length, radius, seed, shape='barrel', rows=7, cols=10):
    """A hand-ground coral bead along +Z, not quite round, with a drilled end."""
    n = Noise(seed)
    verts = []
    for i in range(rows):
        t = i / (rows - 1)
        z = (t - 0.5) * length
        if shape == 'barrel':
            r = radius * (0.72 + 0.28 * math.sin(math.pi * t) ** 0.6)
        else:
            r = radius * max(math.sin(math.pi * t) ** 0.55, 0.28)
        for j in range(cols):
            a = 2 * math.pi * j / cols
            p = np.array([math.cos(a), math.sin(a), 0.0])
            lump = 1 + 0.035 * float(n(p * 1.1 + z * 30 + seed))
            verts.append((p[0] * r * lump, p[1] * r * lump, z))
    faces = []
    for i in range(rows - 1):
        for j in range(cols):
            a = i * cols + j
            b = i * cols + (j + 1) % cols
            faces.append((a, b, b + cols, a + cols))
    # close the ends just inside the drill hole
    faces.append(tuple(range(cols))[::-1])
    faces.append(tuple(range((rows - 1) * cols, rows * cols)))
    return np.array(verts, np.float32), faces


def place(v, p, tangent, spin=0.0):
    """Stand a bead on +Z at p, pointing along tangent."""
    z = Vector(tangent).normalized()
    x = z.orthogonal().normalized()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed() @ Matrix.Rotation(spin, 3, 'Z')
    return (np.array(m) @ v.T).T + np.array(p)


def lay_strand(tree, cx, half_width, drop, radius, n=70):
    """A closed U of beads laid on the wearer: down the chest, over the shoulders, across the back."""
    def top(x):
        hit = tree.ray_cast(Vector((x, 0.01, 1.7)), Vector((0, 0, -1)))[0]
        return hit.z if hit is not None else 1.36

    left, right = top(cx + half_width), top(cx - half_width)
    mid = (left + right) / 2 - 0.006

    def level(a):
        # level across the chest, reaching each shoulder only at the very top
        return mid + (left - right) / 2 * math.sin(a) ** 5

    pts = []
    for a in np.linspace(-0.5 * np.pi, 0.5 * np.pi, n):
        q = Vector((cx + half_width * math.sin(a), -0.6, level(a) - drop * math.cos(a)))
        hit, normal, _, _ = tree.ray_cast(q, Vector((0, 1, 0)))
        if hit is not None:
            pts.append(hit + normal * radius)
    for y in np.linspace(-0.035, 0.055, 9):
        hit, normal, _, _ = tree.ray_cast(Vector((cx + half_width, y, 1.7)), Vector((0, 0, -1)))
        if hit is not None:
            pts.append(hit + normal * radius)
    for a in np.linspace(0.5 * np.pi, -0.5 * np.pi, n // 2):
        q = Vector((cx + half_width * math.sin(a), 0.6, level(a) - 0.022 * math.cos(a)))
        hit, normal, _, _ = tree.ray_cast(q, Vector((0, -1, 0)))
        if hit is not None:
            pts.append(hit + normal * radius)
    for y in np.linspace(0.055, -0.035, 9):
        hit, normal, _, _ = tree.ray_cast(Vector((cx - half_width, y, 1.7)), Vector((0, 0, -1)))
        if hit is not None:
            pts.append(hit + normal * radius)
    p = np.array(pts, np.float64)
    for _ in range(14):
        p = (p + np.roll(p, 1, axis=0) + np.roll(p, -1, axis=0)) / 3
        if _ % 3 == 2:
            for i in range(len(p)):
                q = Vector(p[i])
                hit, normal, _h, _d = tree.find_nearest(q)
                if hit is not None and (q - hit).dot(normal) < radius:
                    p[i] = np.array(hit + normal * radius)
    return p


def chest_tree(body, blouse):
    """Surface the jewellery rests on: the blouse and the skin below the chin, as evaluated."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    verts = [ev.matrix_world @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons if all(verts[i].z < 1.44 for i in p.vertices)]
    ev.to_mesh_clear()
    base = len(verts)
    verts += [v.co.copy() for v in blouse.data.vertices]
    polys += [tuple(i + base for i in p.vertices) for p in blouse.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def lobe_point(body, rig, side):
    """The lowest point of the ear, on the posed head."""
    sign = 1 if side == 'L' else -1
    co = np.array([v.co for v in body.data.vertices])
    ear = (co[:, 0] * sign > 0.066) & (co[:, 1] > -0.06) & (co[:, 2] > 1.46) & (co[:, 2] < 1.60)
    idx = np.nonzero(ear)[0]
    return head_matrix(rig) @ Vector(co[idx[np.argmin(co[idx, 2])]])


def earring_parts(body, rig, rng):
    """Three coral beads hanging from each lobe."""
    parts = []
    for side in 'LR':
        p = lobe_point(body, rig, side) + Vector((0, 0.001, -0.002))
        for L, r, shape in ((0.007, 0.0040, 'round'), (0.014, 0.0044, 'barrel'), (0.0085, 0.0050, 'round')):
            v, f = bead_mesh(L, r, int(rng.integers(1, 9999)), shape)
            p = p + Vector((0, 0, -L / 2))
            parts.append((place(v, p, (0, 0, 1), rng.uniform(0, 6.28)), f))
            p = p + Vector((0, 0, -L / 2 - 0.0003))
    return parts


def bracelet_parts(body, rig, rng):
    """A single strand on each forearm, above the ivory."""
    P = rig.pose.bones
    co = verts_world(body)
    parts = []
    for side in 'LR':
        tail = np.array(P[f'wrist.{side}'].head)
        axis = tail - np.array(P[f'lowerarm02.{side}'].head)
        axis /= np.linalg.norm(axis)
        c = tail - axis * 0.085
        w = co - c
        h = w @ axis
        rad = w - h[:, None] * axis
        near = (np.abs(h) < 0.012) & (np.linalg.norm(rad, axis=1) < 0.06)
        x = np.cross(axis, (0, 0, 1.0))
        x /= np.linalg.norm(x)
        y = np.cross(axis, x)
        a = np.linspace(0, 2 * np.pi, 48, endpoint=False)
        dirs = np.cos(a)[:, None] * x + np.sin(a)[:, None] * y
        reach = (rad[near] @ dirs.T).max(0)
        closed = c + dirs * (reach + 0.0064)[:, None]
        closed = np.vstack([closed, closed[:1]])
        cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(closed, axis=0), axis=1))])
        s = 0.0
        while s < cum[-1] - 0.006:
            L, r = rng.uniform(0.0085, 0.012), rng.uniform(0.0052, 0.0062)
            q = np.array([np.interp(s + L / 2, cum, closed[:, i]) for i in range(3)])
            q2 = np.array([np.interp(s + L / 2 + 0.002, cum, closed[:, i]) for i in range(3)])
            v, f = bead_mesh(L, r, int(rng.integers(1, 9999)), 'barrel')
            parts.append((place(v, q, q2 - q, rng.uniform(0, 6.28)), f))
            s += L + 0.0004
    return parts


def make_necklaces(body, blouse, rig, col):
    """Three strands of nkalari coral, two lying at the collar and one long, with earrings and wrist strands."""
    tree = chest_tree(body, blouse)
    coral = mats.coral()
    rng = np.random.default_rng(8)
    parts = []
    counted = []
    neck = rig.pose.bones['neck01'].head
    for half_width, drop, bead_r, bead_l in ((0.066, 0.050, 0.0062, 0.0100), (0.086, 0.094, 0.0074, 0.0125), (0.108, 0.140, 0.0086, 0.0160)):
        p = lay_strand(tree, neck.x, half_width, drop, bead_r * 0.95)
        closed = np.vstack([p, p[:1]])
        seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
        cum = np.concatenate([[0], np.cumsum(seg)])
        s = 0.0
        count = 0
        while s < cum[-1] - bead_l * 0.6:
            # long tubes and small rounds in the way big coral is strung
            kind = rng.random()
            if kind < 0.8:
                L, Rr, shape = bead_l * rng.uniform(0.9, 1.25), bead_r * rng.uniform(0.92, 1.06), 'barrel'
            else:
                L, Rr, shape = bead_l * rng.uniform(0.55, 0.7), bead_r * rng.uniform(0.88, 0.98), 'round'
            mid = s + L / 2
            q = np.array([np.interp(mid, cum, closed[:, i]) for i in range(3)])
            q2 = np.array([np.interp(mid + 0.002, cum, closed[:, i]) for i in range(3)])
            v, f = bead_mesh(L, Rr, int(rng.integers(1, 9999)), shape)
            parts.append((place(v, q, q2 - q, rng.uniform(0, 6.28)), f))
            s += L + 0.0004
            count += 1
        counted.append(count)
    print('coral beads', counted, flush=True)
    parts += earring_parts(body, rig, rng) + bracelet_parts(body, rig, rng)
    return join_beads('Coral', parts, col, coral)


def ring_mesh(inner, outer, width, seed, rows=14, cols=96):
    """A turned ring along Z with a rounded section, a little out of true like carved tusk."""
    n = Noise(seed)
    verts = []
    for j in range(cols):
        a = 2 * math.pi * j / cols
        wob = 1 + 0.012 * float(n(np.array([math.cos(a), math.sin(a), 0.0]) * 1.4 + seed))
        for i in range(rows):
            b = 2 * math.pi * i / rows
            r = (inner + outer) / 2 + (outer - inner) / 2 * math.cos(b)
            z = width / 2 * math.sin(b)
            z *= 1 - 0.2 * (math.cos(b) < 0)
            verts.append((math.cos(a) * r * wob, math.sin(a) * r * wob, z))
    faces = []
    for j in range(cols):
        for i in range(rows):
            faces.append(((j * rows + i), (j * rows + (i + 1) % rows), (((j + 1) % cols) * rows + (i + 1) % rows), (((j + 1) % cols) * rows + i)))
    return np.array(verts, np.float32), faces


def make_bangles(rig, col):
    """Odu aka at the wrists and odu ukwu at the ankles, sized to hang free of the arm."""
    ivory = mats.ivory()
    P = rig.pose.bones
    made = []
    for side, sign in (('L', 1), ('R', -1)):
        # two wrist rings, sliding down the forearm toward the elbow-side of the wrist bones
        head = P[f'lowerarm02.{side}'].head
        tail = P[f'wrist.{side}'].head
        axis = (tail - head).normalized()
        for k, back in enumerate((0.022, 0.052)):
            c = tail - axis * back + Vector((0, 0, -0.007 - 0.003 * k))
            tilt = Quaternion(Vector((1, 0, 0)), math.radians(6 * (1 - 2 * k)))
            z = (tilt @ axis).normalized()
            x = z.orthogonal().normalized()
            m = Matrix((x, z.cross(x), z)).transposed().to_4x4()
            m.translation = c
            v, f = ring_mesh(0.0325 + 0.0015 * k, 0.0435 + 0.0015 * k, 0.017, 60 + k + (0 if side == 'L' else 5))
            ob = obj_from_arrays(f'OduAka.{side}.{k}', v, f, col)
            ob.matrix_world = m
            ob.data.materials.append(ivory)
            made.append(ob)
        # one heavy ring at each ankle, resting on the top of the foot
        ankle = P[f'foot.{side}'].head
        c = Vector((ankle.x - sign * 0.002, ankle.y + 0.003, 0.092))
        tilt = Quaternion(Vector((1, 0, 0)), math.radians(-9)) @ Quaternion(Vector((0, 1, 0)), math.radians(4 * sign))
        m = tilt.to_matrix().to_4x4()
        m.translation = c
        v, f = ring_mesh(0.0425, 0.0545, 0.0195, 70 + (0 if side == 'L' else 5))
        ob = obj_from_arrays(f'OduUkwu.{side}', v, f, col)
        ob.matrix_world = m
        ob.data.materials.append(ivory)
        made.append(ob)
    return made
