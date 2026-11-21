"""Sprites for the 2D fight: Ògún and Ekwensu in seventeen poses each, and the Ofala backdrop.

Both fighters stand on the skeleton all fighters share (characters/gamekit.py), so the
poses are written once and given to both. Ògún is his game model. Ekwensu has no
game model yet, so one is put together here for these pictures only: his portrait's own
parts, carried back to the rest pose and hung on the shared skeleton at their full weight.
It is good for a render and far too heavy for a game engine.

    blender -b --factory-startup --python 2d-threejs/fight/make_sprites.py -- ekwensu frames sheets backdrop

    ekwensu    the posable Ekwensu, saved to the work folder
    frames     every pose of both fighters, one picture each, in the work folder; for the
               fire pose it also prints where the mouth is, which index.html needs
               (who=ogun or who=ekwensu for one fighter, only=idle0,ko for some poses)
    sheets     img/ogun.webp and img/ekwensu.webp: the pictures in a grid, six across
    backdrop   img/ofala.webp, from locations/ofala/Renders/Ofala_Front.png

Set GAME_WORK to a scratch folder; without it a work/ folder beside this script is used.
"""
import os
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / 'characters'))
import gamekit as gk  # noqa: E402

WORK = Path(os.environ.get('GAME_WORK', HERE / 'work'))
IMG = HERE / 'img'

# One cell of a sheet. The fighter faces right: forward (-Y) is to the right of the picture.
# index.html holds the same numbers.
PX_PER_M = 220
ALONG = (-1.6, 1.2)          # metres of the fight line a cell shows, front to back
UP = (-0.05, 2.40)           # metres of height
CELL = (round((ALONG[1] - ALONG[0]) * PX_PER_M), round((UP[1] - UP[0]) * PX_PER_M))     # 616 x 539
COLUMNS = 6

EK = REPO / '3d' / 'ekwensu'
CLOTH = ('Trousers', 'RaffiaFringe', 'RaffiaCord', 'Strap', 'BeadsBlack', 'BeadsRed', 'BeadsWhite')
ON_HEAD = ('OkpuAgu', 'Eye.L', 'Eye.R', 'Brows', 'EdgeHair', 'Lashes')
BANGLES = ('IronBangle.L.0', 'IronBangle.L.1', 'IronBangle.R.0', 'IronBangle.R.1')
POUCH = ('Pouch', 'PouchFlap', 'PouchToggle')
MACHETE = ('Mma', 'MmaFittings', 'MmaHandle')
LEGS = ['pelvis', 'thigh_l', 'thigh_r', 'calf_l', 'calf_r', 'spine_01']
HIPS = ['pelvis', 'thigh_l', 'thigh_r', 'spine_01']
TRUNK = ['spine_03', 'spine_02', 'spine_01', 'pelvis', 'clavicle_l', 'clavicle_r', 'neck_01']


