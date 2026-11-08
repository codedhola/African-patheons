"""The forge: an open smithy at night, its fire the only light but the moon.

This follows the layout of stage 08 in this repo, Ògún's forge: a lit mud wall with tools
hung on it, a heap of charcoal, the hearth, pot bellows and a clay pipe, an anvil with a
glowing bar, a hammer and a quench pot, a floor of beaten earth with slag, and a roof of
rafters and palm fronds on heavy posts. Its shapes and sizes are this study's, not a
record of a real smithy.

He stands at the middle of it facing -Y. The hearth burns at his left, the anvil stands at
his right hand, and the back wall closes the view behind him.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

import iron
import materials as mats
from common import obj_from_arrays
from dress import smoothstep
from procedural import Noise, merged, rock_mesh, sweep

HEARTH = Vector((1.30, 0.22, 0.0))
ANVIL = Vector((-1.05, -0.12, 0.0))
WALL_Y = 2.25
EAVE_FRONT, RIDGE = 2.55, 3.35
BAR_TEMP = 1250          # kelvin, the heated end of the bar on the anvil


# ----- materials ----------------------------------------------------------

def earth_material():
    """Beaten laterite, dark with charcoal dust, swept smooth where the smith walks."""
    g = mats.Graph('ForgeFloor')
    obj = g.node('TexCoord').outputs['Object']
    big = g.node('TexNoise', Vector=obj, Scale=0.9, Detail=6, Roughness=0.6).outputs['Fac']
    pebbles = g.node('TexVoronoi', Vector=obj, Scale=38, Randomness=1.0).outputs['Distance']
    mid = g.node('TexNoise', Vector=obj, Scale=7.0, Detail=8, Roughness=0.62).outputs['Fac']
    fine = g.node('TexNoise', Vector=obj, Scale=95, Detail=6, Roughness=0.7).outputs['Fac']
    grit = g.node('TexVoronoi', Vector=obj, Scale=260, Randomness=1.0).outputs['Distance']
    soot = g.node('Attribute', attribute_name='soot', attribute_type='GEOMETRY').outputs['Fac']
    col = g.ramp(big, [(0.25, (0.050, 0.026, 0.015)), (0.55, (0.080, 0.042, 0.024)), (0.80, (0.105, 0.058, 0.034))])
    col = g.mix(g.math('MULTIPLY', mid, 0.5), col, (0.060, 0.034, 0.022))
    col = g.mix(g.math('MULTIPLY', soot, g.math('ADD', 0.55, g.math('MULTIPLY', mid, 0.45))), col, (0.014, 0.012, 0.011))
    lumps = g.math('MULTIPLY', g.math('SUBTRACT', 1.0, g.math('MULTIPLY', pebbles, 5.0), clamp=True), g.math('GREATER_THAN', mid, 0.52))
    col = g.mix(g.math('MULTIPLY', lumps, 0.5), col, (0.16, 0.10, 0.06))
    h = g.math('ADD', g.math('MULTIPLY', mid, 0.9), g.math('ADD', g.math('MULTIPLY', fine, 0.55), g.math('ADD', g.math('MULTIPLY', grit, 0.35), g.math('MULTIPLY', lumps, 0.8))))
    normal = g.bump(h, 0.9, 0.006)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=g.math('ADD', 0.78, g.math('MULTIPLY', fine, 0.15)), Normal=normal)
    return g.finish(bsdf.outputs[0])


def mud_material(name='MudWall'):
    """Laterite plaster smoothed by hand: strokes, small cracks, soot rising above the fire."""
    g = mats.Graph(name)
    obj = g.node('TexCoord').outputs['Object']
    strokes = g.node('Mapping', Vector=obj, Scale=(1.0, 1.0, 3.2), Rotation=(0.4, 0.0, 0.25)).outputs[0]
    hand = g.node('TexNoise', Vector=strokes, Scale=6.0, Detail=6, Roughness=0.55).outputs['Fac']
    blot = g.node('TexNoise', Vector=obj, Scale=1.6, Detail=5).outputs['Fac']
    crack = g.node('TexVoronoi', Vector=g.node('Mapping', Vector=obj, Scale=(1.0, 1.0, 1.6)).outputs[0], Scale=2.6, Randomness=1.0, feature='DISTANCE_TO_EDGE').outputs['Distance']
    fine = g.node('TexNoise', Vector=obj, Scale=120, Detail=5, Roughness=0.7).outputs['Fac']
    soot = g.node('Attribute', attribute_name='soot', attribute_type='GEOMETRY').outputs['Fac']
    col = g.ramp(blot, [(0.3, (0.045, 0.022, 0.012)), (0.6, (0.068, 0.034, 0.019)), (0.85, (0.085, 0.045, 0.026))])
    col = g.mix(g.math('MULTIPLY', hand, 0.45), col, (0.050, 0.025, 0.014))
    cracks = g.math('MULTIPLY', g.math('LESS_THAN', crack, 0.0045), g.math('GREATER_THAN', blot, 0.42))
    col = g.mix(g.math('MULTIPLY', cracks, 0.6), col, (0.04, 0.02, 0.012))
    col = g.mix(soot, col, (0.020, 0.016, 0.013))
    h = g.math('ADD', g.math('MULTIPLY', hand, 0.7), g.math('ADD', g.math('MULTIPLY', fine, 0.25), g.math('MULTIPLY', cracks, -0.5)))
    normal = g.bump(h, 0.6, 0.006)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.88, Normal=normal)
    return g.finish(bsdf.outputs[0])


def clay_material(name='FiredClay', soot_level=0.5):
    g = mats.Graph(name)
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=14, Detail=6).outputs['Fac']
    fine = g.node('TexNoise', Vector=obj, Scale=160, Detail=4).outputs['Fac']
    soot = g.node('Attribute', attribute_name='soot', attribute_type='GEOMETRY').outputs['Fac']
    col = g.ramp(n, [(0.3, (0.075, 0.034, 0.017)), (0.7, (0.135, 0.062, 0.030))])
    blot = g.node('TexNoise', Vector=obj, Scale=3.0, Detail=5).outputs['Fac']
    col = g.mix(g.math('MULTIPLY', soot, g.math('MULTIPLY', soot_level, g.math('ADD', 0.6, blot))), col, (0.012, 0.010, 0.009))
    normal = g.bump(g.math('ADD', n, g.math('MULTIPLY', fine, 0.7)), 0.7, 0.004)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.9, Normal=normal)
    return g.finish(bsdf.outputs[0])


def wood_material(name='PostWood'):
    """Adzed hardwood, dark with age and smoke."""
    g = mats.Graph(name)
    obj = g.node('TexCoord').outputs['Object']
    stretched = g.node('Mapping', Vector=obj, Scale=(6.0, 6.0, 0.35)).outputs[0]
    grain = g.node('TexWave', Vector=stretched, Scale=4.0, Distortion=9.0, Detail=6, wave_type='RINGS').outputs['Fac']
    adze = g.node('TexVoronoi', Vector=g.node('Mapping', Vector=obj, Scale=(9.0, 9.0, 3.0)).outputs[0], Scale=2.0).outputs['Distance']
    col = g.ramp(grain, [(0.2, (0.018, 0.011, 0.007)), (0.7, (0.042, 0.026, 0.015)), (1.0, (0.060, 0.038, 0.022))])
    normal = g.bump(g.math('ADD', grain, g.math('MULTIPLY', adze, 0.8)), 0.5, 0.004)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.74, Normal=normal)
    return g.finish(bsdf.outputs[0])


def thatch_material():
    """The underside of a palm-frond roof, browned and blackened by years of smoke."""
    g = mats.Graph('Thatch')
    obj = g.node('TexCoord').outputs['Object']
    ribs = g.node('Mapping', Vector=obj, Scale=(1.0, 40.0, 1.0)).outputs[0]
    lines = g.node('TexNoise', Vector=ribs, Scale=3.0, Detail=5).outputs['Fac']
    patch = g.node('TexNoise', Vector=obj, Scale=2.0, Detail=4).outputs['Fac']
    col = g.ramp(g.math('ADD', g.math('MULTIPLY', lines, 0.6), g.math('MULTIPLY', patch, 0.4)),
                 [(0.3, (0.010, 0.008, 0.006)), (0.6, (0.040, 0.026, 0.013)), (0.8, (0.075, 0.050, 0.024))])
    normal = g.bump(lines, 0.8, 0.01)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.9, Normal=normal)
    return g.finish(bsdf.outputs[0])


def ember_material(name='Embers', strength=3.5):
    """Charcoal in the fire: black where it has crusted over, glowing in the cracks between."""
    g = mats.Graph(name)
    obj = g.node('TexCoord').outputs['Object']
    heat = g.node('Attribute', attribute_name='heat', attribute_type='GEOMETRY').outputs['Fac']
    cracks = g.node('TexVoronoi', Vector=obj, Scale=55, feature='DISTANCE_TO_EDGE').outputs['Distance']
    n = g.node('TexNoise', Vector=obj, Scale=24, Detail=4).outputs['Fac']
    glow = g.math('MULTIPLY', g.math('SUBTRACT', 1.0, g.math('MULTIPLY', cracks, 16.0), clamp=True), g.math('MULTIPLY', heat, heat))
    patch = g.math('MULTIPLY', g.math('SUBTRACT', n, 0.66), 5.0, clamp=True)
    glow = g.math('ADD', glow, g.math('MULTIPLY', patch, g.math('MULTIPLY', heat, 0.25)))
    bb = g.node('Blackbody', Temperature=920)
    hot = g.node('Blackbody', Temperature=1250)
    colour = g.mix(g.math('MULTIPLY', n, 1.2), bb.outputs[0], hot.outputs[0])
    em = g.node('Emission', Color=colour, Strength=g.math('MULTIPLY', glow, strength))
    coal = g.node('BsdfPrincipled', Base_Color=(0.010, 0.009, 0.009, 1), Roughness=0.78)
    coal.inputs['Specular IOR Level'].default_value = 0.25
    add = g.node('AddShader')
    g.link(coal.outputs[0], add.inputs[0])
    g.link(em.outputs[0], add.inputs[1])
    return g.finish(add.outputs[0])


def hot_iron_material():
    """The bar on the anvil: yellow-orange at its heated end, falling through red to black iron."""
    g = mats.Graph('HotIron')
    obj = g.node('TexCoord').outputs['Object']
    heat = g.node('Attribute', attribute_name='heat', attribute_type='GEOMETRY').outputs['Fac']
    scale = g.node('TexNoise', Vector=obj, Scale=120, Detail=4).outputs['Fac']
    temp = g.math('ADD', 700.0, g.math('MULTIPLY', heat, BAR_TEMP - 700.0))
    bb = g.node('Blackbody', Temperature=temp)
    strength = g.math('MULTIPLY', g.math('POWER', heat, 3.0), g.math('ADD', 30.0, g.math('MULTIPLY', scale, 20.0)))
    em = g.node('Emission', Color=bb.outputs[0], Strength=strength)
    dark = g.node('BsdfPrincipled', Base_Color=(0.02, 0.019, 0.018, 1), Metallic=0.6, Roughness=0.5)
    add = g.node('AddShader')
    g.link(dark.outputs[0], add.inputs[0])
    g.link(em.outputs[0], add.inputs[1])
    return g.finish(add.outputs[0])


def anvil_material():
    """The anvil: black forged iron on its sides, its face polished bright by the hammer."""
    g = mats.Graph('AnvilIron')
    obj = g.node('TexCoord').outputs['Object']
    geo = g.node('NewGeometry')
    up = g.math('GREATER_THAN', g.node('SeparateXYZ', Vector=geo.outputs['Normal']).outputs[2], 0.85)
    n = g.node('TexNoise', Vector=obj, Scale=50, Detail=6).outputs['Fac']
    scratch = g.node('TexNoise', Vector=g.node('Mapping', Vector=obj, Scale=(1.0, 40.0, 1.0)).outputs[0], Scale=60, Detail=3).outputs['Fac']
    side = g.ramp(n, [(0.3, (0.012, 0.011, 0.011)), (0.7, (0.040, 0.034, 0.030))])
    col = g.mix(up, side, g.ramp(scratch, [(0.3, (0.30, 0.29, 0.28)), (0.7, (0.45, 0.44, 0.42))]))
    rough = g.mix(up, g.math('ADD', 0.68, g.math('MULTIPLY', n, 0.2)), g.math('ADD', 0.18, g.math('MULTIPLY', scratch, 0.12)))
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Metallic=g.mix(up, 0.2, 1.0), Roughness=rough, Normal=g.bump(n, 0.3, 0.001))
    return g.finish(bsdf.outputs[0])


def slag_material():
    """Furnace slag: black glassy lumps, rusty where iron is left in them."""
    g = mats.Graph('Slag')
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=60, Detail=5).outputs['Fac']
    pits = g.node('TexVoronoi', Vector=obj, Scale=180).outputs['Distance']
    col = g.ramp(n, [(0.35, (0.012, 0.011, 0.010)), (0.65, (0.045, 0.022, 0.012))])
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=g.math('ADD', 0.25, g.math('MULTIPLY', n, 0.4)), Normal=g.bump(pits, 0.8, 0.002))
    bsdf.inputs['Specular IOR Level'].default_value = 0.6
    return g.finish(bsdf.outputs[0])


def leather_material():
    g = mats.Graph('BellowsHide')
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=40, Detail=6).outputs['Fac']
    wr = g.node('TexVoronoi', Vector=obj, Scale=90, feature='DISTANCE_TO_EDGE').outputs['Distance']
    col = g.ramp(n, [(0.3, (0.05, 0.028, 0.014)), (0.7, (0.10, 0.060, 0.030))])
    normal = g.bump(g.math('ADD', n, g.math('MULTIPLY', wr, 3.0)), 0.5, 0.0015)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.55, Normal=normal)
    return g.finish(bsdf.outputs[0])


def water_material():
    g = mats.Graph('QuenchWater')
    obj = g.node('TexCoord').outputs['Object']
    ripple = g.node('TexNoise', Vector=obj, Scale=30, Detail=2).outputs['Fac']
    bsdf = g.node('BsdfPrincipled', Base_Color=(0.01, 0.009, 0.008, 1), Roughness=0.04, Normal=g.bump(ripple, 0.08, 0.002))
    return g.finish(bsdf.outputs[0])


def spark_material():
    g = mats.Graph('Sparks')
    fade = g.node('Attribute', attribute_name='fade', attribute_type='GEOMETRY').outputs['Fac']
    bb = g.node('Blackbody', Temperature=1900)
    em = g.node('Emission', Color=bb.outputs[0], Strength=g.math('MULTIPLY', fade, 140.0))
    return g.finish(em.outputs[0])


# ----- geometry helpers ---------------------------------------------------

def grid(name, nx, ny, x0, x1, y0, y1, height, col, attrs=None):
    xs, ys = np.linspace(x0, x1, nx), np.linspace(y0, y1, ny)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    Z = height(X, Y)
    verts = np.stack([X, Y, Z], -1).reshape(-1, 3)
    faces = [(i * ny + j, (i + 1) * ny + j, (i + 1) * ny + j + 1, i * ny + j + 1) for i in range(nx - 1) for j in range(ny - 1)]
    ob = obj_from_arrays(name, verts, faces, col)
    for k, fn in (attrs or {}).items():
        ob.data.attributes.new(k, 'FLOAT', 'POINT').data.foreach_set('value', fn(X, Y).ravel().astype(np.float32))
    return ob


def lathe(profile, sides=48):
    pts = np.array(profile, float)
    a = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    verts = np.stack([np.outer(pts[:, 0], np.cos(a)), np.outer(pts[:, 0], np.sin(a)), np.tile(pts[:, 1:2], (1, sides))], -1).reshape(-1, 3)
    rows = len(pts)
    faces = [(i * sides + j, i * sides + (j + 1) % sides, (i + 1) * sides + (j + 1) % sides, (i + 1) * sides + j) for i in range(rows - 1) for j in range(sides)]
    return verts, faces


def lumpy(v, seed, amount, freq=6.0):
    n = Noise(seed)
    return v + (v - v.mean(0)) / (np.linalg.norm(v - v.mean(0), axis=1, keepdims=True) + 1e-6) * (amount * n.fbm(v * freq, 3))[:, None]


def place(ob, at, yaw=0.0, scale=1.0):
    ob.matrix_world = Matrix.Translation(Vector(at)) @ Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Diagonal((scale, scale, scale, 1))
    return ob


def soot_by_height(ob, z0, z1):
    co = np.array([v.co for v in ob.data.vertices])
    w = np.array(ob.matrix_world)
    z = co @ w[2, :3] + w[2, 3]
    ob.data.attributes.new('soot', 'FLOAT', 'POINT').data.foreach_set('value', smoothstep(z, z0, z1).astype(np.float32))


# ----- the parts ----------------------------------------------------------

def make_floor(col):
    n = Noise(5)

    def height(X, Y):
        p = np.stack([X, Y, np.zeros_like(X)], -1)
        worn = 0.010 * n.fbm(p * 0.8, 3) + 0.0035 * n.fbm(p * 9.0, 3)
        # a shallow dip worn round the anvil and the hearth, where the work is done
        for c, r in ((ANVIL, 0.9), (HEARTH, 1.1), (Vector((0, 0, 0)), 0.8)):
            worn -= 0.012 * np.exp(-((X - c.x) ** 2 + (Y - c.y) ** 2) / r ** 2)
        keep = smoothstep(np.hypot(X - 0.05, Y + 0.02), 0.35, 0.75)
        return worn * keep

    def soot(X, Y):
        d = np.minimum(np.hypot(X - HEARTH.x, Y - HEARTH.y) / 1.9, np.hypot(X - ANVIL.x, Y - ANVIL.y) / 1.2)
        heap = np.hypot(X + 1.75, Y - 1.75) / 1.1
        return np.clip(np.maximum(1 - d, 1 - heap) * 1.05, 0, 1) * (0.6 + 0.4 * (n.fbm(np.stack([X, Y, np.ones_like(X)], -1) * 1.7, 3) + 0.5))

    ob = grid('ForgeFloor', 260, 220, -6.5, 6.5, -6.0, 5.0, height, col, {'soot': soot})
    ob.data.materials.append(earth_material())
    return ob


def make_slag(col, rng, material):
    parts = []
    for _ in range(90):
        r = rng.uniform(0.010, 0.035)
        ang, dist = rng.uniform(0, 2 * np.pi), abs(rng.normal(0, 1.1)) + 0.4
        c = (HEARTH if rng.random() < 0.65 else ANVIL) + Vector((math.cos(ang) * dist, math.sin(ang) * dist, 0))
        if math.hypot(c.x, c.y) < 0.55 or c.y > WALL_Y - 0.15:
            continue
        v, f = rock_mesh(int(rng.integers(1, 99999)))
        v = v * np.array([r, r * rng.uniform(0.6, 1.0), r * rng.uniform(0.55, 0.85)]) + np.array([c.x, c.y, r * 0.30])
        parts.append((v, f))
    v, f = merged(parts)
    ob = obj_from_arrays('Slag', v, f, col)
    ob.data.materials.append(material)
    return ob


def make_debris(col, rng):
    """Charcoal crumbs, small laterite stones and flakes of scale kicked about the floor."""
    parts, kinds = [], []
    for _ in range(520):
        ang, dist = rng.uniform(0, 2 * np.pi), 0.3 + abs(rng.normal(0, 1.3))
        c = Vector((math.cos(ang) * dist, math.sin(ang) * dist - 0.2, 0))
        if c.y > WALL_Y - 0.1 or (c - HEARTH).length < 0.55 or (c - ANVIL).length < 0.30 or abs(c.x) > 3.2:
            continue
        if abs(c.x - 0.05) < 0.30 and abs(c.y + 0.03) < 0.22:      # not under his feet
            continue
        r = rng.uniform(0.003, 0.012) * (1.6 if rng.random() < 0.12 else 1.0)
        v, f = rock_mesh(int(rng.integers(1, 99999)))
        v = v * np.array([r, r * rng.uniform(0.6, 1.0), r * rng.uniform(0.35, 0.7)])
        R = np.array(Matrix.Rotation(rng.uniform(0, 6.28), 3, 'Z'))
        parts.append(((R @ v.T).T + np.array([c.x, c.y, r * 0.25]), f))
        kinds.append(np.full(len(v), rng.random()))
    v, f = merged(parts)
    ob = obj_from_arrays('Debris', v, f, col)
    ob.data.attributes.new('kind', 'FLOAT', 'POINT').data.foreach_set('value', np.concatenate(kinds).astype(np.float32))
    g = mats.Graph('Debris')
    kind = g.node('Attribute', attribute_name='kind', attribute_type='GEOMETRY').outputs['Fac']
    col_ = g.ramp(kind, [(0.0, (0.012, 0.011, 0.010)), (0.55, (0.014, 0.012, 0.011)), (0.60, (0.11, 0.050, 0.026)), (0.85, (0.16, 0.08, 0.04)), (0.88, (0.05, 0.045, 0.042)), (1.0, (0.07, 0.06, 0.055))], 'CONSTANT')
    bsdf = g.node('BsdfPrincipled', Base_Color=col_, Roughness=0.7)
    ob.data.materials.append(g.finish(bsdf.outputs[0]))
    return ob


def make_wall(col):
    """The back wall of puddled mud, a little out of plumb and thicker at its foot."""
    n = Noise(11)
    xs, zs = np.linspace(-3.4, 3.4, 220), np.linspace(-0.05, 2.62, 110)
    X, Z = np.meshgrid(xs, zs, indexing='ij')
    p = np.stack([X, Z, np.zeros_like(X)], -1)
    Y = WALL_Y + 0.025 * n.fbm(p * 1.3, 4) + 0.008 * n.fbm(p * 7, 3) - 0.05 * np.clip(0.3 - Z, 0, None)
    # the wall's top is uneven where courses of mud were laid
    top = 2.42 + 0.06 * n.fbm(np.stack([X * 0.9, np.zeros_like(X), np.ones_like(X)], -1), 3)
    Z = np.minimum(Z, top)
    verts = np.stack([X, Y, Z], -1).reshape(-1, 3)
    ny = len(zs)
    faces = [(i * ny + j, i * ny + j + 1, (i + 1) * ny + j + 1, (i + 1) * ny + j) for i in range(len(xs) - 1) for j in range(ny - 1)]
    ob = obj_from_arrays('MudWall', verts, faces, col)
    d = np.hypot(X - HEARTH.x, (Z - 0.6) * 0.6)
    soot = np.clip(smoothstep(Z, 0.7, 2.2) * np.exp(-(d / 1.8) ** 2) * 1.3 + 0.55 * smoothstep(Z, 1.4, 2.4), 0, 1)
    ob.data.attributes.new('soot', 'FLOAT', 'POINT').data.foreach_set('value', soot.ravel().astype(np.float32))
    ob.data.materials.append(mud_material())
    sol = ob.modifiers.new('Thickness', 'SOLIDIFY')
    sol.thickness = 0.30
    sol.offset = -1
    return ob


def make_roof(col):
    """Posts, a ridge pole and rafters, and the thatch over them."""
    wood = wood_material()
    parts = []
    rng = np.random.default_rng(4)
    posts = [(-2.9, -1.75), (2.9, -1.75), (-2.9, WALL_Y - 0.05), (2.9, WALL_Y - 0.05), (0.0, WALL_Y - 0.05)]
    for x, y in posts:
        h = EAVE_FRONT if y < 0 else 2.75
        path = np.array([(x, y, -0.05), (x + rng.normal(0, 0.012), y + rng.normal(0, 0.012), h * 0.5), (x + rng.normal(0, 0.02), y, h + 0.1)])
        parts.append(sweep(path, 0.095 if y < 0 else 0.08, sides=12))
    # the wall plate and front beam, then rafters from them to the ridge
    for y, h in ((-1.75, EAVE_FRONT), (WALL_Y - 0.05, 2.75)):
        parts.append(sweep(np.array([(-3.3, y, h), (0, y, h + 0.015), (3.3, y, h)]), 0.07, sides=10))
    ridge_y = 0.35
    parts.append(sweep(np.array([(-3.4, ridge_y, RIDGE), (3.4, ridge_y, RIDGE)]), 0.075, sides=10))
    for x in np.linspace(-3.1, 3.1, 14):
        x2 = x + rng.normal(0, 0.03)
        for y, h in ((-1.95, EAVE_FRONT - 0.08), (WALL_Y + 0.15, 2.70)):
            parts.append(sweep(np.array([(x2, y, h), (x2, (y + ridge_y) / 2, (h + RIDGE) / 2 + 0.02), (x2, ridge_y, RIDGE)]), 0.038, sides=8))
    v, f = merged(parts)
    frame = obj_from_arrays('RoofFrame', v, f, col)
    frame.data.materials.append(wood)
    # thatch: two sagging planes laid over the rafters
    th = thatch_material()
    n = Noise(9)
    obs = [frame]
    for name, y0, h0 in (('ThatchFront', -2.3, EAVE_FRONT - 0.25), ('ThatchBack', WALL_Y + 0.55, 2.55)):
        us, ts = np.linspace(-3.6, 3.6, 80), np.linspace(0, 1, 30)
        U, T = np.meshgrid(us, ts, indexing='ij')
        Y = y0 + (ridge_y - y0) * T
        Z = h0 + (RIDGE + 0.06 - h0) * T + 0.06 + 0.03 * np.sin(np.pi * T) + 0.02 * n.fbm(np.stack([U, T * 3, np.zeros_like(U)], -1), 3)
        verts = np.stack([U, Y, Z], -1).reshape(-1, 3)
        nt = len(ts)
        faces = [(i * nt + j, (i + 1) * nt + j, (i + 1) * nt + j + 1, i * nt + j + 1) for i in range(len(us) - 1) for j in range(nt - 1)]
        ob = obj_from_arrays(name, verts, faces, col)
        ob.data.materials.append(th)
        sol = ob.modifiers.new('Thickness', 'SOLIDIFY')
        sol.thickness = 0.18
        obs.append(ob)
    return obs


def make_hearth(col):
    """A low clay hearth: a ring wall round a bed of charcoal, the clay pipe from the bellows let in at its side."""
    clay = clay_material('HearthClay', 0.9)
    v, f = lathe([(0.30, 0.0), (0.47, 0.0), (0.50, 0.08), (0.48, 0.30), (0.44, 0.36), (0.40, 0.37), (0.36, 0.34), (0.34, 0.22), (0.20, 0.20), (0.0, 0.19)], 64)
    v = lumpy(v, 13, 0.020, 5.0)
    ring = obj_from_arrays('Hearth', v, f, col)
    place(ring, HEARTH)
    soot_by_height(ring, -0.05, 0.30)
    ring.data.materials.append(clay)
    sub = ring.modifiers.new('Smooth', 'SUBSURF')
    sub.levels = sub.render_levels = 1

    # the bed of charcoal, heaped higher where the pipe blows into it
    rng = np.random.default_rng(31)
    parts, heat = [], []
    for _ in range(320):
        a, r = rng.uniform(0, 2 * np.pi), 0.34 * math.sqrt(rng.random())
        size = rng.uniform(0.018, 0.045)
        z = 0.20 + 0.19 * (1 - (r / 0.34) ** 2) ** 1.2 + rng.uniform(0, 0.04)
        v, f = rock_mesh(int(rng.integers(1, 99999)))
        v = v * np.array([size, size * rng.uniform(0.6, 1.0), size * rng.uniform(0.5, 0.8)])
        R = np.array(Matrix.Rotation(rng.uniform(0, 6.28), 3, Vector(rng.normal(0, 1, 3)).normalized()))
        v = (R @ v.T).T + np.array([HEARTH.x + math.cos(a) * r, HEARTH.y + math.sin(a) * r, z])
        parts.append((v, f))
        heat.append(np.full(len(v), float(np.clip(1.15 - r / 0.34 + rng.normal(0, 0.15), 0.15, 1.0))))
    v, f = merged(parts)
    coals = obj_from_arrays('Embers', v, f, col)
    # the core of the fire, white-hot under the coals, seen only through the gaps between them
    bed_v, bed_f = lathe([(0.0, 0.33), (0.12, 0.32), (0.24, 0.27), (0.31, 0.21), (0.33, 0.195)], 48)
    bed = obj_from_arrays('FireBed', bed_v + np.array([HEARTH.x, HEARTH.y, 0.0]), bed_f, col)
    g = mats.Graph('FireBed')
    nz = g.node('TexNoise', Vector=g.node('TexCoord').outputs['Object'], Scale=18, Detail=4).outputs['Fac']
    em = g.node('Emission', Color=g.mix(nz, g.node('Blackbody', Temperature=1150).outputs[0], g.node('Blackbody', Temperature=1500).outputs[0]),
                Strength=g.math('ADD', 3.0, g.math('MULTIPLY', nz, 5.0)))
    bed.data.materials.append(g.finish(em.outputs[0]))
    coals.data.attributes.new('heat', 'FLOAT', 'POINT').data.foreach_set('value', np.concatenate(heat).astype(np.float32))
    coals.data.materials.append(ember_material())
    return ring, coals


def make_bellows(col):
    """Two pot bellows behind the hearth: clay bowls with hide tops and sticks, their pipes joining in one clay tuyère."""
    clay = clay_material('BellowsClay', 0.75)
    hide = leather_material()
    wood = bpy.data.materials.get('PostWood') or wood_material()
    obs = []
    out = (Vector((HEARTH.x, HEARTH.y, 0)) - Vector((2.10, 0.95, 0))).normalized()
    side = Vector((-out.y, out.x, 0))
    for k, s in enumerate((-1, 1)):
        c = Vector((2.10, 0.95, 0)) + side * (0.22 * s)
        v, f = lathe([(0.0, 0.0), (0.16, 0.0), (0.21, 0.06), (0.22, 0.16), (0.20, 0.22), (0.19, 0.23)], 40)
        pot = obj_from_arrays(f'BellowsPot.{k}', lumpy(v, 40 + k, 0.006, 5.0), f, col)
        place(pot, c)
        soot_by_height(pot, -0.02, 0.24)
        pot.data.materials.append(clay)
        top_v, top_f = lathe([(0.0, 0.262), (0.08, 0.258), (0.16, 0.245), (0.195, 0.232)], 40)
        top = obj_from_arrays(f'BellowsHide.{k}', top_v, top_f, col)
        place(top, c)
        top.data.materials.append(hide)
        stick = obj_from_arrays(f'BellowsStick.{k}', *sweep(np.array([(0, 0, 0.26), (0.01 * s, 0.0, 0.62), (0.015 * s, -0.01, 0.92)]), 0.013, sides=8), col)
        place(stick, c)
        stick.data.materials.append(wood)
        obs += [pot, top, stick]
    # the tuyère: a tapering clay pipe into the side of the hearth
    a = Vector((2.10, 0.95, 0.08)) + out * 0.18
    b = Vector((HEARTH.x, HEARTH.y, 0.24)) - out * 0.30
    path = np.array([tuple(a.lerp(b, t)) for t in np.linspace(0, 1, 12)])
    pipe = obj_from_arrays('Tuyere', *sweep(path, np.linspace(0.075, 0.055, 12), sides=16), col)
    pipe.data.materials.append(clay)
    obs.append(pipe)
    return obs


def make_anvil(col, metal):
    """An iron anvil block let into a hardwood stump, the bar on it, a hammer and tongs beside it."""
    wood = bpy.data.materials.get('PostWood') or wood_material()
    v, f = lathe([(0.0, 0.0), (0.24, 0.0), (0.25, 0.20), (0.235, 0.42), (0.23, 0.44), (0.0, 0.445)], 36)
    stump = obj_from_arrays('AnvilStump', lumpy(v, 7, 0.012, 3.0), f, col)
    place(stump, ANVIL)
    stump.data.materials.append(wood)
    # the block: slightly tapered, its face polished by work
    w, d, h = 0.13, 0.10, 0.17
    base_z = 0.43
    vs = []
    for z, s in ((0.0, 0.92), (h * 0.85, 1.0), (h, 0.98)):
        for x, y in ((-w, -d), (w, -d), (w, d), (-w, d)):
            vs.append((x * s, y * s, base_z + z))
    vs = np.array(vs)
    faces = [(0, 3, 2, 1), (8, 9, 10, 11)]
    for r in range(2):
        for k in range(4):
            a, b = r * 4 + k, r * 4 + (k + 1) % 4
            faces.append((a, b, b + 4, a + 4))
    block = obj_from_arrays('Anvil', vs, faces, col)
    bev = block.modifiers.new('Bevel', 'BEVEL')
    bev.width = 0.008
    bev.segments = 3
    place(block, ANVIL, yaw=math.radians(-12))
    block.data.materials.append(anvil_material())
    # the bar: heated at the end over the face of the anvil, cooling toward the tongs that hold it
    s = np.linspace(0, 1, 60)
    tip = ANVIL + Vector((0.07, -0.05, base_z + h + 0.012))
    direction = Vector((math.cos(math.radians(150)), math.sin(math.radians(150)), 0))
    path = np.array([tuple(tip + direction * (0.42 * t) + Vector((0, 0, 0.0))) for t in s])
    bv, bf = sweep(path, 0.0105, sides=4)
    bar = obj_from_arrays('HotBar', bv, bf, col)
    heat = np.repeat(np.clip(1.0 - s / 0.38, 0, 1) ** 1.3, 4)
    bar.data.attributes.new('heat', 'FLOAT', 'POINT').data.foreach_set('value', heat.astype(np.float32))
    bar.data.materials.append(hot_iron_material())
    # tongs gripping the bar's cool end, their handles resting on the ground
    grip = tip + direction * 0.40
    parts = []
    for sgn in (1, -1):
        p = [grip + Vector((0, 0, 0.012 * sgn)), grip + direction * 0.05 + Vector((0, 0, 0.004 * sgn)),
             grip + direction * 0.30 + Vector((0.0, 0.0, -0.20 + 0.03 * sgn)), grip + direction * 0.52 + Vector((0, 0, -0.575 + 0.03 * sgn))]
        parts.append(sweep(np.array([tuple(q) for q in p]), 0.008, sides=6))
    v, f = merged(parts)
    tongs = obj_from_arrays('Tongs', v, f, col)
    tongs.data.materials.append(metal)
    # a heavy hammer on the stump
    hv, hf = merged([sweep(np.array([(0, 0, 0), (0.32, 0, 0.0)]), 0.017, sides=10),
                     sweep(np.array([(0.30, -0.06, 0.0), (0.30, 0.07, 0.0)]), np.array([0.030, 0.026]), sides=4)])
    hammer = obj_from_arrays('Hammer', hv, hf, col)
    hammer.matrix_world = Matrix.Translation(ANVIL + Vector((0.20, -0.32, 0.017))) @ Matrix.Rotation(math.radians(-25), 4, 'Z')
    hammer.data.materials.append(metal)
    return [stump, block, bar, tongs, hammer]


def make_quench(col):
    clay = clay_material('PotClay', 0.25)
    at = ANVIL + Vector((-0.42, -0.50, 0))
    v, f = lathe([(0.0, 0.0), (0.15, 0.0), (0.21, 0.10), (0.22, 0.22), (0.17, 0.34), (0.15, 0.37), (0.165, 0.39), (0.15, 0.40), (0.135, 0.36)], 48)
    pot = obj_from_arrays('QuenchPot', lumpy(v, 3, 0.004, 6), f, col)
    place(pot, at)
    pot.data.materials.append(clay)
    wv, wf = lathe([(0.0, 0.33), (0.155, 0.33)], 48)
    water = obj_from_arrays('QuenchWater', wv, wf, col)
    place(water, at)
    water.data.materials.append(water_material())
    return [pot, water]


def make_charcoal_heap(col):
    rng = np.random.default_rng(8)
    parts = []
    c = Vector((-1.75, 1.72, 0))
    for _ in range(420):
        a, r = rng.uniform(0, 2 * np.pi), 0.62 * math.sqrt(rng.random())
        z = 0.42 * (1 - (r / 0.62) ** 1.6) + rng.uniform(-0.02, 0.03)
        size = rng.uniform(0.025, 0.06)
        v, f = rock_mesh(int(rng.integers(1, 99999)))
        v = v * np.array([size, size * rng.uniform(0.5, 0.9), size * rng.uniform(0.4, 0.7)])
        R = np.array(Matrix.Rotation(rng.uniform(0, 6.28), 3, Vector(rng.normal(0, 1, 3)).normalized()))
        parts.append(((R @ v.T).T + np.array([c.x + math.cos(a) * r, c.y + math.sin(a) * r * 0.8, max(z, 0.0)]), f))
    v, f = merged(parts)
    ob = obj_from_arrays('CharcoalHeap', v, f, col)
    g = mats.Graph('Charcoal')
    n = g.node('TexNoise', Vector=g.node('TexCoord').outputs['Object'], Scale=80, Detail=4).outputs['Fac']
    bsdf = g.node('BsdfPrincipled', Base_Color=(0.014, 0.013, 0.013, 1), Roughness=g.math('ADD', 0.35, g.math('MULTIPLY', n, 0.4)), Normal=g.bump(n, 0.6, 0.002))
    bsdf.inputs['Specular IOR Level'].default_value = 0.6
    ob.data.materials.append(g.finish(bsdf.outputs[0]))
    return ob


def make_wall_tools(col, metal):
    """Tools on pegs along the back wall: hoe blades, a machete, tongs and hammers."""
    from iron import tool_parts
    rng = np.random.default_rng(14)
    wood = bpy.data.materials.get('PostWood') or wood_material()
    parts, pegs = [], []
    for x, kind, s in ((-1.45, 'hoe', 3.0), (-1.15, 'hoe', 2.6), (-0.82, 'tongs', 4.2), (-0.50, 'ada', 4.6), (-0.15, 'hammer', 3.4),
                       (0.18, 'spear', 3.2), (0.48, 'tongs', 3.8), (0.78, 'hoe', 2.8)):
        top = np.array([x, WALL_Y - 0.035, 1.62 + rng.normal(0, 0.03)])
        tv, tf = merged(tool_parts(kind, rng))
        tv = tv * s
        R = np.array(Matrix.Rotation(rng.normal(0, 0.05), 3, 'Y'))
        tv = (R @ tv.T).T
        tv[:, 1] -= tv[:, 1].max() + 0.004           # flat against the wall
        parts.append((tv + top, tf))
        pegs.append(sweep(np.array([top + (0, 0.04, 0.012), top + (0, -0.05, 0.015)]), 0.008, sides=6))
    v, f = merged(parts)
    tools = obj_from_arrays('WallTools', v, f, col)
    tools.data.materials.append(metal)
    v, f = merged(pegs)
    peg = obj_from_arrays('WallPegs', v, f, col)
    peg.data.materials.append(wood)
    return [tools, peg]


def make_sparks(col, count=46):
    """Sparks thrown up from the fire, each drawn as the streak it leaves in a short exposure."""
    rng = np.random.default_rng(77)
    parts, fade = [], []
    for _ in range(count):
        start = HEARTH + Vector((rng.normal(0, 0.10), rng.normal(0, 0.10), 0.34))
        v0 = Vector((rng.normal(0, 0.55), rng.normal(0, 0.55), rng.uniform(1.0, 2.8)))
        t0 = rng.uniform(0.0, 0.5)
        dt = rng.uniform(0.02, 0.06)
        pts = []
        for t in np.linspace(t0, t0 + dt, 6):
            pts.append(tuple(start + v0 * t + Vector((0, 0, -4.9 * t * t)) + Vector((0, 0, 0.2 * t))))
        v, f = sweep(np.array(pts), np.linspace(0.0011, 0.0005, 6), sides=4)
        parts.append((v, f))
        fade.append(np.full(len(v), float(np.clip(1.15 - t0 * 1.6, 0.25, 1.0))))
    v, f = merged(parts)
    ob = obj_from_arrays('Sparks', v, f, col)
    ob.data.attributes.new('fade', 'FLOAT', 'POINT').data.foreach_set('value', np.concatenate(fade).astype(np.float32))
    ob.data.materials.append(spark_material())
    ob.visible_shadow = False
    return ob


def make_smoke(col, density=0.018):
    """A thin haze of smoke under the roof for the firelight to show in."""
    g = mats.Graph('Smoke')
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=0.9, Detail=3).outputs['Fac']
    xyz = g.node('SeparateXYZ', Vector=obj).outputs
    z = xyz[2]
    dens = g.math('MULTIPLY', g.math('ADD', 0.5, n), g.math('ADD', 0.4, g.math('MULTIPLY', z, 0.35)))
    # right over the fire the smoke has risen away: clear it there, or the lamps standing in for the fire light it white
    d2 = g.math('ADD', g.math('POWER', g.math('SUBTRACT', xyz[0], HEARTH.x), 2.0),
                g.math('ADD', g.math('POWER', g.math('SUBTRACT', xyz[1], HEARTH.y), 2.0), g.math('POWER', g.math('SUBTRACT', z, 0.45), 2.0)))
    clear = g.math('MULTIPLY', g.math('SUBTRACT', g.math('SQRT', d2), 0.35), 1.6, clamp=True)
    dens = g.math('MULTIPLY', dens, clear)
    vol = g.node('VolumePrincipled', Density=g.math('MULTIPLY', dens, density), Anisotropy=0.45)
    vol.inputs['Color'].default_value = (0.62, 0.58, 0.54, 1)
    g.t.links.new(vol.outputs[0], g.out.inputs['Volume'])
    v = np.array([(-3.0, -1.7, 0.02), (3.0, -1.7, 0.02), (3.0, WALL_Y - 0.08, 0.02), (-3.0, WALL_Y - 0.08, 0.02)])
    verts = np.vstack([v, v + np.array([0, 0, 2.6])])
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = obj_from_arrays('Smoke', verts, faces, col, smooth=False)
    ob.data.materials.append(g.mat)
    return ob


def make_night():
    """Night outside the shed: a deep blue sky, a little brighter low down."""
    sc = bpy.context.scene
    world = bpy.data.worlds.get('Night') or bpy.data.worlds.new('Night')
    sc.world = world
    world.use_nodes = True
    t = world.node_tree
    t.nodes.clear()
    out = t.nodes.new('ShaderNodeOutputWorld')
    bg = t.nodes.new('ShaderNodeBackground')
    tc = t.nodes.new('ShaderNodeTexCoord')
    sep = t.nodes.new('ShaderNodeSeparateXYZ')
    ramp = t.nodes.new('ShaderNodeValToRGB')
    t.links.new(tc.outputs['Generated'], sep.inputs[0])
    t.links.new(sep.outputs[2], ramp.inputs[0])
    ramp.color_ramp.elements[0].position = 0.5
    ramp.color_ramp.elements[0].color = (0.010, 0.014, 0.030, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (0.0025, 0.0035, 0.009, 1)
    t.links.new(ramp.outputs[0], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 1.0
    t.links.new(bg.outputs[0], out.inputs['Surface'])
    return world


def build(col_far, col_near):
    metal = bpy.data.materials.get('Iron') or iron.iron_material()
    rng = np.random.default_rng(3)
    make_floor(col_near)
    make_slag(col_near, rng, slag_material())
    make_debris(col_near, rng)
    make_wall(col_far)
    make_roof(col_far)
    ring, coals = make_hearth(col_near)
    make_bellows(col_near)
    make_anvil(col_near, metal)
    make_quench(col_near)
    make_charcoal_heap(col_far)
    make_wall_tools(col_far, metal)
    make_sparks(col_near)
    make_smoke(col_far)
    make_night()
    return coals
