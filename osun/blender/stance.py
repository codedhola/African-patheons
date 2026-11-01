"""Her pose: weight on her left leg, the fan raised beside her head, the bell low at her left.

Priestesses carry brass fans in procession along the river, and devotees ring the ààjà in
prayer. Both hands are posed around the actual objects, as Ahiajoku's were around the yam.
"""
import math

import bpy
from mathutils import Matrix, Vector

import pose as tk

tk.ROOT_SHIFT = Vector((0.027, 0.0, -0.003))
tk.ARM_ROLL = dict(lowerarm01=0.2, lowerarm02=0.8)      # keep the forearm's twist away from the elbow
tk.FOOT_YAW = {'L': math.radians(4), 'R': math.radians(-17)}
PELVIS_TILT = math.radians(2.8)         # about Y: her right hip drops

WRIST = {'R': Vector((-0.298, -0.215, 1.262)), 'L': Vector((0.405, -0.205, 1.015))}
POLE = {'R': Vector((-0.70, 0.30, -1)), 'L': Vector((0.45, 0.60, -1))}
HAND_DIR = {'R': Vector((0.16, -0.95, 0.24)).normalized(), 'L': Vector((0.60, -0.78, -0.10)).normalized()}
PALM_DIR = {'R': Vector((0.98, 0.20, 0.0)).normalized(), 'L': Vector((-0.78, -0.62, 0.0)).normalized()}
GRIP_REACH = 0.074      # wrist to where the handle crosses the hand, at the base of the fingers
GRIP_DEPTH = 0.0245     # bone line to the axis of a handle lying in the palm
GRIP_SLANT = math.radians(16)      # the handle runs across the palm on the slant, little finger nearer the wrist
FINGER_R = {2: 0.0082, 3: 0.0084, 4: 0.0080, 5: 0.0070}
CURL_RATE = (2.0, 3.0, 1.8)      # degrees a step at each joint, knuckle to tip
CURL_LIMIT = (80, 100, 48)


def pose_arm(rig, side):
    P = rig.pose.bones
    B = rig.data.bones
    shoulder = P[f'upperarm01.{side}'].matrix.translation.copy()
    la = (B[f'lowerarm01.{side}'].head_local - B[f'upperarm01.{side}'].head_local).length
    lb = (B[f'wrist.{side}'].head_local - B[f'lowerarm01.{side}'].head_local).length
    elbow = tk.two_bone(shoulder, WRIST[side], la, lb, POLE[side])
    tk.aim(P[f'upperarm01.{side}'], elbow - shoulder)
    tk.aim(P[f'upperarm02.{side}'], elbow - P[f'upperarm02.{side}'].matrix.translation)
    tk.aim(P[f'lowerarm01.{side}'], WRIST[side] - elbow)
    tk.aim(P[f'lowerarm02.{side}'], WRIST[side] - P[f'lowerarm02.{side}'].matrix.translation)

    # turn the forearm until the palm faces the way the grip needs, as for the yam
    base = {n: P[f'{n}.{side}'].rotation_quaternion.copy() for n in tk.ARM_ROLL}
    wbase = P[f'wrist.{side}'].rotation_quaternion.copy()

    def try_roll(a):
        from mathutils import Quaternion
        for name, share in tk.ARM_ROLL.items():
            P[f'{name}.{side}'].rotation_quaternion = base[name] @ Quaternion((0, 1, 0), a * share)
        P[f'wrist.{side}'].rotation_quaternion = wbase
        tk.update()
        tk.aim_hand(rig, side, HAND_DIR[side])
        return tk.palm_normal(rig, side).dot(PALM_DIR[side])

    best = max((try_roll(math.radians(a)), a) for a in range(-170, 171, 10))[1]
    span = 5
    while span > 0.2:
        best = max((try_roll(math.radians(a)), a) for a in (best - span, best, best + span))[1]
        span /= 2
    score = try_roll(math.radians(best))
    print('palm', side, 'roll', best, 'match', round(score, 3), flush=True)


def grip_frame(rig, side):
    """Where a handle lies in the hand: its centre, and its axis from the little finger to the thumb."""
    P = rig.pose.bones
    wrist = P[f'wrist.{side}'].matrix.translation
    along = tk.hand_along(rig, side)
    palm = tk.palm_normal(rig, side)
    axis = (P[f'finger2-1.{side}'].matrix.translation - P[f'finger5-1.{side}'].matrix.translation).normalized()
    axis = (axis - axis.dot(palm) * palm).normalized()
    axis = (axis * math.cos(GRIP_SLANT) + along * math.sin(GRIP_SLANT)).normalized()
    return wrist + along * GRIP_REACH + palm * GRIP_DEPTH, axis


def place_prop(ob, centre, axis, face=None):
    """Stand a prop built along +Z on a grip: Z on the handle axis, -Y toward face."""
    z = axis.normalized()
    want = (face or Vector((0, -1, 0))).normalized()
    y = (-(want - want.dot(z) * z)).normalized()
    x = y.cross(z)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = centre
    ob.matrix_world = m
    bpy.context.view_layer.update()


def tree_of(ob):
    return tk.yam_tree(ob)


def gap(tree, points):
    """Smallest distance from any point to the prop's surface."""
    return min(tree.find_nearest(p)[3] for p in points)