def smoothstep(x, a, b):
    t = np.clip((np.asarray(x, np.float64) - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ----- a posable Ekwensu ------------------------------------------------------

def on_bone(ob, rig, bone):
    """Hang an object from a bone, where it stands."""
    world = ob.matrix_world.copy()
    ob.parent, ob.parent_type, ob.parent_bone = rig, 'BONE', bone
    bpy.context.view_layer.update()
    ob.matrix_world = world


def skinned(ob, rig, W, names):
    gk.set_weights(ob, W, names)
    m = ob.modifiers.new('Armature', 'ARMATURE')
    m.object = rig
    ob.modifiers.move(len(ob.modifiers) - 1, 0)
    ob.parent = rig
    ob.matrix_world = Matrix.Identity(4)


def stage_ekwensu():
    body, rig = gk.game_body(EK / 'blender')
    body.name = body.data.name = 'EkwensuBody'
    col = gk.collection('Ekwensu')
    for ob in (body, rig):
        gk.link(ob, col)

    got = gk.append(EK / 'ekwensu.blend', objects=('Body', 'Rig') + CLOTH + ON_HEAD + BANGLES + POUCH + MACHETE)
    missing = [n for n in ('Body', 'Rig') + CLOTH + ON_HEAD + BANGLES + POUCH + MACHETE if n not in got]
    assert not missing, missing
    for ob in got.values():
        gk.link(ob, col)
    bpy.context.view_layer.update()
    for ob in got.values():                    # off the turntable, each where it stands
        if ob.parent is not None and ob.parent not in got.values():
            world = ob.matrix_world.copy()
            ob.parent = None
            ob.matrix_world = world
    for ob in list(bpy.data.objects):          # the turntable itself, and anything else that came along
        if ob not in got.values() and ob not in (body, rig):
            bpy.data.objects.remove(ob)
    bpy.context.view_layer.update()
    pbody, prig = got['Body'], got['Rig']
    assert np.allclose(np.array(prig.matrix_world), np.eye(4), atol=1e-5), 'the portrait rig is not at the origin'
    apart = float(np.abs(gk.coords(pbody.data) - gk.coords(body.data)).max())
    print('rest pose differs from the portrait by', apart, 'm', flush=True)
    assert apart < 1e-5

    # the skin: the portrait's material, what it reads from the mesh, and the part the trousers hide
    body.data.materials.clear()
    body.data.materials.append(pbody.data.materials[0])
    for ca in pbody.data.color_attributes:
        if ca.name not in body.data.color_attributes and ca.domain == 'POINT':
            a = np.empty(len(pbody.data.vertices) * 4, np.float32)
            ca.data.foreach_get('color', a)
            body.data.color_attributes.new(ca.name, ca.data_type, 'POINT').data.foreach_set('color', a)
    for m in pbody.modifiers:
        if m.type == 'MASK' and m.vertex_group:
            src = pbody.vertex_groups[m.vertex_group].index
            vg = body.vertex_groups.new(name=m.vertex_group)
            vg.add([v.index for v in pbody.data.vertices if any(g.group == src and g.weight > 0.5 for g in v.groups)], 1.0, 'REPLACE')
            mask = body.modifiers.new('Mask', 'MASK')
            mask.vertex_group, mask.invert_vertex_group = m.vertex_group, m.invert_vertex_group
    body.modifiers.new('Smooth', 'SUBSURF').render_levels = 1

    un = gk.Unposer(pbody, prig)
    binder = gk.Binder(body, rig)
    names = binder.names

    for name in CLOTH:
        ob = got[name]
        rest = un.points(gk.world_coords(ob), un.trunk)
        gk.set_coords(ob.data, rest)
        if name == 'Trousers':
            W = binder.at(rest, LEGS)
        elif name in ('RaffiaFringe', 'RaffiaCord'):
            W = binder.at(rest, HIPS)
            # the lower a strand hangs the more it keeps to the hips, so a raised thigh lifts it without carrying it out straight
            lag = (0.35 * smoothstep(rest[:, 2].max() - rest[:, 2], 0.10, 0.50))[:, None]
            hips = np.zeros_like(W)
            hips[:, names.index('pelvis')] = 1.0
            W = (1 - lag) * W + lag * hips
        else:
            W = binder.at(rest, TRUNK)
        skinned(ob, rig, W, names)
        print(f'  {name:14} {len(rest):7} points on', int((W.sum(0) > 0).sum()), 'bones', flush=True)

    head_back = np.linalg.inv(un.bone['head'])
    for name in ON_HEAD:
        ob = got[name]
        ob.matrix_world = Matrix((head_back @ np.array(ob.matrix_world)).tolist())
        on_bone(ob, rig, 'head')
    for name in BANGLES:
        ob = got[name]
        world = np.array(ob.matrix_world)
        ob.matrix_world = Matrix((un.rigid(world[:3, 3]) @ world).tolist())
        on_bone(ob, rig, 'lowerarm_' + name.split('.')[1].lower())
    centre = gk.world_coords(got['Pouch']).mean(0)
    back = un.rigid(centre, un.trunk)
    carried = names[int(np.argmax(binder.at([gk.transform(centre[None], back)[0]], TRUNK)[0]))]
    for name in POUCH:
        ob = got[name]
        ob.matrix_world = Matrix((back @ np.array(ob.matrix_world)).tolist())
        on_bone(ob, rig, carried)
    print('  the pouch rides', carried, flush=True)
    hand_back = np.linalg.inv(un.bone['wrist.R'])
    mma = got['Mma']
    mma.matrix_world = Matrix((hand_back @ np.array(mma.matrix_world)).tolist())
    on_bone(mma, rig, 'hand_r')
    mma.name = 'Blade'

    for ob in (pbody, prig):
        bpy.data.objects.remove(ob)
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    WORK.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(WORK / 'ekwensu_posable.blend'), compress=True)
    print('saved', WORK / 'ekwensu_posable.blend', flush=True)


# ----- the poses, written once for both ----------------------------------------

GUARD = dict(pelvis=(0, 0, -0.075), turn=-32, twist=10, lean=6, pitch=0, head=22, nod=0,
             foot_l=(0.20, -0.30, 0), yaw_l=-8, knee_l=(0.25, -1, 0), flat_l=True,
             foot_r=(-0.22, 0.30, 0), yaw_r=-48, knee_r=(-0.6, -1, 0), flat_r=True,
             hand_l=(0.16, -0.46, 1.50), elbow_l=(0.4, 0.2, -1),
             hand_r=(-0.26, -0.22, 1.32), elbow_r=(-0.5, 0.4, -1), blade=(0, -0.55, 1))

# Places are in metres on Ògún and are brought to each figure's own size. x is to the figure's
# left, -y is forward, a foot's third number is how far it is lifted, a hand's is its height.
POSES = [
    ('idle0', {}),
    ('idle1', dict(pelvis=(0, 0, -0.095), hand_l=(0.16, -0.45, 1.475), hand_r=(-0.26, -0.22, 1.30))),
    ('walk0', dict(pelvis=(0, -0.03, -0.055), foot_l=(0.20, -0.22, 0.07), foot_r=(-0.22, 0.26, 0))),
    ('walk1', dict(pelvis=(0, 0.02, -0.05), foot_l=(0.20, -0.26, 0), foot_r=(-0.22, 0.12, 0.07))),
    ('slash0', dict(turn=-14, twist=26, lean=-3, hand_l=(0.10, -0.50, 1.40),
                    hand_r=(-0.36, 0.16, 1.84), elbow_r=(-1, 0.6, 0.2), blade=(0, 0.7, 0.7))),
    ('slash1', dict(pelvis=(0, -0.15, -0.13), turn=-56, twist=-16, lean=15, foot_l=(0.20, -0.48, 0),
                    hand_l=(0.32, -0.08, 1.22), elbow_l=(1, 0.6, -0.4),
                    hand_r=(-0.04, -0.80, 1.24), elbow_r=(-0.6, 0.2, -1), blade=(0, -1, -0.22))),
    ('kick0', dict(pelvis=(0, 0.03, -0.03), pitch=-5, turn=-20, foot_l=(0.12, 0.08, 0), yaw_l=15, knee_l=(0.2, -1, 0),
                   foot_r=(-0.13, -0.32, 0.55), knee_r=(0, -1, 1), flat_r=False,
                   hand_l=(0.24, -0.34, 1.44), hand_r=(-0.36, 0.02, 1.20), blade=(0, 0.3, 1))),
    ('kick1', dict(pelvis=(0, 0.05, 0.0), pitch=-13, turn=-20, foot_l=(0.12, 0.10, 0), yaw_l=20, knee_l=(0.2, -1, 0),
                   foot_r=(-0.13, -0.92, 0.95), knee_r=(0, -0.3, 1), flat_r=False,
                   hand_l=(0.26, -0.30, 1.42), elbow_l=(0.5, 0.2, -1),
                   hand_r=(-0.42, 0.12, 1.12), elbow_r=(-0.4, 0.6, -0.4), blade=(0, 0.6, 0.8))),
    ('block', dict(pelvis=(0, 0.05, -0.10), lean=-3, head=12, hand_l=(0.10, -0.36, 1.60), elbow_l=(0.6, 0, -1),
                   hand_r=(-0.12, -0.36, 1.46), elbow_r=(-0.6, 0, -1), blade=(0.35, -0.15, 1))),
    ('hit', dict(pelvis=(0, 0.12, -0.05), turn=-18, twist=4, lean=-17, pitch=-7, head=4, nod=-16, foot_r=(-0.22, 0.42, 0),
                 hand_l=(0.38, -0.20, 1.20), elbow_l=(1, 0.4, -0.5),
                 hand_r=(-0.42, -0.02, 1.10), elbow_r=(-1, 0.5, -0.3), blade=(0, -0.7, -0.5))),
    ('ko', dict(down=True)),
    ('win', dict(pelvis=(0, 0, -0.01), turn=-22, twist=6, lean=-2, head=18, foot_l=(0.16, -0.10, 0), yaw_l=-6,
                 foot_r=(-0.16, 0.10, 0), yaw_r=-34, hand_l=(0.30, -0.02, 1.04), elbow_l=(1, 0.6, 0),
                 hand_r=(-0.30, -0.10, 1.80), elbow_r=(-1, 0.3, 0), blade=(0, -0.4, 1))),
    # bent down, under a slash and under fire
    ('crouch', dict(pelvis=(0, 0.04, -0.52), lean=20, knee_l=(0.4, -1, 0.2), knee_r=(-0.8, -1, 0.2),
                    hand_l=(0.16, -0.42, 1.00), hand_r=(-0.26, -0.18, 0.86), blade=(0, -0.4, 1))),
    # from the crouch, the right leg swept out along the ground
    ('sweep', dict(pelvis=(0, 0.12, -0.56), turn=-20, twist=0, pitch=-14, lean=4,
                   foot_l=(0.24, 0.10, 0), yaw_l=30, knee_l=(0.8, -1, 0.3),
                   foot_r=(-0.08, -1.05, 0), knee_r=(0, -0.2, 1), flat_r=False,
                   hand_l=(0.34, 0.40, 0.35), elbow_l=(1, 1, 0), hand_r=(-0.36, 0.05, 0.95), blade=(0, 0.2, 1))),
    # in the air, knees drawn up. The game lifts the picture; here the toes hang just above the ground
    ('jump', dict(pelvis=(0, 0, -0.19), lean=12, foot_l=(0.18, -0.16, 0.13), flat_l=False, knee_l=(0.3, -1, 0.3),
                  foot_r=(-0.20, 0.16, 0.13), flat_r=False, knee_r=(-0.5, -1, 0.3),
                  hand_l=(0.20, -0.36, 1.30), hand_r=(-0.30, -0.10, 1.22), blade=(0, -0.3, 1))),
    # in the air, the right leg driven out and down
    ('flykick', dict(pelvis=(0, 0.05, -0.22), turn=-24, pitch=-16, lean=2,
                     foot_l=(0.16, 0.16, 0.22), flat_l=False, knee_l=(0.3, -1, 0.6),
                     foot_r=(-0.10, -0.95, 0.30), flat_r=False, knee_r=(0, -0.3, 1),
                     hand_l=(0.28, -0.20, 1.22), hand_r=(-0.42, 0.22, 1.25), elbow_r=(-0.5, 0.8, -0.3), blade=(0, 0.6, 0.8))),
    # leaning in to breathe fire, the arms thrown back
    ('fire', dict(pelvis=(0, -0.06, -0.12), turn=-30, twist=8, lean=24, nod=-14, foot_l=(0.20, -0.36, 0),
                  hand_l=(0.42, 0.10, 1.00), elbow_l=(1, 1, 0.3), hand_r=(-0.44, 0.24, 1.00), elbow_r=(-1, 1, 0.3),
                  blade=(0, 0.7, -0.4))),
]
MOUTH = (0.0, -0.095, -0.040)        # the lips from the start of the head bone at rest, on Ògún


def blade_tip(rig, blade):
    """The point of the blade farthest from the hand and the way its flat faces, both in the blade's own space."""
    world = gk.world_coords(blade)
    far = int(np.argmax(np.linalg.norm(world - np.array(rig.pose.bones['hand_r'].matrix.translation), axis=1)))
    co = gk.coords(blade.data)
    _, _, axes = np.linalg.svd(co - co.mean(0), full_matrices=False)
    return blade.data.vertices[far].co.copy(), Vector(axes[2])           # the thinnest way through a blade is across its flat


def aim_blade(rig, blade, tip, direction):
    """Turn the right hand at the wrist until the blade points along direction with its flat to the camera.

    The camera looks along the fight line's side, so a blade swung in the plane of the fight
    shows its whole width, as one swung edge first would.
    """
    point, flat = tip
    direction = Vector(direction).normalized()
    hand = rig.pose.bones['hand_r']

    def turn(q):
        pivot = hand.matrix.translation.copy()
        hand.matrix = Matrix.Translation(pivot) @ q.to_matrix().to_4x4() @ Matrix.Translation(-pivot) @ hand.matrix
        bpy.context.view_layer.update()

    bpy.context.view_layer.update()
    turn(((blade.matrix_world @ point) - hand.matrix.translation).normalized().rotation_difference(direction))
    side = Vector((1, 0, 0)) - direction.x * direction
    if side.length > 0.2:
        faces = blade.matrix_world.to_3x3() @ flat
        faces = (faces - faces.dot(direction) * direction).normalized()
        side.normalize()
        turn(faces.rotation_difference(side if faces.dot(side) >= 0 else -side))


def lowest(meshes):
    dg = bpy.context.evaluated_depsgraph_get()
    low = 1e9
    for ob in meshes:
        ev = ob.evaluated_get(dg)
        co = np.empty(len(ev.data.vertices) * 3)
        ev.data.vertices.foreach_get('co', co)
        low = min(low, float(gk.transform(co.reshape(-1, 3), np.array(ev.matrix_world))[:, 2].min()))
    return low


def strike(rig, blade, tip, body, changes):
    """Put the rig in the guard with the changes a pose makes to it."""
    p = dict(GUARD, **changes)
    at = gk._own_size(rig)
    P, B = rig.pose.bones, rig.data.bones
    gk.clear_pose(rig)
    pelvis = P['pelvis']
    if p.get('down'):
        # flat on the back, head away from the other fighter
        gk.spin(pelvis, (1, 0, 0), -88)
        pelvis.matrix = Matrix.Translation(Vector(at(0, 0.25, 0.16)) - pelvis.matrix.translation) @ pelvis.matrix
        bpy.context.view_layer.update()
        gk.spin(P['neck_01'], (1, 0, 0), 10)
        gk.reach_limb(rig, 'thigh_l', 'calf_l', 'foot_l', at(0.16, -0.42, 0.10), (0, 0, 1))
        gk.reach_limb(rig, 'upperarm_l', 'lowerarm_l', 'hand_l', at(0.55, 0.55, 0.10), (1, -0.3, 0.2))
        gk.reach_limb(rig, 'upperarm_r', 'lowerarm_r', 'hand_r', at(-0.50, 0.20, 0.10), (-1, 0.3, 0.2))
        aim_blade(rig, blade, tip, (-0.3, -1, 0.05))
        pelvis.matrix = Matrix.Translation((0, 0, -lowest([body]))) @ pelvis.matrix
        bpy.context.view_layer.update()
        return
    pelvis.matrix = Matrix.Translation(at(*p['pelvis'])) @ pelvis.matrix
    bpy.context.view_layer.update()
    gk.spin(pelvis, (0, 0, 1), p['turn'])
    across = Matrix.Rotation(np.radians(p['turn']), 3, 'Z') @ Vector((1, 0, 0))
    if p['pitch']:
        gk.spin(pelvis, across, p['pitch'])
    gk.spin(P['spine_02'], (0, 0, 1), p['twist'])
    across = Matrix.Rotation(np.radians(p['turn'] + p['twist']), 3, 'Z') @ Vector((1, 0, 0))
    gk.spin(P['spine_03'], across, p['lean'])
    ankle = B['foot_l'].head_local.z
    for s in 'lr':
        x, y, lift = at(*p['foot_' + s])
        gk.reach_limb(rig, 'thigh_' + s, 'calf_' + s, 'foot_' + s, (x, y, ankle + lift), p['knee_' + s])
        if p['flat_' + s]:
            gk.level_foot(rig, s, p['yaw_' + s])
    for s in 'lr':
        gk.reach_limb(rig, 'upperarm_' + s, 'lowerarm_' + s, 'hand_' + s, at(*p['hand_' + s]), p['elbow_' + s])
    gk.spin(P['head'], (0, 0, 1), p['head'])
    if p['nod']:
        gk.spin(P['head'], across, p['nod'])
    for s in 'lr':
        gk.close_hand(rig, s)
    aim_blade(rig, blade, tip, p['blade'])


# ----- pictures ----------------------------------------------------------------

def daylight(samples):
    """The light of the Ofala arena's own render: a high sun from the camera's side, and the sky."""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.resolution_x, sc.render.resolution_y = CELL
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    world = bpy.data.worlds.new('Sky')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.62, 0.74, 1.0, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9
    sc.world = world
    col = gk.collection('Light')
    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN'))
    sun.data.energy, sun.data.color, sun.data.angle = 4.8, (1.0, 0.95, 0.86), np.radians(3)
    sun.rotation_euler = Vector((0.62, -0.38, -0.70)).to_track_quat('-Z', 'Y').to_euler()
    col.objects.link(sun)
    # the earth of the arena throws warm light back up
    earth = bpy.data.objects.new('Earth', bpy.data.lights.new('Earth', 'AREA'))
    earth.data.energy, earth.data.color, earth.data.size = 500, (1.0, 0.72, 0.5), 6
    earth.location = (-1.5, -0.2, -1.2)
    earth.rotation_euler = (Vector((-1.5, -0.2, -1.2)) - Vector((0, -0.2, 1.0))).to_track_quat('Z', 'Y').to_euler()
    col.objects.link(earth)
    cam = bpy.data.objects.new('SideCamera', bpy.data.cameras.new('SideCamera'))
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = ALONG[1] - ALONG[0]
    middle = Vector((0, (ALONG[0] + ALONG[1]) / 2, (UP[0] + UP[1]) / 2))
    cam.location = middle + Vector((-12, 0, 0))
    cam.rotation_euler = Vector((1, 0, 0)).to_track_quat('-Z', 'Y').to_euler()
    col.objects.link(cam)
    sc.camera = cam


def fighter(who):
    """Open a fighter's file. Returns the rig, the blade and the body's mesh."""
    if who == 'ogun':
        bpy.ops.wm.open_mainfile(filepath=str(REPO / 'characters' / 'ogun' / 'SK_Ogun.blend'))
        return bpy.data.objects['Armature'], bpy.data.objects['SM_Ogun_Ada'], bpy.data.objects['SK_Ogun']
    bpy.ops.wm.open_mainfile(filepath=str(WORK / 'ekwensu_posable.blend'))
    return bpy.data.objects['Armature'], bpy.data.objects['Blade'], bpy.data.objects['EkwensuBody']


def stage_frames(who=None, only=None, samples=40):
    out = WORK / 'frames'
    out.mkdir(parents=True, exist_ok=True)
    wanted = only.split(',') if only else [name for name, _ in POSES]
    for name in ([who] if who else ['ogun', 'ekwensu']):
        rig, blade, body = fighter(name)
        daylight(int(samples))
        tip = blade_tip(rig, blade)
        sc = bpy.context.scene
        for pose, changes in POSES:
            if pose not in wanted:
                continue
            strike(rig, blade, tip, body, changes)
            sc.render.filepath = str(out / f'{name}_{pose}.png')
            bpy.ops.render.render(write_still=True)
            print('frame', name, pose, 'lowest point', round(lowest([body]) * 1000, 1), 'mm', flush=True)
            if pose == 'fire':
                # where the fire starts: the game draws it, from the mouth, in pixels forward of the feet and above them
                head = rig.data.bones['head']
                lips = head.head_local + Vector(gk._own_size(rig)(*MOUTH))
                lips = rig.pose.bones['head'].matrix @ head.matrix_local.inverted() @ lips
                print('mouth', name, 'forward', round(-lips.y * PX_PER_M), 'up', round(lips.z * PX_PER_M), 'pixels', flush=True)


def stage_sheets():
    IMG.mkdir(exist_ok=True)
    rows = -(-len(POSES) // COLUMNS)
    for name in ('ogun', 'ekwensu'):
        sheet = np.zeros((rows * CELL[1], COLUMNS * CELL[0], 4), np.float32)
        for k, (pose, _) in enumerate(POSES):
            img = bpy.data.images.load(str(WORK / 'frames' / f'{name}_{pose}.png'))
            tile = gk.pixels(img).copy()
            bpy.data.images.remove(img)
            assert tile.shape[:2] == (CELL[1], CELL[0]), tile.shape
            r, c = divmod(k, COLUMNS)
            top = (rows - 1 - r) * CELL[1]                 # arrays are bottom-up, the sheet reads top-down
            sheet[top:top + CELL[1], c * CELL[0]:(c + 1) * CELL[0]] = tile
        save_webp(sheet, IMG / f'{name}.webp', 90)


def save_webp(a, path, quality):
    h, w = a.shape[:2]
    img = bpy.data.images.new('out', w, h, alpha=a.shape[2] == 4)
    if a.shape[2] == 3:
        a = np.dstack([a, np.ones((h, w), np.float32)])
    img.pixels.foreach_set(np.ascontiguousarray(a, np.float32).ravel())
    img.file_format = 'WEBP'
    img.filepath_raw = str(path)
    img.save(quality=quality)
    bpy.data.images.remove(img)
    print('wrote', path, f'{w} x {h},', round(Path(path).stat().st_size / 1e3), 'kB', flush=True)


def stage_backdrop():
    IMG.mkdir(exist_ok=True)
    img = bpy.data.images.load(str(REPO / 'locations' / 'ofala' / 'Renders' / 'Ofala_Front.png'))
    a = gk.pixels(img)[..., :3].copy()
    bpy.data.images.remove(img)
    save_webp(a, IMG / 'ofala.webp', 86)


STAGES = dict(ekwensu=stage_ekwensu, frames=stage_frames, sheets=stage_sheets, backdrop=stage_backdrop)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    named = dict(a.split('=', 1) for a in args if '=' in a)
    for stage in [a for a in args if '=' not in a]:
        if stage == 'frames':
            stage_frames(**{k: named[k] for k in ('who', 'only', 'samples') if k in named})
        else:
            STAGES[stage]()


main()
