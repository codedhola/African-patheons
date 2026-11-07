"""The ajá: a village dog asleep on the warm floor of the forge, at his side.

The dog is one of Ògún's symbols (Wikipedia: Ogun), and the gallery figure keeps one at his
side; stage 08 has it asleep by the fire. It is drawn as the short-coated, prick-eared dogs of
West African villages are: tan with white on the chest, paws and muzzle, lying on its chest
with its head on its forepaws and its hind legs folded to one side. Its form is this study's.

The body is a set of metaballs in the dog's own frame, nose toward +X, joined into one smooth
skin and coated with hair curves combed from nose to tail and down the legs.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

import materials as mats
from common import edge_adjacency, obj_from_arrays
from dress import smoothstep
from procedural import Noise, add_curves

K = 1 / 0.57             # a metaball's surface lies at 0.57 of its radius when it stands alone

# ellipsoids: name, centre, radii, rotation (axis, degrees)
BLOBS = [
    ('chest', (0.100, 0.0, 0.136), (0.145, 0.104, 0.124), None),
    ('ribs', (-0.050, 0.0, 0.130), (0.130, 0.095, 0.106), None),
    ('loin', (-0.185, 0.003, 0.128), (0.088, 0.080, 0.086), None),
    ('rump', (-0.290, 0.012, 0.124), (0.100, 0.102, 0.106), None),
    ('withers', (0.150, 0.0, 0.205), (0.090, 0.085, 0.070), None),
    ('skull', (0.340, 0.0, 0.318), (0.078, 0.063, 0.062), ((0, 1, 0), 8)),
    ('brow', (0.374, 0.0, 0.338), (0.030, 0.044, 0.024), None),
    ('cheek.L', (0.370, 0.031, 0.298), (0.040, 0.027, 0.032), None),
    ('cheek.R', (0.370, -0.031, 0.298), (0.040, 0.027, 0.032), None),
    ('nose', (0.488, 0.0, 0.302), (0.012, 0.0145, 0.010), None),
    ('snout', (0.432, 0.0, 0.302), (0.060, 0.030, 0.026), None),
    ('flew.L', (0.432, 0.019, 0.285), (0.050, 0.016, 0.017), None),
    ('flew.R', (0.432, -0.019, 0.285), (0.050, 0.016, 0.017), None),
    ('jaw', (0.408, 0.0, 0.276), (0.056, 0.022, 0.015), None),
    ('thigh.L', (-0.255, 0.082, 0.096), (0.098, 0.050, 0.082), ((0, 0, 1), -12)),
    ('thigh.R', (-0.255, -0.082, 0.096), (0.098, 0.050, 0.082), ((0, 0, 1), 12)),
    ('fpaw.L', (0.440, 0.058, 0.022), (0.042, 0.029, 0.022), None),
    ('fpaw.R', (0.424, -0.060, 0.022), (0.042, 0.029, 0.022), ((0, 0, 1), -8)),
    ('hpaw.L', (-0.130, 0.114, 0.020), (0.040, 0.026, 0.020), None),
    ('hpaw.R', (-0.140, -0.114, 0.020), (0.040, 0.026, 0.020), None),
]
# capsules: name, from, to, radius
LIMBS = [
    ('neck', (0.180, 0.0, 0.195), (0.305, 0.0, 0.292), 0.063),
    ('uarm.L', (0.155, 0.068, 0.140), (0.115, 0.074, 0.040), 0.035),
    ('uarm.R', (0.155, -0.068, 0.140), (0.115, -0.074, 0.040), 0.035),
    ('farm.L', (0.115, 0.074, 0.034), (0.398, 0.060, 0.028), 0.026),
    ('farm.R', (0.115, -0.074, 0.034), (0.382, -0.062, 0.028), 0.026),
    ('hock.L', (-0.330, 0.098, 0.034), (-0.165, 0.112, 0.025), 0.023),
    ('hock.R', (-0.330, -0.098, 0.034), (-0.172, -0.112, 0.025), 0.023),
]
EARS = [((0.322, 0.040, 0.362), 1), ((0.322, -0.040, 0.362), -1)]
TAIL = [(-0.385, 0.0, 0.142), (-0.432, -0.045, 0.085), (-0.410, -0.110, 0.040), (-0.320, -0.150, 0.026), (-0.215, -0.163, 0.024), (-0.120, -0.160, 0.024)]
EYES = [(0.392, 0.031, 0.322), (0.392, -0.031, 0.322)]
EYE_R = 0.0098


def build_metaball(col):
    mb = bpy.data.metaballs.new('DogMeta')
    mb.resolution = 0.008
    mb.render_resolution = 0.0045
    mb.threshold = 0.6
    ob = bpy.data.objects.new('DogMeta', mb)
    col.objects.link(ob)
    for name, c, r, rot in BLOBS:
        e = mb.elements.new(type='ELLIPSOID')
        e.co = c
        e.radius = 1.0
        e.size_x, e.size_y, e.size_z = (x * K for x in r)
        e.stiffness = 2.0 if name not in ('nose', 'ear.L', 'ear.R') else 3.0
        if rot:
            e.rotation = Quaternion(Vector(rot[0]).normalized(), math.radians(rot[1]))
    for name, a, b, r in LIMBS:
        a, b = Vector(a), Vector(b)
        e = mb.elements.new(type='CAPSULE')
        e.co = (a + b) / 2
        e.radius = r * K
        e.size_x = (b - a).length / 2
        e.rotation = Vector((1, 0, 0)).rotation_difference(b - a)
        e.stiffness = 2.0
    pts = np.array(TAIL)
    s = np.linspace(0, 1, 26)
    t = np.linspace(0, 1, len(pts))
    path = np.stack([np.interp(s, t, pts[:, i]) for i in range(3)], 1)
    for k, p in enumerate(path):
        e = mb.elements.new(type='BALL')
        e.co = p
        e.radius = (0.024 - 0.013 * s[k] ** 1.3) * K
        e.stiffness = 2.6
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    bpy.data.metaballs.remove(mb)
    return me


def ear_parts():
    """Prick ears laid back in sleep: cupped triangles of skin, each with a front and a back."""
    parts = []
    nu, nv = 9, 12
    for base, side in EARS:
        u = np.linspace(-1, 1, nu)
        v = np.linspace(0, 1, nv)
        U, V = np.meshgrid(u, v, indexing='ij')
        width = 0.027 * (1 - V) ** 0.85 + 0.0030
        cup = 0.014 * (1 - U ** 2) * (1 - V * 0.6)
        local = []
        for t in (-1, 1):
            x = U * width
            z = V * 0.070
            y = cup + t * (0.0055 * (1 - V) ** 1.3 + 0.0010) * (1 - 0.5 * U ** 4)
            local.append(np.stack([x, y * side, z], -1))
        R = Matrix.Rotation(math.radians(-14), 3, 'Y') @ Matrix.Rotation(math.radians(-16 * side), 3, 'X')
        R = np.array(R)
        verts = [(R @ g.reshape(-1, 3).T).T + np.array(base) for g in local]
        verts = np.vstack(verts)
        idx = lambda k, i, j: k * nu * nv + i * nv + j
        faces = []
        for i in range(nu - 1):
            for j in range(nv - 1):
                faces.append((idx(0, i, j), idx(0, i + 1, j), idx(0, i + 1, j + 1), idx(0, i, j + 1)))
                faces.append((idx(1, i, j), idx(1, i, j + 1), idx(1, i + 1, j + 1), idx(1, i + 1, j)))
        for j in range(nv - 1):
            for i in (0, nu - 1):
                faces.append((idx(0, i, j), idx(0, i, j + 1), idx(1, i, j + 1), idx(1, i, j)))
        for i in range(nu - 1):
            faces.append((idx(0, i, nv - 1), idx(0, i + 1, nv - 1), idx(1, i + 1, nv - 1), idx(1, i, nv - 1)))
        parts.append((verts, faces))
    return parts


def regions(co):
    """Coat markings and bare skin, per vertex: white, dark saddle, nose leather, eye slits."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    white = np.zeros(len(co))
    # chest and throat
    white = np.maximum(white, smoothstep(-np.abs(y) + 0.060, 0.0, 0.03) * smoothstep(x, 0.08, 0.16) * smoothstep(0.16, 0.11, z) * smoothstep(x, 0.42, 0.36))
    # paws and the end of the muzzle
    white = np.maximum(white, smoothstep(0.050, 0.032, z) * (smoothstep(x, 0.36, 0.40) + smoothstep(-0.10, -0.16, x) * smoothstep(np.abs(y), 0.09, 0.10)))
    tail_tip = np.linalg.norm(co - np.array(TAIL[-1]), axis=1)
    white = np.maximum(white, smoothstep(0.06, 0.03, tail_tip))
    dark = smoothstep(z, 0.18, 0.24) * smoothstep(x, -0.35, -0.2) * smoothstep(0.30, 0.22, x)
    dark = np.maximum(dark, smoothstep(z, 0.33, 0.37) * smoothstep(x, 0.28, 0.31) * 0.5)
    # a dark mask over the muzzle, as many fawn village dogs have, and dark-rimmed ears
    dark = np.maximum(dark, smoothstep(x, 0.395, 0.425) * smoothstep(z, 0.24, 0.26))
    for c in ((0.315, 0.050, 0.400), (0.315, -0.050, 0.400)):
        dark = np.maximum(dark, smoothstep(0.050, 0.030, np.linalg.norm(co - np.array(c), axis=1)) * 0.7)
    nose = smoothstep(0.0165, 0.0115, np.linalg.norm((co - np.array([0.491, 0.0, 0.303])) * np.array([1.0, 0.85, 1.15]), axis=1))
    eye = np.zeros(len(co))
    for c in EYES:
        eye = np.maximum(eye, smoothstep(EYE_R + 0.0045, EYE_R + 0.0015, np.linalg.norm(co - np.array(c), axis=1)))
    return white, dark, nose, eye


