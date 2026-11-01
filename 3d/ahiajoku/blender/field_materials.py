"""Cycles materials for the yams, the barn and the field."""
from materials import Graph


def yam_skin():
    """Dry fibrous bark, fissured across the tuber, dusted with red earth."""
    g = Graph('YamSkin')
    obj = g.node('TexCoord').outputs['Object']
    warped = g.node('TexNoise', Vector=obj, Scale=30, Detail=3).outputs['Color']
    warp = g.node('VectorMath', operation='ADD', Vector=obj)
    g.link(g.node('VectorMath', operation='SCALE', Vector=warped, Scale=0.016).outputs[0], warp.inputs[1])
    # scales run round the tuber, so squash the cells along its length (object Z)
    pos = g.node('Mapping', Vector=warp.outputs[0], Scale=(1, 1, 1.9)).outputs[0]
    plates = g.node('TexVoronoi', Vector=pos, Scale=250, feature='DISTANCE_TO_EDGE', Randomness=1.0).outputs['Distance']
    cracks = g.math('POWER', g.math('MINIMUM', g.math('DIVIDE', plates, 0.10), 1.0), 0.7)
    fibre = g.node('TexNoise', Vector=g.node('Mapping', Vector=obj, Scale=(1, 1, 7)).outputs[0], Scale=420, Detail=6, Roughness=0.62).outputs['Fac']
    big = g.node('TexNoise', Vector=pos, Scale=34, Detail=6, Roughness=0.62).outputs['Fac']
    bark = g.ramp(big, [(0.30, (0.052, 0.030, 0.018)), (0.50, (0.105, 0.066, 0.040)), (0.68, (0.175, 0.118, 0.074))])
    bark = g.mix(g.math('MULTIPLY', fibre, 0.5), bark, (0.040, 0.024, 0.015))
    bark = g.mix(g.math('MULTIPLY', g.math('SUBTRACT', 1.0, cracks), 0.72), bark, (0.018, 0.011, 0.007))
    soil = g.ramp(g.node('TexNoise', Vector=pos, Scale=58, Detail=7, Roughness=0.72).outputs['Fac'], [(0.50, (0, 0, 0)), (0.66, (1, 1, 1))])
    bark = g.mix(g.math('MULTIPLY', soil, 0.62), bark, (0.205, 0.088, 0.046))
    h = g.math('ADD', g.math('MULTIPLY', cracks, 0.6), g.math('MULTIPLY', fibre, 0.7))
    normal = g.bump(h, 1.0, 0.0018)
    bsdf = g.node('BsdfPrincipled', Base_Color=bark, Roughness=0.88, Normal=normal)
    bsdf.inputs['Specular IOR Level'].default_value = 0.26
    return g.finish(bsdf.outputs[0])


def yam_flesh():
    """The chopped head: white flesh gone cream and tan where it has dried."""
    g = Graph('YamFlesh')
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=120, Detail=6, Roughness=0.62).outputs['Fac']
    col = g.ramp(n, [(0.32, (0.30, 0.20, 0.11)), (0.5, (0.52, 0.42, 0.28)), (0.68, (0.68, 0.61, 0.48))])
    normal = g.bump(g.node('TexNoise', Vector=obj, Scale=340, Detail=6).outputs['Fac'], 0.7, 0.0009)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.62, Normal=normal,
                  Subsurface_Weight=0.5, Subsurface_Scale=0.003)
    return g.finish(bsdf.outputs[0])


def rootlet():
    g = Graph('Rootlet')
    bsdf = g.node('BsdfPrincipled', Base_Color=(0.075, 0.046, 0.029, 1), Roughness=0.8)
    return g.finish(bsdf.outputs[0])


def cane():
    """Split cane for the basket, each strand a shade apart."""
    g = Graph('Cane')
    pick = g.node('Attribute', attribute_name='strand', attribute_type='GEOMETRY').outputs['Fac']
    stretched = g.node('Mapping', Vector=g.node('TexCoord').outputs['Object'], Scale=(420, 420, 420)).outputs[0]
    grain = g.node('TexNoise', Vector=stretched, Scale=1, Detail=6, Roughness=0.6).outputs['Fac']
    col = g.ramp(pick, [(0.0, (0.235, 0.135, 0.058)), (0.5, (0.35, 0.215, 0.098)), (1.0, (0.46, 0.31, 0.15))])
    col = g.mix(g.math('MULTIPLY', grain, 0.45), col, (0.09, 0.05, 0.022))
    normal = g.bump(grain, 0.5, 0.0005)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.55, Normal=normal)
    return g.finish(bsdf.outputs[0])


