"""Run one stage of the Ọ̀ṣọ́ọ̀sì build: Blender -b --python build.py -- stage [stage ...]

Most of the method is in 3d/toolkit: this adds it to the path and sets out what is his.
"""
import os
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(HERE.parent.parent / 'toolkit'))
os.environ.setdefault('RENDER_WORK', str(HERE / 'work'))


def stage_textures():
    import aro
    from common import TEX
    aro.paint(TEX)


def stage_body():
    import figure
    figure.build()


def stage_pose():
    import pose as toolkit_pose
    import stance
    from common import WORK, collection, save
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '10_body.blend'))
    rig, body = bpy.data.objects['Rig'], bpy.data.objects['Body']
    stance.take_up_bow(rig, body, collection('Props'))
    # the arms are keyed from nearly at the draw: a sleeve carried far up with a rising arm is left behind
    # inside it, so his sleeves are cut round the arms almost where they end, and the cloth settles round them
    toolkit_pose.key_pose(rig, start=0.9)
    save('20_posed.blend')


def stage_trousers():
    import trousers
    from common import WORK
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '20_posed.blend'))
    trousers.stage()


def stage_tunic():
    import drape
    from common import WORK
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '30_trousers.blend'))
    drape.tunic_stage()


def stage_dress():
    import numpy as np
    from mathutils import Vector

    import bow as gear
    import dress
    import figure
    import hair
    import materials as mats
    import regalia
    import stance
    from common import WORK, collection, save
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '40_cloth.blend'))
    body, rig, tunic, trousers = (bpy.data.objects[n] for n in ('Body', 'Rig', 'Tunic', 'Trousers'))
    col, props = collection('Figure'), collection('Props')

    dress.skin_masks(body, rig, scalp_shade=False, lip_erode=1)
    _, scalp = hair.make(body, rig, col)
    figure.face_masks(body, np.clip(scalp * 1.4, 0, 1))
    body.data.materials.clear()
    skin = mats.skin()
    print('lips darkened', figure.darken_lips(skin), flush=True)
    body.data.materials.append(skin)
    dress.hide_covered(body, (tunic, trousers))
    body.modifiers.new('Hide under cloth', 'MASK').vertex_group = 'visible'
    sub = body.modifiers.new('Smooth', 'SUBSURF')
    sub.levels, sub.render_levels = 1, 2

    tunic.data.materials.append(mats.akwete('Aro', maps='aro', binding=True,
                                            edge_colours=((0.075, 0.110, 0.230), (0.80, 0.82, 0.84), (0.075, 0.110, 0.230))))
    trousers.data.materials.append(mats.akwete('AroDeep', maps='aro_deep'))
    for ob, thick in ((tunic, 0.0017), (trousers, 0.0019)):
        sub = ob.modifiers.new('Smooth', 'SUBSURF')
        sub.levels = sub.render_levels = 1
        sol = ob.modifiers.new('Thickness', 'SOLIDIFY')
        sol.thickness = thick
        sol.offset = 1
        sol.use_rim = True

    # he looks along the arrow at his mark
    info = eval(body['eyes'])
    M = dress.head_matrix(rig)
    eyes = M @ ((Vector(info['L']['centre']) + Vector(info['R']['centre'])) / 2)
    fine = mats.hair()
    dress.make_eyes(body, rig, col, eyes + stance.AIM * 30, iris_r=0.52, pupil_r=0.19, white=(0.30, 0.26, 0.225),
                    inner=(0.055, 0.024, 0.010), outer=(0.011, 0.006, 0.004))
    dress.make_brows(body, rig, col, fine)
    dress.make_lashes(rig, col, fine)

    # the bow strung through his fingers, and the arrow on the string
    bow_ob = bpy.data.objects['Bow']
    info = eval(bow_ob['draw'])
    up = Vector(info['up'])
    gear.make_string(props, info['loops'], stance.string_path(rig, 'R'))
    nock = stance.string_point(rig, 'R')
    rest = stance.arrow_rest(rig, Vector(info['grip']), up, body, nock)
    gear.nocked_arrow(props, nock, rest, up)

    strap, loop, plane = gear.make_strap(body, tunic, rig, col)
    gear.make_quiver(col, loop, plane)
    regalia.make_beads(body, rig, col, tunic, strap)
    save('50_dressed.blend')


def light(sc, name, kind, at, energy, colour, aim=None, size=None, col=None):
    from mathutils import Vector
    ob = bpy.data.objects.new(name, bpy.data.lights.new(name, kind))
    (col or sc.collection).objects.link(ob)
    ob.data.energy = energy
    ob.data.color = colour
    ob.location = at
    if size is not None:
        if kind == 'AREA':
            ob.data.shape = 'DISK'
            ob.data.size = size
        else:
            ob.data.shadow_soft_size = size
    if aim is not None:
        ob.rotation_euler = (Vector(aim) - Vector(at)).to_track_quat('-Z', 'Y').to_euler()
    return ob


