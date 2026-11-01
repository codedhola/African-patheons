"""Her ìró, bùbá and sash: the toolkit's cloth, cut to her measure.

The ìró is one wrapper tied at the waist and the bùbá a wide-sleeved blouse over it. A gold
sash is tied round the blouse, so while the blouse settles its waist is drawn in and the
cloth above and below gathers on its own.
"""
import math

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import cloth
from common import WORK, collection, edge_adjacency, obj_from_arrays, save, verts_world
from procedural import Noise, add_curves

SIM_END = 150
CINCH_START, CINCH_END = 45, 100
CINCH_LIFT = 0.024
SASH_WIDE = 0.078
SASH_EASE = 0.030       # past its edges the cloth it presses in eases out over this far
END_LONG = (0.56, 0.47)
END_WIDE = 0.105
END_ROWS = 64
END_ACROSS = 20
KNOT_AZ = math.radians(300)     # on her left front


def measure(rig):
    """Fit the toolkit's garment heights to her skeleton."""
    P = rig.pose.bones
    cloth.WAIST_Z = float(P['spine03'].head.z) + 0.040
    cloth.HIP_Z = float(P['pelvis.L'].head.z) + 0.005
    cloth.HEM_Z = 0.118
    cloth.OUTER_EDGE = np.radians(-122)      # the edge falls down the front on her right, the side she steps out on
    cloth.BLOUSE_HEM_Z = cloth.HIP_Z - 0.018
    cloth.SLEEVE_END = 0.255
    cloth.SLEEVE_EASE = 0.030
    cloth.SLEEVE_FLARE = 0.052
    cloth.EASE_BLEND = 40
    n = P['neck01'].head
    cloth.NECK = dict(centre=(float(n.x) + 0.012, float(n.y) + 0.012, float(n.z) + 0.018), radii=(0.112, 0.102, 0.084))
    print('waist', round(cloth.WAIST_Z, 3), 'hip', round(cloth.HIP_Z, 3), 'blouse hem', round(cloth.BLOUSE_HEM_Z, 3), flush=True)
    return cloth.WAIST_Z + 0.012


def wrapper_stage():
    measure(bpy.data.objects['Rig'])
    cloth.wrapper_stage()


def outline(points, z, band=0.012, nphi=120):
    """Centre and support distance of a slice through a cloud of points, by angle."""
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


def add_cinch(ob, body, z):
    """A shape key that draws a ring of the blouse in to the waist, and a pin group that follows it."""
    pos = np.array([v.co for v in ob.data.vertices])
    co = verts_world(body)[cloth.arm_weight(body) < 0.3]
    mid, phi, sup = outline(co, z, 0.03)
    ring = np.nonzero((np.abs(pos[:, 2] - z) < SASH_WIDE * 0.46) & (np.hypot(pos[:, 0] - mid[0], pos[:, 1] - mid[1]) < 0.235))[0]
    goal = pos.copy()
    for i in ring:
        d = pos[i, :2] - mid
        a = math.atan2(d[1], d[0]) % (2 * math.pi)
        r = float(np.interp(a, np.append(phi, 2 * np.pi), np.append(sup, sup[0]))) + 0.0065
        goal[i, :2] = mid + d / np.linalg.norm(d) * r
    goal[ring, 2] += CINCH_LIFT         # the ring rises a little, so the blouse pouches over the sash
    ob.shape_key_add(name='Basis')
    key = ob.shape_key_add(name='Cinch')
    key.data.foreach_set('co', goal.astype(np.float32).ravel())
    key.value = 0
    key.keyframe_insert('value', frame=CINCH_START)
    key.value = 1
    key.keyframe_insert('value', frame=CINCH_END)
    ob.vertex_groups['pin'].add(ring.tolist(), 1.0, 'REPLACE')
    np.savez(WORK / 'cinch_ring.npz', mid=mid, phi=phi, sup=sup + 0.0065)
    print('cinched', len(ring), 'vertices at', round(z, 3), flush=True)