def close_hand(rig, side, tree):
    """Fingers closing at all three joints at once until they rest on the handle, then the thumb over them."""
    P = rig.pose.bones
    along = tk.hand_along(rig, side)
    for k in (2, 3, 4, 5):
        names = [f'finger{k}-{j}.{side}' for j in (1, 2, 3)]
        y = P[names[0]].matrix.to_3x3() @ Vector((0, 1, 0))
        tk.aim(P[names[0]], y.lerp(along, 0.7))
        axis = tuple(tk.curl_axis(rig, side, names[0]))     # once: worked out later it flips as the finger passes 90 degrees
        turned = [0.0, 0.0, 0.0]
        moving = [0, 1, 2]
        while moving:
            for j in list(moving):
                pb = P[names[j]]
                saved = pb.rotation_quaternion.copy()
                tk.spin(pb, axis, math.radians(CURL_RATE[j]))
                turned[j] += CURL_RATE[j]
                # each joint already sits by the handle, so it is judged by what lies beyond it
                if turned[j] > CURL_LIMIT[j] or gap(tree, tk.finger_points(rig, names[j:])[2:]) < FINGER_R[k]:
                    pb.rotation_quaternion = saved
                    tk.update()
                    moving.remove(j)
        print('finger', side, k, 'closed', turned, flush=True)
    close_thumb(rig, side, tree)


def close_thumb(rig, side, tree):
    """Walk the thumb, a few degrees at a time, until its tip lies over the index finger."""
    P = rig.pose.bones
    names = [f'finger1-{j}.{side}' for j in (1, 2, 3)]
    target = P[f'finger2-2.{side}'].tail.lerp(P[f'finger3-2.{side}'].head, 0.35) - tk.palm_normal(rig, side) * 0.012

    def miss():
        return (P[names[2]].tail - target).length

    axes = [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]
    step = math.radians(4)
    for _ in range(90):
        before = miss()
        for name in names:
            pb = P[name]
            for ax in axes:
                for sign in (1, -1):
                    saved = pb.rotation_quaternion.copy()
                    base = miss()
                    tk.spin(pb, tuple(ax), sign * step)
                    if miss() < base and gap(tree, tk.finger_points(rig, names)) > 0.0075:
                        break
                    pb.rotation_quaternion = saved
                    tk.update()
        if before - miss() < 2e-4:
            step *= 0.6
            if step < math.radians(0.5):
                break
    print('thumb', side, 'misses by', round(miss(), 4), flush=True)


def solve(rig, fan, bell):
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    tk.update()
    P = rig.pose.bones
    B = rig.data.bones
    ankle_z = {s: B[f'foot.{s}'].head_local.z for s in 'LR'}
    tk.ANKLE = {'L': Vector((0.082, -0.014, ankle_z['L'])), 'R': Vector((-0.118, -0.128, ankle_z['R'] + 0.002))}

    root = P['root']
    root.matrix = Matrix.Translation(tk.ROOT_SHIFT) @ root.matrix
    tk.update()
    for name in ('pelvis.L', 'pelvis.R', 'spine05'):
        tk.spin(P[name], (0, 1, 0), PELVIS_TILT)
    for name, ang_y, ang_x, ang_z in (('spine04', -1.6, 0.6, -1.2), ('spine03', -1.8, 0.8, -1.2),
                                      ('spine02', -1.6, 1.0, -1.0), ('spine01', -0.8, 1.0, -0.6)):
        pb = P[name]
        tk.spin(pb, (0, 1, 0), math.radians(ang_y))
        tk.spin(pb, (1, 0, 0), math.radians(ang_x))
        tk.spin(pb, (0, 0, 1), math.radians(ang_z))

    # head toward the fan and tipped a little, chin level, so the low camera does not look up under it
    tk.spin(P['neck01'], (0, 0, 1), math.radians(-5))
    tk.spin(P['neck02'], (0, 0, 1), math.radians(-6))
    tk.spin(P['head'], (0, 0, 1), math.radians(-6))
    tk.spin(P['neck02'], (1, 0, 0), math.radians(0.5))
    tk.spin(P['head'], (1, 0, 0), math.radians(1.5))
    tk.spin(P['head'], (0, 1, 0), math.radians(5))

    tk.pose_leg(rig, 'L')
    tk.pose_leg(rig, 'R')

    # the raised shoulder lifts a little, the lowered one drops
    tk.spin(P['clavicle.L'], (0, 1, 0), math.radians(5))
    tk.spin(P['shoulder01.L'], (0, 1, 0), math.radians(6))
    tk.spin(P['shoulder01.L'], (0, 0, 1), math.radians(-7))
    tk.spin(P['shoulder01.R'], (0, 1, 0), math.radians(-2))
    pose_arm(rig, 'R')
    pose_arm(rig, 'L')

    # she holds each by the middle of its handle
    centre, axis = grip_frame(rig, 'R')
    place_prop(fan, centre, axis if axis.z > 0 else -axis)
    close_hand(rig, 'R', tree_of(fan))
    centre, axis = grip_frame(rig, 'L')
    place_prop(bell, centre, axis if axis.z > 0 else -axis)
    close_hand(rig, 'L', tree_of(bell))