def coat_material():
    """The skin under the coat, the leather of the nose and the closed eyes."""
    g = mats.Graph('DogSkin')
    w = g.node('Attribute', attribute_name='white', attribute_type='GEOMETRY').outputs['Fac']
    d = g.node('Attribute', attribute_name='dark', attribute_type='GEOMETRY').outputs['Fac']
    nose = g.node('Attribute', attribute_name='nose', attribute_type='GEOMETRY').outputs['Fac']
    eye = g.node('Attribute', attribute_name='eye', attribute_type='GEOMETRY').outputs['Fac']
    obj = g.node('TexCoord').outputs['Object']
    grain = g.node('TexVoronoi', Vector=obj, Scale=700, feature='DISTANCE_TO_EDGE').outputs['Distance']
    col = g.mix(w, (0.12, 0.050, 0.020), (0.50, 0.44, 0.37))
    col = g.mix(d, col, (0.06, 0.030, 0.014))
    col = g.mix(nose, col, (0.010, 0.008, 0.008))
    col = g.mix(eye, col, (0.006, 0.004, 0.004))
    rough = g.mix(nose, 0.75, 0.42)
    normal = g.bump(g.math('MULTIPLY', grain, nose), 0.6, 0.0004)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=rough, Normal=normal)
    return g.finish(bsdf.outputs[0])


