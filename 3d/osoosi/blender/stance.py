"""His pose: drawing the bow, the arrow nocked and aimed up into the canopy.

The bow and arrow are his main symbols (Wikipedia: Oshosi), and his gallery figure draws the
bow as if to loose his single arrow. He stands side-on to his mark, the bow in his left hand at
arm's length and the string drawn back with the right to under his jaw, his head
turned to look along the arrow. The shot is aimed up, at something high in the trees.

An archer shooting upward bends at the waist and keeps the T of his shoulders and arms, so the
whole upper body is tilted along the shot. The draw is then built from the face outward: the
string hand is set under the jaw, where the string comes closest to the face without the hand pressing in;
the bow's grip is set ahead of it along the aim, a full draw away or as far as the bow arm reaches;
and the bow arm is solved to reach it.

The hands are held as an archer holds them. The drawing hand keeps its wrist straight, in line
with the forearm; the back of the hand stays flat, three fingers hooked on the string at their
first joints, the little finger folded and the thumb relaxed along the top of the index finger. The bow's handle sits in the
palm, against the pad at the base of the thumb, with the fingers wrapped loosely round its front
and the thumb laid forward over them. The drawing hand is turned nearly half round about the
forearm, which the ordinary skinning would wring thin, so the forearms are skinned to keep their volume.

He faces -Y; his left is +X, where the mark is.
"""
import math

import bpy
import numpy as np
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree

import dress
import pose as tk
from common import verts_world

AIM = Vector((1.0, -0.30, 0.30)).normalized()          # toward the mark: to his left, a little toward the camera, about 16 degrees up
DRAW_MAX = 0.66             # from the nock to the arrow's rest on the bow hand, at full draw
ARROW_OVER_GRIP = 0.040     # the arrow crosses the bow just above the top of the fist
TILT = (('spine05', 2.0), ('spine04', 3.2), ('spine03', 3.4), ('spine02', 2.8), ('spine01', 1.8))    # degrees, along the shot
HEAD_YAW = (('neck01', 24), ('neck02', 26), ('head', 24))           # as far round as the shot, so the arrow lies along his cheek
HEAD_PITCH = 3.0
# where the nock may sit, from the midpoint between the eyes in the head's rest frame: beside the right corner of the mouth
ANCHORS = [(x, y, z) for x in (-0.045, -0.055, -0.065, -0.075, -0.085) for y in (-0.020, 0.0, 0.020) for z in (-0.070, -0.085, -0.100, -0.115)]
ARM_CHAIN = ('upperarm01', 'upperarm02', 'lowerarm01', 'lowerarm02', 'wrist')
FORE_TWIST = (('lowerarm02', 0.5), ('wrist', 0.5))       # the hand's turn about the forearm, half in the forearm's far half and half at the wrist
FOREARM_VOLUME = (0.12, 0.30, 1.04, 1.18)       # along the forearm, elbow 0 to wrist 1: where preserve-volume skinning fades in and out
POLE = {'L': Vector((0.0, 0.45, -1.0)), 'R': Vector((-1.00, 0.55, -0.10))}      # the drawing elbow out beside his head
WRIST_STRAIGHT = 0.8      # how far the drawing hand follows the forearm's line rather than the arrow's
GRIP_REACH = 0.056        # the handle in the palm, against the pad at the base of the thumb, not hooked at the finger roots
GRIP_DEPTH = 0.031        # and far enough out that the palm meets the leather rather than sinking into it
FINGER_R = {2: 0.0090, 3: 0.0092, 4: 0.0088, 5: 0.0078}
CURL_RATE = (2.0, 3.0, 1.8)
CURL_LIMIT = (95, 100, 60)
HOOK = {2: (6, 72, 48), 3: (4, 76, 50), 4: (8, 74, 46), 5: (58, 88, 56)}      # the draw: knuckles flat, three fingers hooked at their first joints, the little finger folded


def bow_up():
    """The bow stands upright in the vertical plane of the shot."""
    z = Vector((0, 0, 1.0))
    return (z - z.dot(AIM) * AIM).normalized()


def pitch_axis():
    """About this axis a turn takes the line of sight up along the shot."""
    flat = Vector((AIM.x, AIM.y, 0)).normalized()
    return flat.cross(Vector((0, 0, 1))).normalized()


