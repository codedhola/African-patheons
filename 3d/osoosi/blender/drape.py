"""His tunic: the toolkit's blouse, cut to a man's measure, in pale indigo strip cloth.

His gallery figure wears a blue tunic over short trousers. This one is a loose pullover to the
top of the thigh with short sleeves, as a hunter would wear in the forest: the toolkit's blouse,
cut from the body with the arms part-way up, then simulated while the arms rise into the draw,
so the folds round the shoulders come from the move. Its hem hangs over the trousers' waist.
"""
import math

import bpy
import numpy as np

import cloth
import pose as posing
from common import WORK, collection, edge_adjacency, save, verts_world


def measure(rig):
    """Fit the toolkit's garment heights to his skeleton."""
    P = rig.pose.bones
    cloth.WAIST_Z = float(P['spine03'].head.z) + 0.035
    cloth.HIP_Z = float(P['pelvis.L'].head.z) + 0.005
    cloth.BLOUSE_HEM_Z = float(P['upperleg01.L'].head.z) - 0.045
    cloth.SLEEVE_END = 0.150
    cloth.SLEEVE_EASE = 0.026
    cloth.SLEEVE_FLARE = 0.022
    cloth.EASE_BLEND = 30
    n = P['neck01'].head
    cloth.NECK = dict(centre=(float(n.x), float(n.y) + 0.004, float(n.z) + 0.020), radii=(0.098, 0.092, 0.080))
    print('waist', round(cloth.WAIST_Z, 3), 'hip', round(cloth.HIP_Z, 3), 'tunic hem', round(cloth.BLOUSE_HEM_Z, 3), flush=True)
    return float(P['shoulder01.L'].head.z) + 0.06


def outline(points, z, band=0.012, nphi=120):
    slab = points[np.abs(points[:, 2] - z) < band, :2]
    mid = (slab.max(0) + slab.min(0)) / 2
    phi = np.linspace(0, 2 * np.pi, nphi, endpoint=False)
    dirs = np.stack([np.cos(phi), np.sin(phi)], 1)
    return mid, phi, ((slab - mid) @ dirs.T).max(0)


def fill_hollows(ob, body, rig, zlo, zhi, ease=0.020):
    """Stand the tunic off the body's hollows: woven cloth bridges them, it does not follow them in."""
    pos = np.array([v.co for v in ob.data.vertices])
    co = verts_world(body)[cloth.arm_weight(body) < 0.3]
    torso = np.ones(len(pos), bool)
    for side, (s, d) in cloth.arm_axes(rig).items():
        along = (pos - s) @ d
        radial = np.linalg.norm((pos - s) - along[:, None] * d, axis=1)
        torso &= ~((along > -0.01) & (radial < 0.10))
    zs = np.linspace(zlo, zhi, 34)
    table = [outline(co, z, 0.014) for z in zs]
    phi = table[0][1]
    sup = np.array([t[2] for t in table])
    mid = np.array([t[0] for t in table])
    for _ in range(3):
        sup[1:-1] = (sup[:-2] + sup[1:-1] * 2 + sup[2:]) / 4
    moved = 0
    for i in np.nonzero(torso & (pos[:, 2] > zlo) & (pos[:, 2] < zhi))[0]:
        p = pos[i]
        k = float(np.interp(p[2], zs, np.arange(len(zs))))
        k0 = min(int(k), len(zs) - 2)
        m = mid[k0] + (mid[k0 + 1] - mid[k0]) * (k - k0)
        d = p[:2] - m
        r = np.linalg.norm(d)
        a = math.atan2(d[1], d[0]) % (2 * math.pi)
        s = sup[k0] + (sup[k0 + 1] - sup[k0]) * (k - k0)
        want = float(np.interp(a, np.append(phi, 2 * np.pi), np.append(s, s[0]))) + ease
        w = float(np.clip((p[2] - zlo) / 0.05, 0, 1) * np.clip((zhi - p[2]) / 0.05, 0, 1))
        if want > r:
            pos[i, :2] = m + d / r * (r + (want - r) * w)
            moved += 1
    ob.data.vertices.foreach_set('co', pos.astype(np.float32).ravel())
    ob.data.update()
    print('filled hollows at', moved, 'vertices', flush=True)


