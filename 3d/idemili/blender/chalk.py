"""Nzu: white chalk lines on her face.

Nzu, calabash chalk or kaolin, is the sacred white chalk of the Igbo: offered at shrines, tied
to purity and the ancestors, and worn on the forehead and round the eyes by priests and
diviners (Basu and Chika-Kanu 2020). Her gallery figure wears a line down the middle of her
forehead and a short stroke across each cheek, and they are drawn so here, as if with a finger:
dry, a little broken, thinning at the ends.

The chalk is a thin film laid over the face as it renders, cut from the posed body at its render
smoothing and lifted a fraction of a millimetre off the skin. Where the strokes fall is set in
metres from the midpoint between her eyes, in the head's own frame.
"""
import bpy
import numpy as np

import dress
import materials as mats
from common import obj_from_arrays
from procedural import Noise

# start, end and width, in metres: x to her left, z up, seen from in front
STROKES = (
    ((0.0, 0.078), (0.0, 0.031), 0.0052),          # down the middle of the forehead, stopping above the brows
    ((0.027, -0.019), (0.049, -0.041), 0.0047),     # down and out across each cheek
    ((-0.027, -0.019), (-0.049, -0.041), 0.0047),
)
LIFT = 0.00035


def segment(p, a, b):
    a, b = np.asarray(a), np.asarray(b)
    ab = b - a
    t = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1), t


def face_as_rendered(body):
    """The posed body's vertices, normals and faces at its render subdivision, with nothing masked."""
    sub = body.modifiers.get('Smooth')
    mask = body.modifiers.get('Hide under cloth')
    saved = (sub.levels if sub else None, mask.show_viewport if mask else None)
    if sub:
        sub.levels = sub.render_levels
    if mask:
        mask.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    n = len(me.vertices)
    co = np.zeros(n * 3)
    nor = np.zeros(n * 3)
    me.vertices.foreach_get('co', co)
    me.vertices.foreach_get('normal', nor)
    polys = [tuple(p.vertices) for p in me.polygons]
    mw = np.array(ev.matrix_world)
    ev.to_mesh_clear()
    if sub:
        sub.levels = saved[0]
    if mask:
        mask.show_viewport = saved[1]
    co = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
    nor = nor.reshape(-1, 3) @ mw[:3, :3].T
    nor /= np.linalg.norm(nor, axis=1, keepdims=True)
    return co, nor, polys


def chalk_material():
    """Dry kaolin: matte white, powdery, thinner where the finger dragged."""
    g = mats.Graph('Nzu')
    obj = g.node('TexCoord').outputs['Object']
    cover = g.node('Attribute', attribute_name='chalk', attribute_type='GEOMETRY').outputs['Fac']
    powder = g.node('TexNoise', Vector=obj, Scale=2600, Detail=3, Roughness=0.7).outputs['Fac']
    grain = g.node('TexVoronoi', Vector=obj, Scale=5200, Randomness=1.0).outputs['Distance']
    col = g.ramp(powder, [(0.3, (0.70, 0.68, 0.63)), (0.7, (0.86, 0.84, 0.79))])
    alpha = g.math('MULTIPLY', cover, g.math('ADD', 0.55, g.math('MULTIPLY', powder, 0.7)), clamp=True)
    bsdf = g.node('BsdfPrincipled', Base_Color=col, Roughness=0.96, Alpha=alpha,
                  Normal=g.bump(g.math('ADD', powder, g.math('MULTIPLY', grain, 0.6)), 0.5, 0.00015))
    bsdf.inputs['Specular IOR Level'].default_value = 0.2
    return g.finish(bsdf.outputs[0])


def make(body, rig, col):
    co, nor, polys = face_as_rendered(body)
    M = np.array(dress.head_matrix(rig))
    Minv = np.linalg.inv(M)
    rest = co @ Minv[:3, :3].T + Minv[:3, 3]
    info = eval(body['eyes'])
    e = (np.array(info['L']['centre']) + np.array(info['R']['centre'])) / 2
    rel = rest - e
    face = (rel[:, 1] < 0.040) & (np.abs(rel[:, 0]) < 0.075) & (rel[:, 2] > -0.075) & (rel[:, 2] < 0.110)
    p = rel[:, [0, 2]]
    noise = Noise(53)
    rng = np.random.default_rng(53)
    cover = np.zeros(len(co))
    for k, (a, b, width) in enumerate(STROKES):
        d, t = segment(p, a, b)
        # a finger's stroke: full in the middle, thinning to its ends, and wavering a little along its length
        w = width * (0.45 + 0.55 * np.sin(np.pi * np.clip(t * 0.94 + 0.03, 0, 1)) ** 0.6)
        w *= 1 + 0.12 * noise(np.stack([t * 6 + k * 3.1, np.zeros_like(t), np.zeros_like(t)], 1))
        stroke = np.clip((w - d) / 0.0007 + 0.5, 0, 1)
        dry = np.clip(0.70 + 0.55 * noise.fbm(rel * 700 + k * 11.0, 3), 0, 1)
        cover = np.maximum(cover, stroke * dry * rng.uniform(0.86, 1.0))
    cover *= face
    keep = [f for f in polys if cover[list(f)].max() > 0.02]
    used = sorted({i for f in keep for i in f})
    remap = {old: new for new, old in enumerate(used)}
    verts = co[used] + nor[used] * LIFT
    ob = obj_from_arrays('Nzu', verts, [tuple(remap[i] for i in f) for f in keep], col)
    ob.data.attributes.new('chalk', 'FLOAT', 'POINT').data.foreach_set('value', cover[used].astype(np.float32))
    ob.data.materials.append(chalk_material())
    ob.visible_shadow = False
    print('nzu: faces', len(keep), 'vertices', len(used), flush=True)
    return ob
