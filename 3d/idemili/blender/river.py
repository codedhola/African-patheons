"""The river: the Idemili at dawn, mist on the water and the bush close along its banks.

Idemili is both a river and a goddess (Idemili North local government), and her gallery figure
stands in the water with the python rising beside her. This stretch of the river is invented:
a quiet reach between banks of raffia palms, oil palms and forest trees, the sun just up behind
her and mist still lying on the water.

She stands at the origin facing -Y, in the shallows by the near bank, the water over her
ankles. The river runs along X behind her; the near bank is in front of her, toward the camera.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

import materials as mats
from common import obj_from_arrays
from dress import smoothstep
from procedural import Noise, add_curves, merged, sweep

WATER_Z = 0.105
SUN = Vector((-0.34, 0.93, 0.10)).normalized()      # toward the sun: just risen over the far bank, behind her and a little to her right
HAZE = (0.60, 0.62, 0.62)


def bed_height(x, y):
    """The bed and banks: the near bank behind the camera, her shallows, the channel, the far bank under the trees."""
    n = Noise(9)
    p = np.stack([x, y, np.zeros_like(x)], -1)
    h = np.where(y < -1.9, WATER_Z + 0.02 + 0.05 * (-1.9 - y), 0.0)
    h = np.where((y >= -1.9) & (y < -1.1), (WATER_Z + 0.02) * (-1.1 - y) / 0.8, h)
    deep = smoothstep(y, 0.9, 6.0) * -0.85 + smoothstep(y, 11.0, 16.0) * 1.10
    h = np.where(y >= 0.9, deep, h)
    h = h + 0.010 * n.fbm(p * 1.4, 3) + 0.004 * n.fbm(p * 9.0, 2)
    keep = smoothstep(np.hypot(x, y), 0.70, 1.20)          # level where she stands and the python lies
    return h * keep


def grid_mesh(name, xs, ys, height, col):
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    Z = height(X, Y)
    verts = np.stack([X, Y, Z], -1).reshape(-1, 3)
    ny = len(ys)
    faces = [(i * ny + j, (i + 1) * ny + j, (i + 1) * ny + j + 1, i * ny + j + 1) for i in range(len(xs) - 1) for j in range(ny - 1)]
    return obj_from_arrays(name, verts, faces, col), X, Y, Z


def haze(g, colour, distance=900.0):
    """Blend toward the misty sky with distance."""
    dist = g.node('CameraData').outputs['View Distance']
    f = g.math('SUBTRACT', 1.0, g.math('EXPONENT', g.math('DIVIDE', dist, -distance)))
    return g.mix(f, colour, HAZE)


def mud_material():
    """River mud and silt, dark where wet, with leaf litter and grass up the near bank."""
    g = mats.Graph('RiverMud')
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=2.5, Detail=6).outputs['Fac']
    fine = g.node('TexNoise', Vector=obj, Scale=120, Detail=6, Roughness=0.7).outputs['Fac']
    grains = g.node('TexVoronoi', Vector=obj, Scale=700, Randomness=1.0).outputs['Distance']
    wet = g.node('Attribute', attribute_name='wet', attribute_type='GEOMETRY').outputs['Fac']
    grass = g.node('Attribute', attribute_name='grass', attribute_type='GEOMETRY').outputs['Fac']
    col = g.ramp(n, [(0.3, (0.10, 0.075, 0.050)), (0.7, (0.17, 0.13, 0.085))])
    col = g.mix(g.math('MULTIPLY', fine, 0.35), col, (0.10, 0.08, 0.055))
    col = g.mix(wet, col, (0.075, 0.060, 0.045))
    blades = g.node('TexNoise', Vector=g.node('Mapping', Vector=obj, Scale=(40.0, 40.0, 4.0)).outputs[0], Scale=20, Detail=4).outputs['Fac']
    col = g.mix(grass, col, g.ramp(blades, [(0.3, (0.020, 0.045, 0.010)), (0.7, (0.075, 0.11, 0.030))]))
    normal = g.bump(g.math('ADD', g.math('MULTIPLY', fine, 0.6), g.math('ADD', g.math('MULTIPLY', grains, 0.4), g.math('MULTIPLY', g.math('MULTIPLY', blades, grass), 2.0))), 0.5, 0.0015)
    bsdf = g.node('BsdfPrincipled', Base_Color=haze(g, col), Roughness=g.mix(wet, 0.85, 0.30), Normal=normal)
    return g.finish(bsdf.outputs[0])


def water_material():
    """River water: still and glassy in the shallows, a dark green-brown that deepens with depth below."""
    g = mats.Graph('RiverWater')
    obj = g.node('TexCoord').outputs['Object']
    flow = g.node('Mapping', Vector=obj, Scale=(0.5, 1.4, 1.0)).outputs[0]
    waves = g.node('TexNoise', Vector=flow, Scale=5.0, Detail=6, Roughness=0.6).outputs['Fac']
    small = g.node('TexNoise', Vector=g.node('Mapping', Vector=obj, Scale=(1.0, 2.5, 1.0)).outputs[0], Scale=28, Detail=3).outputs['Fac']
    rings = g.node('Attribute', attribute_name='rings', attribute_type='GEOMETRY').outputs['Fac']
    h = g.math('ADD', g.math('MULTIPLY', waves, 0.7), g.math('MULTIPLY', small, 0.35))
    # at dawn the river lies nearly still; nearest her only the rings from her ankles and the python break it
    xy = g.node('SeparateXYZ', Vector=obj).outputs
    near = g.math('SQRT', g.math('ADD', g.math('POWER', xy[0], 2.0), g.math('POWER', g.math('ADD', xy[1], 0.4), 2.0)))
    calm = g.math('ADD', 0.10, g.math('MULTIPLY', g.math('MULTIPLY', g.math('SUBTRACT', near, 1.0), 0.30, clamp=True), 0.55))
    h = g.math('ADD', g.math('MULTIPLY', h, calm), g.math('MULTIPLY', rings, 0.5))
    bsdf = g.node('BsdfPrincipled', Base_Color=(1, 1, 1, 1), Roughness=0.045, Normal=g.bump(h, 1.0, 0.012))
    bsdf.inputs['Transmission Weight'].default_value = 1.0
    bsdf.inputs['IOR'].default_value = 1.333
    # sunlight reaches the bed through the surface: shadow rays pass it, as the caustics it makes would average out
    shadow = g.node('LightPath').outputs['Is Shadow Ray']
    clear = g.node('BsdfTransparent')
    surface = g.node('MixShader', Fac=shadow)
    g.link(bsdf.outputs[0], surface.inputs[1])
    g.link(clear.outputs[0], surface.inputs[2])
    absorb = g.t.nodes.new('ShaderNodeVolumeAbsorption')
    absorb.inputs['Color'].default_value = (0.58, 0.70, 0.55, 1)
    absorb.inputs['Density'].default_value = 1.6
    g.t.links.new(absorb.outputs[0], g.out.inputs['Volume'])
    return g.finish(surface.outputs[0])


def foliage_material(name='Foliage', low=(0.010, 0.032, 0.008), high=(0.060, 0.120, 0.022)):
    g = mats.Graph(name)
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=3.0, Detail=6).outputs['Fac']
    leafy = g.node('TexVoronoi', Vector=obj, Scale=9.0, Randomness=1.0).outputs['Distance']
    col = g.ramp(n, [(0.3, low), (0.7, high)])
    col = g.mix(g.math('MULTIPLY', leafy, 0.8), col, (0.005, 0.015, 0.004))
    bsdf = g.node('BsdfPrincipled', Base_Color=haze(g, col), Roughness=0.7, Normal=g.bump(leafy, 1.0, 0.3))
    translucent = g.node('BsdfTranslucent', Color=haze(g, col))
    both = g.node('MixShader', Fac=0.25)
    g.link(bsdf.outputs[0], both.inputs[1])
    g.link(translucent.outputs[0], both.inputs[2])
    return g.finish(both.outputs[0])


def bark_material():
    g = mats.Graph('Bark')
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=g.node('Mapping', Vector=obj, Scale=(8, 8, 1)).outputs[0], Scale=4, Detail=5).outputs['Fac']
    col = g.ramp(n, [(0.3, (0.05, 0.04, 0.03)), (0.7, (0.14, 0.11, 0.08))])
    bsdf = g.node('BsdfPrincipled', Base_Color=haze(g, col), Roughness=0.85, Normal=g.bump(n, 0.6, 0.02))
    return g.finish(bsdf.outputs[0])


def mist_material():
    """Low mist over the water: thickest at the surface, thinning within a few metres, broken into drifts."""
    g = mats.Graph('Mist')
    obj = g.node('TexCoord').outputs['Object']
    z = g.node('SeparateXYZ', Vector=obj).outputs[2]
    drift = g.node('TexNoise', Vector=g.node('Mapping', Vector=obj, Scale=(0.18, 0.35, 0.9)).outputs[0], Scale=1.0, Detail=4, Roughness=0.6).outputs['Fac']
    low = g.math('EXPONENT', g.math('MULTIPLY', z, -0.9))
    density = g.math('MULTIPLY', g.math('MULTIPLY', low, g.math('ADD', 0.25, g.math('MULTIPLY', g.math('SUBTRACT', drift, 0.30), 2.0, clamp=True))), 0.085)
    vol = g.t.nodes.new('ShaderNodeVolumePrincipled')
    vol.inputs['Color'].default_value = (0.92, 0.92, 0.90, 1)
    vol.inputs['Anisotropy'].default_value = 0.62
    g.t.links.new(density, vol.inputs['Density'])
    g.t.links.new(vol.outputs[0], g.out.inputs['Volume'])
    return g.mat


# ----- the parts ----------------------------------------------------------

def make_bed(col):
    xs = np.concatenate([np.linspace(-90, -8, 60), np.linspace(-8, 8, 330)[1:-1], np.linspace(8, 90, 60)])
    ys = np.concatenate([np.linspace(-12, -3, 40), np.linspace(-3, 6, 300)[1:-1], np.linspace(6, 60, 90)])
    ob, X, Y, Z = grid_mesh('RiverBed', xs, ys, bed_height, col)
    wet = np.clip((WATER_Z + 0.03 - Z) / 0.03, 0, 1)
    ob.data.attributes.new('wet', 'FLOAT', 'POINT').data.foreach_set('value', wet.ravel().astype(np.float32))
    grass = smoothstep(Y, 14.5, 18.0) * smoothstep(Z, WATER_Z + 0.02, WATER_Z + 0.10) + smoothstep(-Y, 2.0, 2.9)
    ob.data.attributes.new('grass', 'FLOAT', 'POINT').data.foreach_set('value', np.clip(grass, 0, 1).ravel().astype(np.float32))
    ob.data.materials.append(mud_material())
    return ob


def make_water(col, sources):
    """A closed slab of water from the surface down past the bed, rings spreading from her ankles and the python."""
    xs = np.linspace(-90, 90, 361)
    ys = np.linspace(-1.85, 60, 300)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    top = np.stack([X, Y, np.full_like(X, WATER_Z)], -1).reshape(-1, 3)
    rings = np.zeros(X.shape)
    for fx, fy, size in sources:
        r = np.hypot(X - fx, Y - fy)
        rings += np.sin(r * 110) * np.exp(-r / (0.12 * size)) * smoothstep(r, 0.035 * size, 0.06 * size)
    nx, ny = len(xs), len(ys)
    faces = [(i * ny + j, (i + 1) * ny + j, (i + 1) * ny + j + 1, i * ny + j + 1) for i in range(nx - 1) for j in range(ny - 1)]
    loop = [i * ny for i in range(nx)] + [(nx - 1) * ny + j for j in range(1, ny)] + \
           [i * ny + ny - 1 for i in range(nx - 2, -1, -1)] + [j for j in range(ny - 2, 0, -1)]
    base = len(top)
    ring = top[loop] * np.array([1, 1, 0]) + np.array([0, 0, -1.6])
    verts = np.vstack([top, ring])
    m = len(loop)
    for k in range(m):
        a, b = loop[k], loop[(k + 1) % m]
        faces.append((b, a, base + k, base + (k + 1) % m))
    faces.append(tuple(base + k for k in range(m - 1, -1, -1)))
    ob = obj_from_arrays('RiverWater', verts, faces, col, smooth=False)
    ob.data.attributes.new('rings', 'FLOAT', 'POINT').data.foreach_set('value', np.concatenate([rings.ravel(), np.zeros(m)]).astype(np.float32))
    ob.data.materials.append(water_material())
    return ob


def make_mist(col):
    """A box of mist over the river behind her, from a couple of metres back to beyond the far bank."""
    x0, x1, y0, y1, z0, z1 = -70.0, 70.0, 2.2, 45.0, WATER_Z, 7.0
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = obj_from_arrays('Mist', v, f, col, smooth=False)
    ob.data.materials.append(mist_material())
    ob.visible_shadow = False
    return ob


def crown_mesh(seed, radius, leaves=9000):
    """A crown of leaves: small cards scattered through a few lumps of the crown's volume, thickest at its skin."""
    rng = np.random.default_rng(seed)
    lumps = [rng.normal(0, radius * 0.32, 3) * np.array([1, 1, 0.55]) for _ in range(6)]
    verts, faces = [], []
    for k in range(leaves):
        c = lumps[k % len(lumps)]
        d = rng.normal(0, 1, 3)
        d /= np.linalg.norm(d)
        p = c + d * radius * 0.62 * rng.uniform(0.55, 1.0) ** 0.35 * np.array([1, 1, 0.75])
        size = rng.uniform(0.14, 0.26)
        a = rng.normal(0, 1, 3)
        a -= a.dot(d) * d
        a /= np.linalg.norm(a)
        b = np.cross(d, a)
        base = len(verts)
        verts += [p - a * size * 0.5, p + b * size * 0.35, p + a * size * 0.5, p - b * size * 0.35]
        faces.append((base, base + 1, base + 2, base + 3))
    return np.array(verts), faces


