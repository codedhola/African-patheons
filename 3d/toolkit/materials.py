"""Cycles materials for a figure and her regalia, and the Graph helper that builds them."""
import bpy

from common import TEX


class Graph:
    """Thin wrapper so a node tree reads as a few lines instead of dozens."""

    def __init__(self, name):
        self.mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        self.mat.use_nodes = True
        self.t = self.mat.node_tree
        self.t.nodes.clear()
        self.out = self.t.nodes.new('ShaderNodeOutputMaterial')
        self.mat.cycles.displacement_method = 'BUMP'

    def node(self, kind, **inputs):
        n = self.t.nodes.new('ShaderNode' + kind)
        for key, value in inputs.items():
            if key in n.bl_rna.properties and key not in n.inputs:
                setattr(n, key, value)
            elif hasattr(value, 'is_linked') or isinstance(value, bpy.types.NodeSocket):
                self.t.links.new(value, n.inputs[key.replace('_', ' ')])
            else:
                n.inputs[key.replace('_', ' ')].default_value = value
        return n

    def link(self, a, b):
        self.t.links.new(a, b)

    def math(self, op, a, b=None, clamp=False):
        n = self.t.nodes.new('ShaderNodeMath')
        n.operation = op
        n.use_clamp = clamp
        for sock, v in zip(n.inputs, (a, b)):
            if v is None:
                continue
            if isinstance(v, bpy.types.NodeSocket):
                self.t.links.new(v, sock)
            else:
                sock.default_value = v
        return n.outputs[0]

    def mix(self, fac, a, b, blend='MIX'):
        n = self.t.nodes.new('ShaderNodeMix')
        n.data_type = 'RGBA'
        n.blend_type = blend
        # the node keeps float, vector and colour sockets under the same names: 0 factor, 6 A, 7 B, out 2
        for sock, v in ((n.inputs[0], fac), (n.inputs[6], a), (n.inputs[7], b)):
            if isinstance(v, bpy.types.NodeSocket):
                self.t.links.new(v, sock)
            elif sock.type == 'RGBA':
                v = (v, v, v) if isinstance(v, (int, float)) else v
                sock.default_value = (*v[:3], 1)
            else:
                sock.default_value = v
        return n.outputs[2]

    def ramp(self, fac, stops, interp='LINEAR'):
        n = self.t.nodes.new('ShaderNodeValToRGB')
        cr = n.color_ramp
        cr.interpolation = interp
        while len(cr.elements) < len(stops):
            cr.elements.new(0)
        for el, (pos, col) in zip(cr.elements, stops):
            el.position = pos
            el.color = (*col[:3], 1)
        self.t.links.new(fac, n.inputs['Fac'])
        return n.outputs['Color']

    def image(self, name, vector, colorspace='Non-Color', interpolation='Linear', extension='REPEAT'):
        n = self.t.nodes.new('ShaderNodeTexImage')
        path = TEX / name
        n.image = bpy.data.images.load(str(path), check_existing=True)
        n.image.colorspace_settings.name = colorspace
        n.interpolation = interpolation
        n.extension = extension
        self.t.links.new(vector, n.inputs['Vector'])
        return n

    def bump(self, height, strength=1.0, distance=0.001, normal=None):
        n = self.t.nodes.new('ShaderNodeBump')
        n.inputs['Strength'].default_value = strength
        n.inputs['Distance'].default_value = distance
        self.t.links.new(height, n.inputs['Height'])
        if normal is not None:
            self.t.links.new(normal, n.inputs['Normal'])
        return n.outputs['Normal']

    def finish(self, bsdf):
        self.t.links.new(bsdf, self.out.inputs['Surface'])
        return self.mat


