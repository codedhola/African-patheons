"""Her pose: the white pot carried on her left hip, her right arm loose at her side.

The gallery figure carries the pot so. Her weight is on her left leg and that hip is pushed
out under the pot, as a load carried on the hip is. The pot is placed first, against the hip
with room for the cloth, and her left hand is solved to it: palm on the pot's belly, fingers
closing until they rest on it.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

import pose as tk
from common import verts_world

ROOT_SHIFT = Vector((0.032, 0.0, -0.004))
ARM_ROLL = dict(lowerarm01=0.2, lowerarm02=0.8)
FOOT_YAW = {'L': math.radians(5), 'R': math.radians(-15)}
PELVIS_TILT = math.radians(3.2)         # about Y: her right hip drops, the left rises under the pot

POT_ABOVE_HIP = 0.115       # the pot's middle above the hip joints
POT_CLEAR = 0.034           # from the skin to the pot: the wrapper and blouse lie between
POT_TILT = math.radians(13)  # its mouth leans away from her
CONTACT_AZ = math.radians(-62)     # where her palm lies on the pot: front and outside
PALM_REACH = 0.062
PALM_DEPTH = 0.016
POLE = {'L': Vector((0.75, 0.9, -0.2)), 'R': Vector((-0.40, 1.0, 0.0))}
WRIST_R = Vector((-0.262, -0.035, 0.875))
HAND_DIR_R = Vector((0.08, -0.10, -0.99)).normalized()
PALM_DIR_R = Vector((0.92, 0.38, 0.0)).normalized()
FINGER_R = {2: 0.0080, 3: 0.0082, 4: 0.0078, 5: 0.0068}
CURL_RATE = (2.0, 3.0, 1.8)
CURL_LIMIT = (55, 70, 45)
LOOSE = {2: (16, 24, 12), 3: (20, 28, 14), 4: (24, 32, 16), 5: (28, 36, 18)}


def solve_arm(rig, side, wrist, pole, hand_dir, palm_dir):
    P = rig.pose.bones
    B = rig.data.bones
    shoulder = P[f'upperarm01.{side}'].matrix.translation.copy()
    la = (B[f'lowerarm01.{side}'].head_local - B[f'upperarm01.{side}'].head_local).length
    lb = (B[f'wrist.{side}'].head_local - B[f'lowerarm01.{side}'].head_local).length
    elbow = tk.two_bone(shoulder, wrist, la, lb, pole)
    tk.aim(P[f'upperarm01.{side}'], elbow - shoulder)
    tk.aim(P[f'upperarm02.{side}'], elbow - P[f'upperarm02.{side}'].matrix.translation)
    tk.aim(P[f'lowerarm01.{side}'], wrist - elbow)
    tk.aim(P[f'lowerarm02.{side}'], wrist - P[f'lowerarm02.{side}'].matrix.translation)
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
    print('palm', side, 'roll', best, 'match', round(try_roll(math.radians(best)), 3), flush=True)


def gap(tree, points):
    return min(tree.find_nearest(p)[3] for p in points)


def close_on(rig, side, tree):
    """Fingers closing at all three joints at once until they rest on the pot."""
    P = rig.pose.bones
    along = tk.hand_along(rig, side)
    for k in (2, 3, 4, 5):
        names = [f'finger{k}-{j}.{side}' for j in (1, 2, 3)]
        y = P[names[0]].matrix.to_3x3() @ Vector((0, 1, 0))
        tk.aim(P[names[0]], y.lerp(along, 0.45))
        axis = tuple(tk.curl_axis(rig, side, names[0]))     # once: worked out later it flips past 90 degrees
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
    # the thumb lies along the pot, toward the index finger
    names = [f'finger1-{j}.{side}' for j in (1, 2, 3)]
    target = P[f'finger2-1.{side}'].head.lerp(P[f'finger2-2.{side}'].head, 0.5) - tk.palm_normal(rig, side) * 0.004
    walk_thumb(rig, names, target, tree)


def walk_thumb(rig, names, target, tree=None, clear=0.0075):
    P = rig.pose.bones

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
                    if miss() < base and (tree is None or gap(tree, tk.finger_points(rig, names)) > clear):
                        break
                    P[name].rotation_quaternion = saved
                    tk.update()
        if before - miss() < 2e-4:
            step *= 0.6
            if step < math.radians(0.5):
                break
    print('thumb misses by', round(miss(), 4), flush=True)


def rest_hand(rig, side):
    """A hand let hang: fingers drawn together and a little curled, the thumb along the index finger."""
    P = rig.pose.bones
    along = tk.hand_along(rig, side)
    for k, angles in LOOSE.items():
        names = [f'finger{k}-{j}.{side}' for j in (1, 2, 3)]
        y = P[names[0]].matrix.to_3x3() @ Vector((0, 1, 0))
        tk.aim(P[names[0]], y.lerp(along, 0.55))
        axis = tuple(tk.curl_axis(rig, side, names[0]))
        for name, a in zip(names, angles):
            tk.spin(P[name], axis, math.radians(a))
    names = [f'finger1-{j}.{side}' for j in (1, 2, 3)]
    target = P[f'finger2-2.{side}'].head - tk.palm_normal(rig, side) * 0.004 + (P[f'finger2-1.{side}'].head - P[f'finger3-1.{side}'].head).normalized() * 0.011
    walk_thumb(rig, names, target)


def pot_matrix(body, rig):
    """Stand the pot against her left hip, clear of the skin by the cloth's thickness, its mouth leaning out."""
    P = rig.pose.bones
    hip = P['upperleg01.L'].head
    z = float(hip.z) + POT_ABOVE_HIP
    from cloth import arm_weight
    co = verts_world(body)
    co = co[arm_weight(body) < 0.2]          # the arm is not yet down, and the pot goes against the hip, not the arm
    band = co[(np.abs(co[:, 2] - z) < 0.05) & (co[:, 0] > 0.05) & (np.abs(co[:, 1] - float(hip.y)) < 0.10)]
    side = float(band[:, 0].max())
    centre = Vector((side + POT_CLEAR + 0.128, float(hip.y) + 0.01, z))
    m = Matrix.Translation(centre) @ Matrix.Rotation(POT_TILT, 4, 'Y') @ Matrix.Rotation(math.radians(-4), 4, 'X')
    return m


