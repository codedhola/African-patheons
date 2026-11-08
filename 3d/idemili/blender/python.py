"""Éké Idemili: the royal python, her messenger, rising beside her from the water.

The Idemili North local government calls the river a goddess who sent the royal python as her
messenger, and in Idemili no one may harm one: a python killed by accident is wrapped in white
cloth and given a funeral (Okonkwo 2021). The royal python is a stocky snake with a small head
and smooth scales, up to about 1.8 m long, dark brown with light brown blotches on its back and
sides, its belly white or cream with black markings (Wikipedia: Ball python). Its pose follows
her gallery figure: the forepart raised out of the water beside her right hand, the rest lying
in the shallows round in front of her feet. The layout of the blotches is this study's.

Local frame: hers. She faces -Y; her right is -X. The coils rest on the bed under the water.
"""
import math

import bpy
import numpy as np
from mathutils import Vector

import dress
import materials as mats
from common import obj_from_arrays
from procedural import Noise

R_BODY = 0.026
# from just behind the head to the tip of the tail: its head turned toward her below her right hand, the
# neck curving up out of the water in an S, then round in front of her feet to beside her left heel
PATH = np.array([
    (-0.250, -0.150, 0.560), (-0.290, -0.150, 0.562), (-0.325, -0.148, 0.535), (-0.345, -0.150, 0.470),
    (-0.346, -0.162, 0.392), (-0.360, -0.185, 0.300), (-0.386, -0.210, 0.200), (-0.396, -0.232, 0.110),
    (-0.372, -0.256, 0.050), (-0.300, -0.292, 0.030), (-0.180, -0.322, 0.027), (0.010, -0.352, 0.027),
    (0.186, -0.316, 0.026), (0.312, -0.196, 0.025), (0.348, -0.030, 0.022), (0.300, 0.120, 0.016),
])


def catmull_rom(points, n):
    p = np.vstack([points[:1] * 2 - points[1:2], points, points[-1:] * 2 - points[-2:-1]])
    out = []
    for i in range(1, len(p) - 2):
        for t in np.linspace(0, 1, n, endpoint=False):
            a, b, c, d = p[i - 1], p[i], p[i + 1], p[i + 2]
            out.append(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t ** 3))
    out.append(points[-1])
    return np.array(out)


def resample(path, step):
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    s = np.arange(0, cum[-1], step)
    return np.stack([np.interp(s, cum, path[:, i]) for i in range(3)], 1), cum[-1]


def radius_at(t):
    """Girth from neck (0) to tail tip (1): a slim neck, a stocky body, a short tapering tail."""
    neck = 0.42 + 0.58 * np.clip(t / 0.10, 0, 1) ** 0.7
    tail = np.clip((1 - t) / 0.16, 0, 1) ** 0.85
    return R_BODY * np.minimum(neck, 1.0) * (0.12 + 0.88 * tail)


