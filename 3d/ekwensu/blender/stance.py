"""His pose: the machete low in his right hand, his left hand on his hip, his weight on his right leg.

The gallery figure stands so: one hand on the hip, a machete in the other. The right hand is
closed round the real handle, as Ògún's was; the left is set against the posed body, palm on
the flank above the hip and fingers forward, as a man stands who is in no hurry. It rests where
the trousers and the fringe will be, a few centimetres off the skin, so the strands pass under it.
"""
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

import pose as tk

ROOT_SHIFT = Vector((-0.030, 0.0, -0.006))
ARM_ROLL = dict(lowerarm01=0.2, lowerarm02=0.8)      # keep the forearm's twist away from the elbow
FOOT_YAW = {'L': math.radians(18), 'R': math.radians(-6)}
PELVIS_TILT = math.radians(-3.0)        # about Y: his left hip drops, the right takes the weight

WRIST = {'R': Vector((-0.312, -0.095, 0.935))}
POLE = {'R': Vector((-0.35, 1.0, 0.0)), 'L': Vector((1.0, 0.55, -0.15))}
# the right wrist turns a little toward the little finger, so the blade's point drops
HAND_DIR = {'R': Vector((-0.04, 0.42, -0.91)).normalized()}
PALM_DIR = {'R': Vector((0.93, -0.36, 0.0)).normalized()}
EDGE_DIR = Vector((-0.80, 0.60, 0.0)).normalized()      # the machete's edge turned out and back, its flat toward the square
HIP_HAND_ABOVE = 0.105     # palm above the hip joint
HIP_FINGERS = Vector((0.05, -0.85, -0.52)).normalized()     # fingers forward and down over the hip
GRIP_REACH = 0.078      # wrist to where the handle crosses the hand, at the base of the fingers
GRIP_DEPTH = 0.0245     # bone line to the axis of a handle lying in the palm
GRIP_SLANT = math.radians(14)      # the handle runs across the palm on the slant, little finger nearer the wrist
FINGER_R = {2: 0.0092, 3: 0.0094, 4: 0.0090, 5: 0.0080}
CURL_RATE = (2.0, 3.0, 1.8)      # degrees a step at each joint, knuckle to tip
CURL_LIMIT = (85, 100, 55)
LOOSE = {2: (10, 14, 8), 3: (12, 16, 9), 4: (14, 18, 10), 5: (16, 20, 11)}      # fingers laid along the hip, barely bent


def pose_arm(rig, side, wrist, hand_dir, palm_dir):
    P = rig.pose.bones
    B = rig.data.bones
    shoulder = P[f'upperarm01.{side}'].matrix.translation.copy()
    la = (B[f'lowerarm01.{side}'].head_local - B[f'upperarm01.{side}'].head_local).length
    lb = (B[f'wrist.{side}'].head_local - B[f'lowerarm01.{side}'].head_local).length
    elbow = tk.two_bone(shoulder, wrist, la, lb, POLE[side])
    tk.aim(P[f'upperarm01.{side}'], elbow - shoulder)
    tk.aim(P[f'upperarm02.{side}'], elbow - P[f'upperarm02.{side}'].matrix.translation)
    tk.aim(P[f'lowerarm01.{side}'], wrist - elbow)
    tk.aim(P[f'lowerarm02.{side}'], wrist - P[f'lowerarm02.{side}'].matrix.translation)

    # turn the forearm until the palm faces the way the grip needs
    base = {n: P[f'{n}.{side}'].rotation_quaternion.copy() for n in ARM_ROLL}
    wbase = P[f'wrist.{side}'].rotation_quaternion.copy()

    def try_roll(a):
        for name, share in ARM_ROLL.items():
            P[f'{name}.{side}'].rotation_quaternion = base[name] @ Quaternion((0, 1, 0), a * share)
        P[f'wrist.{side}'].rotation_quaternion = wbase
        tk.update()
        tk.aim_hand(rig, side, hand_dir)
        return tk.palm_normal(rig, side).dot(palm_dir)

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
    # round a thick handle the index finger's middle bone lies across its far side: the thumb comes over onto it
    mid = P[f'finger2-2.{side}'].head.lerp(P[f'finger2-2.{side}'].tail, 0.6)
    target = mid + tk.palm_normal(rig, side) * 0.011

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
                    if miss() < base and gap(tree, tk.finger_points(rig, names)) > 0.0082:
                        break
                    pb.rotation_quaternion = saved
                    tk.update()
        if before - miss() < 2e-4:
            step *= 0.6
            if step < math.radians(0.5):
                break
    print('thumb', side, 'misses by', round(miss(), 4), flush=True)


