"""Run one stage of the Ògún build: Blender -b --python build.py -- stage [stage ...]

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
    import iron
    import stance
    from common import WORK, collection, save
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '10_body.blend'))
    rig = bpy.data.objects['Rig']
    blade = iron.make_machete(collection('Props'))
    # nothing he wears is simulated through a move of the arms, so the pose is not keyed
    stance.solve(rig, blade)
    save('20_posed.blend')


def stage_textures():
    import etu
    from common import TEX
    etu.paint(TEX)


def stage_sokoto():
    import sokoto
    from common import WORK
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '20_posed.blend'))
    sokoto.sokoto_stage()


def stage_mariwo():
    import numpy as np

    import mariwo
    from common import WORK, collection, save
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '30_sokoto.blend'))
    body, rig, sokoto = (bpy.data.objects[n] for n in ('Body', 'Rig', 'Sokoto'))
    col = collection('Figure')
    palm = mariwo.palm_material()
    mariwo.make_fringe(body, sokoto, col, palm, float(np.load(WORK / 'waist_z.npy')))
    mariwo.make_headband(body, rig, col, palm)
    save('35_mariwo.blend')


def stage_dress():
    import numpy as np

    import dress
    import figure
    import hair
    import iron
    import materials as mats
    from common import WORK, collection, save
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '35_mariwo.blend'))
    body, rig, sokoto = (bpy.data.objects[n] for n in ('Body', 'Rig', 'Sokoto'))
    col = collection('Figure')

    dress.skin_masks(body, rig, scalp_shade=False, lip_erode=1)
    _, _, scalp, _ = hair.make(body, rig, col)
    figure.face_masks(body, np.clip(scalp * 1.4, 0, 1))
    body.data.materials.clear()
    skin = mats.skin()
    print('lips darkened', figure.darken_lips(skin), flush=True)
    body.data.materials.append(skin)
    dress.hide_covered(body, (sokoto,))
    body.modifiers.new('Hide under cloth', 'MASK').vertex_group = 'visible'
    sub = body.modifiers.new('Smooth', 'SUBSURF')
    sub.levels, sub.render_levels = 1, 2

    sokoto.data.materials.append(mats.akwete('Etu', maps='etu'))
    sub = sokoto.modifiers.new('Smooth', 'SUBSURF')
    sub.levels = sub.render_levels = 1
    sol = sokoto.modifiers.new('Thickness', 'SOLIDIFY')
    sol.thickness = 0.0019
    sol.offset = 1
    sol.use_rim = True

    fine = mats.hair()
    dress.make_eyes(body, rig, col, (-0.6, -4.0, 1.45), iris_r=0.52, pupil_r=0.19, white=(0.30, 0.26, 0.225),
                    inner=(0.055, 0.024, 0.010), outer=(0.011, 0.006, 0.004))
    dress.make_brows(body, rig, col, fine)
    dress.make_lashes(rig, col, fine)

    metal = iron.iron_material()
    cord = bpy.data.objects['MariwoCord']
    cord_top = float(max((cord.matrix_world @ v.co).z for v in cord.data.vertices))
    iron.make_chain(body, (sokoto, cord), rig, col, metal, cord_top)
    iron.make_bangles(rig, body, col, metal)
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

    import numpy as np
    from mathutils import Vector

    import dog
    import forge
    from common import WORK, collection, obj_from_arrays, save
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '50_dressed.blend'))
    sc = bpy.context.scene
    props, field, near = collection('Props'), collection('Setting'), collection('Near')

    # the dog sleeps at his side and turns with him on the turntable
    dog.make(props)
    turn = bpy.data.objects.new('Turntable', None)
    sc.collection.objects.link(turn)
    for name in ('Figure', 'Props'):
        for ob in bpy.data.collections[name].objects:
            if ob.parent is None:
                ob.parent = turn

    forge.build(field, near)

    cam = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera'))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.sensor_width = 36

    # the fire: a broad glow over the hearth and a hot core low in the coals
    h = forge.HEARTH
    # set down among the coals, so the hearth's own wall shades its outside, as the fire's would
    fire = light(sc, 'FireLight', 'POINT', h + Vector((0.04, 0.06, 0.45)), 300, (1.0, 0.52, 0.22), size=0.34)
    low = light(sc, 'FireLow', 'POINT', h + Vector((0, 0, 0.30)), 35, (1.0, 0.36, 0.08), size=0.12)
    # the coals and the inside of the hearth glow by the coals' own light: the lamps standing in for
    # the fire do not light them, and the coals do not stand in their way; the hearth's wall still does
    def excluding(name, objects):
        c = bpy.data.collections.new(name)
        for ob in objects:
            c.objects.link(ob)
        for co in c.collection_objects:
            co.light_linking.link_state = 'EXCLUDE'
        return c
    unlit = excluding('FireUnlit', [bpy.data.objects[n] for n in ('Embers', 'Hearth', 'FireBed')])
    clear = excluding('FireClear', [bpy.data.objects[n] for n in ('Embers', 'FireBed')])
    for lamp in (fire, low):
        lamp.light_linking.receiver_collection = unlit
        lamp.light_linking.blocker_collection = clear
    bar = bpy.data.objects['HotBar']
    tip = Vector(bar.data.vertices[0].co)
    light(sc, 'BarGlow', 'POINT', tip + Vector((0, 0, 0.05)), 34, (1.0, 0.33, 0.06), size=0.03)
    # moonlight through the open side of the shed, cool and faint
    moon = light(sc, 'Moon', 'SUN', (0, 0, 10), 1.9, (0.50, 0.62, 1.0))
    moon.rotation_euler = Vector((-0.93, 0.18, 0.27)).to_track_quat('Z', 'Y').to_euler()
    moon.data.angle = math.radians(0.6)
    # firelight thrown back off the floor and the wall, toward the front of him
    light(sc, 'Bounce', 'AREA', (0.6, -2.6, 0.45), 16, (1.0, 0.58, 0.32), aim=(0, 0, 1.1), size=3.0)
    # a low soft lamp only the skin receives: dark skin by firelight needs more light than the iron can take
    skin_only = bpy.data.collections.new('SkinOnly')
    skin_only.objects.link(bpy.data.objects['Body'])
    lift = light(sc, 'SkinLift', 'AREA', (1.15, -1.75, 1.80), 48, (1.0, 0.60, 0.34), aim=(0, -0.05, 1.50), size=1.2)
    lift.light_linking.receiver_collection = skin_only

    # the dark stage used for the turntable, as for the other figures
    studio = collection('Studio')
    size = 30
    floor = obj_from_arrays('Floor', [(-size, -size, -0.004), (size, -size, -0.004), (size, size, -0.004), (-size, size, -0.004)], [(0, 1, 2, 3)], studio)
    import materials as mats
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
    path = HERE.parent / 'ogun.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True, copy=True)
    print('packaged', path, round(path.stat().st_size / 1e6, 1), 'MB', flush=True)


STAGES = dict(package=stage_package, textures=stage_textures, body=stage_body, pose=stage_pose, sokoto=stage_sokoto, mariwo=stage_mariwo,
              dress=stage_dress, scene=stage_scene)

if __name__ == '__main__':
    for name in sys.argv[sys.argv.index('--') + 1:]:
        STAGES[name]()