def solve(rig, body, pot):
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    tk.update()
    P = rig.pose.bones
    B = rig.data.bones
    ankle_z = {s: B[f'foot.{s}'].head_local.z for s in 'LR'}
    ankle = {'L': Vector((0.095, -0.006, ankle_z['L'])), 'R': Vector((-0.128, -0.098, ankle_z['R'] + 0.002))}
    root = P['root']
    root.matrix = Matrix.Translation(ROOT_SHIFT) @ root.matrix
    tk.update()
    for name in ('pelvis.L', 'pelvis.R', 'spine05'):
        tk.spin(P[name], (0, 1, 0), PELVIS_TILT)
    for name, ang_y, ang_x, ang_z in (('spine04', -1.8, 0.6, 1.0), ('spine03', -2.0, 0.6, 1.2),
                                      ('spine02', -1.6, 0.6, 1.2), ('spine01', -0.8, 0.8, 0.8)):
        pb = P[name]
        tk.spin(pb, (0, 1, 0), math.radians(ang_y))
        tk.spin(pb, (1, 0, 0), math.radians(ang_x))
        tk.spin(pb, (0, 0, 1), math.radians(ang_z))
    # her head turned a little to her right and tipped toward the pot side, chin level
    tk.spin(P['neck01'], (0, 0, 1), math.radians(-4))
    tk.spin(P['neck02'], (0, 0, 1), math.radians(-4))
    tk.spin(P['head'], (0, 0, 1), math.radians(-4))
    tk.spin(P['head'], (0, 1, 0), math.radians(-4))
    tk.spin(P['head'], (1, 0, 0), math.radians(1.0))
    tk.pose_leg(rig, 'L', ankle['L'], FOOT_YAW['L'])
    tk.pose_leg(rig, 'R', ankle['R'], FOOT_YAW['R'])
    for side, sign in (('L', 1), ('R', -1)):
        tk.spin(P[f'clavicle.{side}'], (0, 1, 0), math.radians(2.5 * sign))
        tk.spin(P[f'shoulder01.{side}'], (0, 1, 0), math.radians(2.5 * sign))

    # the pot first, then the arm that holds it
    pot.matrix_world = pot_matrix(body, rig)
    bpy.context.view_layer.update()
    m = pot.matrix_world
    c = m.translation
    up = (m.to_3x3() @ Vector((0, 0, 1))).normalized()
    out = Vector((math.cos(CONTACT_AZ), math.sin(CONTACT_AZ), 0))
    out = (out - out.dot(up) * up).normalized()
    contact = c + out * 0.131 + up * 0.012
    hand_dir = (-up * 0.85 - out * 0.15 + Vector((-0.25, -0.15, 0))).normalized()
    hand_dir = (hand_dir - hand_dir.dot(out) * out).normalized()
    wrist = contact - hand_dir * PALM_REACH + out * PALM_DEPTH
    solve_arm(rig, 'L', wrist, POLE['L'], hand_dir, -out)
    close_on(rig, 'L', tk.prop_tree(pot))
    solve_arm(rig, 'R', WRIST_R, POLE['R'], HAND_DIR_R, PALM_DIR_R)
    rest_hand(rig, 'R')