def palm_mesh(seed, height, fronds=14, frond_len=(4.5, 6.0), rise=(-0.1, 0.7), leaflet=0.95):
    """A palm: a trunk and a crown of arching fronds, each a rachis with leaflets.

    With a tall trunk and fronds of five metres it is an oil palm; with a short trunk and fronds
    twice as long, rising steeply before they arch over, it is a raffia palm of the swamps.
    """
    rng = np.random.default_rng(seed)
    lean = rng.normal(0, 0.06, 2)
    t = np.linspace(0, 1, 16)
    trunk = np.stack([lean[0] * height * t ** 1.5, lean[1] * height * t ** 1.5, height * t], 1)
    parts = [sweep(trunk, np.linspace(0.32, 0.24, 16), sides=10)]
    top = trunk[-1]
    leaves = []
    for k in range(fronds):
        az = 2 * math.pi * k / fronds + rng.normal(0, 0.12)
        up = rng.uniform(*rise)
        L = rng.uniform(*frond_len)
        s = np.linspace(0, 1, 22)
        out = np.array([math.cos(az), math.sin(az), 0])
        path = top + out[None] * (L * s)[:, None] + np.array([0, 0, 1.0])[None] * (L * (up * s - 0.55 * s ** 2))[:, None]
        side = np.cross(out, (0, 0, 1.0))
        for i in range(2, 21):
            for sgn in (1, -1):
                a = path[i]
                b = a + side * sgn * leaflet * (1 - s[i]) ** 0.4 + np.array([0, 0, -0.42 * leaflet]) + out * 0.30
                leaves.append(np.array([a, b, b + out * 0.16, a + out * 0.16]))
        parts.append(sweep(path, 0.05, sides=4))
    fv = np.concatenate(leaves)
    ff = [(4 * i, 4 * i + 1, 4 * i + 2, 4 * i + 3) for i in range(len(leaves))]
    return merged(parts), (fv, ff)