def buba_stage():
    body, rig, wrapper = (bpy.data.objects[n] for n in ('Body', 'Rig', 'Wrapper'))
    cinch_z = measure(rig)
    cloth.set_frame(1)
    cloth.add_collider(wrapper, outer=0.004)
    if 'Collision' not in body.modifiers:
        cloth.add_collider(body)
    ob = cloth.make_blouse(body, rig, collection('Figure'), wrapper)
    cloth.blouse_uv(ob, cloth.arm_axes(rig))
    fill_hollows(ob, body, rig, cinch_z + 0.03, 1.325)
    add_cinch(ob, body, cinch_z)
    mod = ob.modifiers.new('Cloth', 'CLOTH')
    cloth.cotton(mod, mass=0.34, tension=30, compression=30, shear=22, bending=7, pin='pin')
    mod.point_cache.frame_end = SIM_END
    adj = edge_adjacency(ob.data)
    co = cloth.relax(cloth.run_sim(ob, SIM_END), adj, 2)
    # the body's fine surface detail should not print through a cotton blouse
    front = (co[:, 1] < -0.04) & (co[:, 2] > cinch_z + 0.09) & (co[:, 2] < 1.31)
    co[front] = cloth.relax(co, adj, 26)[front]
    np.save(WORK / 'blouse_final.npy', co)
    cloth.set_frame(1)
    ob.shape_key_clear()
    cloth.freeze(ob, co)
    edge = ob.data.attributes.new('edge_dist', 'FLOAT', 'POINT')
    edge.data.foreach_set('value', np.clip(cloth.geodesic_from_boundary(ob.data) / 0.1, 0, 1).astype(np.float32))
    body.modifiers.remove(body.modifiers['Collision'])
    wrapper.modifiers.remove(wrapper.modifiers['Collision'])
    # from here on she stays in the final pose
    cloth.set_frame(40)
    rig.animation_data.action = None
    np.save(WORK / 'cinch_z.npy', np.array(cinch_z + CINCH_LIFT))
    save('40_cloth.blend')


def press_under(ob, ring, z):
    """A tied sash flattens what it crosses: pouched cloth goes under it and eases out past its edges."""
    mid, phi, sup = ring
    co = np.array([v.co for v in ob.data.vertices])
    d = co[:, :2] - mid
    r = np.hypot(d[:, 0], d[:, 1])
    a = np.arctan2(d[:, 1], d[:, 0]) % (2 * np.pi)
    limit = np.interp(a, np.append(phi, 2 * np.pi), np.append(sup, sup[0]))
    # make_blouse tagged its sleeve faces; they hang past the sash and stay free of it
    sleeve = np.zeros(len(ob.data.polygons), int)
    ob.data.attributes['sleeve'].data.foreach_get('value', sleeve)
    torso = np.ones(len(co), bool)
    for poly in ob.data.polygons:
        if sleeve[poly.index]:
            torso[list(poly.vertices)] = False
    w = np.clip((SASH_WIDE / 2 + SASH_EASE - np.abs(co[:, 2] - z)) / (SASH_EASE - 0.005), 0, 1)
    w = w * w * (3 - 2 * w)
    over = torso & (r > limit) & (w > 0)
    co[over, :2] = mid + d[over] * ((limit + (r - limit) * (1 - w))[over] / r[over])[:, None]
    edge = over & (w < 1)
    co[edge] = cloth.relax(co, edge_adjacency(ob.data), 3)[edge]
    cloth.freeze(ob, co)
    print('pressed', int(over.sum()), 'vertices under the sash', flush=True)


