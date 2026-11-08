"""Her akwa miri, tied at the chest: one wrapper, simulated on her as her arms come down.

The gallery figure wears the cloth so. The toolkit's wrapper is cut for the waist; this one is
cut the same way, from outlines of the body by angle at each height, but it starts above her
bust, under her arms, and below the bust it hangs: an outline may grow as it goes down, over
the hips, but it never draws back in to the waist. It runs to the middle of her calves, its outer
edge down the front on her left, and the clay pot stands against it as she carries it.
"""
import math

import bpy
import numpy as np

import cloth
from common import WORK, collection, edge_adjacency, obj_from_arrays, save

HEM_Z = 0.30
OUTER_EDGE = np.radians(-60)     # her left front
OVERLAP = 0.36
LAYER_GAP = 0.009
SIM_END = 110


def top_z(rig):
    """Above her bust, just under her arms: tied across the upper chest, so the cloth covers the breasts and falls from them."""
    P = rig.pose.bones
    return float((P['upperarm01.L'].head.z + P['upperarm01.R'].head.z) / 2) - 0.068


def make_wrapper(body, rig, col):
    nv, nu = 120, 240
    top = top_z(rig)
    v = np.linspace(0, 1, nv)                 # 0 at the top, 1 at the hem
    zs = top + (HEM_Z - top) * v
    # the cut is taken from her final pose, arms down: the skin under them bulges a little as they settle,
    # and the pinned top edge has to lie outside it then, not where it was while her arms were raised
    cloth.set_frame(40)
    co = cloth.body_only_coords(body)
    cloth.set_frame(1)
    phi, dirs, mid, sup = cloth.outlines(co, zs)
    # from the bust down the cloth hangs: it may spread over the hips but never comes back in to the waist
    for i in range(1, nv):
        sup[i] = np.maximum(sup[i], sup[i - 1])
    kernel = np.hanning(15)
    kernel /= kernel.sum()
    pad = np.pad(sup, ((7, 7), (0, 0)), mode='edge')
    sup = np.stack([np.convolve(pad[:, k], kernel, 'valid') for k in range(sup.shape[1])], 1)
    # snug where it is tied across the bust, a little room lower down, and a touch of flare at the hem
    ease = 0.005 + 0.010 * np.clip(v / 0.4, 0, 1) + 0.022 * np.clip((v - 0.5) / 0.5, 0, 1)
    verts = np.zeros((nv, nu, 3))
    uvs = np.zeros((nv, nu, 2))
    for i in range(nv):
        r = sup[i] + ease[i]
        ring = mid[i] + dirs * r[:, None]
        closed = np.vstack([ring, ring[:1]])
        seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
        P = seg.sum()
        Wd = P + OVERLAP
        s = np.linspace(0, Wd, nu)
        start = (OUTER_EDGE % (2 * np.pi)) / (2 * np.pi) * len(phi)
        cum = np.concatenate([[0], np.cumsum(seg)])
        s0 = np.interp(start, np.arange(len(cum)), cum)
        param = (s0 - s) % P
        x = np.interp(param, cum, closed[:, 0])
        y = np.interp(param, cum, closed[:, 1])
        layer = LAYER_GAP * (1 - s / Wd) * (Wd / P)
        d = np.stack([x - mid[i, 0], y - mid[i, 1]], 1)
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        verts[i, :, 0] = x + d[:, 0] * layer
        verts[i, :, 1] = y + d[:, 1] * layer
        verts[i, :, 2] = zs[i]
        uvs[i, :, 0] = s / cloth.U_PERIOD
        uvs[i, :, 1] = (zs[i] - HEM_Z) / cloth.V_PERIOD + 0.012
    print('wrapper: top', round(top, 3), 'round the bust', round(float(np.linalg.norm(np.diff(np.vstack([verts[0], verts[0, :1]]), axis=0), axis=1).sum()), 3), flush=True)
    idx = lambda i, j: i * nu + j
    faces = [(idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)) for i in range(nv - 1) for j in range(nu - 1)]
    ob = obj_from_arrays('Wrapper', verts.reshape(-1, 3), faces, col, uv=uvs.reshape(-1, 2))
    pin = ob.vertex_groups.new(name='pin')
    pin.add([idx(i, j) for i in range(2) for j in range(nu)], 1.0, 'REPLACE')
    return ob


def wrapper_stage():
    body, rig = bpy.data.objects['Body'], bpy.data.objects['Rig']
    pot = bpy.data.objects['ClayPot']
    cloth.set_frame(1)
    cloth.add_collider(body)
    cloth.add_collider(pot, outer=0.004)
    ob = make_wrapper(body, rig, collection('Figure'))
    mod = ob.modifiers.new('Cloth', 'CLOTH')
    cloth.cotton(mod, mass=0.30, tension=28, compression=28, shear=18, bending=4.0, pin='pin')
    mod.point_cache.frame_end = SIM_END
    cl = mod.collision_settings
    cl.use_self_collision = True
    cl.self_distance_min = 0.0035
    cl.self_friction = 8
    co = cloth.relax(cloth.run_sim(ob, SIM_END), edge_adjacency(ob.data), 1)
    np.save(WORK / 'wrapper_final.npy', co)
    cloth.set_frame(1)
    cloth.freeze(ob, co)
    edge = ob.data.attributes.new('edge_dist', 'FLOAT', 'POINT')
    edge.data.foreach_set('value', np.clip(cloth.geodesic_from_boundary(ob.data) / 0.1, 0, 1).astype(np.float32))
    body.modifiers.remove(body.modifiers['Collision'])
    pot.modifiers.remove(pot.modifiers['Collision'])
    # from here on she stays in the final pose
    cloth.set_frame(40)
    rig.animation_data.action = None
    save('30_wrapper.blend')
