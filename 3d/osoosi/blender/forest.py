"""The high forest: a clearing among tall trunks in blue-green mist, under a giant iroko.

This follows stage 06 in this repo: a clearing in high forest, tall trunks fading into the mist,
a giant iroko with buttress roots and offerings at its foot (a clay pot, a calabash, kola nuts and
cowries), lianas, ferns, a mossy fallen log, and pale light coming down from above. The iroko is
held to house a spirit (Wikipedia: Iroko). No real place is copied. The method is Ọ̀ṣun's grove,
without the river: trees, canopy and haze are built the same way.
"""
import math

import bpy
import numpy as np
from mathutils import Vector

import materials as mats
import regalia
from common import obj_from_arrays
from dress import smoothstep
from procedural import Noise, sweep

SUN = Vector((0.48, 0.15, 0.86)).normalized()       # toward the sun: high on his left, the side he aims to, a little behind him
IROKO = (-1.25, 7.6)
IROKO_R = 1.05
NEAR = (-4.8, 4.8, -5.2, 5.6)                      # the patch of fine ground round him
CLEAR = (0.0, 0.0, 2.4)                            # nothing but litter within this of him


def height_field(x, y):
    """The forest floor: a gentle swell and fall, level where he stands, rising among the iroko's roots."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n1 = Noise(7)
    p = np.stack([x, y, np.zeros_like(x)], -1)
    h = 0.30 * n1.fbm(p * 0.06, 3) + 0.05 * n1.fbm(p * 0.6, 3)
    h += 0.10 * np.exp(-((x - IROKO[0]) ** 2 + (y - IROKO[1]) ** 2) / 9.0)
    keep = smoothstep(np.hypot(x, y), 0.7, 2.6)
    return h * keep


def fast_mesh(name, verts, quads, col, attrs=None, material=None):
    """Mesh from big arrays of quads, without going through Python lists."""
    verts = np.asarray(verts, np.float32)
    quads = np.asarray(quads, np.int32)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts))
    me.vertices.foreach_set('co', verts.ravel())
    me.loops.add(len(quads) * 4)
    me.polygons.add(len(quads))
    me.loops.foreach_set('vertex_index', quads.ravel())
    me.polygons.foreach_set('loop_start', np.arange(len(quads)) * 4)
    me.update(calc_edges=True)
    me.polygons.foreach_set('use_smooth', np.ones(len(quads), bool))
    for key, values in (attrs or {}).items():
        a = me.attributes.new(key, 'FLOAT', 'POINT')
        a.data.foreach_set('value', np.asarray(values, np.float32).ravel())
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    if material:
        me.materials.append(material)
    return ob


def grid_quads(nx, ny):
    i, j = np.mgrid[0:nx - 1, 0:ny - 1]
    a = i * ny + j
    return np.stack([a, a + ny, a + ny + 1, a + 1], -1).reshape(-1, 4)


def joined(parts):
    base = 0
    verts, quads = [], []
    for vv, qq in parts:
        verts.append(np.asarray(vv))
        quads.append(np.asarray(qq) + base)
        base += len(vv)
    return np.concatenate(verts), np.concatenate(quads)


# ----- materials ------------------------------------------------------------

def floor_material():
    """Dark humus under a mat of old leaves, with moss where it stays damp."""
    g = mats.Graph('ForestFloor')
    obj = g.node('TexCoord').outputs['Object']
    big = g.node('TexNoise', Vector=obj, Scale=0.9, Detail=6, Roughness=0.6).outputs['Fac']
    mid = g.node('TexNoise', Vector=obj, Scale=9, Detail=6, Roughness=0.62).outputs['Fac']
    fine = g.node('TexNoise', Vector=obj, Scale=160, Detail=6, Roughness=0.7).outputs['Fac']
    leaf_v = g.node('TexNoise', Vector=obj, Scale=22, Detail=3, Roughness=0.5).outputs['Fac']        # old leaves, mottled, under the fresh fall
    soil = g.ramp(fine, [(0.3, (0.016, 0.011, 0.007)), (0.7, (0.040, 0.027, 0.016))])
    litter = g.ramp(leaf_v, [(0.0, (0.050, 0.026, 0.012)), (0.5, (0.11, 0.065, 0.030)), (1.0, (0.17, 0.11, 0.050))])
    cover = g.node('SeparateColor', Color=g.ramp(mid, [(0.35, (0, 0, 0)), (0.55, (1, 1, 1))])).outputs[0]
    col = g.mix(cover, soil, litter)
    moss = g.ramp(fine, [(0.3, (0.020, 0.040, 0.010)), (0.7, (0.050, 0.085, 0.018))])
    damp = g.node('SeparateColor', Color=g.ramp(big, [(0.62, (0, 0, 0)), (0.74, (1, 1, 1))])).outputs[0]
    col = g.mix(damp, col, moss)
    h = g.math('ADD', g.math('MULTIPLY', mid, 0.6), g.math('MULTIPLY', fine, 0.5))
    normal = g.bump(g.math('ADD', h, g.math('MULTIPLY', leaf_v, 0.3)), 1.0, 0.006)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.84, Normal=normal)
    bsdf.inputs['Specular IOR Level'].default_value = 0.32
    return g.finish(bsdf.outputs[0])


def bark_material(name='Bark', base=((0.060, 0.055, 0.046), (0.17, 0.155, 0.13), (0.29, 0.27, 0.23)), moss_level=0.46):
    """Grey-brown bark in long fissures, with moss and lichen in patches."""
    g = mats.Graph(name)
    obj = g.node('TexCoord').outputs['Object']
    tall = g.node('Mapping', Vector=obj, Scale=(1, 1, 0.18)).outputs[0]
    n = g.node('TexNoise', Vector=tall, Scale=7, Detail=7, Roughness=0.62).outputs['Fac']
    fine = g.node('TexNoise', Vector=tall, Scale=44, Detail=5).outputs['Fac']
    col = g.ramp(n, [(0.3, base[0]), (0.52, base[1]), (0.72, base[2])])
    moss_mask = g.ramp(g.node('TexNoise', Vector=obj, Scale=1.1, Detail=6, Roughness=0.62).outputs['Fac'], [(moss_level, (0, 0, 0)), (moss_level + 0.14, (1, 1, 1))])
    moss = g.ramp(fine, [(0.3, (0.030, 0.055, 0.014)), (0.7, (0.090, 0.135, 0.032))])
    col = g.mix(g.node('SeparateColor', Color=moss_mask).outputs[0], col, moss)
    lichen = g.ramp(g.node('TexVoronoi', Vector=obj, Scale=9, Randomness=1.0).outputs['Distance'], [(0.12, (1, 1, 1)), (0.16, (0, 0, 0))])
    col = g.mix(g.math('MULTIPLY', g.node('SeparateColor', Color=lichen).outputs[0], 0.5), col, (0.42, 0.45, 0.38))
    normal = g.bump(g.math('ADD', n, g.math('MULTIPLY', fine, 0.4)), 1.0, 0.018)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.82, Normal=normal)
    return g.finish(bsdf.outputs[0])


def iroko_bark():
    """The iroko's bark: grey-brown ridges split by long wavy fissures running up the trunk, moss low on the buttresses."""
    g = mats.Graph('IrokoBark')
    obj = g.node('TexCoord').outputs['Object']
    xyz = g.node('SeparateXYZ', Vector=obj).outputs
    # round the trunk by arc length, up it by height: the fissures are drawn on that unrolled surface
    around = g.math('MULTIPLY', g.math('ARCTAN2', g.math('SUBTRACT', xyz[1], IROKO[1]), g.math('SUBTRACT', xyz[0], IROKO[0])), IROKO_R)
    flat = g.node('CombineXYZ', X=around, Y=g.math('MULTIPLY', xyz[2], 0.16), Z=0.0).outputs[0]
    ridges = g.node('TexWave', Vector=flat, Scale=4.5, Distortion=9.0, Detail=6, wave_type='BANDS', bands_direction='X').outputs['Fac']
    fade = g.node('TexNoise', Vector=g.node('Mapping', Vector=obj, Scale=(1.0, 1.0, 0.3)).outputs[0], Scale=2.5, Detail=3).outputs['Fac']
    n = g.node('TexNoise', Vector=obj, Scale=6, Detail=7, Roughness=0.62).outputs['Fac']
    fine = g.node('TexNoise', Vector=obj, Scale=70, Detail=5).outputs['Fac']
    # fissures thin, wandering, and fading out here and there, as they do in real bark
    fissure = g.math('MULTIPLY', g.node('SeparateColor', Color=g.ramp(ridges, [(0.04, (1, 1, 1)), (0.14, (0, 0, 0))])).outputs[0],
                     g.node('SeparateColor', Color=g.ramp(fade, [(0.32, (0, 0, 0)), (0.55, (1, 1, 1))])).outputs[0])
    col = g.ramp(n, [(0.3, (0.050, 0.044, 0.037)), (0.55, (0.105, 0.092, 0.076)), (0.78, (0.170, 0.152, 0.126))])
    col = g.mix(fissure, col, (0.034, 0.029, 0.024))
    low = g.math('SUBTRACT', 1.0, g.math('MULTIPLY', xyz[2], 0.4), clamp=True)          # 1 at the ground, gone two and a half metres up
    patch = g.node('TexNoise', Vector=obj, Scale=1.3, Detail=6, Roughness=0.62).outputs['Fac']
    moss_mask = g.node('SeparateColor', Color=g.ramp(g.math('ADD', patch, g.math('MULTIPLY', low, 0.16)), [(0.64, (0, 0, 0)), (0.78, (1, 1, 1))])).outputs[0]
    moss = g.ramp(fine, [(0.3, (0.016, 0.034, 0.009)), (0.7, (0.050, 0.085, 0.020))])
    col = g.mix(g.math('MULTIPLY', moss_mask, g.math('SUBTRACT', 1.0, fissure)), col, moss)
    h = g.math('ADD', g.math('MULTIPLY', g.math('SUBTRACT', 1.0, fissure), 0.8), g.math('MULTIPLY', n, 0.4))
    normal = g.bump(g.math('ADD', h, g.math('MULTIPLY', fine, 0.15)), 1.0, 0.03)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.86, Normal=normal)
    return g.finish(bsdf.outputs[0])


