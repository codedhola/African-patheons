"""His ṣòkòtò: short drawstring trousers of ẹ̀tù, cut from the body and let fall.

The gallery figure wears short trousers of ẹ̀tù under the palm fronds. These end above the
knee and stand well off the leg, as hand-woven cloth does, and a drawstring gathers the
waist: while the trousers settle, a ring at the top is drawn in to the body, so the gathers
below it come from the simulation, as the folds under Ọ̀ṣun's sash did.
"""
import math

import bmesh
import bpy
import numpy as np

import cloth
from common import WORK, collection, edge_adjacency, obj_from_arrays, save, verts_world
from dress import smoothstep

WAIST_ABOVE_HIP = 0.080      # waist line above the hip joints
HEM_ALONG = 0.395            # from the hip joint down the thigh to the hem, just above the knee
EASE_WAIST = 0.040           # before the drawstring takes it in
EASE_HIP = 0.030
EASE_HEM = 0.070
SIM_END = 100
CINCH_START, CINCH_END = 4, 42


def leg_axes(rig):
    P = rig.pose.bones
    out = {}
    for side in 'LR':
        hip = np.array(P[f'upperleg01.{side}'].head)
        knee = np.array(P[f'lowerleg01.{side}'].head)
        out[side] = (hip, (knee - hip) / np.linalg.norm(knee - hip))
    return out


def measure(rig):
    legs = leg_axes(rig)
    hip_z = (legs['L'][0][2] + legs['R'][0][2]) / 2
    cx = (legs['L'][0][0] + legs['R'][0][0]) / 2
    return legs, float(hip_z + WAIST_ABOVE_HIP), float(cx)


def outline(points, z, band=0.012, nphi=120):
    """Centre and support distance of a slice through a cloud of points, by angle."""
    slab = points[np.abs(points[:, 2] - z) < band, :2]
    mid = (slab.max(0) + slab.min(0)) / 2
    phi = np.linspace(0, 2 * np.pi, nphi, endpoint=False)
    dirs = np.stack([np.cos(phi), np.sin(phi)], 1)
    return mid, phi, ((slab - mid) @ dirs.T).max(0)


def make_sokoto(body, rig, col):
    co = verts_world(body)
    armw = cloth.arm_weight(body)
    legs, waist_z, cx = measure(rig)
    side_of = np.where(co[:, 0] > cx, 'L', 'R')
    along = np.zeros(len(co))
    for side in 'LR':
        hip, d = legs[side]
        here = side_of == side
        along[here] = (co[here] - hip) @ d
    crotch_z = min(legs['L'][0][2], legs['R'][0][2]) - 0.06
    keep = (armw <= 0.30) & (co[:, 2] < waist_z + 0.05) & ((along < HEM_ALONG + 0.05) | (co[:, 2] > crotch_z))

    me = body.data
    polys = [p for p in me.polygons if all(keep[i] for i in p.vertices)]
    used = sorted({i for p in polys for i in p.vertices})
    remap = {old: new for new, old in enumerate(used)}
    ob = obj_from_arrays('Sokoto', co[used], [tuple(remap[i] for i in p.vertices) for p in polys], col)

    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for _ in range(2):
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True, smooth=1.0)
    cloth.cut(bm, (0, 0, waist_z), (0, 0, 1))
    for side, sign in (('L', 1), ('R', -1)):
        hip, d = legs[side]
        cloth.cut(bm, tuple(hip + d * HEM_ALONG), tuple(d),
                  where=lambda f: (f.calc_center_median().x - cx) * sign > 0 and f.calc_center_median().z < crotch_z + 0.02)
    cloth.keep_biggest_island(bm)
    bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if v.is_boundary], dist=0.0016)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.polygons.foreach_set('use_smooth', [True] * len(ob.data.polygons))
    ob.data.update()
    n = len(ob.data.vertices)
    print('sokoto', n, 'verts', flush=True)

    pos = np.array([v.co for v in ob.data.vertices])
    adj = edge_adjacency(ob.data)
    # woven cloth bridges the fork of the legs and the hollows of the hips; it does not follow them in
    fork = np.array([cx, float((legs['L'][0][1] + legs['R'][0][1]) / 2), crotch_z])
    w = smoothstep(np.linalg.norm(pos - fork, axis=1), 0.15, 0.05)
    sm = pos.copy()
    for _ in range(90):
        nb = np.array([sm[a].mean(0) if a else sm[i] for i, a in enumerate(adj)])
        sm += (nb - sm) * (0.65 * w)[:, None]
    sm[:, 2] -= 0.025 * w          # and the seat of a loose pair hangs a little low
    ob.data.vertices.foreach_set('co', sm.astype(np.float32).ravel())
    ob.data.update()
    normals = np.zeros(n * 3)
    ob.data.vertices.foreach_get('normal', normals)
    normals = normals.reshape(-1, 3)

    # stand it off the skin: full at the waist for the drawstring to take in, room over the hips, wide at the hem
    z = sm[:, 2]
    t = np.zeros(n)
    side_v = np.where(sm[:, 0] > cx, 'L', 'R')
    for side in 'LR':
        hip, d = legs[side]
        here = side_v == side
        t[here] = np.clip(((sm[here] - hip) @ d) / HEM_ALONG, 0, 1)
    top = smoothstep(z, waist_z - 0.05, waist_z - 0.01)
    off = EASE_HIP + (EASE_HEM - EASE_HIP) * t ** 1.4
    off = off * (1 - top) + EASE_WAIST * top
    # the inside of each leg stays closer, or the two legs would meet
    inward = np.zeros(n)
    for side, sign in (('L', 1), ('R', -1)):
        here = side_v == side
        inward[here] = np.clip(-normals[here, 0] * sign, 0, 1) * (1 - top[here])
    off *= 1 - 0.65 * inward
    for _ in range(6):
        off = np.array([off[a].mean() if a else off[i] for i, a in enumerate(adj)])
    final = sm + normals * off[:, None]
    ob.data.vertices.foreach_set('co', final.astype(np.float32).ravel())
    ob.data.update()
    return ob, waist_z, legs, cx