def akwete(name='Akwete', binding=False, u_scale=1.0, v_offset=0.0, maps='akwete',
           edge_colours=((0.05, 0.075, 0.19), (0.82, 0.76, 0.62), (0.50, 0.10, 0.075))):
    """Warp-faced cotton ground with rayon floats. Cloth maps come from akwete.py, or any set named like them."""
    g = Graph(name)
    uv = g.node('TexCoord').outputs['UV']
    if u_scale != 1.0 or v_offset:
        uv = g.node('Mapping', Vector=uv, Scale=(u_scale, 1, 1), Location=(0, v_offset, 0)).outputs[0]
    col = g.image(f'{maps}_color.png', uv, 'sRGB').outputs['Color']
    height = g.image(f'{maps}_height.png', uv).outputs['Color']
    floats = g.image(f'{maps}_float.png', uv).outputs['Color']

    # one plain-weave repeat of eight threads every 5.2 mm
    fine = g.node('Mapping', Vector=uv, Scale=(116, 221, 1)).outputs[0]
    weave = g.image('weave_height.png', fine).outputs['Color']
    show_weave = g.math('SUBTRACT', 1.0, floats)
    thread = g.math('MULTIPLY', weave, show_weave)
    shaded = g.mix(g.math('MULTIPLY', thread, 0.14), col, (0.34, 0.31, 0.25), 'MULTIPLY')

    h = g.math('ADD', g.math('MULTIPLY', height, 0.75), g.math('MULTIPLY', thread, 0.20))
    normal = g.bump(h, 1.0, 0.0011)
    rough = g.math('ADD', 0.84, g.math('MULTIPLY', floats, -0.40))
    spec = g.math('ADD', 0.30, g.math('MULTIPLY', floats, 0.25))

    base = shaded
    if binding:
        # a narrow indigo binding on the neck, cuffs and hem, with one red line of stitching beside it
        edge = g.node('Attribute', attribute_name='edge_dist', attribute_type='GEOMETRY').outputs['Fac']
        c1, c2, c3 = edge_colours
        band = g.ramp(edge, [(0.0, c1), (0.109, c1), (0.112, c2), (0.128, c2), (0.131, c3), (0.150, c3), (0.153, (1, 1, 1)), (1.0, (1, 1, 1))], 'CONSTANT')
        over = g.math('LESS_THAN', edge, 0.153)
        base = g.mix(over, shaded, band)
        rough = g.mix(over, rough, 0.8)
    bsdf = g.node('BsdfPrincipled', Base_Color=base, Roughness=rough, Normal=normal)
    bsdf.inputs['Sheen Weight'].default_value = 0.55
    bsdf.inputs['Sheen Tint'].default_value = (0.95, 0.88, 0.72, 1)
    bsdf.inputs['Sheen Roughness'].default_value = 0.45
    g.link(spec, bsdf.inputs['Specular IOR Level'])
    # a little of the light comes through a single layer of cotton
    translucent = g.node('BsdfTranslucent', Color=base, Normal=normal)
    both = g.node('MixShader', Fac=0.10)
    g.link(bsdf.outputs[0], both.inputs[1])
    g.link(translucent.outputs[0], both.inputs[2])
    return g.finish(both.outputs[0])


def skin():
    """Deep brown skin. Regions come from two vertex colour layers set by dress.skin_masks."""
    g = Graph('Skin')
    tc = g.node('TexCoord')
    obj = tc.outputs['Object']
    m1 = g.node('Attribute', attribute_name='mask_a', attribute_type='GEOMETRY').outputs['Color']
    m2 = g.node('Attribute', attribute_name='mask_b', attribute_type='GEOMETRY').outputs['Color']
    a = g.node('SeparateColor', Color=m1).outputs
    b = g.node('SeparateColor', Color=m2).outputs
    lips, palm, crease = a[0], a[1], a[2]
    scalp = g.node('Attribute', attribute_name='mask_a', attribute_type='GEOMETRY').outputs['Alpha']
    nails, lids, flush = b[0], b[1], b[2]

    blotch = g.node('TexNoise', Vector=obj, Scale=24, Detail=6, Roughness=0.55).outputs['Fac']
    mottling = g.node('TexNoise', Vector=obj, Scale=230, Detail=4, Roughness=0.6).outputs['Fac']
    tone = g.ramp(blotch, [(0.30, (0.078, 0.037, 0.021)), (0.50, (0.104, 0.050, 0.028)), (0.70, (0.126, 0.058, 0.031))])
    tone = g.mix(g.math('MULTIPLY', mottling, 0.20), tone, (0.052, 0.024, 0.015), 'MIX')
    tone = g.mix(flush, tone, (0.150, 0.056, 0.036))
    tone = g.mix(crease, tone, (0.040, 0.019, 0.012))
    tone = g.mix(lids, tone, (0.056, 0.027, 0.020))
    tone = g.mix(palm, tone, (0.300, 0.150, 0.100))
    lipnoise = g.node('TexNoise', Vector=obj, Scale=420, Detail=3).outputs['Fac']
    lip = g.ramp(lipnoise, [(0.3, (0.080, 0.027, 0.024)), (0.7, (0.135, 0.048, 0.044))])
    tone = g.mix(lips, tone, lip)
    tone = g.mix(nails, tone, (0.46, 0.27, 0.20))
    tone = g.mix(scalp, tone, (0.016, 0.011, 0.009))        # close-cut hair shadows the scalp
    paint = g.node('Attribute', attribute_name='mask_b', attribute_type='GEOMETRY').outputs['Alpha']
    tone = g.mix(paint, tone, (0.010, 0.008, 0.008))        # eye paint, where a figure wears it

    # pores, then fine creases across them, both in metres on the posed body
    pore = g.node('TexVoronoi', Vector=obj, Scale=1500, feature='F1', distance='EUCLIDEAN').outputs['Distance']
    fine = g.node('TexNoise', Vector=obj, Scale=1050, Detail=5, Roughness=0.62).outputs['Fac']
    broad = g.node('TexNoise', Vector=obj, Scale=170, Detail=4, Roughness=0.5).outputs['Fac']
    h = g.math('ADD', g.math('MULTIPLY', pore, 0.20), g.math('MULTIPLY', fine, 0.42))
    n1 = g.bump(h, 0.72, 0.00046)
    normal = g.bump(broad, 0.20, 0.0022, n1)

    rough = g.ramp(g.node('TexNoise', Vector=obj, Scale=60, Detail=3).outputs['Fac'], [(0.3, (0.47, 0.47, 0.47)), (0.7, (0.60, 0.60, 0.60))])
    rough = g.mix(lips, rough, 0.46)
    rough = g.mix(nails, rough, 0.24)
    bsdf = g.node('BsdfPrincipled', Base_Color=tone, Roughness=rough, Normal=normal,
                  Subsurface_Weight=1.0, Subsurface_Scale=0.0065)
    bsdf.subsurface_method = 'RANDOM_WALK'
    bsdf.inputs['Subsurface Radius'].default_value = (1.0, 0.36, 0.20)
    bsdf.inputs['Subsurface Anisotropy'].default_value = 0.7
    bsdf.inputs['IOR'].default_value = 1.42
    bsdf.inputs['Specular IOR Level'].default_value = 0.36
    return g.finish(bsdf.outputs[0])