def log_material():
    """The fallen log: old bark going soft, thick moss on its upper side."""
    g = mats.Graph('MossyLog')
    obj = g.node('TexCoord').outputs['Object']
    up = g.node('SeparateXYZ', Vector=g.node('NewGeometry').outputs['Normal']).outputs[2]
    patch = g.node('TexNoise', Vector=obj, Scale=3.0, Detail=6, Roughness=0.6).outputs['Fac']
    on_top = g.node('SeparateColor', Color=g.ramp(g.math('ADD', up, g.math('MULTIPLY', patch, 0.6)), [(0.58, (0, 0, 0)), (0.74, (1, 1, 1))])).outputs[0]
    fine = g.node('TexNoise', Vector=obj, Scale=90, Detail=6, Roughness=0.7).outputs['Fac']
    tufts = g.node('TexVoronoi', Vector=obj, Scale=140, Randomness=1.0).outputs['Distance']
    bark = g.ramp(g.node('TexNoise', Vector=g.node('Mapping', Vector=obj, Scale=(0.25, 1, 1)).outputs[0], Scale=9, Detail=6).outputs['Fac'],
                  [(0.3, (0.030, 0.022, 0.015)), (0.7, (0.10, 0.075, 0.050))])
    moss = g.ramp(fine, [(0.3, (0.012, 0.028, 0.006)), (0.7, (0.040, 0.075, 0.012))])
    col = g.mix(on_top, bark, moss)
    h = g.math('ADD', g.math('MULTIPLY', fine, 0.5), g.math('MULTIPLY', g.math('MULTIPLY', tufts, -1.0), on_top))
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.85, Normal=g.bump(h, 1.0, 0.006))
    bsdf.inputs['Sheen Weight'].default_value = 0.6
    return g.finish(bsdf.outputs[0])


def foliage_material(name='Foliage', low=(0.012, 0.045, 0.010), mid=(0.032, 0.105, 0.016), high=(0.090, 0.170, 0.026), rough=0.38):
    """Waxy leaves with their colour set leaf by leaf, glowing where the light comes through."""
    g = mats.Graph(name)
    pick = g.node('Attribute', attribute_name='tint', attribute_type='GEOMETRY').outputs['Fac']
    col = g.ramp(pick, [(0.0, low), (0.55, mid), (1.0, high)])
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=rough)
    bsdf.inputs['Specular IOR Level'].default_value = 0.55
    glow = g.mix(0.5, col, (0.75, 0.95, 0.18), 'MULTIPLY')
    trans = g.node('BsdfTranslucent', Color=glow)
    both = g.node('MixShader', Fac=0.42)
    g.link(bsdf.outputs[0], both.inputs[1])
    g.link(trans.outputs[0], both.inputs[2])
    return g.finish(both.outputs[0])


def clay_material():
    """Unglazed earthenware, fired red-brown and blackened in patches, the rim worn pale."""
    g = mats.Graph('Clay')
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=30, Detail=6, Roughness=0.6).outputs['Fac']
    smoke = g.node('TexNoise', Vector=obj, Scale=6, Detail=4).outputs['Fac']
    col = g.ramp(n, [(0.3, (0.16, 0.070, 0.035)), (0.7, (0.27, 0.13, 0.065))])
    col = g.mix(g.node('SeparateColor', Color=g.ramp(smoke, [(0.55, (0, 0, 0)), (0.72, (1, 1, 1))])).outputs[0], col, (0.035, 0.025, 0.020))
    fine = g.node('TexNoise', Vector=obj, Scale=400, Detail=4).outputs['Fac']
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.78, Normal=g.bump(g.math('ADD', n, g.math('MULTIPLY', fine, 0.5)), 0.5, 0.0008))
    return g.finish(bsdf.outputs[0])


def gourd_material():
    """A dried calabash: yellow-brown, glossy with handling, faintly mottled."""
    g = mats.Graph('Calabash')
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=18, Detail=5).outputs['Fac']
    col = g.ramp(n, [(0.3, (0.24, 0.13, 0.045)), (0.7, (0.42, 0.25, 0.085))])
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.34, Normal=g.bump(n, 0.15, 0.0005))
    bsdf.inputs['Coat Weight'].default_value = 0.3
    return g.finish(bsdf.outputs[0])


def kola_material():
    """Fresh kola nuts: pink to red-brown, waxy."""
    g = mats.Graph('Kola')
    seed = g.node('Attribute', attribute_name='bead', attribute_type='GEOMETRY').outputs['Fac']
    col = g.ramp(seed, [(0.0, (0.30, 0.060, 0.050)), (0.5, (0.46, 0.13, 0.090)), (1.0, (0.56, 0.30, 0.20))])
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=300, Detail=3).outputs['Fac']
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.40, Normal=g.bump(n, 0.1, 0.0002),
                  Subsurface_Weight=0.3, Subsurface_Scale=0.003)
    return g.finish(bsdf.outputs[0])


