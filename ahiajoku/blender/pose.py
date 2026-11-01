"""Pose the figure: weight on the right leg, both hands presenting the yam.

Arms and legs are solved as two-bone chains from target positions. Only the arms
are keyed, moving from part-way up to their final place between frames 1 and
POSE_END, and the blouse is simulated through that move.
"""
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

POSE_END = 40

# Blender's front is -Y. Her left is +X.
ROOT_SHIFT = Vector((-0.024, 0.0, -0.004))
PELVIS_TILT = math.radians(2.6)        # about Y: her left hip drops
ANKLE = {'R': Vector((-0.112, -0.004, 0.071)), 'L': Vector((0.128, -0.075, 0.073))}
FOOT_YAW = {'R': math.radians(-4), 'L': math.radians(15)}
ELBOW_POLE = {'R': Vector((-0.62, 0.30, -1)), 'L': Vector((0.62, 0.30, -1))}
ARM_ROLL = dict(lowerarm01=0.36, lowerarm02=0.64)

# The tuber is placed first and the hands are solved to it. Local +Z runs head to tip.
YAM_LENGTH = 0.40
YAM_CENTRE = Vector((0.004, -0.388, 1.098))
YAM_HEAD_DIR = Vector((0.945, -0.10, 0.31)).normalized()    # toward the narrow head, her left
CONTACT_T = {'R': 0.82, 'L': 0.17}                          # along the tuber
HAND_DIR = {'R': Vector((0.20, -1, 0.05)).normalized(), 'L': Vector((-0.24, -1, 0.10)).normalized()}
PALM_REACH = 0.066        # wrist to the middle of the palm
PALM_DEPTH = 0.015        # bone line to the palm's surface
CURL_LIMIT = {1: 72, 2: 88, 3: 64}
FINGER_R = {2: 0.0085, 3: 0.0088, 4: 0.0082, 5: 0.0072}


def yam_matrix():
    """World matrix of the hero tuber."""
    z = -YAM_HEAD_DIR
    x = Vector((0, 0, 1)).cross(z).normalized()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = YAM_CENTRE
    return m


def contact(side, radii):
    """Point under the tuber where the palm meets it, and its upward normal."""
    t = CONTACT_T[side]
    r = radii[int(t * (len(radii) - 1))]
    z = -YAM_HEAD_DIR
    p = YAM_CENTRE + z * (t - 0.5) * YAM_LENGTH
    n = (Vector((0, 0, 1)) - Vector((0, 0, 1)).dot(z) * z).normalized()
    return p - n * r * 0.92, n


def update():
    bpy.context.view_layer.update()


def aim(pb, direction):
    """Turn a pose bone so its Y axis points along direction, in armature space."""
    M = pb.matrix.copy()
    cur = (M.to_3x3() @ Vector((0, 1, 0))).normalized()
    q = cur.rotation_difference(direction.normalized())
    pivot = M.translation.copy()
    pb.matrix = Matrix.Translation(pivot) @ q.to_matrix().to_4x4() @ Matrix.Translation(-pivot) @ M
    update()


def spin(pb, axis, angle):
    """Rotate a pose bone about an armature-space axis through its head."""
    M = pb.matrix.copy()
    pivot = M.translation.copy()
    q = Quaternion(axis, angle)
    pb.matrix = Matrix.Translation(pivot) @ q.to_matrix().to_4x4() @ Matrix.Translation(-pivot) @ M
    update()


def roll(pb, angle):
    pb.rotation_quaternion = pb.rotation_quaternion @ Quaternion((0, 1, 0), angle)
    update()


def two_bone(a, c, la, lb, pole):
    d = c - a
    L = min(d.length, la + lb - 1e-4)
    x = (la * la - lb * lb + L * L) / (2 * L)
    h = math.sqrt(max(la * la - x * x, 0))
    n = d.normalized()
    perp = (pole - pole.dot(n) * n).normalized()
    return a + n * x + perp * h


def rest_length(rig, *names):
    return sum(rig.data.bones[n].length for n in names)


def palm_normal(rig, side):
    """Unit vector out of the palm, from the knuckle bones."""
    P = rig.pose.bones
    wrist = P[f'wrist.{side}'].matrix.translation
    index = P[f'finger2-1.{side}'].matrix.translation
    little = P[f'finger5-1.{side}'].matrix.translation
    along = (P[f'finger3-1.{side}'].matrix.translation - wrist).normalized()
    across = (little - index).normalized()
    # across runs index to little. For the left hand along x across points out of the back.
    n = along.cross(across) if side == 'R' else across.cross(along)
    return n.normalized()


