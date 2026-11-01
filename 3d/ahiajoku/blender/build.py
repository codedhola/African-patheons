"""Run one stage of the Ahiajoku build: Blender -b --python build.py -- stage [stage ...]"""
import os
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(HERE.parent.parent / 'toolkit'))
os.environ.setdefault('RENDER_WORK', str(HERE / 'work'))


def stage_body():
    import body
    body.build()


def stage_pose():
    import field_materials as mats
    import pose
    import stance
    import yam
    from common import WORK, collection, save
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '10_body.blend'))
    rig = bpy.data.objects['Rig']
    col = collection('Props')
    ob, _, radii = yam.yam_object('Yam', 3, col, roots=320, material=mats.yam_skin(), flesh=mats.yam_flesh(),
                                     root_material=mats.rootlet())
    ob.matrix_world = stance.yam_matrix()
    bpy.context.view_layer.update()
    stance.solve(rig, radii.tolist(), pose.prop_tree(ob))
    pose.key_pose(rig)
    save('20_posed.blend')


def stage_wrapper():
    import cloth
    from common import WORK
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '20_posed.blend'))
    cloth.wrapper_stage()


def stage_blouse():
    import cloth
    from common import WORK
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '30_wrapper.blend'))
    cloth.blouse_stage()


def stage_textures():
    import akwete
    from common import TEX
    akwete.paint(TEX)


def stage_dress():
    import pose
    import dress
    import hairline
    import headtie
    import materials as mats
    from common import WORK, collection, save
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '40_cloth.blend'))
    bpy.context.scene.frame_set(pose.POSE_END)
    body, rig = bpy.data.objects['Body'], bpy.data.objects['Rig']
    wrapper, blouse = bpy.data.objects['Wrapper'], bpy.data.objects['Blouse']
    col = collection('Figure')
    dress.skin_masks(body, rig)
    body.data.materials.clear()
    body.data.materials.append(mats.skin())
    dress.hide_covered(body, (wrapper, blouse))
    mask = body.modifiers.new('Hide under cloth', 'MASK')
    mask.vertex_group = 'visible'
    wrapper.data.materials.append(mats.akwete('AkweteWrapper'))
    blouse.data.materials.append(mats.akwete('AkweteBlouse', binding=True))
    for ob in (body, wrapper, blouse):
        sub = ob.modifiers.new('Smooth', 'SUBSURF')
        sub.levels = 1
        sub.render_levels = 2 if ob is body else 1
    for ob, thick in ((wrapper, 0.0016), (blouse, 0.0016)):
        sol = ob.modifiers.new('Thickness', 'SOLIDIFY')
        sol.thickness = thick
        sol.offset = 1
        sol.use_rim = True
    hair = mats.hair()
    dress.make_eyes(body, rig, col, (1.7, -3.2, 1.45))
    dress.make_brows(body, rig, col, hair)
    dress.make_lashes(rig, col, hair)
    dress.make_necklaces(body, blouse, rig, col)
    dress.make_bangles(rig, col)
    headtie.make(body, rig, col, mats.akwete('AkweteTie'))
    hairline.make(body, rig, col, hair)
    save('50_dressed.blend')