# ----- ground ---------------------------------------------------------------

def make_ground(col):
    floor = floor_material()
    x0, x1, y0, y1 = NEAR
    nx, ny = int((x1 - x0) / 0.02), int((y1 - y0) / 0.02)
    X, Y = np.meshgrid(np.linspace(x0, x1, nx), np.linspace(y0, y1, ny), indexing='ij')
    n2 = Noise(44)
    p = np.stack([X, Y, np.zeros_like(X)], -1)
    edge = np.minimum.reduce([X - x0, x1 - X, Y - y0, y1 - Y])
    detail = (0.008 * n2.fbm(p * 4.5, 4, 0.55) + 0.0018 * n2.fbm(p * 30, 3, 0.55)) * np.clip(edge / 0.4, 0, 1)
    Z = height_field(X, Y) + detail
    near = fast_mesh('Floor.near', np.stack([X, Y, Z], -1).reshape(-1, 3), grid_quads(nx, ny), col, material=floor)
    n = 320
    u = np.sign(np.linspace(-1, 1, n)) * np.abs(np.linspace(-1, 1, n)) ** 2.2
    X, Y = np.meshgrid(u * 150, u * 150 + 30, indexing='ij')
    Z = height_field(X, Y)
    inside = (X > x0 + 0.12) & (X < x1 - 0.12) & (Y > y0 + 0.12) & (Y < y1 - 0.12)
    Z = np.where(inside, Z - 0.05, Z)
    far = fast_mesh('Floor.far', np.stack([X, Y, Z], -1).reshape(-1, 3), grid_quads(n, n), col, material=floor)
    return near, far


CARD = np.array([(0.0, 0.0, 0.0), (0.45, 0.30, 0.075), (0.45, 0.0, 0.0), (0.45, -0.30, 0.075), (1.0, 0.0, 0.0)])     # a leaf, folded at its rib