def make_band(col, ring, z):
    """The sash round the waist: a band on the drawn-in ring of the blouse, wrinkled across."""
    rows, cols = 26, 240
    n = Noise(8)
    mid, phi, sup = ring
    sup = np.interp(np.linspace(0, 2 * np.pi, 240, endpoint=False), np.append(phi, 2 * np.pi), np.append(sup, sup[0]))
    phi = np.linspace(0, 2 * np.pi, 240, endpoint=False)
    for _ in range(3):
        sup = (sup + np.roll(sup, 1) + np.roll(sup, -1)) / 3
    across = np.linspace(-0.5, 0.5, rows)
    th = np.linspace(0, 2 * np.pi, cols)
    verts = np.zeros((rows, cols, 3))
    uv = np.zeros((rows, cols, 2))
    for i, a in enumerate(across):
        zi = z + a * SASH_WIDE
        r = np.interp(th, np.append(phi, 2 * np.pi), np.append(sup, sup[0]))
        crease = 0.0015 * np.sin(th * 15 + 1.6 * n(np.stack([np.cos(th), np.sin(th), np.full_like(th, a * 1.6)], -1) * 1.7) * 2.6)
        crease = crease * (0.4 + 0.6 * (1 - (a * 2) ** 2))
        r = r + 0.0055 + crease + 0.0030 * (1 - (a * 2) ** 2)
        verts[i, :, 0] = mid[0] + np.cos(th) * r
        verts[i, :, 1] = mid[1] + np.sin(th) * r
        verts[i, :, 2] = zi + 0.002 * np.sin(th * 7 + a * 4)
        uv[i, :, 0] = th * 0.19 / cloth.U_PERIOD
        uv[i, :, 1] = (a + 0.5) * SASH_WIDE / cloth.V_PERIOD + 0.012
    idx = lambda i, j: i * cols + j
    faces = [(idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)) for i in range(rows - 1) for j in range(cols - 1)]
    ob = obj_from_arrays('Sash', verts.reshape(-1, 3), faces, col, uv=uv.reshape(-1, 2))
    a = KNOT_AZ
    r = float(np.interp(a, phi, sup)) + 0.016
    return ob, Vector((mid[0] + math.cos(a) * r, mid[1] + math.sin(a) * r, z)), Vector((math.cos(a), math.sin(a), 0.0))


def make_knot(col, at, out):
    """A plain square knot: a squat ball of the same cloth, wound round itself."""
    n = Noise(21)
    na, nb = 120, 60
    A, B = np.meshgrid(np.linspace(0, 2 * np.pi, na, endpoint=False), np.linspace(0.01, np.pi - 0.01, nb), indexing='ij')
    u = np.stack([np.sin(B) * np.cos(A), np.sin(B) * np.sin(A), np.cos(B)], -1)
    wind = 0.0052 * np.sin(A * 3 + B * 4 + n.fbm(u * 1.5, 2) * 2.2) ** 2
    out = np.array(out)
    side = np.cross((0, 0, 1.0), out)
    p = u * np.array([0.047, 0.031, 0.034])[None, None] * (1 + wind[..., None] / 0.03)
    world = np.array(at) + out * 0.010 + p[..., 0, None] * side + p[..., 1, None] * out + p[..., 2, None] * np.array([0, 0, 1.0])
    idx = lambda i, j: (i % na) * nb + j
    faces = [(idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)) for i in range(na) for j in range(nb - 1)]
    uv = np.stack([A.ravel() * 0.03 / cloth.U_PERIOD, B.ravel() * 0.03 / cloth.V_PERIOD + 0.018], 1)
    return obj_from_arrays('SashKnot', world.reshape(-1, 3), faces, col, uv=uv)