def pose_arm(rig, side, wrist, hand_dir, palm_dir, quiet=False, straight=0.0):
    """Solve an arm to put its wrist at wrist, then turn the hand along hand_dir with its palm toward palm_dir.
    straight (0 to 1) bends hand_dir that far toward the forearm's own line, for a wrist held straight.

    Every solve starts from rest, so no turn is carried over from the one before. The turn the hand needs
    about the forearm is shared between the forearm's far half and the hand; keep_forearms_round keeps
    the skin from being wrung thin by it.
    """
    P = rig.pose.bones
    B = rig.data.bones
    for name in ARM_CHAIN:
        P[f'{name}.{side}'].rotation_quaternion = (1, 0, 0, 0)
        P[f'{name}.{side}'].scale = (1, 1, 1)
    tk.update()
    shoulder = P[f'upperarm01.{side}'].matrix.translation.copy()
    la = (B[f'lowerarm01.{side}'].head_local - B[f'upperarm01.{side}'].head_local).length
    lb = (B[f'wrist.{side}'].head_local - B[f'lowerarm01.{side}'].head_local).length
    elbow = tk.two_bone(shoulder, wrist, la, lb, POLE[side])
    tk.aim(P[f'upperarm01.{side}'], elbow - shoulder)
    tk.aim(P[f'upperarm02.{side}'], elbow - P[f'upperarm02.{side}'].matrix.translation)
    tk.aim(P[f'lowerarm01.{side}'], wrist - P[f'lowerarm01.{side}'].matrix.translation)
    tk.aim(P[f'lowerarm02.{side}'], wrist - P[f'lowerarm02.{side}'].matrix.translation)
    if straight:
        hand_dir = hand_dir.lerp((wrist - elbow).normalized(), straight).normalized()
        palm_dir = (palm_dir - palm_dir.dot(hand_dir) * hand_dir).normalized()
    base = {n: P[f'{n}.{side}'].rotation_quaternion.copy() for n, _ in FORE_TWIST}

    def try_roll(a):
        for name, share in FORE_TWIST:
            P[f'{name}.{side}'].rotation_quaternion = base[name] @ Quaternion((0, 1, 0), a * share)
        tk.update()
        tk.aim_hand(rig, side, hand_dir)
        return tk.palm_normal(rig, side).dot(palm_dir)

    best = max((try_roll(math.radians(a)), a) for a in range(-180, 180, 10))[1]
    span = 5
    while span > 0.2:
        best = max((try_roll(math.radians(a)), a) for a in (best - span, best, best + span))[1]
        span /= 2
    match = try_roll(math.radians(best))
    if not quiet:
        print('arm', side, 'hand turned', best, 'about the forearm, palm match', round(match, 3), 'elbow', tuple(round(c, 3) for c in elbow), flush=True)


def smoothstep(a, b, x):
    s = np.clip((x - a) / (b - a), 0.0, 1.0)
    return s * s * (3 - 2 * s)


def keep_forearms_round(body, rig):
    """Skin the forearms so they keep their round when the hand is turned.

    The skin follows its bones by blending where they would carry it. Across a large turn about the
    forearm that blend cuts the corner, and the forearm comes out wrung thin; the drawing hand is turned
    nearly half round, and his right forearm lost two fifths of its girth before this. Blender's
    preserve-volume skinning blends the turns themselves, so it is mixed in along each forearm, from
    below the elbow to the heel of the hand, and faded out at both ends, where the bent elbow and
    fingers keep the ordinary skinning.
    """
    co = np.array([body.matrix_world @ v.co for v in body.data.vertices])
    weight = np.zeros(len(co))
    for side in 'LR':
        elbow = np.array(rig.matrix_world @ rig.data.bones[f'lowerarm01.{side}'].head_local)
        wrist = np.array(rig.matrix_world @ rig.data.bones[f'wrist.{side}'].head_local)
        d = wrist - elbow
        t = (co - elbow) @ d / (d @ d)
        a, b, c, e = FOREARM_VOLUME
        fore = np.clip(limb_weight(body, ('lowerarm', 'wrist'), side) * 2, 0, 1)
        weight = np.maximum(weight, smoothstep(a, b, t) * (1 - smoothstep(c, e, t)) * fore)
    group = body.vertex_groups.get('ForearmVolume') or body.vertex_groups.new(name='ForearmVolume')
    for i in np.nonzero(weight > 1e-3)[0]:
        group.add([int(i)], float(weight[i]), 'REPLACE')
    skin = next(m for m in body.modifiers if m.type == 'ARMATURE')
    mod = body.modifiers.get('Forearm volume') or body.modifiers.new('Forearm volume', 'ARMATURE')
    mod.object = skin.object
    mod.use_vertex_groups, mod.use_bone_envelopes = True, False
    mod.use_deform_preserve_volume = True
    mod.use_multi_modifier = True            # mixed with the ordinary skinning above it, by the group's weight
    mod.vertex_group = group.name
    body.modifiers.move(body.modifiers.find(mod.name), body.modifiers.find(skin.name) + 1)
    print('forearms kept round over', int((weight > 0.5).sum()), 'vertices', flush=True)