def rest_hand(rig, side):
    """A hand hanging at rest: the fingers drawn together and a little curled, more toward the little finger.

    The thumb lies along the side of the index finger, as it falls when the hand is let go.
    """
    P = rig.pose.bones
    along = tk.hand_along(rig, side)
    for k, angles in LOOSE.items():
        names = [f'finger{k}-{j}.{side}' for j in (1, 2, 3)]
        y = P[names[0]].matrix.to_3x3() @ Vector((0, 1, 0))
        tk.aim(P[names[0]], y.lerp(along, 0.55))
        axis = tuple(tk.curl_axis(rig, side, names[0]))
        for name, a in zip(names, angles):
            tk.spin(P[name], axis, math.radians(a))
    # walk the thumb tip toward the side of the index finger's middle joint
    names = [f'finger1-{j}.{side}' for j in (1, 2, 3)]
    target = P[f'finger2-2.{side}'].head - tk.palm_normal(rig, side) * 0.004 + (P[f'finger2-1.{side}'].head - P[f'finger3-1.{side}'].head).normalized() * 0.012

    def miss():
        return (P[names[2]].tail - target).length

    step = math.radians(3)
    for _ in range(60):
        before = miss()
        for name in names:
            for ax in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
                for sign in (1, -1):
                    saved = P[name].rotation_quaternion.copy()
                    base = miss()
                    tk.spin(P[name], ax, sign * step)
                    if miss() < base:
                        break
                    P[name].rotation_quaternion = saved
                    tk.update()
        if before - miss() < 2e-4:
            step *= 0.6
            if step < math.radians(0.5):
                break
    print('resting thumb', side, 'misses by', round(miss(), 4), flush=True)


def hip_hand(body, rig):
    """Where his left palm lies: on the flank above the hip, a little in front, measured on the posed body."""
    from cloth import arm_weight
    from common import verts_world
    import numpy as np
    P = rig.pose.bones
    hip = P['upperleg01.L'].head
    z = float(hip.z) + HIP_HAND_ABOVE
    co = verts_world(body)
    co = co[arm_weight(body) < 0.2]
    band = co[(np.abs(co[:, 2] - z) < 0.02) & (co[:, 0] > 0.04) & (np.abs(co[:, 1] - float(hip.y) + 0.01) < 0.05)]
    i = int(np.argmax(band[:, 0]))
    contact = Vector(band[i]) + Vector((0.040, -0.012, 0))     # on the cloth, not the skin: the trousers and fringe lie between
    palm = Vector((-1.0, 0.12, 0.0)).normalized()       # facing in, onto the flank
    wrist = contact - HIP_FINGERS * 0.062 + Vector((0.020, 0, 0))
    return wrist, HIP_FINGERS, palm


def solve(rig, blade, body):
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    tk.update()
    P = rig.pose.bones
    B = rig.data.bones
    ankle_z = {s: B[f'foot.{s}'].head_local.z for s in 'LR'}
    ankle = {'R': Vector((-0.110, -0.006, ankle_z['R'])), 'L': Vector((0.205, -0.125, ankle_z['L'] + 0.002))}

    root = P['root']
    root.matrix = Matrix.Translation(ROOT_SHIFT) @ root.matrix
    tk.update()
    for name in ('pelvis.L', 'pelvis.R', 'spine05'):
        tk.spin(P[name], (0, 1, 0), PELVIS_TILT)
    for name, ang_y, ang_x, ang_z in (('spine04', 1.8, -0.4, -1.6), ('spine03', 2.0, -0.6, -1.8),
                                      ('spine02', 1.4, -0.6, -1.8), ('spine01', 0.6, 0.4, -1.2)):
        pb = P[name]
        tk.spin(pb, (0, 1, 0), math.radians(ang_y))
        tk.spin(pb, (1, 0, 0), math.radians(ang_x))
        tk.spin(pb, (0, 0, 1), math.radians(ang_z))

    # head turned a little to his left and tipped, chin a touch down: he is weighing you up
    tk.spin(P['neck01'], (0, 0, 1), math.radians(5))
    tk.spin(P['neck02'], (0, 0, 1), math.radians(5))
    tk.spin(P['head'], (0, 0, 1), math.radians(5))
    tk.spin(P['head'], (0, 1, 0), math.radians(-4))
    tk.spin(P['head'], (1, 0, 0), math.radians(3.0))

    tk.pose_leg(rig, 'L', ankle['L'], FOOT_YAW['L'])
    tk.pose_leg(rig, 'R', ankle['R'], FOOT_YAW['R'])
    for side, sign in (('L', 1), ('R', -1)):
        tk.spin(P[f'clavicle.{side}'], (0, 1, 0), math.radians(2.5 * sign))
        tk.spin(P[f'shoulder01.{side}'], (0, 1, 0), math.radians(2.5 * sign))
    pose_arm(rig, 'R', WRIST['R'], HAND_DIR['R'], PALM_DIR['R'])
    wrist, fingers, palm = hip_hand(body, rig)
    pose_arm(rig, 'L', wrist, fingers, palm)

    # the blade leaves the thumb side of the fist, so it points the way the grip axis runs
    centre, axis = grip_frame(rig, 'R')
    print('grip axis', tuple(round(c, 3) for c in axis), flush=True)
    place_prop(blade, centre, axis, face=EDGE_DIR)
    close_hand(rig, 'R', tk.prop_tree(bpy.data.objects['MmaHandle']))
    rest_hand(rig, 'L')
