"""Shape and rig the body on MPFB's base mesh.

MPFB ships the CC0 base mesh, its shaping targets and a rig. Everything else on
the figure is made in the other scripts. The result is saved as 10_body.blend.
"""
import os

import bpy
import numpy as np

from common import WORK, collection, load_mpfb, save, verts_world

# A woman of about forty who has worked the land: tall enough to carry the cloth,
# strong in the arms, soft at the waist. The sources say nothing of her looks.
MACRO = dict(gender=0.0, age=0.56, muscle=0.58, weight=0.56, proportions=0.60, height=0.44,
             cupsize=0.52, firmness=0.62,
             race=dict(african=1.0, asian=0.0, caucasian=0.0))

# Weights tuned by eye against test renders.
TARGETS = {
    'head/head-oval': 0.45,
    'head/head-fat-incr': 0.10,
    'forehead/forehead-nubian-incr': 0.15,
    'nose/nose-volume-incr': 0.15,
    'nose/nose-width2-incr': 0.20,
    'nose/nose-point-up': 0.15,
    'nose/nose-compression-compress': 0.10,
    'mouth/mouth-upperlip-volume-incr': 0.35,
    'mouth/mouth-lowerlip-volume-incr': 0.30,
    'mouth/mouth-cupidsbow-incr': 0.45,
    'mouth/mouth-angles-up': 0.18,
    'chin/chin-prominent-incr': 0.15,
    'chin/chin-width-decr': 0.15,
    'neck/measure-neck-height-incr': 0.10,
    'neck/neck-double-decr': 0.5,
    'cheek/l-cheek-bones-incr': 0.35,
    'cheek/r-cheek-bones-incr': 0.35,
    'cheek/l-cheek-volume-incr': 0.08,
    'cheek/r-cheek-volume-incr': 0.08,
    'eyes/l-eye-height2-decr': 0.22,
    'eyes/r-eye-height2-decr': 0.22,
    'eyes/l-eye-eyefold-down': 0.25,
    'eyes/r-eye-eyefold-down': 0.25,
    'forehead/forehead-scale-vert-decr': 0.45,
    'arms/l-upperarm-muscle-incr': 0.25,
    'arms/r-upperarm-muscle-incr': 0.25,
    'arms/l-lowerarm-muscle-incr': 0.20,
    'arms/r-lowerarm-muscle-incr': 0.20,
}


def eye_data(body):
    """Centre and radius of each MakeHuman eye helper, before the helpers go."""
    me = body.data
    co = np.array([v.co for v in me.vertices])
    out = {}
    for side, group in (('L', 'helper-l-eye'), ('R', 'helper-r-eye')):
        gi = body.vertex_groups[group].index
        idx = [v.index for v in me.vertices if any(g.group == gi for g in v.groups)]
        p = co[idx]
        c = (p.max(0) + p.min(0)) / 2
        out[side] = dict(centre=c.tolist(), radius=float(np.ptp(p, axis=0).max() / 2))
    return out


def lash_data(body):
    """MakeHuman's eyelash strips, kept as guides for the lash curves."""
    me = body.data
    co = np.array([v.co for v in me.vertices])
    gi = {g.name: g.index for g in body.vertex_groups}
    eyes = eye_data(body)
    out = {}
    for key, group, eye in (('upper_L', 'helper-l-eyelashes-2', 'L'), ('lower_L', 'helper-l-eyelashes-1', 'L'),
                            ('upper_R', 'helper-r-eyelashes-2', 'R'), ('lower_R', 'helper-r-eyelashes-1', 'R')):
        members = {v.index for v in me.vertices if any(g.group == gi[group] for g in v.groups)}
        quads = [tuple(p.vertices) for p in me.polygons if len(p.vertices) == 4 and all(i in members for i in p.vertices)]
        out[key + '_co'] = co
        out[key + '_quads'] = np.array(quads)
        out[key + '_eye'] = np.array(eyes[eye]['centre'])
    np.savez(WORK / 'lashes.npz', **out)


def build():
    HumanService, TargetService, LocationService, _ = load_mpfb()
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)

    body = HumanService.create_human(macro_detail_dict=dict(MACRO), feet_on_ground=True)
    root = LocationService.get_mpfb_data('targets')
    for name, weight in TARGETS.items():
        TargetService.load_target(body, os.path.join(root, name + '.target.gz'), weight=weight)

    # freeze the shape so later stages see plain vertices
    body.shape_key_add(name='Final', from_mix=True)
    final = np.zeros(len(body.data.vertices) * 3, np.float32)
    body.data.shape_keys.key_blocks['Final'].data.foreach_get('co', final)
    body.shape_key_clear()
    body.data.vertices.foreach_set('co', final)
    body.data.update()

    rig = HumanService.add_builtin_rig(body, 'default', import_weights=True)
    rig.name, body.name = 'Rig', 'Body'
    body.data.name = 'Body'

    body['eyes'] = str(eye_data(body))
    lash_data(body)

    # drop the helper geometry for good, keeping the vertex numbering of what stays
    bpy.context.view_layer.objects.active = body
    keep = body.vertex_groups['body'].index
    kill = [v for v in body.data.vertices if not any(g.group == keep for g in v.groups)]
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[v.index] for v in kill], context='VERTS')
    bm.to_mesh(body.data)
    bm.free()
    mask = body.modifiers.get('Hide helpers')
    if mask:
        body.modifiers.remove(mask)
    body.data.polygons.foreach_set('use_smooth', [True] * len(body.data.polygons))
    body.data.update()

    col = collection('Figure')
    for ob in (body, rig):
        for c in ob.users_collection:
            c.objects.unlink(ob)
        col.objects.link(ob)
    co = verts_world(body)
    print('body', len(body.data.vertices), 'verts, height', round(float(co[:, 2].max()), 3), flush=True)
    save('10_body.blend')


if __name__ == '__main__':
    build()
