"""The bone moves a figure's stance is built from, and the keying of its arms.

Arms and legs are solved as two-bone chains from target positions. Only the arms
are keyed, moving from part-way up to their final place between frames 1 and
POSE_END, and the blouse is simulated through that move.
"""
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

POSE_END = 40


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


def two_bone(a, c, la, lb, pole):
    d = c - a
    L = min(d.length, la + lb - 1e-4)
    x = (la * la - lb * lb + L * L) / (2 * L)
    h = math.sqrt(max(la * la - x * x, 0))
    n = d.normalized()
    perp = (pole - pole.dot(n) * n).normalized()
    return a + n * x + perp * h


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


def pose_leg(rig, side, target, foot_yaw):
    P = rig.pose.bones
    hip = P[f'upperleg01.{side}'].matrix.translation.copy()
    knee0 = rig.data.bones[f'lowerleg01.{side}'].head_local
    ankle0 = rig.data.bones[f'foot.{side}'].head_local
    hip0 = rig.data.bones[f'upperleg01.{side}'].head_local
    la, lb = (knee0 - hip0).length, (ankle0 - knee0).length
    sign = 1 if side == 'L' else -1
    knee = two_bone(hip, target, la, lb, Vector((sign * 0.16, -1, 0)))
    aim(P[f'upperleg01.{side}'], knee - hip)
    aim(P[f'upperleg02.{side}'], knee - P[f'upperleg02.{side}'].matrix.translation)
    aim(P[f'lowerleg01.{side}'], target - knee)
    aim(P[f'lowerleg02.{side}'], target - P[f'lowerleg02.{side}'].matrix.translation)
    # keep the sole flat: put the foot back to its rest attitude, then turn it out
    foot = P[f'foot.{side}']
    rest = rig.data.bones[f'foot.{side}'].matrix_local
    Rz = Quaternion((0, 0, 1), foot_yaw).to_matrix().to_4x4()
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


def prop_tree(ob):
    """BVH of a held object in world space."""
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