def make_trees(col, rng):
    """Raffia palms along the far bank, oil palms and forest trees behind them, and bush on the near bank."""
    bark, leaves = bark_material(), foliage_material()
    palm_leaves = foliage_material('PalmLeaves', (0.016, 0.042, 0.010), (0.075, 0.135, 0.028))
    protos = []
    for seed in range(4):
        v, f = crown_mesh(seed + 2, rng.uniform(3.6, 5.6))
        crown = obj_from_arrays(f'CrownProto.{seed}', v, f, col)
        crown.data.materials.append(leaves)
        th = rng.uniform(3.0, 5.5)
        tv, tf = sweep(np.array([(0, 0, -0.5), (0.3, 0.1, th * 0.6), (0.2, -0.2, th)]), np.array([0.34, 0.22, 0.16]), sides=10)
        trunk = obj_from_arrays(f'TrunkProto.{seed}', tv, tf, col)
        trunk.data.materials.append(bark)
        protos.append(('tree', crown, trunk, th))
    for seed in range(3):
        (tv, tf), (fv, ff) = palm_mesh(seed + 20, rng.uniform(9, 14))
        trunk = obj_from_arrays(f'PalmTrunkProto.{seed}', tv, tf, col)
        trunk.data.materials.append(bark)
        fr = obj_from_arrays(f'PalmFrondProto.{seed}', fv, ff, col)
        fr.data.materials.append(palm_leaves)
        protos.append(('palm', fr, trunk, 0.0))
    raffia = []
    for seed in range(3):
        (tv, tf), (fv, ff) = palm_mesh(seed + 60, rng.uniform(1.2, 2.4), fronds=20, frond_len=(3.6, 5.0), rise=(1.3, 1.9), leaflet=0.75)
        trunk = obj_from_arrays(f'RaffiaTrunkProto.{seed}', tv, tf, col)
        trunk.data.materials.append(bark)
        fr = obj_from_arrays(f'RaffiaFrondProto.{seed}', fv, ff, col)
        fr.data.materials.append(palm_leaves)
        raffia.append(('palm', fr, trunk, 0.0))
    shrubs = []
    for seed in range(3):
        v, f = crown_mesh(seed + 40, rng.uniform(0.9, 1.5), leaves=2600)
        shrub = obj_from_arrays(f'ShrubProto.{seed}', v, f, col)
        shrub.data.materials.append(leaves)
        shrubs.append(shrub)
    placed = 0

    def put(kind, a, b, th, x, y, s):
        z = float(bed_height(np.array([x]), np.array([y]))[0]) if y < 60 else 1.0
        for src in (a, b):
            ob = bpy.data.objects.new(src.name.replace('Proto', ''), src.data)
            col.objects.link(ob)
            ob.matrix_world = Matrix.Translation((x, y, z + (th if (kind == 'tree' and src is a) else 0))) @ Matrix.Rotation(rng.uniform(0, 6.28), 4, 'Z') @ Matrix.Diagonal((s, s, s, 1))

    # the raffia palms crowd the water's edge on the far bank
    for _ in range(70):
        x, y = rng.uniform(-90, 90), rng.uniform(17.5, 24.0)
        if abs(x) < 6.0:                    # the sun comes up over the bank straight behind her: no palm in its way
            continue
        kind, a, b, th = raffia[int(rng.integers(0, 3))]
        put(kind, a, b, th, x, y, rng.uniform(0.8, 1.2))
        placed += 1
    # bush along the far bank's foot
    for _ in range(160):
        x, y = rng.uniform(-120, 120), rng.uniform(15.0, 26.0)
        ob = bpy.data.objects.new('Shrub', shrubs[int(rng.integers(0, 3))].data)
        col.objects.link(ob)
        s = rng.uniform(0.7, 1.5)
        z = float(bed_height(np.array([x]), np.array([y]))[0])
        ob.matrix_world = Matrix.Translation((x, y, z + 0.6 * s)) @ Matrix.Rotation(rng.uniform(0, 6.28), 4, 'Z') @ Matrix.Diagonal((s, s, s * 0.8, 1))
    # forest and oil palms rising behind, and a few trees on the near bank behind the camera
    trees = protos
    for _ in range(320):
        x = rng.uniform(-170, 170)
        y = 22 + rng.exponential(26) if rng.random() < 0.92 else rng.uniform(-30, -8)
        if y > 170:
            continue
        if abs(x) < 6 and y < 0:
            continue
        kind, a, b, th = trees[int(rng.integers(0, len(trees)))]
        put(kind, a, b, th, x, y, rng.uniform(0.8, 1.35))
        placed += 1
    for kind, a, b, th in protos + raffia:
        for ob in (a, b):
            bpy.data.objects.remove(ob)
    for ob in shrubs:
        bpy.data.objects.remove(ob)
    return placed