def card_frames(n, rng, centres, spread, size, droop=0.5, tint_range=(0.0, 1.0)):
    """Where n leaves lie, scattered round the centres (k x 3): base, the leaf's own three axes, its length, its tint."""
    pick = rng.integers(0, len(centres), n)
    u = rng.normal(0, 1, (n, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    r = rng.random(n)[:, None] ** (1 / 3)
    spreads = np.broadcast_to(np.asarray(spread, float), (len(centres),))[pick][:, None]
    base = centres[pick] + u * r * spreads * np.array([1, 1, 0.62])
    heading = rng.uniform(0, 6.283, n)
    drop = rng.uniform(droop * 0.4, droop * 1.6, n)
    along = np.stack([np.cos(heading) * np.cos(drop), np.sin(heading) * np.cos(drop), -np.sin(drop)], 1)
    side = np.cross(along, (0, 0, 1))
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    up = np.cross(side, along)
    L = rng.uniform(0.7, 1.3, n) * size
    tint = rng.uniform(tint_range[0], tint_range[1], n)
    return base, along, side, up, L, tint


def leaf_cards(n, rng, centres, spread, size, droop=0.5, tint_range=(0.0, 1.0)):
    """n leaves as two-quad folded cards. centres is k x 3: leaves scatter round them."""
    base, along, side, up, L, tint = card_frames(n, rng, centres, spread, size, droop, tint_range)
    local = CARD[None, :, 0:1] * along[:, None] + CARD[None, :, 1:2] * side[:, None] + CARD[None, :, 2:3] * up[:, None]
    verts = (base[:, None] + local * L[:, None, None]).reshape(-1, 3)
    i = np.arange(n)[:, None] * 5
    quads = np.concatenate([i + np.array([0, 2, 4, 1]), i + np.array([0, 3, 4, 2])])
    return verts, quads, np.repeat(tint, 5)


def instanced_cards(name, frames, col, material):
    """The same leaves as instances of one card, made when the scene is evaluated: a canopy of a quarter of a
    million leaves is then stored as one point each, not five vertices and two faces."""
    base, along, side, up, L, tint = frames
    # the leaf's axes, side flipped, make a proper rotation; the card is drawn flipped to match, so each leaf lands where it did
    R = np.stack([along, -side, up], 2)
    euler = np.stack([np.arctan2(R[:, 2, 1], R[:, 2, 2]), -np.arcsin(np.clip(R[:, 2, 0], -1, 1)), np.arctan2(R[:, 1, 0], R[:, 0, 0])], 1)
    card = obj_from_arrays(name + 'Card', CARD * np.array([1, -1, 1]), [(0, 2, 4, 1), (0, 3, 4, 2)], col)
    card.data.materials.append(material)
    card.location = (0, 0, -50)                  # the source leaf, out of sight under the ground
    card.hide_render = True
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(base))
    me.vertices.foreach_set('co', base.astype(np.float32).ravel())
    me.attributes.new('rot', 'FLOAT_VECTOR', 'POINT').data.foreach_set('vector', euler.astype(np.float32).ravel())
    me.attributes.new('scale', 'FLOAT', 'POINT').data.foreach_set('value', L.astype(np.float32))
    me.attributes.new('tint', 'FLOAT', 'POINT').data.foreach_set('value', tint.astype(np.float32))
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    tree = bpy.data.node_groups.new(name + 'Cards', 'GeometryNodeTree')
    tree.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    tree.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    nodes, links = tree.nodes, tree.links
    gi, go = nodes.new('NodeGroupInput'), nodes.new('NodeGroupOutput')
    put = nodes.new('GeometryNodeInstanceOnPoints')
    info = nodes.new('GeometryNodeObjectInfo')
    info.inputs['Object'].default_value = card
    rot = nodes.new('GeometryNodeInputNamedAttribute')
    rot.data_type = 'FLOAT_VECTOR'
    rot.inputs['Name'].default_value = 'rot'
    scale = nodes.new('GeometryNodeInputNamedAttribute')
    scale.data_type = 'FLOAT'
    scale.inputs['Name'].default_value = 'scale'
    real = nodes.new('GeometryNodeRealizeInstances')
    links.new(gi.outputs[0], put.inputs['Points'])
    links.new(info.outputs['Geometry'], put.inputs['Instance'])
    links.new(rot.outputs['Attribute'], put.inputs['Rotation'])
    links.new(scale.outputs['Attribute'], put.inputs['Scale'])
    links.new(put.outputs['Instances'], real.inputs['Geometry'])
    links.new(real.outputs['Geometry'], go.inputs[0])
    ob.modifiers.new('Leaves', 'NODES').node_group = tree
    return ob


# ----- trees ------------------------------------------------------------------

def tree_trunk(rng, height, radius, lean, nodes=46, sides=26, buttress=3.2, ribs=None, phase=None):
    """A straight forest trunk with buttress roots flaring out at its foot."""
    t = np.linspace(0, 1, nodes) ** 1.4
    wander = rng.normal(0, 0.012, (nodes, 2)).cumsum(0) * height * 0.06
    axis = np.stack([wander[:, 0] + lean[0] * t * height, wander[:, 1] + lean[1] * t * height, t * height], 1)
    r = radius * (1 - 0.72 * t) + 0.04
    th = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    ribs = int(rng.integers(4, 7)) if ribs is None else ribs
    phase = rng.uniform(0, 6.28) if phase is None else phase
    rough = Noise(int(rng.integers(1, 9999)))
    T, TH = np.meshgrid(np.arange(nodes), th, indexing='ij')
    fin = np.maximum(np.cos(TH * ribs + phase), 0) ** 5
    flare = buttress * np.exp(-(t[T] * height) / (height * 0.038 + 0.5)) * fin + 0.5 * np.exp(-(t[T] * height) / 2.0)
    bumps = 1 + 0.06 * rough(np.stack([np.cos(TH) * 2, np.sin(TH) * 2, t[T] * 9], -1))
    rad = r[T] * (1 + flare) * bumps
    verts = np.stack([axis[T, 0] + np.cos(TH) * rad, axis[T, 1] + np.sin(TH) * rad, axis[T, 2] - 0.25 * (T == 0)], -1)
    i, j = np.mgrid[0:nodes - 1, 0:sides]
    a = i * sides + j
    b = i * sides + (j + 1) % sides
    quads = np.stack([a, b, b + sides, a + sides], -1).reshape(-1, 4)
    return verts.reshape(-1, 3), quads, axis


def crown(rng, axis, radius, crown_r, limbs=(9, 14)):
    parts, centres, spreads = [], [], []
    for k in range(int(rng.integers(*limbs))):
        at = rng.uniform(0.60, 0.96)
        a = axis[int(at * (len(axis) - 1))]
        heading = rng.uniform(0, 6.283)
        reach = crown_r * rng.uniform(0.55, 1.05) * (1.15 - at * 0.5)
        rise = rng.uniform(0.15, 0.8)
        s = np.linspace(0, 1, 12)[:, None]
        d = np.array([math.cos(heading), math.sin(heading), 0])
        path = a + d * s * reach + np.array([0, 0, 1]) * (s * reach * rise - s * s * reach * 0.25)
        vv, ff = sweep(path, np.linspace(radius * 0.26, 0.03, 12), 7)
        parts.append((vv, np.array(ff)))
        for f in (0.45, 0.75, 1.0):
            centres.append(a + d * f * reach + np.array([0, 0, 1]) * (f * reach * rise - f * f * reach * 0.25 + 0.5))
            spreads.append(reach * 0.34 + 1.0)
    return parts, np.array(centres), np.array(spreads)


def forest_tree(name, seed, col, bark, leaves, height=30.0, radius=0.62, crown_r=9.0, leaf_count=15000, leaf_size=0.22, buttress=3.2):
    """One tall tree: trunk, limbs, and crowded leaf clusters. Used many times over."""
    rng = np.random.default_rng(seed)
    v, q, axis = tree_trunk(rng, height, radius, rng.normal(0, 0.012, 2), buttress=buttress)
    parts, centres, spreads = crown(rng, axis, radius, crown_r)
    verts, quads = joined([(v, q)] + parts)
    trunk = fast_mesh(name + '.wood', verts, quads, col, material=bark)
    lv, lq, tint = leaf_cards(leaf_count, rng, centres, spreads, leaf_size)
    crown_ob = fast_mesh(name + '.crown', lv, lq, col, {'tint': tint}, leaves)
    for ob in (trunk, crown_ob):
        ob.hide_render = ob.hide_viewport = True
    return trunk, crown_ob


def make_iroko(col, leaves):
    """The iroko: taller and broader than the trees round it, its buttresses opening a niche toward the clearing."""
    rng = np.random.default_rng(909)
    bark = iroko_bark()
    toward = math.atan2(-IROKO[1], -IROKO[0])          # the clearing, seen from the tree
    ribs = 5
    phase = math.pi - ribs * toward                    # a gap between two buttresses faces the clearing
    v, q, axis = tree_trunk(rng, 44.0, IROKO_R, (0.0, 0.0), nodes=70, sides=72, buttress=2.1, ribs=ribs, phase=phase)
    parts, centres, spreads = crown(rng, axis, IROKO_R, 15.0, (12, 17))
    verts, quads = joined([(v, q)] + parts)
    trunk = fast_mesh('Iroko', verts + np.array([IROKO[0], IROKO[1], 0.0]), quads, col, material=bark)
    sub = trunk.modifiers.new('Smooth', 'SUBSURF')
    sub.levels, sub.render_levels = 0, 1
    lv, lq, tint = leaf_cards(30000, rng, centres + np.array([IROKO[0], IROKO[1], 0.0]), spreads, 0.24)
    fast_mesh('Iroko.crown', lv, lq, col, {'tint': tint}, leaves)
    base_r = IROKO_R * 1.5 + 0.04
    spot = np.array(IROKO) + np.array([math.cos(toward), math.sin(toward)]) * (base_r + 0.30)
    return trunk, spot, toward


def shrub(name, seed, col, bark, leaves, height=4.5, spread=2.4, leaf_count=2600, leaf_size=0.20):
    """Understorey: a few thin stems and a loose head of big leaves."""
    rng = np.random.default_rng(seed)
    parts, centres = [], []
    for k in range(5):
        a = rng.uniform(0, 6.28)
        s = np.linspace(0, 1, 8)[:, None]
        tip = np.array([math.cos(a) * spread * 0.6, math.sin(a) * spread * 0.6, height * rng.uniform(0.7, 1.05)])
        path = tip * s + np.array([0, 0, 1]) * (-s * s * height * 0.1)
        vv, ff = sweep(path, np.linspace(0.05, 0.012, 8), 5)
        parts.append((vv, np.array(ff)))
        for f in (0.45, 0.7, 1.0):
            centres.append(tip * f)
    verts, quads = joined(parts)
    stem = fast_mesh(name + '.wood', verts, quads, col, material=bark)
    lv, lq, tint = leaf_cards(leaf_count, rng, np.array(centres), spread * 0.42, leaf_size, droop=0.8)
    head = fast_mesh(name + '.leaves', lv, lq, col, {'tint': tint}, leaves)
    for ob in (stem, head):
        ob.hide_render = ob.hide_viewport = True
    return stem, head


def fern(name, seed, col, material, fronds=12, length=0.95):
    """A clump of fern: arching fronds, each a rachis with leaflets down both sides, shorter toward the tip."""
    rng = np.random.default_rng(seed)
    verts, quads, tints, stems = [], [], [], []
    count = 0
    for k in range(fronds):
        heading = k / fronds * 2 * math.pi + rng.uniform(-0.25, 0.25)
        L = length * rng.uniform(0.65, 1.1)
        rise = rng.uniform(0.45, 0.75)
        d = np.array([math.cos(heading), math.sin(heading), 0.0])
        side = np.array([-d[1], d[0], 0.0])
        s = np.linspace(0, 1, 28)
        spine = d[None] * (L * s)[:, None] + np.array([0, 0, 1.0])[None] * (L * rise * np.sin(np.pi * s * 0.62) - L * 0.32 * s ** 2.4)[:, None]
        stems.append(sweep(spine, np.linspace(0.0032, 0.0008, 28), 4))
        tan = np.gradient(spine, axis=0)
        tan /= np.linalg.norm(tan, axis=1, keepdims=True)
        tint = rng.uniform(0, 1)
        for i in range(4, 28):
            t = s[i]
            leaflet = L * 0.24 * math.sin(math.pi * min((t - 0.1) / 0.92, 1.0)) ** 0.8 + 0.008
            up = np.cross(side, tan[i])
            for sgn in (1, -1):
                out = side * sgn * 0.92 + tan[i] * 0.38 - up * 0.18
                out /= np.linalg.norm(out)
                w = leaflet * 0.16
                p0 = spine[i]
                p1 = p0 + out * leaflet * 0.5 + tan[i] * w + up * w * 0.3
                p2 = p0 + out * leaflet * 0.5 - tan[i] * w + up * w * 0.3
                p3 = p0 + out * leaflet * 0.5 + up * w * 0.4
                p4 = p0 + out * leaflet - up * leaflet * 0.10
                verts.append(np.array([p0, p1, p3, p2, p4]))
                base = count * 5
                quads += [(base, base + 2, base + 4, base + 1), (base, base + 3, base + 4, base + 2)]
                tints.append(np.full(5, tint + rng.normal(0, 0.05)))
                count += 1
    ob = fast_mesh(name, np.concatenate(verts), np.array(quads), col, {'tint': np.clip(np.concatenate(tints), 0, 1)}, material)
    sv, sq = joined(stems)
    st = fast_mesh(name + '.stems', sv, sq, col, material=material)
    for o in (ob, st):
        o.hide_render = o.hide_viewport = True
    return ob, st


def liana(rng, top, drop, wobble=0.6):
    n = 26
    s = np.linspace(0, 1, n)[:, None]
    path = top + np.array([0, 0, -1.0]) * s * drop + rng.normal(0, 1, (n, 3)).cumsum(0) * wobble * 0.03 * s
    return sweep(path, np.linspace(0.030, 0.010, n), 5)


def place(src, col, at, yaw, scale, z_scale=None):
    ob = bpy.data.objects.new(src.name.split('.')[0], src.data)
    col.objects.link(ob)
    ob.location = at
    ob.rotation_euler = (0, 0, yaw)
    ob.scale = (scale, scale, z_scale or scale)
    return ob


def in_shaft(x, y, crown_r, heights):
    """True when a crown this wide, centred here, would stand in the way of one of the shafts of sun."""
    for a, b, r in SHAFTS[:1]:                     # only his own: the rest may be broken up by the crowns, as real ones are
        for h in heights:
            t = h / SUN.z
            if math.hypot(x - (a + SUN.x * t), y - (b + SUN.y * t)) < crown_r + r + 1.0:
                return True
    return False


OFFER_EYE = (-0.67, 4.02)


def in_offering_view(x, y, spot, margin=1.0):
    """Near the line from the offering camera to the iroko's niche."""
    p, a, b = np.array([x, y]), np.array(OFFER_EYE), np.array(spot)
    t = np.clip((p - a) @ (b - a) / ((b - a) @ (b - a)), 0, 1)
    return float(np.linalg.norm(p - (a + t * (b - a)))) < margin


def in_view(x, y):
    """The way from the hero camera to him, and the ground just round him: kept open."""
    return (y < 1.2 and abs(x + 0.3) < 2.6 + max(-y, 0) * 0.45) or math.hypot(x - CLEAR[0], y - CLEAR[1]) < CLEAR[2]


def make_forest(col, near):
    bark = bark_material()
    high = foliage_material('Canopy')
    low = foliage_material('Understorey', (0.010, 0.036, 0.012), (0.026, 0.085, 0.022), (0.080, 0.140, 0.034))
    frond = foliage_material('Fern', (0.016, 0.050, 0.010), (0.040, 0.115, 0.018), (0.110, 0.190, 0.030), rough=0.45)
    rng = np.random.default_rng(77)

    tall = [forest_tree(f'Tall{k}', 300 + k, col, bark, high, height=rng.uniform(28, 38), radius=rng.uniform(0.55, 0.85),
                        crown_r=rng.uniform(8, 12)) for k in range(4)]
    mid = [forest_tree(f'Mid{k}', 340 + k, col, bark, high, height=rng.uniform(13, 18), radius=rng.uniform(0.20, 0.32),
                       crown_r=rng.uniform(4, 6), leaf_count=7000, leaf_size=0.20, buttress=1.2) for k in range(3)]
    bushes = [shrub(f'Bush{k}', 400 + k, col, bark, low, height=rng.uniform(2.4, 4.8), spread=rng.uniform(1.6, 3.0)) for k in range(4)]
    ferns = [fern(f'Fern{k}', 440 + k, near, frond, fronds=int(rng.integers(10, 15)), length=rng.uniform(0.75, 1.15)) for k in range(3)]
    iroko, spot, toward = make_iroko(col, high)

    placed = dict(tall=0, mid=0, bush=0, fern=0)
    spots = [IROKO]

    def far_enough(x, y, gap):
        return all(math.hypot(x - a, y - b) > gap for a, b in spots)

    # a close ring of tall trunks round the clearing, so they stand in rows into the mist; then the forest beyond
    tries = 0
    while placed['tall'] < 75 and tries < 9000:
        tries += 1
        x, y = rng.uniform(-32, 32), rng.uniform(-12, 42)
        r = math.hypot(x, y)
        if r < rng.uniform(7.0, 10.0) or in_view(x, y) or (y < -3 and abs(x) < 12) or not far_enough(x, y, 4.6) or in_shaft(x, y, 11.0, (20, 27, 34)):
            continue
        spots.append((x, y))
        k = int(rng.integers(0, len(tall)))
        z = float(height_field(np.array([x]), np.array([y]))[0]) - 0.1
        for part in tall[k]:
            place(part, col, (x, y, z), rng.uniform(0, 6.28), rng.uniform(0.85, 1.2))
        placed['tall'] += 1
    tries = 0
    while placed['tall'] < 190 and tries < 9000:
        tries += 1
        x, y = rng.uniform(-75, 75), rng.uniform(-35, 110)
        r = math.hypot(x, y)
        if r < rng.uniform(7.5, 11) or in_view(x, y) or (y < -3 and abs(x) < 14) or not far_enough(x, y, 7.5) or in_shaft(x, y, 11.0, (20, 27, 34)):
            continue
        spots.append((x, y))
        k = int(rng.integers(0, len(tall)))
        z = float(height_field(np.array([x]), np.array([y]))[0]) - 0.1
        for part in tall[k]:
            place(part, col, (x, y, z), rng.uniform(0, 6.28), rng.uniform(0.85, 1.2))
        placed['tall'] += 1

    tries = 0
    while placed['mid'] < 200 and tries < 9000:
        tries += 1
        x, y = rng.uniform(-60, 60), rng.uniform(-25, 95)
        if math.hypot(x, y) < rng.uniform(4.5, 7) or in_view(x, y) or (y < -3 and abs(x) < 8) or not far_enough(x, y, 3.0) or in_shaft(x, y, 5.5, (11, 16)):
            continue
        spots.append((x, y))
        k = int(rng.integers(0, len(mid)))
        z = float(height_field(np.array([x]), np.array([y]))[0]) - 0.05
        for part in mid[k]:
            place(part, col, (x, y, z), rng.uniform(0, 6.28), rng.uniform(0.8, 1.25))
        placed['mid'] += 1

    tries = 0
    while placed['bush'] < 380 and tries < 20000:
        tries += 1
        x, y = rng.uniform(-45, 45), rng.uniform(-22, 80)
        if math.hypot(x, y) < rng.uniform(3.6, 5.5) or in_view(x, y) or math.hypot(x - IROKO[0], y - IROKO[1]) < 3.4 or in_offering_view(x, y, spot, 1.8):
            continue
        k = int(rng.integers(0, len(bushes)))
        z = float(height_field(np.array([x]), np.array([y]))[0]) - 0.03
        for part in bushes[k]:
            place(part, col, (x, y, z), rng.uniform(0, 6.28), rng.uniform(0.75, 1.3))
        placed['bush'] += 1

    tries = 0
    while placed['fern'] < 260 and tries < 30000:
        tries += 1
        x, y = rng.uniform(-14, 14), rng.uniform(-8, 22)
        if in_view(x, y) or math.hypot(x - IROKO[0], y - IROKO[1]) < IROKO_R * 1.6 + 0.4 or math.hypot(x, y) < rng.uniform(2.4, 3.4) or in_offering_view(x, y, spot, 0.9):
            continue
        z = float(height_field(np.array([x]), np.array([y]))[0])
        k = int(rng.integers(0, len(ferns)))
        for part in ferns[k]:
            place(part, near, (x, y, z - 0.02), rng.uniform(0, 6.28), rng.uniform(0.6, 1.25))
        placed['fern'] += 1

    # lianas hanging into the clearing from the limbs above
    parts = []
    for _ in range(60):
        x, y = rng.uniform(-20, 22), rng.uniform(-4, 30)
        if in_view(x, y) and y < 3:
            continue
        parts.append(liana(rng, np.array([x, y, rng.uniform(14, 24)]), rng.uniform(8, 20)))
    verts, quads = joined(parts)
    fast_mesh('Lianas', verts, quads, col, material=bark)
    print('forest', placed, flush=True)
    return high, spot, toward


def make_log(col):
    """A fallen trunk lying across the back of the clearing, old enough to be mossed over and sinking into the floor."""
    rng = np.random.default_rng(13)
    n = Noise(31)
    start, end = np.array([1.2, 3.6]), np.array([5.6, 1.4])
    s = np.linspace(0, 1, 120)
    xy = start[None] + (end - start)[None] * s[:, None]
    xy += np.array([-(end - start)[1], (end - start)[0]])[None] / np.linalg.norm(end - start) * (0.18 * np.sin(s * 2.4))[:, None]
    r = 0.30 * (1 - 0.25 * s) * (1 + 0.06 * n.fbm(np.stack([s * 9, np.zeros_like(s), np.zeros_like(s)], 1), 2))
    z = height_field(xy[:, 0], xy[:, 1]) + r * 0.78
    path = np.column_stack([xy, z])
    v, f = sweep(path, r, sides=36)
    # the bark split and lumpy along it
    a = np.tile(np.linspace(0, 2 * np.pi, 36, endpoint=False), len(s))
    ss = np.repeat(s, 36)
    lump = 1 + 0.05 * n.fbm(np.stack([np.cos(a) * 2, np.sin(a) * 2, ss * 30], 1), 3)
    centre = np.repeat(path, 36, axis=0)
    v = centre + (v - centre) * lump[:, None]
    f = list(f) + [tuple(range(35, -1, -1)), tuple(range((len(s) - 1) * 36, len(s) * 36))]
    ob = obj_from_arrays('FallenLog', v, f, col)
    ob.data.materials.append(log_material())
    sub = ob.modifiers.new('Smooth', 'SUBSURF')
    sub.levels, sub.render_levels = 0, 1
    return ob


def make_offerings(col, spot, toward):
    """At the iroko's foot, between two buttresses: a clay pot, a calabash of kola nuts, and cowries on the ground."""
    rng = np.random.default_rng(55)
    ground = lambda x, y: float(height_field(np.array([x]), np.array([y]))[0])
    face = np.array([math.cos(toward), math.sin(toward)])
    across = np.array([-face[1], face[0]])
    # the pot: round-bellied, a short neck, an everted rim, set a little into the soil
    profile = [(0.002, 0.0), (0.060, 0.004), (0.115, 0.040), (0.150, 0.105), (0.155, 0.150), (0.140, 0.200), (0.100, 0.245), (0.080, 0.262),
               (0.082, 0.280), (0.098, 0.294), (0.093, 0.300), (0.074, 0.286), (0.070, 0.262), (0.088, 0.240), (0.125, 0.198),
               (0.140, 0.150), (0.134, 0.106), (0.100, 0.046), (0.050, 0.014), (0.002, 0.012)]
    v, f = regalia.lathe(profile, 64)
    at = spot + across * 0.22
    pot = obj_from_arrays('OfferingPot', v + np.array([at[0], at[1], ground(*at) - 0.012]), f, col)
    pot.data.materials.append(clay_material())
    pot.modifiers.new('Smooth', 'SUBSURF').render_levels = 1
    # the calabash: half a gourd, cut clean, its rim a little uneven
    rows = 24
    prof = []
    for i in range(rows):
        t = i / (rows - 1)
        a = t * math.pi / 2
        prof.append((0.135 * math.sin(a) + 0.002, 0.090 * (1 - math.cos(a))))
    inner = [(r * 0.94, z + 0.006) for r, z in prof[::-1]]
    v, f = regalia.lathe(prof + inner, 64)
    at2 = spot - across * 0.18 + face * 0.10
    z2 = ground(*at2) + 0.005
    cal = obj_from_arrays('Calabash', v + np.array([at2[0], at2[1], z2]), f, col)
    cal.data.materials.append(gourd_material())
    cal.modifiers.new('Smooth', 'SUBSURF').render_levels = 1
    # kola nuts heaped in it: each a plump lobe with a crease down one side
    parts = []
    from dress import join_beads, sphere
    for k in range(9):
        a, rr = rng.uniform(0, 6.28), 0.075 * math.sqrt(rng.uniform(0, 1))
        bowl = 0.090 * (1 - math.sqrt(max(1 - (rr / 0.13) ** 2, 0.0)))          # the inside of the gourd rises toward its rim
        c = np.array([at2[0] + math.cos(a) * rr, at2[1] + math.sin(a) * rr, z2 + 0.022 + 0.9 * bowl + 0.016 * (k > 5)])
        sv, sf, _ = sphere(0.019, 10, 14)
        sv = sv * np.array([1.0, 0.78, 0.66])
        sv[:, 1] -= 0.004 * np.exp(-(sv[:, 0] / 0.004) ** 2) * (sv[:, 1] > 0)
        yaw = rng.uniform(0, 6.28)
        R = np.array([[math.cos(yaw), -math.sin(yaw), 0], [math.sin(yaw), math.cos(yaw), 0], [0, 0, 1]])
        parts.append((sv @ R.T + c, sf))
    join_beads('KolaNuts', parts, col, kola_material())
    # cowries on the soil in front, and in the calabash with the kola
    v0, f0 = regalia.cowrie_mesh()
    parts = []
    for k in range(14):
        yaw = rng.uniform(0, 6.28)
        c, s_ = math.cos(yaw), math.sin(yaw)
        belly_down = rng.random() < 0.7
        # the shell's back (+y) up, or turned over to show its toothed slit
        R = np.array([[c, 0, s_], [s_, 0, -c], [0, 1, 0]]) if belly_down else np.array([[c, 0, -s_], [s_, 0, c], [0, -1, 0]])
        lift = float(-(v0 @ R.T)[:, 2].min())
        if k < 10:
            p = spot + face * rng.uniform(0.30, 0.55) + across * rng.uniform(-0.30, 0.30)
            z = ground(*p) + lift - 0.0005
        else:
            a = rng.uniform(0, 6.28)
            p = at2 + np.array([math.cos(a), math.sin(a)]) * rng.uniform(0.02, 0.07)
            z = z2 + 0.052 + lift
        parts.append((v0 @ R.T + np.array([p[0], p[1], z]), f0))
    from procedural import merged
    v, f = merged(parts)
    cw = obj_from_arrays('OfferingCowries', v, f, col)
    cw.data.materials.append(regalia.cowrie_material())
    niche_litter(col, spot, face, across, at, at2)
    return pot, cal


def niche_litter(col, spot, face, across, pot_at, gourd_at):
    """Fallen leaves and twigs round the offerings, thinner where the cowries lie, none under the pot or the calabash."""
    rng = np.random.default_rng(57)
    n = 1400
    a = rng.uniform(0, 2 * np.pi, n)
    rr = 1.6 * np.sqrt(rng.uniform(0, 1, n))
    centre = spot + face * 0.45
    x, y = centre[0] + np.cos(a) * rr, centre[1] + np.sin(a) * rr
    p = np.stack([x, y], 1)
    keep = np.hypot(x - IROKO[0], y - IROKO[1]) > IROKO_R * 1.62
    keep &= np.linalg.norm(p - pot_at, axis=1) > 0.19
    keep &= np.linalg.norm(p - gourd_at, axis=1) > 0.17
    w = p - spot
    in_cowries = ((w @ face) > 0.24) & ((w @ face) < 0.62) & (np.abs(w @ across) < 0.36)
    keep &= ~in_cowries | (rng.random(n) < 0.15)
    x, y = x[keep], y[keep]
    n = len(x)
    z = height_field(x, y)
    heading = rng.uniform(0, 6.283, n)
    along = np.stack([np.cos(heading), np.sin(heading), rng.normal(0, 0.05, n)], 1)
    side = np.cross(along, (0, 0, 1))
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    L = rng.uniform(0.05, 0.15, n)
    W = L * rng.uniform(0.20, 0.34, n)
    curl = rng.uniform(-0.03, 0.12, n)
    centres = np.stack([x, y, z + 0.004 + rng.uniform(0.0, 0.010, n) + L * np.maximum(-curl, 0)], 1)
    verts, quads, tint = leaf_blades(np.random.default_rng(58), centres, along, side, L, W, curl, rng.random(n))
    leaf = foliage_material('Litter', (0.040, 0.020, 0.008), (0.13, 0.065, 0.020), (0.30, 0.18, 0.040), rough=0.74)
    fast_mesh('NicheLitter', verts, quads, col, {'tint': tint}, leaf)
    parts = []
    for _ in range(9):
        c = centre + rng.normal(0, 0.55, 2)
        if np.hypot(c[0] - IROKO[0], c[1] - IROKO[1]) < IROKO_R * 1.7:
            continue
        t = rng.uniform(0, 6.28)
        length = rng.uniform(0.12, 0.45)
        s = np.linspace(0, 1, 9)[:, None]
        q = np.array([c[0], c[1], 0.0]) + np.array([math.cos(t), math.sin(t), 0]) * s * length + rng.normal(0, 0.006, (9, 3)).cumsum(0)
        q[:, 2] = height_field(q[:, 0], q[:, 1]) + 0.007
        parts.append(sweep(q, np.linspace(0.008, 0.0025, 9), 5))
    if parts:
        verts, quads = joined(parts)
        fast_mesh('NicheSticks', verts, quads, col, material=bpy.data.materials['Bark'])
    print('leaves round the offerings', n, flush=True)


def leaf_blades(rng, centres, along, side, length, width, curl, tint, sections=10):
    """Fallen leaves as strips across the midrib: a stalk, a pointed blade, its two halves folded up, the whole curled."""
    n = len(centres)
    t = np.linspace(0, 1, sections)[None, :, None]
    half = np.sin(np.pi * np.clip((t - 0.10) / 0.90, 0, 1) ** 0.8) ** 0.8 + 0.04
    length, width, curl = (a[:, None, None] for a in (length, width, curl))
    up = np.array([0, 0, 1.0])
    mid = centres[:, None] + along[:, None] * length * (t - 0.5) + up * length * curl * (2 * t - 1) ** 2
    edge = side[:, None] * width * half
    left, right = (mid + sign * edge + up * width * half * rng.uniform(0.03, 0.32, (n, 1, 1)) for sign in (-1, 1))
    verts = np.stack([left, mid, right], 2).reshape(-1, 3)
    a = np.arange(sections - 1)[:, None] * 3 + np.array([0, 1])
    cell = np.stack([a, a + 1, a + 4, a + 3], -1).reshape(-1, 4)
    quads = (np.arange(n)[:, None, None] * (sections * 3) + cell).reshape(-1, 4)
    browned = np.repeat(tint, sections * 3) - np.tile((0.16, 0.0, 0.16), n * sections)
    return verts, quads, np.clip(browned, 0, 1)


def make_litter(col, feet):
    """Fallen leaves thick on the floor, and sticks."""
    rng = np.random.default_rng(38)
    x0, x1, y0, y1 = NEAR
    n = 4200
    x, y = rng.uniform(x0 + 0.2, x1 - 0.2, n), rng.uniform(y0 + 0.2, y1 - 0.2, n)
    keep = np.ones(n, bool)
    for fx, fy in feet:
        keep &= np.hypot(x - fx, y - fy) > 0.13
    x, y = x[keep], y[keep]
    z = height_field(x, y)
    n = len(x)
    heading = rng.uniform(0, 6.283, n)
    along = np.stack([np.cos(heading), np.sin(heading), rng.normal(0, 0.05, n)], 1)
    side = np.cross(along, (0, 0, 1))
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    L = rng.uniform(0.05, 0.16, n)
    W = L * rng.uniform(0.20, 0.34, n)
    curl = rng.uniform(-0.03, 0.12, n)
    stack = rng.uniform(0.0, 0.012, n)
    centres = np.stack([x, y, z + 0.004 + stack + L * np.maximum(-curl, 0)], 1)
    verts, quads, tint = leaf_blades(np.random.default_rng(39), centres, along, side, L, W, curl, rng.random(n))
    leaf = foliage_material('Litter', (0.040, 0.020, 0.008), (0.13, 0.065, 0.020), (0.30, 0.18, 0.040), rough=0.74)
    fast_mesh('Litter', verts, quads, col, {'tint': tint}, leaf)
    parts = []
    for _ in range(40):
        a, b = rng.uniform(x0 + 0.4, x1 - 0.4), rng.uniform(y0 + 0.4, y1 - 0.4)
        if math.hypot(a, b) < 0.5:
            continue
        t = rng.uniform(0, 6.28)
        L = rng.uniform(0.15, 0.9)
        s = np.linspace(0, 1, 9)[:, None]
        p = np.array([a, b, 0.0]) + np.array([math.cos(t), math.sin(t), 0]) * s * L + rng.normal(0, 0.01, (9, 3)).cumsum(0)
        p[:, 2] = height_field(p[:, 0], p[:, 1]) + 0.008
        parts.append(sweep(p, np.linspace(0.010, 0.003, 9), 5))
    verts, quads = joined(parts)
    fast_mesh('Sticks', verts, quads, col, material=bpy.data.materials['Bark'])


def make_canopy(col, material, holes):
    """A roof of leaves high over the clearing, with gaps. The sun comes through them as separate shafts.

    Each hole is given by where its light lands on the ground, and a radius.
    """
    rng = np.random.default_rng(66)
    cells = []
    for x in np.arange(-38, 38, 1.6):
        for y in np.arange(-16, 64, 1.6):
            z = rng.uniform(16.0, 27.0)
            px, py = x + rng.normal(0, 0.45), y + rng.normal(0, 0.45)
            t = z / SUN.z
            gx, gy = px - SUN.x * t, py - SUN.y * t
            if any(math.hypot(gx - a, gy - b) < r + 0.5 for a, b, r in holes) or rng.random() < 0.18:
                continue
            cells.append((px, py, z))
    frames = card_frames(len(cells) * 120, rng, np.array(cells), 1.25, 0.22)
    print('canopy cells', len(cells), flush=True)
    return instanced_cards('Canopy', frames, col, material)


# each shaft by where its light lands on the ground, and its radius. The first falls on him: the light that reaches
# his head and shoulders lands, if nothing stopped it, a little to his right.
SHAFTS = ((-0.40, -0.05, 1.7), (3.6, 5.5, 0.8), (-4.2, 9.5, 1.1), (6.8, 12.0, 1.2), (-1.8, 15.5, 0.9), (2.6, 21.0, 1.3), (-7.5, 4.5, 0.8),
          (9.5, 3.0, 0.9), (-10.0, 16.0, 1.0), (1.0, 30.0, 1.4), (-3.2, 3.2, 0.7))


def make_sun_mask(col, holes=SHAFTS, z=23.0):
    """A sheet only the sun can see. Its gaps turn sunlight into shafts, and a scatter of small ones into dapples.

    The real canopy is too thin to do this on its own, and would cost far more to make dense enough.
    """
    step = 0.45
    xs = np.arange(-95, 95, step)
    ys = np.arange(-70, 140, step)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    t = z / SUN.z
    gx, gy = X - SUN.x * t, Y - SUN.y * t
    n = Noise(12)
    p = np.stack([gx, gy, np.zeros_like(gx)], -1)
    wobble = 0.28 * n.fbm(p * 1.3, 3, 0.6)
    solid = np.ones(X.shape, bool)
    for a, b, r in holes:
        solid &= np.hypot(gx - a, gy - b) > r * (1 + wobble)
    dapple = n.fbm(p * 0.95, 3, 0.55) > 0.46
    solid &= ~dapple
    # each row's unbroken runs of solid cells become one long quad: the same cover, a fraction of the faces
    h = step / 2
    x0s, x1s, rows = [], [], []
    for j in range(solid.shape[1]):
        edges = np.diff(np.concatenate([[0], solid[:, j].astype(np.int8), [0]]))
        starts, ends = np.nonzero(edges == 1)[0], np.nonzero(edges == -1)[0] - 1
        x0s.append(xs[starts] - h)
        x1s.append(xs[ends] + h)
        rows.append(np.full(len(starts), ys[j]))
    x0, x1, cy = np.concatenate(x0s), np.concatenate(x1s), np.concatenate(rows)
    quads = np.arange(len(cy) * 4).reshape(-1, 4)
    verts = np.empty((len(cy) * 4, 3), np.float32)
    verts[0::4] = np.stack([x0, cy - h, np.full_like(cy, z)], 1)
    verts[1::4] = np.stack([x1, cy - h, np.full_like(cy, z)], 1)
    verts[2::4] = np.stack([x1, cy + h, np.full_like(cy, z)], 1)
    verts[3::4] = np.stack([x0, cy + h, np.full_like(cy, z)], 1)
    ob = fast_mesh('SunMask', verts, quads, col)
    ob.visible_camera = False
    ob.visible_diffuse = False
    ob.visible_glossy = False
    ob.visible_transmission = False
    ob.visible_volume_scatter = False
    print('sun mask quads', len(quads), flush=True)
    return ob


def make_framing(col, material, eye, target, corners):
    """Out-of-focus leaves in the hero picture's corners, hanging into the clearing from the understorey."""
    rng = np.random.default_rng(90)
    eye = np.array(eye, float)
    look = np.array(target, float) - eye
    look /= np.linalg.norm(look)
    side = np.cross(look, (0, 0, 1))
    side /= np.linalg.norm(side)
    up = np.cross(side, look)
    centres, spreads = [], []
    for sx, sz, d, sp in corners:
        centres.append(eye + look * d + side * sx * d * 0.40 + up * sz * d * 0.50)
        spreads.append(sp)
    v, q, tint = leaf_cards(3000, rng, np.array(centres), np.array(spreads), 0.055, droop=0.7)
    return fast_mesh('NearLeaves', v, q, col, {'tint': tint}, material)


def make_sky():
    """A pale sky seen through the gaps, grey-green from the leaves, brightest round the sun."""
    w = bpy.data.worlds.get('Forest') or bpy.data.worlds.new('Forest')
    w.use_nodes = True
    t = w.node_tree
    t.nodes.clear()
    out = t.nodes.new('ShaderNodeOutputWorld')
    bg = t.nodes.new('ShaderNodeBackground')
    coord = t.nodes.new('ShaderNodeTexCoord')
    norm = t.nodes.new('ShaderNodeVectorMath')
    norm.operation = 'NORMALIZE'
    t.links.new(coord.outputs['Generated'], norm.inputs[0])
    dot = t.nodes.new('ShaderNodeVectorMath')
    dot.operation = 'DOT_PRODUCT'
    dot.inputs[1].default_value = SUN
    t.links.new(norm.outputs[0], dot.inputs[0])
    ramp = t.nodes.new('ShaderNodeValToRGB')
    t.links.new(dot.outputs['Value'], ramp.inputs['Fac'])
    stops = [(0.0, (0.26, 0.36, 0.34)), (0.55, (0.40, 0.52, 0.48)), (0.86, (0.78, 0.84, 0.74)), (0.975, (1.6, 1.6, 1.30)), (1.0, (5.0, 4.8, 3.8))]
    cr = ramp.color_ramp
    while len(cr.elements) < len(stops):
        cr.elements.new(0)
    for el, (p, c) in zip(cr.elements, stops):
        el.position = p
        el.color = (*c, 1)
    t.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 0.9
    t.links.new(bg.outputs[0], out.inputs['Surface'])
    w.cycles.sampling_method = 'NONE'       # so that the sun mask, which only blocks light sampling, leaves the sky alone
    bpy.context.scene.world = w
    return w


def make_mist(col, density=0.019):
    """The blue-green mist of stage 06: what fades the far trunks, and shows the shafts of light."""
    v = np.array([(x, y, z) for x in (-60, 60) for y in (-36, 100) for z in (-1.0, 32)], float)
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    ob = obj_from_arrays('Mist', v, f, col, smooth=False)
    g = mats.Graph('MistVolume')
    t = g.t
    t.nodes.clear()
    out = t.nodes.new('ShaderNodeOutputMaterial')
    vol = t.nodes.new('ShaderNodeVolumePrincipled')
    vol.inputs['Color'].default_value = (0.74, 0.90, 0.86, 1)
    vol.inputs['Density'].default_value = density
    vol.inputs['Anisotropy'].default_value = 0.55
    t.links.new(vol.outputs[0], out.inputs['Volume'])
    ob.data.materials.append(g.mat)
    return ob


def build(far, near, feet, hero_eye, hero_target):
    """The whole setting. far holds what is only seen at a distance, near what is close round him."""
    make_ground(near)
    high, spot, toward = make_forest(far, near)
    make_canopy(far, high, SHAFTS)
    make_sun_mask(far)
    make_log(near)
    make_offerings(near, spot, toward)
    make_litter(near, feet)
    make_framing(far, bpy.data.materials['Understorey'], hero_eye, hero_target,
                 ((-1.0, 0.86, 1.8, 0.30), (-0.70, 1.02, 2.0, 0.32), (0.98, 0.88, 1.9, 0.28), (0.74, 1.06, 2.1, 0.30)))
    make_sky()
    make_mist(far)
    return spot
