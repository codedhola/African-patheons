"""A calabash of oranges set down on the sand. Orange is among her offerings in Wikipedia's list."""
import math

import numpy as np

import materials as mats
from brass import lathe, smooth_profile
from common import obj_from_arrays
from procedural import Noise


def calabash_material():
    """Dried gourd, polished by handling, with a burned band of chevrons and dots."""
    g = mats.Graph('Calabash')
    coord = g.node('TexCoord')
    obj = coord.outputs['Object']
    sep = g.node('SeparateXYZ', Vector=obj).outputs
    nor = g.node('SeparateXYZ', Vector=coord.outputs['Normal']).outputs
    n = g.node('TexNoise', Vector=obj, Scale=40, Detail=6, Roughness=0.6).outputs['Fac']
    col = g.ramp(n, [(0.3, (0.27, 0.13, 0.042)), (0.55, (0.44, 0.235, 0.075)), (0.74, (0.58, 0.345, 0.13))])
    # the burned band sits by height, the chevrons come from the angle round the bowl
    angle = g.math('ARCTAN2', sep[1], sep[0])
    zig = g.math('PINGPONG', g.math('MULTIPLY', angle, 2.546), 1.0)
    band_z = g.math('DIVIDE', g.math('SUBTRACT', sep[2], 0.070), 0.036)
    line = g.math('ABSOLUTE', g.math('SUBTRACT', band_z, zig))
    burn = g.math('LESS_THAN', line, 0.13)
    rim_a = g.math('LESS_THAN', g.math('ABSOLUTE', g.math('SUBTRACT', sep[2], 0.116)), 0.0030)
    rim_b = g.math('LESS_THAN', g.math('ABSOLUTE', g.math('SUBTRACT', sep[2], 0.056)), 0.0030)
    mark = g.math('MAXIMUM', burn, g.math('MAXIMUM', rim_a, rim_b))
    # the outside only: the wall faces away from the bowl's axis
    outside = g.math('ADD', g.math('MULTIPLY', nor[0], sep[0]), g.math('MULTIPLY', nor[1], sep[1]))
    mark = g.math('MULTIPLY', mark, g.math('GREATER_THAN', outside, 0.0))
    col = g.mix(mark, col, (0.030, 0.014, 0.008))
    normal = g.bump(g.math('MULTIPLY', mark, -1.0), 0.5, 0.0006)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.36, Normal=normal)
    return g.finish(bsdf.outputs[0])


def orange_material():
    g = mats.Graph('Orange')
    obj = g.node('TexCoord').outputs['Object']
    pores = g.node('TexVoronoi', Vector=obj, Scale=520, Randomness=1.0).outputs['Distance']
    blotch = g.node('TexNoise', Vector=obj, Scale=32, Detail=4).outputs['Fac']
    pick = g.node('ObjectInfo').outputs['Random']
    tint = g.ramp(pick, [(0.0, (0.82, 0.25, 0.012)), (1.0, (0.90, 0.40, 0.018))])
    col = g.mix(g.math('MULTIPLY', blotch, 0.35), tint, (0.62, 0.42, 0.03))
    normal = g.bump(pores, 0.6, 0.0006)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.34, Normal=normal,
                  Subsurface_Weight=0.5, Subsurface_Scale=0.006)
    return g.finish(bsdf.outputs[0])


def orange_mesh(seed, radius=0.039):
    n = Noise(seed)
    rows, cols = 26, 36
    verts = []
    for i in range(rows):
        a = math.pi * (i + 0.5) / rows
        for j in range(cols):
            b = 2 * math.pi * j / cols
            d = np.array([math.sin(a) * math.cos(b), math.sin(a) * math.sin(b), math.cos(a)])
            r = radius * (1 + 0.02 * float(n(d * 2 + seed))) * (1 - 0.05 * d[2] ** 2)
            verts.append(d * r)
    faces = [(i * cols + j, i * cols + (j + 1) % cols, (i + 1) * cols + (j + 1) % cols, (i + 1) * cols + j) for i in range(rows - 1) for j in range(cols)]
    faces.append(tuple(range(cols))[::-1])
    faces.append(tuple(range((rows - 1) * cols, rows * cols)))
    return np.array(verts, np.float32), faces


def make(col, at):
    """The bowl and its fruit. Returns the bowl, with the fruit parented to it."""
    body = smooth_profile([(0.0, 0.0), (0.040, 0.0), (0.085, 0.010), (0.118, 0.040), (0.131, 0.078), (0.124, 0.112), (0.112, 0.128),
                           (0.106, 0.127), (0.116, 0.110), (0.121, 0.078), (0.108, 0.044), (0.078, 0.020), (0.0, 0.012)], 160)
    v, f = lathe(body, 72)
    bowl = obj_from_arrays('Calabash', v, f, col)
    bowl.data.materials.append(calabash_material())
    bowl.location = at
    fruit = orange_material()
    rng = np.random.default_rng(13)
    # five, her number: four in the bowl and one resting on them
    spots = [(0.058, 20, 0.058), (0.058, 110, 0.058), (0.058, 200, 0.058), (0.058, 290, 0.058), (0.0, 0, 0.112)]
    for k, (r, a, z) in enumerate(spots):
        vv, ff = orange_mesh(70 + k)
        ob = obj_from_arrays(f'OrangeFruit.{k}', vv, ff, col)
        ob.data.materials.append(fruit)
        ob.parent = bowl
        ob.location = (r * math.cos(math.radians(a)) + rng.normal(0, 0.0015), r * math.sin(math.radians(a)) + rng.normal(0, 0.0015), z)
        ob.rotation_euler = tuple(rng.uniform(0, 6.28, 3))
    return bowl
