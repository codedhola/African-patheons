"""Mbe, the tortoise: at his feet, for the alụsị of bargains and of the tortoise.

Wikipedia calls Ekwensu the alụsị of the tortoise, and his gallery figure keeps one at his feet.
It is drawn as a hinge-back tortoise of West African forests and farmland, about 22 cm long,
walking: a domed shell of scutes ringed with growth lines, a scaly head and neck, and stout legs.
Its form is this study's. Local frame: head toward +X, standing on z = 0.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

import materials as mats
from common import TEX, edge_adjacency, obj_from_arrays
from dress import smoothstep
from procedural import Noise

A, B = 0.112, 0.078            # half length and half width of the shell at its rim
RIM_Z, DOME = 0.040, 0.082
K = 1 / 0.57


def paint_shell(n=640):
    """Colour and groove height of the carapace, seen from above, in a square map from -1 to 1."""
    y, x = np.mgrid[0:n, 0:n] / (n - 1) * 2 - 1
    r = np.hypot(x, y)
    ang = np.arctan2(y, x)
    lines = np.full(x.shape, 9.0)
    # marginal ring, cut into scutes round the edge
    lines = np.minimum(lines, np.abs(r - 0.80))
    marg = np.abs(((ang / (2 * np.pi) * 24) % 1) - 0.5) / 24 * 2 * np.pi * r
    lines = np.where(r > 0.80, np.minimum(lines, np.abs(marg - np.pi / 24 * r)), lines)
    # vertebral column down the middle, costal scutes either side, all cut across
    inner = r < 0.80
    lines = np.where(inner, np.minimum(lines, np.abs(np.abs(y) - (0.24 - 0.05 * x ** 2))), lines)
    for cx in (-0.50, -0.17, 0.17, 0.50):
        lines = np.where(inner, np.minimum(lines, np.abs(x - cx - 0.06 * np.sign(y) * np.abs(y))), lines)
    groove = smoothstep(lines, 0.022, 0.006)
    # growth rings inside each scute, following its edges in
    rings = 0.5 + 0.5 * np.sin(lines * 95)
    rings *= smoothstep(lines, 0.02, 0.05)
    # each scute dark at the edges, amber toward its centre
    centre = smoothstep(lines, 0.03, 0.16)
    noise = Noise(12)
    blot = noise.fbm(np.stack([x * 6, y * 6, np.zeros_like(x)], -1), 3)
    dark = np.array([0.075, 0.050, 0.028])
    amber = np.array([0.48, 0.33, 0.13])
    col = dark[None, None] * (1 - centre[..., None]) + amber[None, None] * centre[..., None]
    col = col * (1 - 0.18 * rings[..., None]) * (1 + 0.15 * blot[..., None])
    col = col * (1 - 0.75 * groove[..., None])
    height = 0.6 - 0.5 * groove + 0.08 * rings
    from weave import save, save_gray
    save(TEX / 'tortoise_shell.png', np.dstack([np.clip(col, 0, 1), np.ones(x.shape)]).astype(np.float32))
    save_gray(TEX / 'tortoise_height.png', np.clip(height, 0, 1).astype(np.float32))


def shell_material():
    g = mats.Graph('TortoiseShell')
    uv = g.node('TexCoord').outputs['UV']
    col = g.image('tortoise_shell.png', uv, 'sRGB', extension='EXTEND').outputs['Color']
    h = g.image('tortoise_height.png', uv, extension='EXTEND').outputs['Color']
    fine = g.node('TexNoise', Vector=g.node('TexCoord').outputs['Object'], Scale=300, Detail=4).outputs['Fac']
    normal = g.bump(g.math('ADD', h, g.math('MULTIPLY', fine, 0.08)), 0.9, 0.0016)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=g.math('ADD', 0.38, g.math('MULTIPLY', fine, 0.2)), Normal=normal)
    bsdf.inputs['Coat Weight'].default_value = 0.10
    bsdf.inputs['Coat Roughness'].default_value = 0.2
    return g.finish(bsdf.outputs[0])


def skin_material():
    """Scaly grey-brown skin: big plates on the forelegs, fine scales elsewhere."""
    g = mats.Graph('TortoiseSkin')
    obj = g.node('TexCoord').outputs['Object']
    scales = g.node('TexVoronoi', Vector=obj, Scale=260, feature='DISTANCE_TO_EDGE').outputs['Distance']
    plates = g.node('TexVoronoi', Vector=obj, Scale=110, feature='DISTANCE_TO_EDGE').outputs['Distance']
    big = g.node('Attribute', attribute_name='plates', attribute_type='GEOMETRY').outputs['Fac']
    edge = g.mix(big, scales, plates)
    n = g.node('TexNoise', Vector=obj, Scale=60, Detail=4).outputs['Fac']
    col = g.ramp(n, [(0.3, (0.032, 0.025, 0.018)), (0.7, (0.095, 0.072, 0.045))])
    col = g.mix(g.math('MULTIPLY', g.math('LESS_THAN', edge, 0.05), 0.6), col, (0.03, 0.025, 0.02))
    normal = g.bump(g.math('MULTIPLY', g.math('SUBTRACT', 1.0, g.math('MULTIPLY', edge, 6.0), clamp=True), -1.0), 0.7, 0.0008)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.62, Normal=normal)
    return g.finish(bsdf.outputs[0])


def make_shell(col):
    """The carapace, a domed ellipse highest a little behind the middle, and the flat plastron under it."""
    rows, cols = 70, 160
    t = np.linspace(0, 1, rows)
    a = np.linspace(0, 2 * np.pi, cols, endpoint=False)
    T, Ang = np.meshgrid(t, a, indexing='ij')
    rho = 1 - T                                      # 1 at the rim, 0 on top
    x = A * rho * np.cos(Ang)
    y = B * rho * np.sin(Ang)
    hump = 1 + 0.10 * np.cos(Ang) * rho              # a little higher behind
    z = RIM_Z + DOME * np.clip(1 - rho ** 2.2, 0, 1) ** 0.62 / hump
    # the marginal scutes flare out at the back and over the legs
    z += 0.006 * smoothstep(rho, 0.86, 1.0) * (0.5 - 0.5 * np.cos(Ang))
    verts = np.stack([x, y, z], -1).reshape(-1, 3)
    faces = [(i * cols + j, i * cols + (j + 1) % cols, (i + 1) * cols + (j + 1) % cols, (i + 1) * cols + j) for i in range(rows - 1) for j in range(cols)]
    uv = np.stack([x.ravel() / A * 0.5 + 0.5, y.ravel() / B * 0.5 + 0.5], 1)
    # close the top, and add the plastron as a slightly domed plate under the rim
    top = len(verts)
    verts = np.vstack([verts, [[0, 0, float(z[-1].mean())]]])
    uv = np.vstack([uv, [[0.5, 0.5]]])
    faces += [((rows - 1) * cols + j, (rows - 1) * cols + (j + 1) % cols, top) for j in range(cols)]
    shell = obj_from_arrays('Carapace', verts, faces, col, uv=uv)
    shell.data.materials.append(shell_material())
    sol = shell.modifiers.new('Thickness', 'SOLIDIFY')
    sol.thickness = 0.004
    sol.offset = -1
    pa = np.linspace(0, 2 * np.pi, cols, endpoint=False)
    rim = np.stack([A * 0.94 * np.cos(pa), B * 0.92 * np.sin(pa), np.full(cols, RIM_Z - 0.010)], 1)
    centre = np.array([[0.0, 0.0, RIM_Z - 0.016]])
    pv = np.vstack([rim, centre])
    pf = [(j, cols, (j + 1) % cols) for j in range(cols)]
    plastron = obj_from_arrays('Plastron', pv, pf, col)
    g = mats.Graph('Plastron')
    bsdf = g.node('BsdfPrincipled', Base_Color=(0.36, 0.26, 0.11, 1), Roughness=0.5)
    plastron.data.materials.append(g.finish(bsdf.outputs[0]))
    return shell, plastron


def make_body(col):
    """Head, neck, legs and tail as metaballs, joined into one scaly skin."""
    mb = bpy.data.metaballs.new('TortoiseMeta')
    mb.resolution = mb.render_resolution = 0.0028
    mb.threshold = 0.6
    ob = bpy.data.objects.new('TortoiseMeta', mb)
    col.objects.link(ob)

    def capsule(a, b, r):
        a, b = Vector(a), Vector(b)
        e = mb.elements.new(type='CAPSULE')
        e.co = (a + b) / 2
        e.radius = r * K
        e.size_x = (b - a).length / 2
        e.rotation = Vector((1, 0, 0)).rotation_difference(b - a)
        e.stiffness = 2.0

    def blob(c, radii, stiff=2.0):
        e = mb.elements.new(type='ELLIPSOID')
        e.co = c
        e.radius = 1.0
        e.size_x, e.size_y, e.size_z = (q * K for q in radii)
        e.stiffness = stiff

    capsule((0.078, 0.0, 0.040), (0.142, 0.0, 0.060), 0.0125)         # neck, reaching out
    blob((0.162, 0.0, 0.063), (0.022, 0.0145, 0.0135))                # head
    blob((0.181, 0.0, 0.058), (0.010, 0.0100, 0.0090), 2.6)           # beak
    for s in (1, -1):
        capsule((0.062, 0.052 * s, 0.034), (0.098, 0.085 * s, 0.010), 0.014)     # forelegs, splayed forward
        blob((0.103, 0.090 * s, 0.008), (0.016, 0.014, 0.008))                   # forefeet
        capsule((-0.070, 0.050 * s, 0.032), (-0.082, 0.070 * s, 0.008), 0.017)   # hind legs, elephantine
        blob((-0.084, 0.072 * s, 0.007), (0.016, 0.016, 0.007))
    capsule((-0.100, 0.0, 0.034), (-0.124, 0.0, 0.024), 0.008)        # tail
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    bpy.data.metaballs.remove(mb)
    body = bpy.data.objects.new('TortoiseBody', me)
    col.objects.link(body)
    co = np.array([v.co for v in me.vertices])
    co[:, 2] = np.maximum(co[:, 2], 0.0)
    me.vertices.foreach_set('co', co.astype(np.float32).ravel())
    me.update()
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    plates = smoothstep(co[:, 0], 0.07, 0.09) * smoothstep(co[:, 2], 0.03, 0.015) * smoothstep(np.abs(co[:, 1]), 0.04, 0.06)
    me.attributes.new('plates', 'FLOAT', 'POINT').data.foreach_set('value', plates.astype(np.float32))
    me.materials.append(skin_material())
    # eyes: two small dark beads in the head
    g = mats.Graph('TortoiseEye')
    bsdf = g.node('BsdfPrincipled', Base_Color=(0.02, 0.012, 0.006, 1), Roughness=0.15)
    bsdf.inputs['Coat Weight'].default_value = 1.0
    from dress import sphere
    eyes = []
    for s in (1, -1):
        v, f, _ = sphere(0.0042, 10, 14)
        e = obj_from_arrays(f'TortoiseEye.{s}', v + np.array([0.170, 0.0122 * s, 0.067]), f, col)
        e.data.materials.append(g.mat)
        eyes.append(e)
    return body, eyes


def make(col, at=(0.34, -0.40, 0.0), yaw=-140.0, scale=1.0):
    paint_shell()
    shell, plastron = make_shell(col)
    body, eyes = make_body(col)
    m = Matrix.Translation(Vector(at)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z') @ Matrix.Diagonal((scale, scale, scale, 1))
    for ob in [shell, plastron, body] + eyes:
        ob.matrix_world = m
    print('tortoise', len(body.data.vertices), 'skin verts', flush=True)
    return shell
