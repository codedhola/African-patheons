"""His okpu agụ: the knitted leopard cap of bravery.

Wikipedia (Igbo regalia and headdresses) describes it as a round, slanting cap of knitted wool,
striped black, white and red; the black and white recall the leopard's markings, and the red
was reserved for warriors who had taken heads in battle or brought home a leopard. The cap here
follows his skull, slants down over his left ear and rolls at the brim; how its bands run and
where the leopard's rosettes fall are this study's.
"""
import math

import numpy as np
from mathutils import Vector

import dress
import materials as mats
from common import obj_from_arrays
from procedural import Noise, add_curves

RINGS, SPOKES = 90, 300
SLANT = math.radians(7)          # the cap sits lower over his left ear
CIRCUMFERENCE = 0.60


def centre_of(body):
    info = eval(body['eyes'])
    e = (np.array(info['L']['centre']) + np.array(info['R']['centre'])) / 2
    return np.array([0.0, e[1] + 0.105, e[2] + 0.030])


def edge_elevation(az):
    """The cap's lower edge, as elevation from the head's centre: across the middle of the forehead in front,
    a centimetre or two over the tops of the ears, down over the back of the skull; lower on his left."""
    c = np.cos(az - np.radians(270))                   # 1 in front, -1 behind
    left = np.cos(az)                                  # +X is his left
    return np.radians(-3.0 + 18.0 * c - 3.0 * c * c) - SLANT * left


def knit_material():
    """Knitted wool in bands of red, black and white, the white spotted like a leopard; soft, matte and a little fuzzy."""
    g = mats.Graph('OkpuAgu')
    uv = g.node('TexCoord').outputs['UV']
    sep = g.node('SeparateXYZ', Vector=uv).outputs
    u, v = sep[0], sep[1]                              # metres round the head, metres up from the brim
    up = g.node('Attribute', attribute_name='up', attribute_type='GEOMETRY').outputs['Fac']
    red, black, white = (0.36, 0.012, 0.010), (0.010, 0.009, 0.009), (0.62, 0.59, 0.52)
    bands = g.ramp(up, [(0.00, red), (0.13, red), (0.135, black), (0.20, black), (0.205, white), (0.40, white), (0.405, black),
                        (0.46, black), (0.465, red), (0.56, red), (0.565, black), (0.62, black), (0.625, white), (0.84, white),
                        (0.845, black), (0.92, black), (0.925, red), (1.0, red)], 'CONSTANT')
    is_white = g.math('GREATER_THAN', g.node('SeparateColor', Color=bands).outputs[2], 0.3)
    # leopard rosettes: broken black rings with a dark spot or two inside, on the white bands
    cells = g.node('TexVoronoi', Vector=g.node('CombineXYZ', X=g.math('MULTIPLY', u, 38.0), Y=g.math('MULTIPLY', v, 38.0), Z=0.0).outputs[0],
                   Randomness=0.9).outputs['Distance']
    rough_edge = g.node('TexNoise', Vector=g.node('CombineXYZ', X=g.math('MULTIPLY', u, 160.0), Y=g.math('MULTIPLY', v, 160.0), Z=1.0).outputs[0], Scale=1.0).outputs['Fac']
    ring = g.math('LESS_THAN', g.math('ABSOLUTE', g.math('SUBTRACT', cells, g.math('ADD', 0.30, g.math('MULTIPLY', rough_edge, 0.10)))), 0.07)
    spot = g.math('LESS_THAN', cells, 0.10)
    leopard = g.math('MULTIPLY', is_white, g.math('MAXIMUM', g.math('MULTIPLY', ring, g.math('GREATER_THAN', rough_edge, 0.42)), spot))
    col = g.mix(leopard, bands, (0.012, 0.010, 0.010))
    # stocking stitch: columns of little Vs, about four to the centimetre each way
    col_u = g.math('MULTIPLY', u, 420.0)
    row_v = g.math('MULTIPLY', v, 470.0)
    vee = g.math('ABSOLUTE', g.math('SUBTRACT', g.math('FRACT', g.math('ADD', row_v, g.math('MULTIPLY', g.math('ABSOLUTE', g.math('SUBTRACT', g.math('FRACT', col_u), 0.5)), 1.4))), 0.5))
    column = g.math('ABSOLUTE', g.math('SINE', g.math('MULTIPLY', col_u, math.pi)))
    stitch = g.math('MULTIPLY', column, g.math('SUBTRACT', 1.0, vee))
    fuzz = g.node('TexNoise', Vector=g.node('CombineXYZ', X=g.math('MULTIPLY', u, 900.0), Y=g.math('MULTIPLY', v, 900.0), Z=2.0).outputs[0], Scale=1.0, Detail=3).outputs['Fac']
    col = g.mix(g.math('MULTIPLY', g.math('SUBTRACT', 1.0, stitch), 0.35), col, (0.004, 0.003, 0.003))
    normal = g.bump(g.math('ADD', stitch, g.math('MULTIPLY', fuzz, 0.3)), 0.8, 0.0012)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.92, Normal=normal)
    bsdf.inputs['Sheen Weight'].default_value = 0.45
    bsdf.inputs['Sheen Roughness'].default_value = 0.4
    bsdf.inputs['Sheen Tint'].default_value = (1.0, 0.96, 0.92, 1)
    return g.finish(bsdf.outputs[0])