def stage_scene():
    import math

    import forest
    import materials as mats
    import render_views as views
    from common import WORK, collection, obj_from_arrays, save
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '50_dressed.blend'))
    sc = bpy.context.scene
    rig = bpy.data.objects['Rig']
    turn = bpy.data.objects.new('Turntable', None)
    sc.collection.objects.link(turn)
    for name in ('Figure', 'Props'):
        for ob in bpy.data.collections[name].objects:
            if ob.parent is None:
                ob.parent = turn
    feet = []
    for s in 'LR':
        foot = rig.pose.bones[f'foot.{s}']
        feet += [(float(foot.head.x), float(foot.head.y)), (float(foot.tail.x), float(foot.tail.y))]
    forest.build(collection('Setting'), collection('Near'), feet, views.HERO_EYE, views.HERO_TARGET)

    cam = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera'))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.sensor_width = 36
    cam.data.clip_end = 600
    # pale light from high above, behind him and on the side of his mark, coming down through the gaps
    sun = light(sc, 'Sun', 'SUN', (0, 0, 10), 22.0, (1.0, 0.95, 0.84))
    sun.rotation_euler = forest.SUN.to_track_quat('Z', 'Y').to_euler()
    sun.data.angle = math.radians(1.4)
    # the bright mist of the clearing in front of him: a broad cool light from the side he faces
    light(sc, 'Fill', 'AREA', (2.6, -3.2, 2.1), 220, (0.82, 0.94, 0.92), aim=(0.2, 0, 1.3), size=4.0)
    # the gap in the canopy over the clearing: a soft light from high above and a little behind him
    gap = light(sc, 'Skylight', 'AREA', (0.4, 1.6, 9.0), 900, (0.86, 0.96, 0.94), aim=(0.0, 0.0, 1.0), size=7.0)
    gap.visible_camera = False
    # a low soft lamp only the skin receives, as for the other figures
    skin_only = bpy.data.collections.new('SkinOnly')
    skin_only.objects.link(bpy.data.objects['Body'])
    lift = light(sc, 'SkinLift', 'AREA', (1.4, -2.4, 1.7), 40, (1.0, 0.86, 0.70), aim=(0.05, 0, 1.45), size=2.0)
    lift.light_linking.receiver_collection = skin_only

    studio = collection('Studio')
    size = 30
    floor = obj_from_arrays('Floor', [(-size, -size, -0.004), (size, -size, -0.004), (size, size, -0.004), (-size, size, -0.004)], [(0, 1, 2, 3)], studio)
    g = mats.Graph('StageFloor')
    bsdf = g.node('BsdfPrincipled', Base_Color=(0.030, 0.029, 0.027, 1), Roughness=0.55)
    floor.data.materials.append(g.finish(bsdf.outputs[0]))
    key = light(sc, 'StudioKey', 'SPOT', (-2.7, -4.3, 3.3), 1650, (1.0, 0.80, 0.56), aim=(0, 0, 0.9), col=studio)
    key.data.spot_size = math.radians(40)
    key.data.spot_blend = 0.7
    key.data.shadow_soft_size = 0.22
    rim = light(sc, 'StudioRim', 'SPOT', (3.4, 3.9, 2.8), 1300, (0.62, 0.74, 1.0), aim=(0, 0, 1.0), col=studio)
    rim.data.spot_size = math.radians(30)
    rim.data.spot_blend = 0.8
    rim.data.shadow_soft_size = 0.3
    light(sc, 'StudioWash', 'AREA', (1.6, -3.4, 1.5), 55, (1.0, 0.80, 0.60), aim=(0, 0, 1.0), size=3.0, col=studio)
    save('60_scene.blend')


def stage_package():
    """Write the finished scene into the repo as one self-contained .blend."""
    from common import WORK
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '60_scene.blend'))
    bpy.ops.file.pack_all()
    bpy.context.preferences.filepaths.save_version = 0      # no .blend1 left beside it in the repo
    path = HERE.parent / 'osoosi.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True, copy=True)
    print('packaged', path, round(path.stat().st_size / 1e6, 1), 'MB', flush=True)


STAGES = dict(package=stage_package, textures=stage_textures, body=stage_body, pose=stage_pose, trousers=stage_trousers,
              tunic=stage_tunic, dress=stage_dress, scene=stage_scene)

if __name__ == '__main__':
    for name in sys.argv[sys.argv.index('--') + 1:]:
        STAGES[name]()