def eye():
    g = Graph('Eye')
    uv = g.node('TexCoord').outputs['UV']
    col = g.image('eye_color.png', uv, 'sRGB', extension='EXTEND').outputs['Color']
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.5)
    bsdf.inputs['Coat Weight'].default_value = 1.0
    bsdf.inputs['Coat Roughness'].default_value = 0.035
    bsdf.inputs['Coat IOR'].default_value = 1.38
    return g.finish(bsdf.outputs[0])


def hair(name='Hair', colour=(0.008, 0.006, 0.005, 1)):
    g = Graph(name)
    bsdf = g.node('BsdfPrincipled', Base_Color=colour, Roughness=0.46)
    return g.finish(bsdf.outputs[0])


def coral():
    """Polished coral, each bead tinted by its own random value."""
    g = Graph('Coral')
    obj = g.node('TexCoord').outputs['Object']
    pick = g.node('Attribute', attribute_name='bead', attribute_type='GEOMETRY').outputs['Fac']
    base = g.ramp(pick, [(0.0, (0.40, 0.050, 0.026)), (0.5, (0.54, 0.075, 0.036)), (1.0, (0.66, 0.125, 0.060))])
    pale = g.ramp(g.node('TexWave', Vector=obj, Scale=260, Distortion=4, Detail=3).outputs['Fac'], [(0.40, (0, 0, 0)), (0.75, (1, 1, 1))])
    col = g.mix(g.math('MULTIPLY', pale, 0.12), base, (0.80, 0.34, 0.22))
    grain = g.node('TexNoise', Vector=obj, Scale=700, Detail=4).outputs['Fac']
    normal = g.bump(grain, 0.10, 0.00025)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.24, Normal=normal,
                  Subsurface_Weight=0.45, Subsurface_Scale=0.0022)
    bsdf.inputs['Subsurface Radius'].default_value = (1.0, 0.22, 0.12)
    return g.finish(bsdf.outputs[0])


def ivory():
    g = Graph('Ivory')
    tc = g.node('TexCoord').outputs['Object']
    grain = g.node('TexWave', Vector=tc, Scale=120, Distortion=7, Detail=5, wave_type='RINGS').outputs['Fac']
    age = g.node('TexNoise', Vector=tc, Scale=38, Detail=5).outputs['Fac']
    col = g.ramp(age, [(0.32, (0.74, 0.62, 0.42)), (0.66, (0.86, 0.77, 0.60))])
    col = g.mix(g.math('MULTIPLY', grain, 0.14), col, (0.52, 0.37, 0.20))
    normal = g.bump(grain, 0.10, 0.0002)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.30, Normal=normal,
                  Subsurface_Weight=0.8, Subsurface_Scale=0.004)
    return g.finish(bsdf.outputs[0])