def body_frames(path):
    """Tangents, and a dorsal direction for each point: up where the body lies along the bed, and turned out,
    away from her, where it rears with its head toward her, so its patterned flank faces the front."""
    tan = np.gradient(path, axis=0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    upright = np.abs(tan[:, 2]) ** 2
    want = np.array([0, 0, 1.0])[None] * (1 - upright[:, None]) + np.array([-1.0, 0.15, 0.3])[None] * upright[:, None]
    dorsal = want - (want * tan).sum(1, keepdims=True) * tan
    dorsal /= np.linalg.norm(dorsal, axis=1, keepdims=True)
    for _ in range(30):
        dorsal[1:-1] = (dorsal[:-2] + dorsal[1:-1] * 2 + dorsal[2:]) / 4
        dorsal -= (dorsal * tan).sum(1, keepdims=True) * tan
        dorsal /= np.linalg.norm(dorsal, axis=1, keepdims=True)
    side = np.cross(tan, dorsal)
    return tan, dorsal, side


def python_material():
    """Smooth scales, dark brown with light brown blotches along the back and sides, the belly cream marked with black."""
    g = mats.Graph('RoyalPython')
    obj = g.node('TexCoord').outputs['Object']
    along = g.node('Attribute', attribute_name='along', attribute_type='GEOMETRY').outputs['Fac']     # metres from the neck
    round_ = g.node('Attribute', attribute_name='round', attribute_type='GEOMETRY').outputs['Fac']    # 0 on the spine, 1 on the belly
    t = g.node('Attribute', attribute_name='taper', attribute_type='GEOMETRY').outputs['Fac']
    # blotches: big rounded patches of light brown down each flank, often with a dark heart, and saddles over the spine
    flank = g.node('TexVoronoi', Vector=g.node('CombineXYZ', X=g.math('MULTIPLY', along, 15.0), Y=g.math('MULTIPLY', round_, 3.2), Z=0.0).outputs[0],
                   Randomness=0.85).outputs['Distance']
    saddle = g.node('TexVoronoi', Vector=g.node('CombineXYZ', X=g.math('MULTIPLY', along, 8.0), Y=0.0, Z=1.0).outputs[0], Randomness=0.7).outputs['Distance']
    wobble = g.node('TexNoise', Vector=g.node('CombineXYZ', X=g.math('MULTIPLY', along, 60.0), Y=g.math('MULTIPLY', round_, 12.0), Z=2.0).outputs[0],
                    Scale=1.0, Detail=3).outputs['Fac']
    edge = g.math('ADD', 0.36, g.math('MULTIPLY', wobble, 0.16))
    on_flank = g.math('MULTIPLY', g.math('GREATER_THAN', round_, 0.18), g.math('LESS_THAN', round_, 0.62))
    blotch = g.math('MULTIPLY', g.math('LESS_THAN', flank, edge), on_flank)
    heart = g.math('MULTIPLY', blotch, g.math('LESS_THAN', flank, 0.11))
    on_spine = g.math('LESS_THAN', round_, g.math('ADD', 0.14, g.math('MULTIPLY', wobble, 0.06)))
    blotch = g.math('MAXIMUM', blotch, g.math('MULTIPLY', on_spine, g.math('LESS_THAN', saddle, 0.22)))
    dark = (0.030, 0.019, 0.012)
    tan_c = g.ramp(wobble, [(0.3, (0.24, 0.15, 0.068)), (0.7, (0.34, 0.22, 0.10))])
    col = g.mix(g.math('SUBTRACT', blotch, g.math('MULTIPLY', heart, 0.85)), dark, tan_c)
    # the belly: cream, with black flecks
    belly = g.math('MULTIPLY', g.math('SUBTRACT', round_, 0.70), 8.0, clamp=True)
    fleck = g.node('TexVoronoi', Vector=g.node('CombineXYZ', X=g.math('MULTIPLY', along, 70.0), Y=g.math('MULTIPLY', round_, 9.0), Z=3.0).outputs[0]).outputs['Distance']
    cream = g.mix(g.math('LESS_THAN', fleck, 0.16), (0.55, 0.50, 0.38), (0.035, 0.028, 0.022))
    col = g.mix(belly, col, cream)
    # the scales: small and smooth, each a slight dome with a dark seam round it, glossy
    scales = g.node('TexVoronoi', Vector=obj, Scale=230, feature='DISTANCE_TO_EDGE').outputs['Distance']
    seam = g.math('LESS_THAN', scales, 0.06)
    col = g.mix(g.math('MULTIPLY', seam, 0.45), col, (0.012, 0.009, 0.007))
    height = g.math('MINIMUM', g.math('MULTIPLY', scales, 7.0), 1.0)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=g.math('ADD', 0.40, g.math('MULTIPLY', seam, 0.25)), Normal=g.bump(height, 0.35, 0.0006))
    bsdf.inputs['Coat Weight'].default_value = 0.12
    bsdf.inputs['Coat Roughness'].default_value = 0.25
    return g.finish(bsdf.outputs[0])


def make_body(col, material):
    path, length = resample(catmull_rom(PATH, 24), 0.004)
    tan, dorsal, side = body_frames(path)
    n = len(path)
    t = np.linspace(0, 1, n)
    r = radius_at(t)
    sides = 32
    a = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    # round in section, a little flattened on the belly as a resting snake is
    ring = np.stack([np.cos(a), np.sin(a)], 1)
    round_ring = np.arccos(np.clip(ring[:, 1], -1, 1)) / np.pi               # 0 on the spine, 1 on the belly
    ring[:, 1] = np.where(ring[:, 1] < 0, ring[:, 1] * 0.78, ring[:, 1])
    verts = path[:, None] + (dorsal[:, None] * ring[None, :, 1:2] + side[:, None] * ring[None, :, 0:1]) * r[:, None, None]
    verts = verts.reshape(-1, 3)
    faces = [(i * sides + j, (i + 1) * sides + j, (i + 1) * sides + (j + 1) % sides, i * sides + (j + 1) % sides) for i in range(n - 1) for j in range(sides)]
    faces.append(tuple(range(n * sides - 1, (n - 1) * sides - 1, -1)))     # the tail's tip closed
    ob = obj_from_arrays('PythonBody', verts, faces, col)
    me = ob.data
    along = np.repeat(np.linspace(0, length, n), sides)
    round_ = np.tile(round_ring, n)
    for name, val in (('along', along), ('round', round_), ('taper', np.repeat(t, sides))):
        me.attributes.new(name, 'FLOAT', 'POINT').data.foreach_set('value', val.astype(np.float32))
    me.materials.append(material)
    sub = ob.modifiers.new('Smooth', 'SUBSURF')
    sub.levels = sub.render_levels = 1
    print('python', round(length, 2), 'm long', flush=True)
    return ob, path[0], -tan[0], dorsal[0], r[0]