def make_far_land(col):
    """The land behind the far bank, rising gently under the forest."""
    n = Noise(41)

    def h(X, Y):
        p = np.stack([X * 0.01, Y * 0.01, np.zeros_like(X)], -1)
        return 1.0 + 4.0 * smoothstep(Y, 60, 400) + 2.5 * n.fbm(p, 4)
    ob, X, Y, Z = grid_mesh('FarLand', np.linspace(-700, 700, 120), np.linspace(55, 700, 80), h, col)
    g = mats.Graph('FarLand')
    obj = g.node('TexCoord').outputs['Object']
    nz = g.node('TexNoise', Vector=obj, Scale=0.05, Detail=6).outputs['Fac']
    colr = g.ramp(nz, [(0.35, (0.025, 0.05, 0.012)), (0.65, (0.08, 0.10, 0.035))])
    bsdf = g.node('BsdfPrincipled', Base_Color=haze(g, colr), Roughness=0.9)
    ob.data.materials.append(g.finish(bsdf.outputs[0]))
    return ob


def make_reeds(col, rng):
    """Grass and reeds along the near bank's edge, short of the camera."""
    strands = []
    for _ in range(2400):
        x = rng.uniform(-9, 9)
        y = rng.uniform(-2.9, -1.6)
        if abs(x) < 1.7 and (y > -2.25 or rng.random() < 0.6):       # open water in front of her; only the bank at the camera's feet is grown up
            continue
        base = np.array([x, y, float(bed_height(np.array([x]), np.array([y]))[0])])
        L = rng.uniform(0.25, 0.8) if abs(x) > 1.2 else rng.uniform(0.08, 0.22)      # short and sparse in front of her
        bend = rng.normal(0, 0.25, 2)
        s = np.linspace(0, 1, 6)
        strands.append(base + np.stack([bend[0] * s ** 2 * L, bend[1] * s ** 2 * L, s * L], 1))
    g = mats.Graph('Reed')
    bsdf = g.node('BsdfPrincipled', Base_Color=(0.09, 0.11, 0.035, 1), Roughness=0.6)
    return add_curves('Reeds', np.array(strands, np.float32), 0.0016, 0.0003, col, g.finish(bsdf.outputs[0]))