def make_cap(body, rig, col, hair_lift=0.0035):
    M = np.array(dress.head_matrix(rig))
    centre = centre_of(body)
    tree = dress.head_tree(body)
    az = np.linspace(0, 2 * np.pi, SPOKES, endpoint=False)
    t = np.linspace(0, 1, RINGS) ** 0.9
    AZ, T = np.meshgrid(az, t, indexing='ij')
    EL = edge_elevation(AZ) * (1 - T) + np.radians(89.0) * T
    d = np.stack([np.cos(EL) * np.cos(AZ), np.cos(EL) * np.sin(AZ), np.sin(EL)], -1)
    radius = np.zeros(AZ.shape)
    for idx in np.ndindex(AZ.shape):
        ray = Vector(d[idx])
        hit = tree.ray_cast(Vector(centre) + ray * 0.3, -ray, 0.3)
        radius[idx] = 0.3 - hit[3] if hit[0] is not None else np.nan
    radius = np.where(np.isnan(radius), np.nanmedian(radius, axis=1, keepdims=True), radius)
    for _ in range(12):
        radius = (radius + np.roll(radius, 1, 0) + np.roll(radius, -1, 0)) / 3
        radius[:, 1:-1] = (radius[:, 1:-1] + radius[:, :-2] + radius[:, 2:]) / 3
    n = Noise(61)
    # knit stands a little off the hair; the crown slouches toward the low side, and the brim is rolled
    ease = hair_lift + 0.0040 + 0.010 * dress.smoothstep(T, 0.2, 1.0) * (0.6 + 0.4 * np.clip(np.cos(AZ), 0, 1))
    roll = 0.0052 * np.exp(-((T - 0.035) / 0.03) ** 2)
    rumple = 0.0010 * n.fbm(d * 6.0, 3)
    r = radius + ease + roll + rumple
    pts = centre + d * r[..., None]
    rows = RINGS
    idx = lambda i, j: (i % SPOKES) * rows + j
    faces = [(idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)) for i in range(SPOKES) for j in range(rows - 1)]
    ob = obj_from_arrays('OkpuAgu', pts.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3], faces, col)
    # UVs in metres: round the head, and up the cap from the brim
    arc = np.concatenate([np.zeros((SPOKES, 1)), np.cumsum(np.linalg.norm(np.diff(pts, axis=1), axis=2), axis=1)], 1)
    me = ob.data
    layer = me.uv_layers.new(name='UVMap')
    loops = np.zeros(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', loops)
    U = (AZ / (2 * np.pi) * CIRCUMFERENCE).ravel()[loops]
    V = arc.ravel()[loops]
    start = np.zeros(len(me.polygons), np.int32)
    me.polygons.foreach_get('loop_start', start)
    for s in start:
        q = U[s:s + 4]
        if q.max() - q.min() > CIRCUMFERENCE / 2:
            U[s:s + 4] = np.where(q < CIRCUMFERENCE / 2, q + CIRCUMFERENCE, q)
    layer.data.foreach_set('uv', np.stack([U, V], 1).astype(np.float32).ravel())
    me.attributes.new('up', 'FLOAT', 'POINT').data.foreach_set('value', T.ravel().astype(np.float32))
    me.materials.append(knit_material())
    sol = ob.modifiers.new('Thickness', 'SOLIDIFY')
    sol.thickness = 0.0035
    sol.offset = -1
    sub = ob.modifiers.new('Smooth', 'SUBSURF')
    sub.levels = sub.render_levels = 1
    return ob, centre


def make_edge_hair(body, rig, col, material, centre, per_face=34):
    """Close-cut coiled hair below the cap: at the temples, round the ears and down to the nape."""
    M = dress.head_matrix(rig)
    me = body.data
    rng = np.random.default_rng(23)
    strands = []
    info = eval(body['eyes'])
    eye_z = (info['L']['centre'][2] + info['R']['centre'][2]) / 2
    eye_y = (info['L']['centre'][1] + info['R']['centre'][1]) / 2
    for f in dress.layer_faces('scalp_solid'):
        poly = me.polygons[f]
        vs = [me.vertices[i].co for i in poly.vertices]
        nrm = poly.normal
        for _ in range(per_face):
            w = rng.dirichlet((1, 1, 1, 1)[:len(vs)])
            p = sum((v * a for v, a in zip(vs, w)), Vector((0, 0, 0)))
            d = p - Vector(centre)
            az = math.atan2(d.y, d.x) % (2 * math.pi)
            el = math.asin(d.z / d.length)
            if el > float(edge_elevation(az)) + math.radians(3):
                continue
            # the hairline, in metres from the eye centres: nothing in front of the temples, whose line slopes back
            # as it rises, and in front of the ears nothing below the foot of the sideburn
            y_rel, z_rel = p.y - eye_y, p.z - eye_z
            if y_rel < 0.045 - max(z_rel - 0.030, 0.0) or (y_rel < 0.10 and z_rel < -0.026):
                continue
            L = rng.uniform(0.0022, 0.0040)
            ph, turns = rng.uniform(0, 6.28), rng.uniform(1.2, 2.0)
            t1 = nrm.orthogonal().normalized()
            t2 = nrm.cross(t1)
            pts = [M @ (p + nrm * (L * s) + (t1 * math.cos(ph + s * turns * 6.28) + t2 * math.sin(ph + s * turns * 6.28)) * (0.0007 * math.sin(math.pi * min(s * 1.2, 1))))
                   for s in np.linspace(0, 1, 7)]
            strands.append(pts)
    ob = add_curves('EdgeHair', np.array(strands, np.float32), 0.00007, 0.00003, col, material)
    print('edge hair curves', len(strands), flush=True)
    return ob