def grip_centre(rig, side):
    """Where a handle lies across the fist: a little beyond the wrist, in the curl of the fingers."""
    P = rig.pose.bones
    wrist = P[f'wrist.{side}'].matrix.translation
    return wrist + tk.hand_along(rig, side) * GRIP_REACH + tk.palm_normal(rig, side) * GRIP_DEPTH


def gap(tree, points):
    return min(tree.find_nearest(p)[3] for p in points)


def close_hand(rig, side, tree, up):
    """Fingers closing at all three joints at once until they rest on the bow's grip, then the thumb over the index finger."""
    P = rig.pose.bones
    along = tk.hand_along(rig, side)
    for k in (2, 3, 4, 5):
        names = [f'finger{k}-{j}.{side}' for j in (1, 2, 3)]
        y = P[names[0]].matrix.to_3x3() @ Vector((0, 1, 0))
        tk.aim(P[names[0]], y.lerp(along, 0.7))
        axis = tuple(tk.curl_axis(rig, side, names[0]))
        turned = [0.0, 0.0, 0.0]
        moving = [0, 1, 2]
        while moving:
            for j in list(moving):
                pb = P[names[j]]
                saved = pb.rotation_quaternion.copy()
                tk.spin(pb, axis, math.radians(CURL_RATE[j]))
                turned[j] += CURL_RATE[j]
                if turned[j] > CURL_LIMIT[j] or gap(tree, tk.finger_points(rig, names[j:])[2:]) < FINGER_R[k]:
                    pb.rotation_quaternion = saved
                    tk.update()
                    moving.remove(j)
        print('finger', side, k, 'closed', turned, flush=True)
    # the thumb lies over the index finger's middle bone, on the outside of the fist, without going round the grip
    names = [f'finger1-{j}.{side}' for j in (1, 2, 3)]
    mid = P[f'finger2-2.{side}'].head.lerp(P[f'finger2-2.{side}'].tail, 0.5)
    grip = grip_centre(rig, side)
    radial = mid - grip
    radial = (radial - radial.dot(up) * up).normalized()
    target = mid + radial * 0.011 + up * 0.009
    swing_thumb(rig, side, names, target, tree, 0.0066)
    walk_thumb(rig, names, target, tree, clear=0.0066)


def swing_thumb(rig, side, names, target, tree, clear):
    """Try the thumb's base turned about the hand's length and about the palm, the rest of it curled by steps;
    keep the pose that comes nearest the target without touching the grip. The walk then only has to finish it."""
    P = rig.pose.bones
    base = [P[n].rotation_quaternion.copy() for n in names]
    along = tuple(tk.hand_along(rig, side))
    palm = tuple(tk.palm_normal(rig, side))
    best = (9.0, None)
    for a1 in range(-80, 81, 10):
        for a2 in range(-60, 61, 15):
            for c in (0, 20, 40):
                for pb, q in zip((P[n] for n in names), base):
                    pb.rotation_quaternion = q
                    pb.scale = (1, 1, 1)
                tk.update()
                tk.spin(P[names[0]], along, math.radians(a1))
                tk.spin(P[names[0]], palm, math.radians(a2))
                if c:
                    axis = tuple(tk.curl_axis(rig, side, names[1]))
                    tk.spin(P[names[1]], axis, math.radians(c))
                    tk.spin(P[names[2]], axis, math.radians(c))
                d = (P[names[2]].tail - target).length
                if d < best[0] and gap(tree, tk.finger_points(rig, names)) > clear:
                    best = (d, [P[n].rotation_quaternion.copy() for n in names], (a1, a2, c))
    if best[1] is None:
        for pb, q in zip((P[n] for n in names), base):
            pb.rotation_quaternion = q
    else:
        for n, q in zip(names, best[1]):
            P[n].rotation_quaternion = q
        print('thumb swung', best[2], 'to within', round(best[0], 4), flush=True)
    for n in names:
        P[n].scale = (1, 1, 1)
    tk.update()