def pose_leg(rig, side):
    P = rig.pose.bones
    hip = P[f'upperleg01.{side}'].matrix.translation.copy()
    knee0 = rig.data.bones[f'lowerleg01.{side}'].head_local
    ankle0 = rig.data.bones[f'foot.{side}'].head_local
    hip0 = rig.data.bones[f'upperleg01.{side}'].head_local
    la, lb = (knee0 - hip0).length, (ankle0 - knee0).length
    target = ANKLE[side]
    sign = 1 if side == 'L' else -1
    knee = two_bone(hip, target, la, lb, Vector((sign * 0.16, -1, 0)))
    aim(P[f'upperleg01.{side}'], knee - hip)
    aim(P[f'upperleg02.{side}'], knee - P[f'upperleg02.{side}'].matrix.translation)
    aim(P[f'lowerleg01.{side}'], target - knee)
    aim(P[f'lowerleg02.{side}'], target - P[f'lowerleg02.{side}'].matrix.translation)
    # keep the sole flat: put the foot back to its rest attitude, then turn it out
    foot = P[f'foot.{side}']
    rest = rig.data.bones[f'foot.{side}'].matrix_local
    Rz = Quaternion((0, 0, 1), FOOT_YAW[side]).to_matrix().to_4x4()
    head = foot.matrix.translation.copy()
    foot.matrix = Matrix.Translation(head) @ Rz @ rest.to_3x3().to_4x4()
    update()


def hand_along(rig, side):
    P = rig.pose.bones
    return (P[f'finger3-1.{side}'].matrix.translation - P[f'wrist.{side}'].matrix.translation).normalized()


def aim_hand(rig, side, direction):
    pb = rig.pose.bones[f'wrist.{side}']
    spin(pb, tuple(hand_along(rig, side).cross(direction).normalized()),
         hand_along(rig, side).angle(direction))


def pose_arm(rig, side, radii):
    P = rig.pose.bones
    B = rig.data.bones
    sign = 1 if side == 'L' else -1

    # lower the arm from the A-pose: the shoulder girdle follows it down a little
    spin(P[f'clavicle.{side}'], (0, 1, 0), sign * math.radians(5))
    spin(P[f'shoulder01.{side}'], (0, 1, 0), sign * math.radians(6))
    spin(P[f'shoulder01.{side}'], (0, 0, 1), sign * math.radians(-7))

    palm, up = contact(side, radii)
    wrist = palm - HAND_DIR[side] * PALM_REACH - up * PALM_DEPTH
    shoulder = P[f'upperarm01.{side}'].matrix.translation.copy()
    la = (B[f'lowerarm01.{side}'].head_local - B[f'upperarm01.{side}'].head_local).length
    lb = (B[f'wrist.{side}'].head_local - B[f'lowerarm01.{side}'].head_local).length
    elbow = two_bone(shoulder, wrist, la, lb, ELBOW_POLE[side])
    aim(P[f'upperarm01.{side}'], elbow - shoulder)
    aim(P[f'upperarm02.{side}'], elbow - P[f'upperarm02.{side}'].matrix.translation)
    aim(P[f'lowerarm01.{side}'], wrist - elbow)
    aim(P[f'lowerarm02.{side}'], wrist - P[f'lowerarm02.{side}'].matrix.translation)

    # supinate through the forearm, the wrist taking only the last few degrees
    base = {n: P[f'{n}.{side}'].rotation_quaternion.copy() for n in ARM_ROLL}
    wbase = P[f'wrist.{side}'].rotation_quaternion.copy()

    def try_roll(a):
        for name, share in ARM_ROLL.items():
            P[f'{name}.{side}'].rotation_quaternion = base[name] @ Quaternion((0, 1, 0), a * share)
        P[f'wrist.{side}'].rotation_quaternion = wbase
        update()
        aim_hand(rig, side, HAND_DIR[side])
        return palm_normal(rig, side).dot(up)

    best = max(((try_roll(math.radians(a)), a) for a in range(-170, 171, 10)))[1]
    span = 5
    while span > 0.2:
        best = max((try_roll(math.radians(a)), a) for a in (best - span, best, best + span))[1]
        span /= 2
    score = try_roll(math.radians(best))
    print('palm', side, 'roll', best, 'up', round(score, 3), flush=True)


def curl_axis(rig, side, bone):
    """Axis that swings a finger bone toward the palm side."""
    y = rig.pose.bones[bone].matrix.to_3x3() @ Vector((0, 1, 0))
    return y.cross(palm_normal(rig, side)).normalized()


def finger_points(rig, names):
    pts = []
    P = rig.pose.bones
    for n in names:
        a, b = P[n].head, P[n].tail
        for f in (0.0, 0.34, 0.67, 1.0):
            pts.append((a.lerp(b, f)))
    return pts


def clearance(tree, points):
    """Smallest signed distance from points to the tuber's skin (negative inside)."""
    low = 1
    for p in points:
        hit, normal, _, dist = tree.find_nearest(p)
        if hit is None:
            continue
        d = dist if (p - hit).dot(normal) >= 0 else -dist
        low = min(low, d)
    return low