def tunic_uv(ob, axes, top_z):
    """Strips run down the body from the shoulders and along each sleeve, as a tunic is cut from strip cloth.

    U is along the strips, V across them: front and back panels each start their strips at the centre line.
    """
    rest = np.array([v.co for v in ob.data.vertices])
    me = ob.data
    layer = me.uv_layers.new(name='UVMap')
    nloops = len(me.loops)
    uv = np.zeros((nloops, 2), np.float32)
    v_idx = np.zeros(nloops, np.int32)
    me.loops.foreach_get('vertex_index', v_idx)
    for poly in me.polygons:
        ids = list(poly.loop_indices)
        p = rest[v_idx[ids]]
        c = p.mean(0)
        sleeve = False
        for side, sign in (('L', 1), ('R', -1)):
            s, d = axes[side]
            along = (c - s) @ d
            radial = np.linalg.norm((c - s) - along * d)
            if c[0] * sign > 0 and along > 0.012 and radial < 0.085:
                sleeve = True
                a = (p - s) @ d
                ref = np.cross(d, (0, 1, 0))
                ref /= np.linalg.norm(ref)
                w = p - s - a[:, None] * d
                angle = np.arctan2(w @ np.cross(d, ref), w @ ref)
                if angle.max() - angle.min() > np.pi:
                    angle = np.where(angle < 0, angle + 2 * np.pi, angle)
                uv[ids, 0] = a / cloth.U_PERIOD + 0.31
                uv[ids, 1] = (angle * 0.065) / cloth.V_PERIOD + (0.20 if side == 'L' else 0.70)
        if not sleeve:
            # each panel is flat cloth wrapped on an oval, so measure along the oval from the centre line
            front = c[1] < -0.012
            depth = np.abs(p[:, 1] + 0.012) + 0.03
            across = 0.17 * np.arctan2(p[:, 0], depth * 1.25)
            uv[ids, 0] = (top_z - p[:, 2]) / cloth.U_PERIOD
            uv[ids, 1] = across / cloth.V_PERIOD + (0.0 if front else 0.5) + 0.0455
    layer.data.foreach_set('uv', uv.ravel())


def tunic_stage():
    body, rig, trousers = (bpy.data.objects[n] for n in ('Body', 'Rig', 'Trousers'))
    top_z = measure(rig)
    cloth.set_frame(1)
    cloth.add_collider(trousers, outer=0.004)
    if 'Collision' not in body.modifiers:
        cloth.add_collider(body)
    # his drawing arm lifts the right sleeve above the height the toolkit cuts the neck at: keep it whole
    ob = cloth.make_blouse(body, rig, collection('Figure'), trousers, raised_arms=True)
    ob.name = ob.data.name = 'Tunic'
    tunic_uv(ob, cloth.arm_axes(rig), top_z)
    fill_hollows(ob, body, rig, cloth.WAIST_Z - 0.06, 1.25)
    mod = ob.modifiers.new('Cloth', 'CLOTH')
    cloth.cotton(mod, mass=0.36, tension=32, compression=32, shear=24, bending=10, pin='pin')
    adj = edge_adjacency(ob.data)
    co = cloth.relax(cloth.run_sim(ob), adj, 2)
    front = (co[:, 1] < -0.04) & (co[:, 2] > cloth.WAIST_Z - 0.04) & (co[:, 2] < 1.28)
    co[front] = cloth.relax(co, adj, 18)[front]
    np.save(WORK / 'tunic_final.npy', co)
    cloth.set_frame(1)
    cloth.freeze(ob, co)
    edge = ob.data.attributes.new('edge_dist', 'FLOAT', 'POINT')
    edge.data.foreach_set('value', np.clip(cloth.geodesic_from_boundary(ob.data) / 0.1, 0, 1).astype(np.float32))
    body.modifiers.remove(body.modifiers['Collision'])
    trousers.modifiers.remove(trousers.modifiers['Collision'])
    # from here on he stays in the final pose
    cloth.set_frame(posing.POSE_END)
    rig.animation_data.action = None
    save('40_cloth.blend')