def fur_material():
    """Principled hair: fawn coat, darker along the back, white where the 'white' attribute says."""
    g = mats.Graph('DogFur')
    w = g.node('Attribute', attribute_name='white', attribute_type='GEOMETRY').outputs['Fac']
    d = g.node('Attribute', attribute_name='dark', attribute_type='GEOMETRY').outputs['Fac']
    bsdf = g.t.nodes.new('ShaderNodeBsdfHairPrincipled')
    bsdf.parametrization = 'MELANIN'
    mel = g.math('ADD', 0.55, g.math('MULTIPLY', d, 0.32))
    mel = g.math('MULTIPLY', mel, g.math('SUBTRACT', 1.0, g.math('MULTIPLY', w, 0.92)))
    g.link(mel, bsdf.inputs['Melanin'])
    bsdf.inputs['Melanin Redness'].default_value = 1.0
    bsdf.inputs['Tint'].default_value = (1.0, 0.84, 0.64, 1)
    bsdf.inputs['Roughness'].default_value = 0.38
    bsdf.inputs['Radial Roughness'].default_value = 0.55
    bsdf.inputs['Coat'].default_value = 0.25
    bsdf.inputs['Random Color'].default_value = 0.15
    bsdf.inputs['Random Roughness'].default_value = 0.2
    return g.finish(bsdf.outputs[0])


