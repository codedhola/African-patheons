"""Does a clip made on one fighter play on the others?

Every fighter is built on the same skeleton (gamekit.game_body), so in the engine they can
share one Skeleton asset and with it their clips. This script tries that before any other
fighter exists: it makes the bare game body of each figure in 3d/, poses it as the engine
will when it plays the clip, and measures what could go wrong: feet off the floor, feet
that slide, and arms that pass through a broader body.

    blender -b --factory-startup --python characters/check_shared_motion.py -- [figure ...]

With no figures named, every folder of 3d/ that has a blender/figure.py is tried. The clip
is Ògún's guard; another can be named with blend=<file> clip=<action>. It writes
shared_motion.json beside itself and Renders/Shared_Motion.png: each figure's shadow from
the front quarter and from the side, in the order of the json.
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gamekit as gk  # noqa: E402

FIGURES = gk.REPO / '3d'
ARM = ('lowerarm', 'hand', 'thumb', 'index', 'middle', 'ring', 'pinky')
WHOLE_ARM = ARM + ('upperarm',)
STEP = 5                    # frames between looks
INK = (0.10, 0.09, 0.09)


def source_rig(blend, clip):
    """The rig the clip was made on, playing it."""
    rig = gk.append(blend, objects=('Armature',))['Armature']
    rig.name = 'Source'
    gk.link(rig, gk.collection('Source'))
    with bpy.data.libraries.load(str(blend), link=False) as (src, dst):
        dst.actions = [clip]
    gk.use_action(rig, dst.actions[0])
    return rig, dst.actions[0]


def posed(ob):
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    co = np.empty(len(ev.data.vertices) * 3)
    ev.data.vertices.foreach_get('co', co)
    return co.reshape(-1, 3)


def arm_parts(body, rig):
    """Which vertices are forearm and hand, and which faces are neither arm at all."""
    names = [b.name for b in rig.data.bones]
    W = gk.weights(body, names)
    lower = W[:, [i for i, n in enumerate(names) if n.startswith(ARM)]].sum(1) > 0.5
    whole = W[:, [i for i, n in enumerate(names) if n.startswith(WHOLE_ARM)]].sum(1) > 0.01
    rest = [f for f in gk.polygons(body.data) if not any(whole[v] for v in f)]
    return np.flatnonzero(lower), rest


def depth_in_body(co, lower, rest):
    """How far the forearms and hands are inside the rest of the body, in metres: the deepest, and how many past 5 mm."""
    tree = BVHTree.FromPolygons([tuple(v) for v in co], rest)
    deepest, many = 0.0, 0
    for i in lower:
        p = Vector(co[i])
        loc, normal, _, _ = tree.find_nearest(p, 0.10)
        if loc is None:
            continue
        inside = -(p - loc).dot(normal)
        if inside > 0.005:
            many += 1
        deepest = max(deepest, inside)
    return deepest, many


def try_figure(name, blend, clip):
    body, rig = gk.game_body(FIGURES / name / 'blender')
    source, action = source_rig(blend, clip)
    sc = bpy.context.scene
    first, last = (int(round(v)) for v in action.frame_range)
    lower, rest = arm_parts(body, rig)
    stand = gk.coords(body.data)
    r = dict(figure=name, height_m=round(float(stand[:, 2].max()), 3),
             hips_m=round(float(rig.data.bones['pelvis'].head_local.z), 3),
             bones=len(rig.data.bones),
             same_bones=sorted(b.name for b in rig.data.bones) == sorted(b.name for b in source.data.bones))

    # the floor under each way of moving the hips, at the clip's first frame
    sc.frame_set(first)
    for hips in ('own', 'clip', 'scaled'):
        gk.follow(rig, source, hips)
        r[f'lowest_point_mm_hips_{hips}'] = round(float(posed(body)[:, 2].min()) * 1000, 1)
    shown = posed(body)

    low, slide, deep, many = [], {'l': 0.0, 'r': 0.0}, 0.0, 0
    start, hand = {}, []
    for frame in range(first, last + 1, STEP):
        sc.frame_set(frame)
        gk.follow(rig, source, 'scaled')
        co = posed(body)
        low.append(float(co[:, 2].min()))
        for side in 'lr':
            at = rig.pose.bones['foot_' + side].matrix.translation.copy()
            start.setdefault(side, at)
            slide[side] = max(slide[side], (at - start[side]).length)
        hand.append(np.array(rig.pose.bones['hand_l'].matrix.translation))
        d, n = depth_in_body(co, lower, rest)
        deep, many = max(deep, d), max(many, n)
    r.update(frames_looked_at=len(low),
             lowest_point_mm=[round(min(low) * 1000, 1), round(max(low) * 1000, 1)],
             foot_slide_mm=[round(slide[s] * 1000, 1) for s in 'lr'],
             hand_travel_mm=round(float(np.linalg.norm(np.array(hand) - hand[0], axis=1).max()) * 1000, 1),
             arms_in_body_mm=round(deep * 1000, 1), arm_vertices_over_5mm=many)
    faces = gk.polygons(body.data)
    return r, shown, faces


def picture(shapes, out):
    """Each figure in the clip's first pose, as a shadow: from the front quarter and from the side, all to one scale."""
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light, sh.color_type, sh.single_color = 'FLAT', 'SINGLE', INK
    sh.show_object_outline, sh.show_cavity = False, False
    sc.view_settings.view_transform = 'Standard'
    world = bpy.data.worlds.new('Paper')
    world.color = (0.93, 0.93, 0.92)
    sc.world = world
    sc.render.film_transparent = False
    cam = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera'))
    sc.collection.objects.link(cam)
    sc.camera = cam
    col = gk.collection('Shown')
    tiles = []
    look = (0.0, -0.05, 0.93)
    for k, (name, co, faces) in enumerate(shapes):
        ob = gk.new_object(name, co, faces, col)
        for degrees in (28, 90):
            tiles.append(gk.shoot(out.with_name(f'_{k}_{degrees}.png'), cam, gk.around(look, degrees, 5.2), look,
                                  width=300 if degrees == 28 else 260, height=600))
        bpy.data.objects.remove(ob)
    gk.sheet(tiles, out)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    named = dict(a.split('=', 1) for a in args if '=' in a)
    blend = Path(named.get('blend', HERE / 'ogun' / 'SK_Ogun.blend'))
    clip = named.get('clip', 'A_Ogun_GuardIdle')
    figures = [a for a in args if '=' not in a] or sorted(p.parent.parent.name for p in FIGURES.glob('*/blender/figure.py'))
    report, shapes = [], []
    for name in figures:
        r, co, faces = try_figure(name, blend, clip)
        print(json.dumps(r), flush=True)
        report.append(r)
        shapes.append((name, co, faces))
    (HERE / 'shared_motion.json').write_text(json.dumps(dict(clip=clip, made_on=blend.parent.name, figures=report), indent=1) + '\n')
    out = HERE / 'Renders' / 'Shared_Motion.png'
    out.parent.mkdir(exist_ok=True)
    picture(shapes, out)
    print('drawn', out, flush=True)


main()