def walk_thumb(rig, names, target, tree=None, clear=0.0080, quiet=False):
    P = rig.pose.bones

    def miss():
        return (P[names[2]].tail - target).length

    step = math.radians(4)
    for _ in range(80):
        before = miss()
        for name in names:
            for ax in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
                for sign in (1, -1):
                    saved = P[name].rotation_quaternion.copy()
                    base = miss()
                    tk.spin(P[name], ax, sign * step)
                    for n in names:                   # keep scale from creeping over hundreds of turns
                        P[n].scale = (1, 1, 1)
                    tk.update()
                    if miss() < base and (tree is None or gap(tree, tk.finger_points(rig, names)) > clear):
                        break
                    P[name].rotation_quaternion = saved
                    tk.update()
        if before - miss() < 2e-4:
            step *= 0.6
            if step < math.radians(0.5):
                break
    if not quiet:
        print('thumb misses by', round(miss(), 4), flush=True)


def hook_hand(rig, side, thumb=True, face=None):
    """The drawing hand: three fingers hooked round the string at their first joints, the little finger folded,
    the thumb relaxed along the top of the index finger. Given the face, the thumb keeps clear of it."""
    P = rig.pose.bones
    along = tk.hand_along(rig, side)
    for k, angles in HOOK.items():
        names = [f'finger{k}-{j}.{side}' for j in (1, 2, 3)]
        y = P[names[0]].matrix.to_3x3() @ Vector((0, 1, 0))
        tk.aim(P[names[0]], y.lerp(along, 0.6))
        axis = tuple(tk.curl_axis(rig, side, names[0]))
        for name, a in zip(names, angles):
            tk.spin(P[name], axis, math.radians(a))
    if thumb:
        names = [f'finger1-{j}.{side}' for j in (1, 2, 3)]
        palm = tk.palm_normal(rig, side)
        # with his palm against his jaw there is no room to tuck the thumb under: it lies along the top of the index finger
        target = P[f'finger2-2.{side}'].head + bow_up() * 0.012 - palm * 0.006
        if face is not None:
            swing_thumb(rig, side, names, target, face, 0.0085)
        walk_thumb(rig, names, target, face, clear=0.0085)


def unhook(rig, side):
    """Straighten the fingers. Scale is reset too: setting bone matrices over and over lets it creep, and it compounds down a finger."""
    P = rig.pose.bones
    for k in (1, 2, 3, 4, 5):
        for j in (1, 2, 3):
            pb = P[f'finger{k}-{j}.{side}']
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.scale = (1, 1, 1)
            pb.location = (0, 0, 0)
    tk.update()


def pocket(rig, side, k):
    """Where the string lies in a hooked finger: in the crook of its last joint, on the inside of the hook."""
    P = rig.pose.bones
    mid, tip = P[f'finger{k}-2.{side}'], P[f'finger{k}-3.{side}']
    inside = (tip.tail - tip.head).normalized() - (mid.tail - mid.head).normalized()
    if inside.length < 1e-3:
        inside = tk.palm_normal(rig, side)
    return tip.head + inside.normalized() * (FINGER_R[k] * 0.85 + 0.0013)


def string_point(rig, side):
    """The nock: on the string between the index and middle fingers, as in the Mediterranean draw."""
    return (pocket(rig, side, 2) + pocket(rig, side, 3)) / 2


def string_path(rig, side):
    """The string's way across the drawing hand, top to bottom: index finger, nock, middle and ring fingers."""
    return [pocket(rig, side, 2), string_point(rig, side), pocket(rig, side, 3), pocket(rig, side, 4)]