def stage_scene():
    import field_materials as mats
    import render_views
    import setting
    from common import WORK, collection, obj_from_arrays, save
    from mathutils import Vector
    import math
    import numpy as np
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '50_dressed.blend'))
    bpy.context.scene.frame_set(40)
    props, field = collection('Props'), collection('Setting')
    skin, flesh, root = mats.yam_skin(), mats.yam_flesh(), mats.rootlet()

    basket = setting.make_basket(props)
    setting.fill_basket(basket, props, skin, flesh, root)
    basket.location = (*setting.BASKET_AT, 0.0)
    basket.scale = (0.88, 0.88, 0.88)
    bpy.context.scene.frame_set(40)

    # everything that belongs to the figure turns together
    turn = bpy.data.objects.new('Turntable', None)
    bpy.context.scene.collection.objects.link(turn)
    for name in ('Figure', 'Props'):
        for ob in bpy.data.collections[name].objects:
            if ob.parent is None:
                ob.parent = turn

    setting.make_near_ground(collection('Near'))
    setting.make_ground(field)
    setting.make_field(field, setting.height_field)
    setting.make_barn(field, skin, flesh)
    setting.make_treeline(field)

    cam = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera'))
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.data.sensor_width = 36

    # the moon, clear of the bush, a little right of her head as the hero camera sees it
    eye = Vector(render_views.HERO_EYE)
    look = (Vector(render_views.HERO_TARGET) - eye).normalized()
    side = look.cross(Vector((0, 0, 1))).normalized()
    up = side.cross(look)
    distance = 400
    moon_at = eye + look * distance + side * distance * 0.112 + up * distance * 0.083
    setting.make_moon(field, moon_at, distance * 0.031)
    moon_dir = (moon_at - eye).normalized()
    setting.make_sky(moon_dir=moon_dir)

    def clear_of_sightlines(x, y):
        bearing = Vector((x - eye.x, y - eye.y, 0)).normalized()
        moon_flat = Vector((moon_dir.x, moon_dir.y, 0)).normalized()
        head = Vector((-eye.x, -eye.y, 0)).normalized()
        axis = Vector((look.x, look.y, 0)).normalized()
        off_axis = math.degrees(bearing.angle(axis))
        return bearing.angle(moon_flat) > math.radians(5.5) and bearing.angle(head) > math.radians(3.5) and not 9.5 < off_axis < 16

    setting.make_palms(field, clear_of_sightlines)

    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN'))
    bpy.context.scene.collection.objects.link(sun)
    sun.data.energy = 3.4
    sun.data.color = (1.0, 0.56, 0.30)
    sun.data.angle = math.radians(2.2)
    direction = Vector((-0.70, -0.70, 0.12)).normalized()
    sun.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()

    fill = bpy.data.objects.new('Fill', bpy.data.lights.new('Fill', 'AREA'))
    bpy.context.scene.collection.objects.link(fill)
    fill.data.shape = 'DISK'
    fill.data.size = 3.0
    fill.data.energy = 26
    fill.data.color = (1.0, 0.72, 0.50)
    fill.location = (2.6, -3.4, 1.5)
    fill.rotation_euler = (Vector((0, 0, 1.1)) - fill.location).to_track_quat('-Z', 'Y').to_euler()

    # a low soft lamp that only the skin sees, because deep skin beside cream cloth
    # needs more light than the cloth can take. Cycles light linking does the separating.
    skin_only = bpy.data.collections.new('SkinOnly')
    skin_only.objects.link(bpy.data.objects['Body'])
    lift = bpy.data.objects.new('SkinLift', bpy.data.lights.new('SkinLift', 'AREA'))
    bpy.context.scene.collection.objects.link(lift)
    lift.data.shape = 'DISK'
    lift.data.size = 1.6
    lift.data.energy = 30
    lift.data.color = (1.0, 0.70, 0.48)
    lift.location = (1.5, -2.5, 1.65)
    lift.rotation_euler = (Vector((0, 0, 1.45)) - lift.location).to_track_quat('-Z', 'Y').to_euler()
    lift.light_linking.receiver_collection = skin_only

    # a dark floor and two lamps for the turntable, under the same warm key
    studio = collection('Studio')
    a = np.linspace(0, 2 * np.pi, 96, endpoint=False)
    floor_v = np.vstack([[[0, 0, -0.004]], np.stack([np.cos(a) * 30, np.sin(a) * 30, np.full(96, -0.004)], 1)])
    floor = obj_from_arrays('Floor', floor_v, [(0, 1 + i, 1 + (i + 1) % 96) for i in range(96)], studio)
    floor.data.materials.append(mats.soil(False))
    key = bpy.data.objects.new('StudioKey', bpy.data.lights.new('StudioKey', 'SPOT'))
    studio.objects.link(key)
    key.data.energy = 2600
    key.data.color = (1.0, 0.66, 0.40)
    key.data.spot_size = math.radians(34)
    key.data.spot_blend = 0.7
    key.data.shadow_soft_size = 0.22
    key.location = (-2.7, -4.3, 3.3)
    key.rotation_euler = (Vector((0, 0, 0.9)) - key.location).to_track_quat('-Z', 'Y').to_euler()
    rim = bpy.data.objects.new('StudioRim', bpy.data.lights.new('StudioRim', 'SPOT'))
    studio.objects.link(rim)
    rim.data.energy = 1500
    rim.data.color = (0.55, 0.68, 1.0)
    rim.data.spot_size = math.radians(26)
    rim.data.spot_blend = 0.8
    rim.data.shadow_soft_size = 0.3
    rim.location = (3.4, 3.9, 2.8)
    rim.rotation_euler = (Vector((0, 0, 1.0)) - rim.location).to_track_quat('-Z', 'Y').to_euler()
    wash = bpy.data.objects.new('StudioWash', bpy.data.lights.new('StudioWash', 'AREA'))
    studio.objects.link(wash)
    wash.data.shape = 'DISK'
    wash.data.size = 3.0
    wash.data.energy = 90
    wash.data.color = (1.0, 0.74, 0.54)
    wash.location = (1.6, -3.4, 1.5)
    wash.rotation_euler = (Vector((0, 0, 1.0)) - wash.location).to_track_quat('-Z', 'Y').to_euler()
    save('60_scene.blend')


def stage_package():
    """Write the finished scene into the repo as one self-contained .blend."""
    from common import WORK
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '60_scene.blend'))
    bpy.ops.file.pack_all()
    bpy.context.scene.frame_set(40)
    path = HERE.parent / 'ahiajoku.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True, copy=True)
    print('packaged', path, round(path.stat().st_size / 1e6, 1), 'MB', flush=True)


STAGES = dict(package=stage_package, scene=stage_scene, textures=stage_textures, body=stage_body, pose=stage_pose, wrapper=stage_wrapper, blouse=stage_blouse, dress=stage_dress)

if __name__ == '__main__':
    for name in sys.argv[sys.argv.index('--') + 1:]:
        STAGES[name]()