def sokoto_uv(ob, waist_z, legs, cx):
    """Strips run down each leg, as trousers are cut from strip cloth; the seams fall inside the legs."""
    rest = np.array([v.co for v in ob.data.vertices])
    me = ob.data
    layer = me.uv_layers.new(name='UVMap')
    v_idx = np.zeros(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', v_idx)
    uv = np.zeros((len(me.loops), 2), np.float32)
    for poly in me.polygons:
        ids = list(poly.loop_indices)
        p = rest[v_idx[ids]]
        c = p.mean(0)
        side, sign = ('L', 1) if c[0] > cx else ('R', -1)
        hip, d = legs[side]
        e1 = np.cross(d, (0, 1.0, 0))
        e1 *= sign / np.linalg.norm(e1)            # outward, away from the other leg
        e2 = np.cross(d, e1)
        w = p - hip
        ang = np.arctan2(w @ e2, w @ e1)
        if ang.max() - ang.min() > np.pi:
            ang = np.where(ang < 0, ang + 2 * np.pi, ang)
        uv[ids, 0] = (waist_z - p[:, 2]) / cloth.U_PERIOD
        uv[ids, 1] = (ang * 0.115 + (0.0 if side == 'L' else 0.52)) / cloth.V_PERIOD + 0.02
    layer.data.foreach_set('uv', uv.ravel())


def add_drawstring(ob, body, waist_z):
    """A shape key that draws the top of the trousers in to the waist, and the pins that hold it there."""
    pos = np.array([v.co for v in ob.data.vertices])
    co = verts_world(body)[cloth.arm_weight(body) < 0.3]
    ring = np.nonzero(pos[:, 2] > waist_z - 0.028)[0]
    goal = pos.copy()
    for i in ring:
        mid, phi, sup = outline(co, pos[i, 2], 0.012)
        dvec = pos[i, :2] - mid
        a = math.atan2(dvec[1], dvec[0]) % (2 * math.pi)
        r = float(np.interp(a, np.append(phi, 2 * np.pi), np.append(sup, sup[0]))) + 0.007
        goal[i, :2] = mid + dvec / np.linalg.norm(dvec) * r
    ob.shape_key_add(name='Basis')
    key = ob.shape_key_add(name='Drawstring')
    key.data.foreach_set('co', goal.astype(np.float32).ravel())
    key.value = 0
    key.keyframe_insert('value', frame=CINCH_START)
    key.value = 1
    key.keyframe_insert('value', frame=CINCH_END)
    ob.vertex_groups.new(name='pin').add(ring.tolist(), 1.0, 'REPLACE')
    print('drawstring takes in', len(ring), 'vertices', flush=True)


def sokoto_stage():
    body, rig = bpy.data.objects['Body'], bpy.data.objects['Rig']
    cloth.set_frame(1)
    cloth.add_collider(body)
    ob, waist_z, legs, cx = make_sokoto(body, rig, collection('Figure'))
    sokoto_uv(ob, waist_z, legs, cx)
    add_drawstring(ob, body, waist_z)
    mod = ob.modifiers.new('Cloth', 'CLOTH')
    cloth.cotton(mod, mass=0.42, tension=34, compression=34, shear=24, bending=12, pin='pin')
    mod.point_cache.frame_end = SIM_END
    cl = mod.collision_settings
    cl.use_self_collision = True
    cl.self_distance_min = 0.004
    cl.self_friction = 6
    adj = edge_adjacency(ob.data)
    co = cloth.relax(cloth.run_sim(ob, SIM_END), adj, 2)
    np.save(WORK / 'sokoto_final.npy', co)
    cloth.set_frame(1)
    ob.shape_key_clear()
    cloth.freeze(ob, co)
    edge = ob.data.attributes.new('edge_dist', 'FLOAT', 'POINT')
    edge.data.foreach_set('value', np.clip(cloth.geodesic_from_boundary(ob.data) / 0.1, 0, 1).astype(np.float32))
    body.modifiers.remove(body.modifiers['Collision'])
    np.save(WORK / 'waist_z.npy', np.array(waist_z))
    save('30_sokoto.blend')