def make_ends(col, tree, at, out):
    """Two tails hanging from the knot, narrow where they leave it. One mesh, two strips."""
    verts, uvs, faces, pins, base = [], [], [], [], 0
    side = Vector((0, 0, 1)).cross(out)
    for long, shift, turn in ((END_LONG[0], 0.024, 0.0), (END_LONG[1], -0.020, 0.0)):
        s = np.linspace(0, 1, END_ROWS)
        a = np.linspace(-1, 1, END_ACROSS)
        S, A = np.meshgrid(s, a, indexing='ij')
        path = []
        for t in s:
            z = at.z - 0.012 - t * long * 0.97
            q = at + side * (shift + 0.05 * shift / abs(shift) * t) + out * 0.6
            q.z = z
            hit = tree.ray_cast(q, -out, 0.8)
            p = hit[0] + out * 0.024 if hit[0] is not None else q - out * 0.55
            path.append(p)
        path = np.array(path)
        for _ in range(8):
            path[1:-1] = (path[:-2] + path[1:-1] * 2 + path[2:]) / 4
        half = (0.020 + (END_WIDE / 2 - 0.020) * np.clip(S / 0.42, 0, 1) ** 0.7)
        pleat = 0.012 * np.sin(A * 7.5 + 0.8) * (1 - np.clip(S / 0.5, 0, 1))
        pos = path[(S * (END_ROWS - 1)).round().astype(int)] + np.array(side)[None, None] * (A * half)[..., None] + np.array(out)[None, None] * pleat[..., None]
        verts.append(pos.reshape(-1, 3))
        uvs.append(np.stack([S.ravel() * long / cloth.U_PERIOD + 0.1, (A.ravel() + 1) / 2 * END_WIDE / cloth.V_PERIOD + 0.012], 1))
        idx = lambda i, j: base + i * END_ACROSS + j
        faces += [(idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)) for i in range(END_ROWS - 1) for j in range(END_ACROSS - 1)]
        pins += [idx(i, j) for i in range(3) for j in range(END_ACROSS)]
        base += END_ROWS * END_ACROSS
    ob = obj_from_arrays('SashEnds', np.concatenate(verts), faces, col, uv=np.concatenate(uvs))
    ob.vertex_groups.new(name='pin').add(pins, 1.0, 'REPLACE')
    return ob


def fringe(ob, col, material):
    """Knotted warp ends along the foot of each tail."""
    rng = np.random.default_rng(5)
    co = np.array([v.co for v in ob.data.vertices]).reshape(2, END_ROWS, END_ACROSS, 3)
    strands = []
    for strip in co:
        edge = strip[-1]
        drop = edge - strip[-4]
        drop /= np.linalg.norm(drop, axis=1, keepdims=True)
        for j in range(END_ACROSS - 1):
            for t in np.linspace(0, 1, 9, endpoint=False):
                a = edge[j] * (1 - t) + edge[j + 1] * t
                d = drop[j] + np.array([0, 0, -1.2])
                d /= np.linalg.norm(d)
                L = rng.uniform(0.050, 0.068)
                w = rng.normal(0, 1, (6, 3)).cumsum(0) * 0.0014
                f = np.linspace(0, 1, 6)[:, None]
                strands.append(a + d * f * L + w * f)
    return add_curves('Fringe', np.array(strands, np.float32), 0.00042, 0.00028, col, material)


def surface_tree(obs):
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys, base = [], [], 0
    for ob in obs:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        verts += [ev.matrix_world @ v.co for v in me.vertices]
        polys += [tuple(i + base for i in p.vertices) for p in me.polygons]
        base += len(me.vertices)
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys)


def sash_stage():
    bpy.ops.wm.open_mainfile(filepath=str(WORK / '40_cloth.blend'))
    blouse, wrapper = (bpy.data.objects[n] for n in ('Blouse', 'Wrapper'))
    z = float(np.load(WORK / 'cinch_z.npy'))
    col = collection('Figure')
    saved = np.load(WORK / 'cinch_ring.npz')
    ring = saved['mid'], saved['phi'], saved['sup']
    press_under(blouse, ring, z)
    band, at, out = make_band(col, ring, z)
    make_knot(col, at, out)
    tree = surface_tree([wrapper, blouse])
    ob = make_ends(col, tree, at, out)
    cloth.add_collider(wrapper, outer=0.004)
    cloth.add_collider(blouse, outer=0.004)
    mod = ob.modifiers.new('Cloth', 'CLOTH')
    cloth.cotton(mod, mass=0.30, tension=24, compression=24, shear=16, bending=4, pin='pin')
    co = cloth.relax(cloth.run_sim(ob, 80), edge_adjacency(ob.data), 1)
    bpy.context.scene.frame_set(1)
    cloth.freeze(ob, co)
    wrapper.modifiers.remove(wrapper.modifiers['Collision'])
    blouse.modifiers.remove(blouse.modifiers['Collision'])
    save('45_sash.blend')