def flow(p, n):
    """Which way the coat lies at p: nose to tail on the body, down the legs, out along the ears and tail."""
    x, y, z = p
    for name, a, b, r in LIMBS:
        if name.startswith(('uarm', 'farm', 'hock')):
            a, b = np.array(a), np.array(b)
            d = b - a
            t = np.clip((p - a) @ d / (d @ d), 0, 1)
            if np.linalg.norm(p - (a + t * d)) < r + 0.012:
                v = d if name.startswith(('farm', 'hock')) else -d
                if name.startswith('uarm'):
                    v = np.array([0, 0, -1.0])
                return v / np.linalg.norm(v), 0.55
    pts = np.array(TAIL)
    dists = np.linalg.norm(pts - p, axis=1)
    k = int(np.argmin(dists))
    if dists[k] < 0.05 and x < -0.10:
        j = min(k + 1, len(pts) - 1)
        v = pts[j] - pts[max(j - 1, 0)]
        return v / np.linalg.norm(v), 1.5
    for side in (1, -1):
        c = np.array([0.318, 0.046 * side, 0.400])
        if np.linalg.norm(p - c) < 0.045:
            return np.array([-0.25, 0.15 * side, 1.0]) / 1.04, 0.75
    if x > 0.29 and z > 0.23:
        v = np.array([-1.0, 0.0, 0.0]) + np.array([0, np.sign(y) * 0.4, -0.3]) * (abs(y) > 0.02)
        return v / np.linalg.norm(v), 0.45 if x < 0.40 else 0.25
    side = np.clip(abs(y) / 0.10, 0, 1)
    v = np.array([-1.0, 0.0, 0.0]) + np.array([0.0, np.sign(y) * 0.3, -0.9]) * side
    return v / np.linalg.norm(v), 1.0


def make_fur(ob, col, per_area=2.5e5, base_length=0.016):
    me = ob.data
    rng = np.random.default_rng(55)
    noise = Noise(12)
    co = np.array([v.co for v in me.vertices])
    def read(name):
        arr = np.zeros(len(co), np.float32)
        me.attributes[name].data.foreach_get('value', arr)
        return arr
    white, dark, nose, eye = (read(name) for name in ('white', 'dark', 'nose', 'eye'))
    strands, w_attr, d_attr = [], [], []
    for poly in me.polygons:
        vs = [co[i] for i in poly.vertices]
        bare = max(max(nose[i], eye[i] * 1.2) for i in poly.vertices)
        if bare > 0.3:
            continue
        cnt = rng.poisson(poly.area * per_area)
        if not cnt:
            continue
        n = np.array(poly.normal)
        tris = [(vs[0], vs[1], vs[2])] + ([(vs[0], vs[2], vs[3])] if len(vs) == 4 else [])
        areas = np.array([np.linalg.norm(np.cross(b - a, c - a)) / 2 for a, b, c in tris])
        wv = float(np.mean([white[i] for i in poly.vertices]))
        dv = float(np.mean([dark[i] for i in poly.vertices]))
        ev = float(np.mean([eye[i] for i in poly.vertices]))
        for _ in range(cnt):
            a, b, c = tris[int(rng.choice(len(tris), p=areas / areas.sum()))]
            r1, r2 = math.sqrt(rng.random()), rng.random()
            p = a * (1 - r1) + b * (r1 * (1 - r2)) + c * (r1 * r2)
            f, lscale = flow(p, n)
            f = f - (f @ n) * n
            if np.linalg.norm(f) < 1e-4:
                f = np.cross(n, (0, 0, 1.0)) if abs(n[2]) < 0.9 else np.cross(n, (1.0, 0, 0))
            f /= np.linalg.norm(f)
            L = base_length * lscale * rng.uniform(0.75, 1.2) * (1 - 0.7 * ev)
            lift = rng.uniform(0.34, 0.62)
            wob = float(noise(p * 120)) * 0.30
            side = np.cross(n, f)
            # each hair leaves the skin at an angle and lies over along the coat
            pts = [p + n * (L * lift * math.sin(math.pi * 0.5 * s)) + f * (L * s * math.cos(lift)) + side * (wob * L * s * s)
                   for s in np.linspace(0, 1, 6)]
            strands.append(pts)
            w_attr.append(wv)
            d_attr.append(dv)
    strands = np.array(strands, np.float32)
    ok = ~np.isnan(strands).any(axis=(1, 2))
    strands = strands[ok]
    w_attr, d_attr = list(np.array(w_attr)[ok]), list(np.array(d_attr)[ok])
    fur = add_curves('DogFur', strands, 0.00007, 0.00002, col, fur_material())
    hc = fur.data
    for name, vals in (('white', w_attr), ('dark', d_attr)):
        at = hc.attributes.new(name, 'FLOAT', 'CURVE')
        at.data.foreach_set('value', np.array(vals, np.float32))
    print('dog fur curves', len(strands), flush=True)
    return fur


