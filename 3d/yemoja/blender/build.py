"""Run one stage of the Yemọja build: Blender -b --python build.py -- stage [stage ...]

Most of the method is in 3d/toolkit: this adds it to the path and sets out what is hers.
"""
import os
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(HERE.parent.parent / 'toolkit'))
os.environ.setdefault('RENDER_WORK', str(HERE / 'work'))


def stage_body():
    import figure
    figure.build()


def stage_pose():
    import pose as toolkit_pose
    import regalia
    import stance
    from common import WORK, collection, save
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '10_body.blend'))
    rig, body = bpy.data.objects['Rig'], bpy.data.objects['Body']
    pot = regalia.make_pot(collection('Props'))
    stance.solve(rig, body, pot)
    # the arms are keyed from part-way up, so the blouse falls into its folds as they come down
    toolkit_pose.key_pose(rig)
    save('20_posed.blend')


def stage_textures():
    import adire
    from common import TEX
    adire.paint(TEX)


def stage_wrapper():
    import drape
    from common import WORK
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '20_posed.blend'))
    drape.wrapper_stage()


def stage_buba():
    import drape
    from common import WORK
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '30_wrapper.blend'))
    drape.buba_stage()


def stage_dress():
    import dress
    import gele
    import materials as mats
    import regalia
    from common import WORK, collection, save
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '40_cloth.blend'))
    body, rig = bpy.data.objects['Body'], bpy.data.objects['Rig']
    wrapper, blouse = bpy.data.objects['Wrapper'], bpy.data.objects['Blouse']
    col = collection('Figure')

    dress.skin_masks(body, rig, scalp_shade=False, lip_erode=1)
    body.data.materials.clear()
    body.data.materials.append(mats.skin())
    dress.hide_covered(body, (wrapper, blouse))
    body.modifiers.new('Hide under cloth', 'MASK').vertex_group = 'visible'

    wrapper.data.materials.append(mats.akwete('AdireWrapper', maps='adire'))
    blouse.data.materials.append(mats.akwete('AdireBuba', maps='adire', binding=True,
                                             edge_colours=((0.045, 0.06, 0.15), (0.60, 0.68, 0.80), (0.045, 0.06, 0.15))))
    for ob in (body, wrapper, blouse):
        sub = ob.modifiers.new('Smooth', 'SUBSURF')
        sub.levels = 1
        sub.render_levels = 2 if ob is body else 1
    for ob in (wrapper, blouse):
        sol = ob.modifiers.new('Thickness', 'SOLIDIFY')
        sol.thickness = 0.0016
        sol.offset = 1
        sol.use_rim = True

    fine = mats.hair()
    dress.make_eyes(body, rig, col, (-1.2, -4.0, 1.30), iris_r=0.52, pupil_r=0.19, white=(0.31, 0.27, 0.235),
                    inner=(0.060, 0.026, 0.011), outer=(0.012, 0.0065, 0.0045))
    dress.make_brows(body, rig, col, fine)
    dress.make_lashes(rig, col, fine)
    gele.make(body, rig, col, mats.akwete('Gele', maps='gele'), mats.hair('CoilHair'))
    regalia.make_beads(body, rig, blouse, col)
    regalia.make_bangles(rig, body, col)
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

    import materials as mats
    import river
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
    feet = [(float(rig.pose.bones[f'foot.{s}'].head.x), float(rig.pose.bones[f'foot.{s}'].head.y)) for s in 'LR']
    river.build(collection('Setting'), collection('Near'), feet)

    cam = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera'))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.sensor_width = 36
    sun = light(sc, 'Sun', 'SUN', (0, 0, 10), 7.0, (1.0, 0.74, 0.50))
    sun.rotation_euler = river.SUN.to_track_quat('Z', 'Y').to_euler()
    sun.data.angle = math.radians(0.6)
    # a low soft lamp only the skin receives: deep skin beside pale cloth needs more light than the cloth can take
    skin_only = bpy.data.collections.new('SkinOnly')
    skin_only.objects.link(bpy.data.objects['Body'])
    lift = light(sc, 'SkinLift', 'AREA', (-0.9, -2.6, 1.6), 40, (1.0, 0.82, 0.66), aim=(0, 0, 1.4), size=2.0)
    lift.light_linking.receiver_collection = skin_only

    studio = collection('Studio')
    size = 30
    floor = obj_from_arrays('Floor', [(-size, -size, -0.004), (size, -size, -0.004), (size, size, -0.004), (-size, size, -0.004)], [(0, 1, 2, 3)], studio)
    g = mats.Graph('StageFloor')
    bsdf = g.node('BsdfPrincipled', Base_Color=(0.030, 0.028, 0.026, 1), Roughness=0.55)
    floor.data.materials.append(g.finish(bsdf.outputs[0]))
    key = light(sc, 'StudioKey', 'SPOT', (-2.7, -4.3, 3.3), 1650, (1.0, 0.80, 0.56), aim=(0, 0, 0.9), col=studio)
    key.data.spot_size = math.radians(34)
    key.data.spot_blend = 0.7
    key.data.shadow_soft_size = 0.22
    rim = light(sc, 'StudioRim', 'SPOT', (3.4, 3.9, 2.8), 1300, (0.62, 0.74, 1.0), aim=(0, 0, 1.0), col=studio)
    rim.data.spot_size = math.radians(26)
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
    path = HERE.parent / 'yemoja.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True, copy=True)
    print('packaged', path, round(path.stat().st_size / 1e6, 1), 'MB', flush=True)


STAGES = dict(package=stage_package, textures=stage_textures, body=stage_body, pose=stage_pose, wrapper=stage_wrapper, buba=stage_buba,
              dress=stage_dress, scene=stage_scene)

if __name__ == '__main__':
    for name in sys.argv[sys.argv.index('--') + 1:]:
        STAGES[name]()