def make_sky(sun=SUN):
    """A pale dawn sky from Blender's physical sky model, hazy with the river's damp; its sun is put out and a lamp stands for it."""
    sc = bpy.context.scene
    world = bpy.data.worlds.get('Dawn') or bpy.data.worlds.new('Dawn')
    sc.world = world
    world.use_nodes = True
    t = world.node_tree
    t.nodes.clear()
    out = t.nodes.new('ShaderNodeOutputWorld')
    bg = t.nodes.new('ShaderNodeBackground')
    sky = t.nodes.new('ShaderNodeTexSky')
    sky.sky_type = 'NISHITA'
    sky.sun_disc = False
    sky.sun_elevation = math.asin(sun.z)
    sky.sun_rotation = math.atan2(sun.x, -sun.y) % (2 * math.pi)
    sky.air_density = 1.0
    sky.dust_density = 4.0
    t.links.new(sky.outputs[0], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 0.30
    t.links.new(bg.outputs[0], out.inputs['Surface'])
    return world


def build(far, near, feet, rise):
    rng = np.random.default_rng(13)
    make_bed(near)
    make_water(near, [(fx, fy, 1.0) for fx, fy in feet] + [(rise[0], rise[1], 1.4)])
    make_reeds(near, rng)
    make_mist(far)
    make_far_land(far)
    print('trees', make_trees(far, rng), flush=True)
    make_sky()
