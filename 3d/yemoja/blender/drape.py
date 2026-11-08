"""Her ìró and bùbá: the toolkit's wrapper and blouse in àdìrẹ, cut to her measure.

The ìró is one wrapper tied at the waist and the bùbá a loose blouse with short sleeves, as
on her gallery figure. The white pot rests against her left hip, so both simulations treat it
as solid and the cloth settles round it.
"""
import math

import bpy
import numpy as np

import cloth
from common import WORK, collection, edge_adjacency, save, verts_world


def measure(rig):
    """Fit the toolkit's garment heights to her skeleton."""
    P = rig.pose.bones
    cloth.WAIST_Z = float(P['spine03'].head.z) + 0.035
    cloth.HIP_Z = float(P['pelvis.L'].head.z) + 0.005
    cloth.HEM_Z = 0.125
    cloth.OUTER_EDGE = np.radians(-60)      # the edge falls down the front on her left
    cloth.BLOUSE_HEM_Z = cloth.HIP_Z - 0.035
    cloth.SLEEVE_END = 0.175
    cloth.SLEEVE_EASE = 0.032
    cloth.SLEEVE_FLARE = 0.030
    cloth.EASE_BLEND = 30
    n = P['neck01'].head
    cloth.NECK = dict(centre=(float(n.x) + 0.010, float(n.y) + 0.010, float(n.z) + 0.016), radii=(0.110, 0.100, 0.082))
    print('waist', round(cloth.WAIST_Z, 3), 'hip', round(cloth.HIP_Z, 3), 'blouse hem', round(cloth.BLOUSE_HEM_Z, 3), flush=True)


def pot_collider(on):
    pot = bpy.data.objects['WhitePot']
    if on and 'Collision' not in pot.modifiers:
        cloth.add_collider(pot, outer=0.004)
    if not on and 'Collision' in pot.modifiers:
        pot.modifiers.remove(pot.modifiers['Collision'])


def wrapper_stage():
    measure(bpy.data.objects['Rig'])
    pot_collider(True)
    cloth.wrapper_stage()


def outline(points, z, band=0.012, nphi=120):
    slab = points[np.abs(points[:, 2] - z) < band, :2]
    mid = (slab.max(0) + slab.min(0)) / 2
    phi = np.linspace(0, 2 * np.pi, nphi, endpoint=False)
    dirs = np.stack([np.cos(phi), np.sin(phi)], 1)
    return mid, phi, ((slab - mid) @ dirs.T).max(0)


def fill_hollows(ob, body, rig, zlo, zhi, ease=0.020):
    """Stand the blouse off the body's hollows: woven cloth bridges them, it does not follow them in."""
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


def buba_stage():
    body, rig, wrapper = (bpy.data.objects[n] for n in ('Body', 'Rig', 'Wrapper'))
    measure(rig)
    cloth.set_frame(1)
    cloth.add_collider(wrapper, outer=0.004)
    if 'Collision' not in body.modifiers:
        cloth.add_collider(body)
    pot_collider(True)
    ob = cloth.make_blouse(body, rig, collection('Figure'), wrapper)
    cloth.blouse_uv(ob, cloth.arm_axes(rig))
    fill_hollows(ob, body, rig, cloth.WAIST_Z + 0.02, 1.25)
    mod = ob.modifiers.new('Cloth', 'CLOTH')
    cloth.cotton(mod, mass=0.34, tension=30, compression=30, shear=22, bending=8, pin='pin')
    adj = edge_adjacency(ob.data)
    co = cloth.relax(cloth.run_sim(ob), adj, 2)
    front = (co[:, 1] < -0.04) & (co[:, 2] > cloth.WAIST_Z + 0.05) & (co[:, 2] < 1.25)
    co[front] = cloth.relax(co, adj, 22)[front]
    np.save(WORK / 'blouse_final.npy', co)
    cloth.set_frame(1)
    cloth.freeze(ob, co)
    edge = ob.data.attributes.new('edge_dist', 'FLOAT', 'POINT')
    edge.data.foreach_set('value', np.clip(cloth.geodesic_from_boundary(ob.data) / 0.1, 0, 1).astype(np.float32))
    body.modifiers.remove(body.modifiers['Collision'])
    wrapper.modifiers.remove(wrapper.modifiers['Collision'])
    pot_collider(False)
    # from here on she stays in the final pose
    cloth.set_frame(40)
    rig.animation_data.action = None
    save('40_cloth.blend')