def make_head(col, material, at, forward, up, neck_r):
    """A small head, broader than the neck behind and narrowing to a rounded snout, held level."""
    f = Vector(forward)
    f.z = 0.0
    f.normalize()
    u = Vector((0, 0, 1.0))
    s = f.cross(u)
    rows, cols = 26, 28
    L = 0.052
    verts = []
    for i in range(rows):
        q = i / (rows - 1)                                      # 0 at the back, 1 at the snout
        w = (0.0165 - 0.0070 * q ** 1.4) * math.sqrt(max(1 - ((q - 0.96) / 0.04) ** 2, 0) if q > 0.96 else 1.0)
        w = max(w, 0.0008)
        h = (0.0115 - 0.0045 * q) * (1.0 if q < 0.96 else max(1 - ((q - 0.96) / 0.04) ** 2, 0.05) ** 0.5)
        back = neck_r / 0.0165
        w = w if q > 0.12 else w * (back + (1 - back) * q / 0.12)
        for j in range(cols):
            a = 2 * math.pi * j / cols
            x, y = math.cos(a) * w, math.sin(a) * h
            if y < 0:
                y *= 0.62                                         # the jaw flatter than the crown
            verts.append(Vector(at) + f * (q * L - 0.004) + s * x + u * (y + 0.001))
    faces = [(i * cols + j, (i + 1) * cols + j, (i + 1) * cols + (j + 1) % cols, i * cols + (j + 1) % cols) for i in range(rows - 1) for j in range(cols)]
    faces.append(tuple(range(rows * cols - 1, (rows - 1) * cols - 1, -1)))
    head = obj_from_arrays('PythonHead', [tuple(v) for v in verts], faces, col)
    me = head.data
    q_attr = np.repeat(np.linspace(0, 1, rows), cols)
    me.attributes.new('along', 'FLOAT', 'POINT').data.foreach_set('value', (-q_attr * L).astype(np.float32))
    ang = np.tile(np.linspace(0, 2 * np.pi, cols, endpoint=False), rows)
    me.attributes.new('round', 'FLOAT', 'POINT').data.foreach_set('value', (np.arccos(np.clip(np.sin(ang), -1, 1)) / np.pi).astype(np.float32))
    me.attributes.new('taper', 'FLOAT', 'POINT').data.foreach_set('value', np.zeros(rows * cols, np.float32))
    me.materials.append(material)
    sub = head.modifiers.new('Smooth', 'SUBSURF')
    sub.levels = sub.render_levels = 1
    # the eyes: dark and glossy, set high on the sides a third of the way back from the snout
    g = mats.Graph('PythonEye')
    bsdf = g.node('BsdfPrincipled', Base_Color=(0.020, 0.014, 0.010, 1), Roughness=0.08)
    bsdf.inputs['Coat Weight'].default_value = 1.0
    eyes = []
    for k in (1, -1):
        v, fc, _ = dress.sphere(0.0031, 10, 14)
        c = Vector(at) + f * (L * 0.62) + s * (k * 0.0118) + u * 0.0058
        e = obj_from_arrays(f'PythonEye.{k}', np.array(v) + np.array(c), fc, col)
        e.data.materials.append(g.mat)
        eyes.append(e)
    return head, eyes


def make(col):
    material = python_material()
    body, neck, forward, dorsal, neck_r = make_body(col, material)
    head, eyes = make_head(col, material, neck, forward, dorsal, neck_r)
    return body, head, eyes


def rise_point():
    """Where the python comes up out of the water, for the rings it makes."""
    return float(PATH[8, 0]), float(PATH[8, 1])