def raffia():
    g = Graph('Raffia')
    bsdf = g.node('BsdfPrincipled', Base_Color=(0.52, 0.40, 0.22, 1), Roughness=0.7)
    return g.finish(bsdf.outputs[0])


def bark_pole():
    g = Graph('Pole')
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=(90), Detail=6, Roughness=0.65).outputs['Fac']
    col = g.ramp(n, [(0.32, (0.030, 0.021, 0.016)), (0.5, (0.085, 0.060, 0.042)), (0.7, (0.16, 0.12, 0.085))])
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.85, Normal=g.bump(n, 1.0, 0.003))
    return g.finish(bsdf.outputs[0])


def soil(clods=True):
    """Red laterite earth, dry on top, damp in the hollows."""
    g = Graph('Soil' if clods else 'SoilFar')
    obj = g.node('TexCoord').outputs['Object']
    big = g.node('TexNoise', Vector=obj, Scale=2.4, Detail=6, Roughness=0.6).outputs['Fac']
    clod = g.node('TexVoronoi', Vector=obj, Scale=46, Randomness=1.0).outputs['Distance']
    grit = g.node('TexVoronoi', Vector=obj, Scale=520, Randomness=1.0).outputs['Distance']
    fine = g.node('TexNoise', Vector=obj, Scale=210, Detail=7, Roughness=0.68).outputs['Fac']
    col = g.ramp(big, [(0.3, (0.120, 0.044, 0.021)), (0.55, (0.175, 0.068, 0.032)), (0.75, (0.235, 0.102, 0.054))])
    col = g.mix(g.math('MULTIPLY', fine, 0.62), col, (0.070, 0.028, 0.016))
    pale = g.ramp(grit, [(0.06, (1, 1, 1)), (0.12, (0, 0, 0))])
    col = g.mix(g.math('MULTIPLY', pale, 0.5), col, (0.36, 0.25, 0.17))
    h = g.math('ADD', g.math('MULTIPLY', g.math('SUBTRACT', 1, clod), 0.6), g.math('MULTIPLY', fine, 0.7))
    h = g.math('ADD', h, g.math('MULTIPLY', g.math('SUBTRACT', 1, grit), 0.4))
    normal = g.bump(h, 1.0, 0.008 if clods else 0.014)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.92, Normal=normal)
    bsdf.inputs['Specular IOR Level'].default_value = 0.22
    return g.finish(bsdf.outputs[0])


def stone():
    g = Graph('Stone')
    obj = g.node('TexCoord').outputs['Object']
    n = g.node('TexNoise', Vector=obj, Scale=380, Detail=6, Roughness=0.62).outputs['Fac']
    pick = g.node('ObjectInfo').outputs['Random']
    tint = g.ramp(pick, [(0.0, (0.15, 0.085, 0.055)), (0.6, (0.26, 0.15, 0.09)), (1.0, (0.40, 0.31, 0.24))])
    col = g.mix(g.math('MULTIPLY', n, 0.6), tint, (0.05, 0.03, 0.02))
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.8, Normal=g.bump(n, 1.0, 0.0015))
    return g.finish(bsdf.outputs[0])


def dry_leaf():
    g = Graph('DryLeaf')
    pick = g.node('ObjectInfo').outputs['Random']
    tint = g.ramp(pick, [(0.0, (0.060, 0.032, 0.016)), (0.6, (0.125, 0.070, 0.030)), (1.0, (0.20, 0.125, 0.055))])
    bsdf = g.node('BsdfPrincipled', Base_Color=tint, Roughness=0.62)
    trans = g.node('BsdfTranslucent', Color=tint)
    both = g.node('MixShader', Fac=0.3)
    g.link(bsdf.outputs[0], both.inputs[1])
    g.link(trans.outputs[0], both.inputs[2])
    return g.finish(both.outputs[0])


def leaf(name='Leaf', colour=(0.030, 0.085, 0.018)):
    g = Graph(name)
    pick = g.node('ObjectInfo').outputs['Random']
    col = g.mix(g.math('MULTIPLY', pick, 0.5), colour, (0.11, 0.135, 0.022))
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.42)
    trans = g.node('BsdfTranslucent', Color=col)
    both = g.node('MixShader', Fac=0.3)
    g.link(bsdf.outputs[0], both.inputs[1])
    g.link(trans.outputs[0], both.inputs[2])
    return g.finish(both.outputs[0])


def moon():
    """The full moon's face, emissive, from a painted map."""
    g = Graph('Moon')
    uv = g.node('TexCoord').outputs['UV']
    col = g.image('moon.png', uv, 'sRGB', extension='CLIP').outputs['Color']
    glow = g.node('Emission', Color=col, Strength=1.9)
    return g.finish(glow.outputs[0])