def make_eyes(col, m, me):
    """Dark, wet eyes set into the head: each pushed out until it shows a little under its lids."""
    g = mats.Graph('DogEye')
    bsdf = g.node('BsdfPrincipled', Base_Color=(0.030, 0.014, 0.006, 1), Roughness=0.25)
    bsdf.inputs['Coat Weight'].default_value = 1.0
    bsdf.inputs['Coat Roughness'].default_value = 0.02
    tree = BVHTree.FromPolygons([v.co for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
    eyes = []
    from dress import sphere
    for k, c in enumerate(EYES):
        c = Vector(c)
        out = Vector((0.55, 0.80 * (1 if c.y > 0 else -1), 0.20)).normalized()
        hit, normal, _, _ = tree.ray_cast(c + out * 0.08, -out, 0.2)
        centre = hit - normal * EYE_R * 0.38 if hit is not None else c
        v, f, _ = sphere(EYE_R, 16, 24)
        ob = obj_from_arrays(f'DogEye.{k}', v + np.array(centre), f, col)
        ob.data.materials.append(g.mat)
        ob.matrix_world = m
        eyes.append(ob)
    return eyes


def make(col, at=(0.70, -0.60, 0.0), yaw=192.0):
    body = build_metaball(col)
    bv = np.array([v.co for v in body.vertices])
    bf = [tuple(p.vertices) for p in body.polygons]
    from procedural import merged
    v, f = merged([(bv, bf)] + ear_parts())
    bpy.data.meshes.remove(body)
    me = bpy.data.meshes.new('Dog')
    me.from_pydata([tuple(map(float, q)) for q in v], [], [tuple(map(int, q)) for q in f])
    me.update()
    ob = bpy.data.objects.new('Dog', me)
    col.objects.link(ob)
    # relax the metaball's tessellation a little
    co = np.array([v.co for v in me.vertices])
    adj = edge_adjacency(me)
    for _ in range(2):
        nb = np.array([co[a].mean(0) if a else co[i] for i, a in enumerate(adj)])
        co += (nb - co) * 0.5
    co[:, 2] = np.maximum(co[:, 2], 0.0)      # it lies on the floor, it does not sink into it
    me.vertices.foreach_set('co', co.astype(np.float32).ravel())
    me.update()
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    white, dark, nose, eye = regions(co)
    for name, data in (('white', white), ('dark', dark), ('nose', nose), ('eye', eye)):
        me.attributes.new(name, 'FLOAT', 'POINT').data.foreach_set('value', data.astype(np.float32))
    me.materials.append(coat_material())
    print('dog mesh', len(me.vertices), 'verts', flush=True)
    fur = make_fur(ob, col)
    m = Matrix.Translation(Vector(at)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z')
    ob.matrix_world = m
    fur.matrix_world = m
    make_eyes(col, m, me)
    return ob, fur