def fit_fingers(rig, side, tree):
    """Close each finger joint by joint until it comes to rest on the tuber."""
    P = rig.pose.bones
    along = hand_along(rig, side)
    for k in (2, 3, 4, 5):
        names = [f'finger{k}-{j}.{side}' for j in (1, 2, 3)]
        # gather the fingers from MakeHuman's splay toward the line of the hand
        y = P[names[0]].matrix.to_3x3() @ Vector((0, 1, 0))
        aim(P[names[0]], y.lerp(along, 0.6))
        rest = {1: 8, 2: 12, 3: 8}
        for j, name in enumerate(names, 1):
            spin(P[name], tuple(curl_axis(rig, side, name)), math.radians(rest[j]))
        for j, name in enumerate(names, 1):
            pb = P[name]
            for _ in range(int(CURL_LIMIT[j] / 3)):
                axis = curl_axis(rig, side, name)
                saved = pb.rotation_quaternion.copy()
                spin(pb, tuple(axis), math.radians(3))
                if clearance(tree, finger_points(rig, names[j - 1:])) < FINGER_R[k]:
                    pb.rotation_quaternion = saved
                    update()
                    break
    # thumb lies along the near side of the tuber
    sign = 1 if side == 'L' else -1
    t1, t2, t3 = (P[f'finger1-{j}.{side}'] for j in (1, 2, 3))
    spin(t1, tuple(along), sign * math.radians(-34))
    spin(t1, tuple(palm_normal(rig, side)), sign * math.radians(-16))
    for pb, ang in ((t2, 18), (t3, 14)):
        spin(pb, tuple(curl_axis(rig, side, pb.name)), math.radians(ang))


def solve(rig, radii, tree=None):
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    update()
    P = rig.pose.bones

    # hips over the standing leg, her left hip dropped, spine answering the other way
    root = P['root']
    root.matrix = Matrix.Translation(ROOT_SHIFT) @ root.matrix
    update()
    spin(P['pelvis.L'], (0, 1, 0), -PELVIS_TILT)
    spin(P['pelvis.R'], (0, 1, 0), -PELVIS_TILT)
    spin(P['spine05'], (0, 1, 0), -PELVIS_TILT)
    for name, ang_y, ang_x, ang_z in (('spine04', 1.4, 0.8, 0.8), ('spine03', 1.6, 1.0, 1.0),
                                      ('spine02', 1.4, 1.6, 1.0), ('spine01', 0.8, 1.6, 0.8)):
        pb = P[name]
        spin(pb, (0, 1, 0), math.radians(ang_y))
        spin(pb, (1, 0, 0), math.radians(ang_x))
        spin(pb, (0, 0, 1), math.radians(ang_z))

    # head level, turned toward her left, chin a little down
    spin(P['neck01'], (0, 1, 0), math.radians(-1.0))
    spin(P['neck02'], (1, 0, 0), math.radians(1.5))
    spin(P['neck03'], (1, 0, 0), math.radians(1.5))
    spin(P['neck01'], (0, 0, 1), math.radians(4))
    spin(P['neck02'], (0, 0, 1), math.radians(5))
    spin(P['head'], (0, 0, 1), math.radians(5))
    spin(P['head'], (1, 0, 0), math.radians(3))
    spin(P['head'], (0, 1, 0), math.radians(-3.5))

    pose_leg(rig, 'R')
    pose_leg(rig, 'L')
    pose_arm(rig, 'R', radii)
    pose_arm(rig, 'L', radii)
    if tree:
        fit_fingers(rig, 'R', tree)
        fit_fingers(rig, 'L', tree)


def yam_tree(ob):
    """BVH of the hero tuber in world space."""
    from mathutils.bvhtree import BVHTree
    verts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    return BVHTree.FromPolygons(verts, [tuple(p.vertices) for p in ob.data.polygons])


def key_pose(rig, start=0.34):
    """Hold the body still and key only the arms, part-way up at frame 1, down at POSE_END."""
    moving = ('clavicle', 'shoulder01', 'upperarm', 'lowerarm', 'wrist', 'finger', 'metacarpal')
    identity = Quaternion((1, 0, 0, 0))
    rig.animation_data_create()
    for pb in rig.pose.bones:
        if not pb.name.startswith(moving):
            continue
        final = pb.rotation_quaternion.copy()
        pb.rotation_quaternion = identity.slerp(final, start)
        pb.keyframe_insert('rotation_quaternion', frame=1)
        pb.rotation_quaternion = final
        pb.keyframe_insert('rotation_quaternion', frame=POSE_END)
    bpy.context.scene.frame_set(POSE_END)