def arrow_rest(rig, grip, up, body=None, nock=None, shaft_r=0.0044):
    """Where the arrow lies on the bow hand: on top of the fist, just to his left of the bow.

    Given the body and the nock, it is raised from there until the shaft clears the skin of the fist
    and the thumb over it, so it rests on the hand rather than through it.
    """
    left = up.cross(AIM).normalized()
    rest = grip + up * ARROW_OVER_GRIP + left * 0.022
    if body is None:
        return rest
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    tree = BVHTree.FromPolygons([ev.matrix_world @ v.co for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
    ev.to_mesh_clear()
    for k in range(40):
        lift = k * 0.002
        point = rest + up * lift
        d = (point - nock).normalized()
        clear = min(tree.find_nearest(point + d * s)[3] for s in np.linspace(-0.12, 0.08, 41))
        if clear > shaft_r + 0.0012:
            break
    print('arrow rest raised', round(lift * 1000), 'mm to clear the fist by', round((clear - shaft_r) * 1000, 1), 'mm', flush=True)
    return point


def draw_hand_to(rig, nock, thumb=False, face=None):
    """Pose the drawing arm so the nock lies between the hooked index and middle fingers. Returns the miss."""
    palm_r = Vector((0, 1, 0))
    palm_r = (palm_r - palm_r.dot(AIM) * AIM).normalized()
    wrist = nock - AIM * 0.082 - palm_r * 0.014
    for _ in range(4):
        unhook(rig, 'R')
        pose_arm(rig, 'R', wrist, AIM, palm_r, quiet=True, straight=WRIST_STRAIGHT)
        hook_hand(rig, 'R', thumb=False, face=face)
        wrist = wrist + (nock - string_point(rig, 'R'))
    unhook(rig, 'R')
    pose_arm(rig, 'R', wrist, AIM, palm_r, quiet=not thumb, straight=WRIST_STRAIGHT)
    hook_hand(rig, 'R', thumb=thumb, face=face)
    return (string_point(rig, 'R') - nock).length


def limb_weight(body, keys, side=None):
    groups = {g.index for g in body.vertex_groups if any(k in g.name for k in keys) and (side is None or g.name.endswith('.' + side))}
    return np.array([sum(g.weight for g in v.groups if g.group in groups) for v in body.data.vertices])


def find_anchor(rig, body, up):
    """Try nocks round the right corner of his jaw and under it; of those whose fingers do not press into his face, keep the one that brings the string closest to it.

    The string near the hand and the arrow along his cheek must stay clear of the face too.
    """
    info = eval(body['eyes'])
    eyes = (Vector(info['L']['centre']) + Vector(info['R']['centre'])) / 2
    M = dress.head_matrix(rig)
    rest = np.array([v.co for v in body.data.vertices])
    arm = limb_weight(body, ('upperarm', 'lowerarm', 'wrist', 'finger', 'metacarpal'))
    right_arm = limb_weight(body, ('upperarm', 'lowerarm', 'wrist', 'finger', 'metacarpal'), 'R')
    head = right_arm < 0.3                # the whole body but the drawing arm: closed round the face, so inside and outside are clear
    trunk = (rest[:, 2] > 1.20) & (arm < 0.2)
    # the thumb is left out while searching: straight, as it is then, it points at his face; it is placed last
    hand = np.nonzero((limb_weight(body, ('wrist', 'finger', 'metacarpal'), 'R') > 0.5) & (limb_weight(body, ('finger1',), 'R') < 0.3))[0]
    thumb = np.nonzero(limb_weight(body, ('finger1',), 'R') > 0.3)[0]
    fore = np.nonzero(limb_weight(body, ('lowerarm',), 'R') > 0.5)[0]
    co = verts_world(body)
    vs = [Vector(c) for c in co]
    tree = BVHTree.FromPolygons(vs, [tuple(p.vertices) for p in body.data.polygons if all(head[i] for i in p.vertices)])
    body_tree = BVHTree.FromPolygons(vs, [tuple(p.vertices) for p in body.data.polygons if all(trunk[i] for i in p.vertices)])

    def signed(p, t=tree):
        loc, nrm, _, d = t.find_nearest(Vector(p))
        if loc is None:
            return 1.0
        return d if (Vector(p) - loc).dot(nrm) >= 0 else -d

    side_dir = (AIM - AIM.dot(up) * up).normalized()
    best, fallback = None, None
    for off in ANCHORS:
        nock = M @ (eyes + Vector(off))
        miss = draw_hand_to(rig, nock)
        co = verts_world(body)
        touch = min(signed(co[i]) for i in hand)
        forearm = min(signed(co[i], body_tree) for i in fore)
        grip = nock + AIM * DRAW_MAX - up * ARROW_OVER_GRIP
        top = grip + up * 0.50 - side_dir * 0.30
        low = grip - up * 0.50 - side_dir * 0.30
        string = [nock + (end - nock).normalized() * s for end in (top, low) for s in np.linspace(0.0, 0.12, 13)]
        arrow = [nock + AIM * s for s in np.linspace(0.0, 0.30, 31)]
        clear_string = min(tree.find_nearest(p)[3] for p in string)
        clear_arrow = min(tree.find_nearest(p)[3] for p in arrow)
        ok = touch > -0.0010 and clear_string > 0.0030 and clear_arrow > 0.0065 and miss < 0.008
        score = clear_string + 0.5 * max(touch - 0.002, 0.0)        # the string close by his mouth, the hand resting on his face
        print('anchor', off, 'fingers', round(touch * 1000, 1), 'mm, forearm', round(forearm * 1000, 1), 'mm, string', round(clear_string * 1000, 1), 'mm, arrow',
              round(clear_arrow * 1000, 1), 'mm, miss', round(miss * 1000, 1), 'mm', 'ok' if ok else '', flush=True)
        if ok and (best is None or score < best[0]):
            best = (score, nock, off)
        if fallback is None or touch > fallback[0]:
            fallback = (touch, nock, off)
    _, nock, off = best or (None, fallback[1], fallback[2])
    print('anchor chosen', off, flush=True)
    draw_hand_to(rig, nock, thumb=True, face=tree)
    co = verts_world(body)
    print('drawing hand rests', round(min(signed(co[i]) for i in hand) * 1000, 1), 'mm off his face; thumb',
          round(min(signed(co[i]) for i in thumb) * 1000, 1), 'mm', flush=True)
    return nock


def solve(rig, body):
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    tk.update()
    P = rig.pose.bones
    B = rig.data.bones

    # feet planted across the line of the shot, a little wider than the hips
    ankle_z = {s: B[f'foot.{s}'].head_local.z for s in 'LR'}
    tk.pose_leg(rig, 'L', Vector((0.165, -0.040, ankle_z['L'])), math.radians(14))
    tk.pose_leg(rig, 'R', Vector((-0.150, 0.045, ankle_z['R'])), math.radians(-10))
    # the upper body bent at the waist along the shot, so the shoulders and arms keep their T
    axis = tuple(pitch_axis())
    for name, deg in TILT:
        tk.spin(P[name], axis, math.radians(deg))
    # the head turned to the mark and tipped a little further up along the shot
    for name, yaw in HEAD_YAW:
        tk.spin(P[name], (0, 0, 1), math.radians(yaw))
    tk.spin(P['head'], axis, math.radians(HEAD_PITCH))

    up = bow_up()
    nock = find_anchor(rig, body, up)

    # the bow arm: the palm turned to the front, so the fist closes round an upright grip; the grip
    # a full draw ahead of the nock, or as far as the arm reaches
    palm_l = Vector((0, -1, 0))
    palm_l = (palm_l - palm_l.dot(AIM) * AIM).normalized()
    draw = DRAW_MAX
    for _ in range(5):
        grip = nock + AIM * draw - up * ARROW_OVER_GRIP
        wrist = grip - AIM * GRIP_REACH - palm_l * GRIP_DEPTH
        for _ in range(3):                                    # the fist's real grip point differs a little from the guess: correct and solve again
            pose_arm(rig, 'L', wrist, AIM, palm_l, quiet=True)
            wrist = wrist + (grip - grip_centre(rig, 'L'))
        pose_arm(rig, 'L', wrist, AIM, palm_l)
        short = (grip - grip_centre(rig, 'L')).dot(AIM)
        print('draw', round(draw, 3), 'bow grip short by', round(short, 4), 'misses by', round((grip_centre(rig, 'L') - grip).length, 4), flush=True)
        if short < 0.003:
            break
        draw -= short + 0.003
    return grip_centre(rig, 'L'), string_point(rig, 'R')


def take_up_bow(rig, body, props):
    """Solve the draw, stand the bow in the bow hand and close the fist on its grip.

    What the dress stage needs to string the bow and nock the arrow is kept on the bow as a property.
    """
    import bow as gear
    keep_forearms_round(body, rig)
    grip, nock = solve(rig, body)
    up = bow_up()
    draw = (grip + up * ARROW_OVER_GRIP - nock).dot(AIM)
    print('draw length', round(draw, 3), flush=True)
    bow_ob, grip_ob, loops, M = gear.make_bow(props, grip, AIM, up, draw, ARROW_OVER_GRIP)
    close_hand(rig, 'L', tk.prop_tree(grip_ob), up)
    bow_ob['draw'] = repr(dict(grip=tuple(grip), up=tuple(up), loops=[tuple(p) for p in loops]))
    return bow_ob
