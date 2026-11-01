"""Run one stage of the Ọ̀ṣun build: Blender -b --python build.py -- stage [stage ...]

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
    import figure
    import pose as toolkit_pose
    import brass
    import stance
    from common import WORK, collection, save
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '10_body.blend'))
    rig = bpy.data.objects['Rig']
    figure.soften_chest(bpy.data.objects['Body'])
    props = collection('Props')
    metal = brass.brass_material()
    fan = brass.make_fan(props, metal)
    bell = brass.make_bell(props, metal)
    stance.solve(rig, fan, bell)
    toolkit_pose.key_pose(rig)
    save('20_posed.blend')


def stage_textures():
    import ofi
    from common import TEX
    ofi.paint(TEX)


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


def stage_sash():
    import drape
    drape.sash_stage()


def stage_dress():
    import agogo
    import brass
    import dress
    import drape
    import materials as mats
    import regalia
    from common import WORK, collection, save
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '45_sash.blend'))
    body, rig = bpy.data.objects['Body'], bpy.data.objects['Rig']
    wrapper, blouse, sash = (bpy.data.objects[n] for n in ('Wrapper', 'Blouse', 'Sash'))
    col = collection('Figure')

    dress.skin_masks(body, rig, scalp_shade=False, lip_erode=2)
    regalia.add_tiroo(body)
    body.data.materials.clear()
    body.data.materials.append(mats.skin())
    dress.hide_covered(body, (wrapper, blouse))
    body.modifiers.new('Hide under cloth', 'MASK').vertex_group = 'visible'

    wrapper.data.materials.append(mats.akwete('OfiWrapper', maps='ofi'))
    blouse.data.materials.append(mats.akwete('OfiBuba', maps='ofi', binding=True,
                                             edge_colours=((0.86, 0.60, 0.13), (0.93, 0.90, 0.82), (0.62, 0.14, 0.08))))
    gold = mats.akwete('OfiGold', maps='gold')
    sash_ends = bpy.data.objects['SashEnds']
    for ob in (sash, sash_ends, bpy.data.objects['SashKnot']):
        ob.data.materials.append(gold)
    for ob in (body, wrapper, blouse, sash, sash_ends):
        sub = ob.modifiers.new('Smooth', 'SUBSURF')
        sub.levels = 1
        sub.render_levels = 2 if ob is body else 1
    for ob in (wrapper, blouse, sash, sash_ends):
        sol = ob.modifiers.new('Thickness', 'SOLIDIFY')
        sol.thickness = 0.0016
        sol.offset = 1
        sol.use_rim = True
    drape.fringe(sash_ends, col, mats.hair('GoldThread', (0.86, 0.55, 0.10, 1)))

    hair = agogo.hair_material()
    fine = mats.hair()
    dress.make_eyes(body, rig, col, (-1.5, -3.6, 1.60), iris_r=0.54, pupil_r=0.20, white=(0.33, 0.285, 0.245),
                   inner=(0.060, 0.026, 0.011), outer=(0.012, 0.0065, 0.0045))
    regalia.make_brows(body, rig, col, fine)
    dress.make_lashes(rig, col, fine)
    _, centre = agogo.make(body, rig, col, hair, mats.hair('CrestForm', (0.007, 0.0045, 0.0035, 1)))
    agogo.make_feathers(rig, centre, col, mats.hair('Ikode', (0.62, 0.015, 0.012, 1)))
    agogo.make_cowries(rig, centre, col, mats.ivory())
    regalia.make_beads(body, rig, blouse, col)
    regalia.make_bangles(rig, body, col, bpy.data.materials.get('Brass') or brass.brass_material())
    save('50_dressed.blend')


def stage_scene():
    import math

    import numpy as np
    from mathutils import Vector

    import grove
    import materials as mats
    import offering
    import render_views as views
    from common import WORK, collection, obj_from_arrays, save
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '50_dressed.blend'))
    sc = bpy.context.scene
    props, field, near = collection('Props'), collection('Setting'), collection('Near')

    offering.make(props, (0.66, -0.46, 0.0))

    # everything that belongs to the figure turns together
    turn = bpy.data.objects.new('Turntable', None)
    sc.collection.objects.link(turn)
    for name in ('Figure', 'Props'):
        for ob in bpy.data.collections[name].objects:
            if ob.parent is None:
                ob.parent = turn

    grove.make_ground(near)
    print('stones', grove.make_stones(near), flush=True)
    high, _ = grove.make_forest(field)
    grove.make_canopy(field, high)
    grove.make_sun_mask(field)
    grove.make_litter(near)
    grove.make_framing(field, high, views.HERO_EYE, views.HERO_TARGET)
    grove.make_sky()
    grove.make_haze(field)

    cam = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera'))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.sensor_width = 36

    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN'))
    sc.collection.objects.link(sun)
    sun.data.energy = 17.0
    sun.data.color = (1.0, 0.80, 0.52)
    sun.data.angle = math.radians(1.6)
    sun.rotation_euler = grove.SUN.to_track_quat('Z', 'Y').to_euler()

    fill = bpy.data.objects.new('Fill', bpy.data.lights.new('Fill', 'AREA'))
    sc.collection.objects.link(fill)
    fill.data.shape = 'DISK'
    fill.data.size = 4.0
    fill.data.energy = 60
    fill.data.color = (1.0, 0.86, 0.68)
    fill.location = (2.4, -4.2, 2.0)
    fill.rotation_euler = (Vector((0, 0, 1.1)) - fill.location).to_track_quat('-Z', 'Y').to_euler()

    # a low soft lamp only the skin receives: deep skin beside white cloth needs more light than the cloth can take
    skin_only = bpy.data.collections.new('SkinOnly')
    skin_only.objects.link(bpy.data.objects['Body'])
    lift = bpy.data.objects.new('SkinLift', bpy.data.lights.new('SkinLift', 'AREA'))
    sc.collection.objects.link(lift)
    lift.data.shape = 'DISK'
    lift.data.size = 2.4
    lift.data.energy = 70
    lift.data.color = (1.0, 0.76, 0.56)
    lift.location = (0.9, -2.7, 1.75)
    lift.rotation_euler = (Vector((0, 0, 1.45)) - lift.location).to_track_quat('-Z', 'Y').to_euler()
    lift.light_linking.receiver_collection = skin_only

    # the dark stage used for the turntable, as for the other figures
    studio = collection('Studio')
    size = 30
    floor = obj_from_arrays('Floor', [(-size, -size, -0.004), (size, -size, -0.004), (size, size, -0.004), (-size, size, -0.004)], [(0, 1, 2, 3)], studio)
    floor.data.attributes.new('bank', 'FLOAT', 'POINT').data.foreach_set('value', np.full(4, 0.09, np.float32))
    floor.data.materials.append(grove.sand_material())
    key = bpy.data.objects.new('StudioKey', bpy.data.lights.new('StudioKey', 'SPOT'))
    studio.objects.link(key)
    key.data.energy = 1650
    key.data.color = (1.0, 0.80, 0.56)
    key.data.spot_size = math.radians(34)
    key.data.spot_blend = 0.7
    key.data.shadow_soft_size = 0.22
    key.location = (-2.7, -4.3, 3.3)
    key.rotation_euler = (Vector((0, 0, 0.9)) - key.location).to_track_quat('-Z', 'Y').to_euler()
    rim = bpy.data.objects.new('StudioRim', bpy.data.lights.new('StudioRim', 'SPOT'))
    studio.objects.link(rim)
    rim.data.energy = 1300
    rim.data.color = (0.62, 0.74, 1.0)
    rim.data.spot_size = math.radians(26)
    rim.data.spot_blend = 0.8
    rim.data.shadow_soft_size = 0.3
    rim.location = (3.4, 3.9, 2.8)
    rim.rotation_euler = (Vector((0, 0, 1.0)) - rim.location).to_track_quat('-Z', 'Y').to_euler()
    wash = bpy.data.objects.new('StudioWash', bpy.data.lights.new('StudioWash', 'AREA'))
    studio.objects.link(wash)
    wash.data.shape = 'DISK'
    wash.data.size = 3.0
    wash.data.energy = 55
    wash.data.color = (1.0, 0.80, 0.60)
    wash.location = (1.6, -3.4, 1.5)
    wash.rotation_euler = (Vector((0, 0, 1.0)) - wash.location).to_track_quat('-Z', 'Y').to_euler()
    save('60_scene.blend')


def stage_package():
    """Write the finished scene into the repo as one self-contained .blend."""
    from common import WORK
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '60_scene.blend'))
    bpy.ops.file.pack_all()
    bpy.context.preferences.filepaths.save_version = 0      # no .blend1 left beside it in the repo
    path = HERE.parent / 'osun.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True, copy=True)
    print('packaged', path, round(path.stat().st_size / 1e6, 1), 'MB', flush=True)


STAGES = dict(package=stage_package, textures=stage_textures, body=stage_body, pose=stage_pose, wrapper=stage_wrapper, buba=stage_buba, sash=stage_sash,
              dress=stage_dress, scene=stage_scene)

if __name__ == '__main__':
    for name in sys.argv[sys.argv.index('--') + 1:]:
        STAGES[name]()
