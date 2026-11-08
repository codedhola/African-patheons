"""Run one stage of the Ekwensu build: Blender -b --python build.py -- stage [stage ...]

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


def stage_body():
    import figure
    figure.build()


def stage_pose():
    import gear
    import stance
    from common import WORK, collection, save
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '10_body.blend'))
    rig, body = bpy.data.objects['Rig'], bpy.data.objects['Body']
    blade = gear.make_machete(collection('Props'))
    # nothing he wears is simulated through a move of the arms, so the pose is not keyed
    stance.solve(rig, blade, body)
    save('20_posed.blend')


def stage_trousers():
    import trousers
    from common import WORK
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '20_posed.blend'))
    trousers.stage()


def stage_fringe():
    import numpy as np

    import fringe
    from common import WORK, collection, save
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '30_trousers.blend'))
    body, trousers = bpy.data.objects['Body'], bpy.data.objects['Trousers']
    fringe.make_fringe(body, trousers, collection('Figure'), fringe.palm_material(), float(np.load(WORK / 'waist_z.npy')))
    save('35_fringe.blend')


def stage_dress():
    import cap
    import dress
    import figure
    import gear
    import materials as mats
    import trousers as cut
    from common import WORK, collection, save
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '35_fringe.blend'))
    body, rig, trousers = (bpy.data.objects[n] for n in ('Body', 'Rig', 'Trousers'))
    col = collection('Figure')

    dress.skin_masks(body, rig, scalp_shade=True, lip_erode=1)
    body.data.materials.clear()
    skin = mats.skin()
    print('lips darkened', figure.darken_lips(skin), flush=True)
    body.data.materials.append(skin)
    dress.hide_covered(body, (trousers,))
    body.modifiers.new('Hide under cloth', 'MASK').vertex_group = 'visible'
    sub = body.modifiers.new('Smooth', 'SUBSURF')
    sub.levels, sub.render_levels = 1, 2

    trousers.data.materials.append(cut.raffia_cloth())
    sub = trousers.modifiers.new('Smooth', 'SUBSURF')
    sub.levels = sub.render_levels = 1
    sol = trousers.modifiers.new('Thickness', 'SOLIDIFY')
    sol.thickness = 0.0024          # raffia cloth is thicker than cotton
    sol.offset = 1
    sol.use_rim = True

    fine = mats.hair()
    dress.make_eyes(body, rig, col, (-0.1, -4.8, 1.2), iris_r=0.52, pupil_r=0.19, white=(0.30, 0.26, 0.225),
                    inner=(0.050, 0.022, 0.009), outer=(0.010, 0.006, 0.004))
    dress.make_brows(body, rig, col, fine)
    dress.make_lashes(rig, col, fine)
    _, centre = cap.make_cap(body, rig, col)
    cap.make_edge_hair(body, rig, col, fine, centre)

    cord = bpy.data.objects['RaffiaCord']
    cord_top = float(max((cord.matrix_world @ v.co).z for v in cord.data.vertices))
    gear.make_strap(body, (trousers, cord), rig, col, cord_top, over=(bpy.data.objects['RaffiaFringe'], cord, trousers, body))
    gear.make_necklace(body, rig, col)
    gear.make_bangles(rig, body, col, gear.iron_material('BangleIron'))
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

    from mathutils import Vector

    import market
    import materials as mats
    import tortoise
    from common import WORK, collection, obj_from_arrays, save
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '50_dressed.blend'))
    sc = bpy.context.scene
    props, far, near = collection('Props'), collection('Setting'), collection('Near')

    # the tortoise walks at his feet and turns with him on the turntable
    tortoise.make(props)
    turn = bpy.data.objects.new('Turntable', None)
    sc.collection.objects.link(turn)
    for name in ('Figure', 'Props'):
        for ob in bpy.data.collections[name].objects:
            if ob.parent is None:
                ob.parent = turn

    flames = market.build(far, near)

    cam = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera'))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.sensor_width = 36
    cam.data.clip_end = 2000          # the moon hangs 900 m off

    # the light: after sunset the sky is the broad source, with a lamp in front of him to his right,
    # hung high on a post out of the picture so its pool falls on him more than on the ground
    key = light(sc, 'LampKey', 'SPOT', (-1.75, -2.25, 2.05), 480, (1.0, 0.56, 0.27), aim=(0.05, -0.10, 1.10))
    key.data.spot_size = math.radians(44)
    key.data.spot_blend = 0.8
    key.data.shadow_soft_size = 0.16
    # the afterglow over the stalls behind him, warm on his back and his left side
    glow = light(sc, 'Afterglow', 'SUN', (0, 0, 10), 0.35, (1.0, 0.56, 0.36))
    toward = Vector((market.SUN.x, market.SUN.y, 0.10)).normalized()
    glow.rotation_euler = toward.to_track_quat('Z', 'Y').to_euler()
    glow.data.angle = math.radians(22)
    # the oil lamps on the tables light their own corners
    for k, flame in enumerate(flames):
        on_ground = flame.location.z < 0.2
        light(sc, f'LampLight.{k}', 'POINT', flame.location + Vector((0, 0, 0.018)), 4.0 if on_ground else 8.0, (1.0, 0.44, 0.13), size=0.012, col=near)
    # a low soft lamp only the skin receives, as for the other figures
    skin_only = bpy.data.collections.new('SkinOnly')
    skin_only.objects.link(bpy.data.objects['Body'])
    lift = light(sc, 'SkinLift', 'AREA', (-0.95, -1.85, 1.75), 30, (1.0, 0.62, 0.38), aim=(0, -0.05, 1.55), size=1.0)
    lift.light_linking.receiver_collection = skin_only

    # the dark stage used for the turntable, as for the other figures
    studio = collection('Studio')
    size = 30
    floor = obj_from_arrays('Floor', [(-size, -size, -0.004), (size, -size, -0.004), (size, size, -0.004), (-size, size, -0.004)], [(0, 1, 2, 3)], studio)
    g = mats.Graph('StageFloor')
    bsdf = g.node('BsdfPrincipled', Base_Color=(0.030, 0.026, 0.023, 1), Roughness=0.55)
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
    path = HERE.parent / 'ekwensu.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True, copy=True)
    print('packaged', path, round(path.stat().st_size / 1e6, 1), 'MB', flush=True)


STAGES = dict(package=stage_package, body=stage_body, pose=stage_pose, trousers=stage_trousers, fringe=stage_fringe,
              dress=stage_dress, scene=stage_scene)

if __name__ == '__main__':
    for name in sys.argv[sys.argv.index('--') + 1:]:
        STAGES[name]()
