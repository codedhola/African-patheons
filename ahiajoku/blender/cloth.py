"""The Akwete pair, simulated on the moving body.

Wrapper: one cloth wound round the hips with its outer edge lying down the front.
Blouse: a loose shell cut from the rest-pose body, so it starts out fitted with
the arms lifted and falls into its folds as the arms come down to hold the yam.

The texture's rows run round the body. UVs are in cloth units: U repeats every
60.5 cm of cloth and V covers the loom's 1.15 m, with V = 0 at the hem border.
"""
import time
from collections import deque

import bmesh
import bpy
import numpy as np
from mathutils import Vector

import pose as posing
from common import WORK, collection, edge_adjacency, obj_from_arrays, save, verts_world

U_PERIOD = 0.605
V_PERIOD = 1.15
SIM_END = 110

WAIST_Z = 1.035
HEM_Z = 0.125
HIP_Z = 0.86
OUTER_EDGE = np.radians(-52)     # where the cloth's outer edge lies: her left front
OVERLAP = 0.36                   # how far the cloth runs on under its own outer edge
LAYER_GAP = 0.009


def set_frame(f):
    bpy.context.scene.frame_set(f)


def arm_weight(body):
    groups = {g.index for g in body.vertex_groups if any(k in g.name for k in ('upperarm', 'lowerarm', 'wrist', 'finger', 'metacarpal'))}
    return np.array([sum(g.weight for g in v.groups if g.group in groups) for v in body.data.vertices])


def body_only_coords(body):
    """Frame 1 coordinates of the body, without the arms."""
    return verts_world(body)[arm_weight(body) < 0.3]


def outlines(co, zs, nphi=120):
    """Support function of the body slice at each height, smoothed through height."""
    phi = np.linspace(0, 2 * np.pi, nphi, endpoint=False)
    dirs = np.stack([np.cos(phi), np.sin(phi)], 1)
    sup = np.zeros((len(zs), nphi))
    mid = np.zeros((len(zs), 2))
    for i, z in enumerate(zs):
        slab = co[np.abs(co[:, 2] - z) < 0.016, :2]
        mid[i] = (slab.max(0) + slab.min(0)) / 2
    # keep the centre line straight: a wrapped skirt hangs from the hips
    mid[:] = mid.mean(0)
    for i, z in enumerate(zs):
        slab = co[np.abs(co[:, 2] - z) < 0.016, :2]
        sup[i] = ((slab - mid[i]) @ dirs.T).max(0)
    return phi, dirs, mid, sup


def make_wrapper(body, col):
    nv, nu = 118, 236
    v = np.linspace(0, 1, nv)                 # 0 at the waist, 1 at the hem
    zs = WAIST_Z + (HEM_Z - WAIST_Z) * v
    co = body_only_coords(body)
    phi, dirs, mid, sup = outlines(co, zs)

    # below the hips the cloth hangs, so an outline may grow downward but never shrink
    ihip = int(np.argmin(np.abs(zs - HIP_Z)))
    for i in range(ihip + 1, nv):
        sup[i] = np.maximum(sup[i], sup[i - 1])
    kernel = np.hanning(15)
    kernel /= kernel.sum()
    pad = np.pad(sup, ((7, 7), (0, 0)), mode='edge')
    sup = np.stack([np.convolve(pad[:, k], kernel, 'valid') for k in range(sup.shape[1])], 1)

    # easing: snug at the waist, room over the hips, a touch of flare at the hem
    ease = 0.011 + 0.016 * np.clip(v / 0.25, 0, 1) + 0.034 * np.clip((v - 0.25) / 0.75, 0, 1)
    verts = np.zeros((nv, nu, 3))
    uvs = np.zeros((nv, nu, 2))
    wid = np.zeros(nv)
    for i in range(nv):
        r = sup[i] + ease[i]
        ring = mid[i] + dirs * r[:, None]
        closed = np.vstack([ring, ring[:1]])
        seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
        P = seg.sum()
        W = P + OVERLAP
        wid[i] = W
        # walk from the outer edge across the front (angle falling), round the back and on under it
        s = np.linspace(0, W, nu)
        start = (OUTER_EDGE % (2 * np.pi)) / (2 * np.pi) * len(phi)
        cum = np.concatenate([[0], np.cumsum(seg)])
        s0 = np.interp(start, np.arange(len(cum)), cum)
        param = (s0 - s) % P
        x = np.interp(param, cum, closed[:, 0])
        y = np.interp(param, cum, closed[:, 1])
        layer = LAYER_GAP * (1 - s / W) * (W / P)
        d = np.stack([x - mid[i, 0], y - mid[i, 1]], 1)
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        verts[i, :, 0] = x + d[:, 0] * layer
        verts[i, :, 1] = y + d[:, 1] * layer
        verts[i, :, 2] = zs[i]
        uvs[i, :, 0] = s / U_PERIOD
        uvs[i, :, 1] = (zs[i] - HEM_Z) / V_PERIOD + 0.012
    print('wrapper: waist', round(wid[0], 3), 'hip', round(wid[ihip], 3), 'hem', round(wid[-1], 3), 'wide', flush=True)

    idx = lambda i, j: i * nu + j
    faces = [(idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)) for i in range(nv - 1) for j in range(nu - 1)]
    ob = obj_from_arrays('Wrapper', verts.reshape(-1, 3), faces, col, uv=uvs.reshape(-1, 2))

    pin = ob.vertex_groups.new(name='pin')
    pin.add([idx(i, j) for i in range(2) for j in range(nu)], 1.0, 'REPLACE')
    return ob


def cotton(mod, mass=0.34, tension=26, compression=26, shear=18, bending=5.0, pin=None):
    cs = mod.settings
    cs.quality = 7
    cs.mass = mass
    cs.tension_stiffness = tension
    cs.compression_stiffness = compression
    cs.shear_stiffness = shear
    cs.bending_stiffness = bending
    cs.tension_damping = 5
    cs.compression_damping = 5
    cs.shear_damping = 5
    cs.air_damping = 1.5
    cs.time_scale = 1.0
    if pin:
        cs.vertex_group_mass = pin
        cs.pin_stiffness = 1.0
    cl = mod.collision_settings
    cl.collision_quality = 3
    cl.distance_min = 0.0035
    cl.friction = 12
    mod.point_cache.frame_start = 1
    mod.point_cache.frame_end = SIM_END


def run_sim(ob, end=SIM_END):
    t0 = time.time()
    for f in range(1, end + 1):
        set_frame(f)
        if f % 10 == 0 or f == 1:
            print(ob.name, 'frame', f, round(time.time() - t0, 1), 's', flush=True)
    return verts_world(ob)


def add_collider(ob, outer=0.005):
    m = ob.modifiers.new('Collision', 'COLLISION')
    ob.collision.thickness_outer = outer
    ob.collision.thickness_inner = 0.02
    ob.collision.cloth_friction = 10
    return m


def freeze(ob, co):
    """Drop the simulation and keep the final shape in the mesh."""
    for m in list(ob.modifiers):
        ob.modifiers.remove(m)
    ob.data.vertices.foreach_set('co', co.astype(np.float32).ravel())
    ob.data.update()
    ob.matrix_world.identity()


def relax(co, adj, iterations=2, amount=0.5):
    """Take the last high-frequency crumple out of a simulated sheet."""
    p = co.copy()
    for _ in range(iterations):
        nb = np.array([p[a].mean(0) if len(a) > 2 else p[i] for i, a in enumerate(adj)])
        p += (nb - p) * amount
    return p


def wrapper_stage():
    body = bpy.data.objects['Body']
    set_frame(1)
    add_collider(body)
    col = collection('Figure')
    ob = make_wrapper(body, col)
    mod = ob.modifiers.new('Cloth', 'CLOTH')
    cotton(mod, pin='pin')
    cl = mod.collision_settings
    cl.use_self_collision = True
    cl.self_distance_min = 0.0035
    cl.self_friction = 8
    co = relax(run_sim(ob), edge_adjacency(ob.data), 1)
    np.save(WORK / 'wrapper_final.npy', co)
    set_frame(1)
    freeze(ob, co)
    save('30_wrapper.blend')


# ----- blouse -------------------------------------------------------------

BLOUSE_HEM_Z = 0.905
SLEEVE_END = 0.155             # along the upper arm from the shoulder joint, in metres
NECK = dict(centre=(0, -0.015, 1.405), radii=(0.105, 0.095, 0.085))    # a round neck, as an ellipsoid


def geodesic_from_boundary(me):
    """Edge-walk distance of each vertex to the nearest real hem, ignoring pinhole slits."""
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    dist = np.full(len(bm.verts), 1e9)
    seen, start = set(), []
    for e in bm.edges:
        if not e.is_boundary or e.index in seen:
            continue
        seen.add(e.index)
        stack, loop = [e], []
        while stack:
            x = stack.pop()
            loop.append(x)
            for v in x.verts:
                for y in v.link_edges:
                    if y.is_boundary and y.index not in seen:
                        seen.add(y.index)
                        stack.append(y)
        if sum(x.calc_length() for x in loop) > 0.1:
            start += [v.index for x in loop for v in x.verts]
    dist[start] = 0
    q = deque(start)
    adj = [[(e.other_vert(v).index, e.calc_length()) for e in v.link_edges] for v in bm.verts]
    while q:
        i = q.popleft()
        for j, L in adj[i]:
            if dist[i] + L < dist[j] and dist[i] + L < 0.1:
                dist[j] = dist[i] + L
                q.append(j)
    bm.free()
    return dist


def arm_axes(rig):
    """Shoulder joint and upper-arm direction of each arm at frame 1."""
    P = rig.pose.bones
    axes = {}
    for side in 'LR':
        s = np.array(P[f'upperarm01.{side}'].head)
        e = np.array(P[f'lowerarm01.{side}'].head)
        axes[side] = (s, (e - s) / np.linalg.norm(e - s))
    return axes


def keep_biggest_island(bm):
    bm.verts.ensure_lookup_table()
    seen, best = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, comp = [v], []
        seen.add(v.index)
        while stack:
            u = stack.pop()
            comp.append(u)
            for e in u.link_edges:
                w = e.other_vert(u)
                if w.index not in seen:
                    seen.add(w.index)
                    stack.append(w)
        if len(comp) > len(best):
            best = comp
    ok = {v.index for v in best}
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in ok], context='VERTS')


def cut(bm, point, normal, where=None):
    """Bisect and throw away the side the normal points to, optionally only on faces a test passes."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    if where:
        faces = [f for f in bm.faces if where(f)]
        verts = {v for f in faces for v in f.verts}
        edges = {e for f in faces for e in f.edges}
        geom = list(verts) + list(edges) + faces
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=point, plane_no=normal, clear_outer=True)


def cut_inside(bm, f):
    """Split the mesh along f = 0 and delete where f < 0."""
    vals = {v: f(v.co) for v in bm.verts}
    new = set()
    for e in [e for e in bm.edges if vals[e.verts[0]] * vals[e.verts[1]] < 0]:
        a, b = e.verts
        fa, fb = vals[a], vals[b]
        _, nv = bmesh.utils.edge_split(e, a, fa / (fa - fb))
        vals[nv] = 0.0
        new.add(nv)
    for face in list(bm.faces):
        vs = [v for v in face.verts if v in new]
        if len(vs) == 2 and not bm.edges.get(vs):
            bmesh.utils.face_split(face, vs[0], vs[1])
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if vals[v] < 0], context='VERTS')


def make_blouse(body, rig, col, wrapper):
    me = body.data
    co = verts_world(body)
    armw = arm_weight(body)
    axes = arm_axes(rig)

    keep = (armw <= 0.35) & (co[:, 2] > BLOUSE_HEM_Z - 0.04)
    for side, sign in (('L', 1), ('R', -1)):
        s, d = axes[side]
        along = (co - s) @ d
        keep |= (armw > 0.35) & (co[:, 0] * sign > 0) & (along < SLEEVE_END + 0.05)
    keep &= co[:, 2] < 1.47

    polys = [p for p in me.polygons if all(keep[i] for i in p.vertices)]
    used = sorted({i for p in polys for i in p.vertices})
    remap = {old: new for new, old in enumerate(used)}
    ob = obj_from_arrays('Blouse', co[used], [tuple(remap[i] for i in p.vertices) for p in polys], col)

    bm = bmesh.new()
    bm.from_mesh(ob.data)
    # remember which faces are sleeve, so the sleeve cuts cannot bite into the torso
    sleeve_layer = bm.faces.layers.int.new('sleeve')
    bm.verts.ensure_lookup_table()
    for f in bm.faces:
        f[sleeve_layer] = int(np.mean([armw[used[v.index]] for v in f.verts]) > 0.35)
    for _ in range(2):
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True, smooth=1.0)
    # clean cuts for the neck, the hem and the sleeve ends
    (cx, cy, cz), (rx, ry, rz) = NECK['centre'], NECK['radii']
    cut_inside(bm, lambda p: ((p.x - cx) / rx) ** 2 + ((p.y - cy) / ry) ** 2 + ((p.z - cz) / rz) ** 2 - 1)
    cut(bm, (0, 0, BLOUSE_HEM_Z), (0, 0, -1))
    for side, sign in (('L', 1), ('R', -1)):
        s, d = axes[side]
        cut(bm, tuple(s + d * SLEEVE_END), tuple(d), where=lambda f: f[sleeve_layer] and f.calc_center_median().x * sign > 0)
    keep_biggest_island(bm)
    print('blouse open edges:', sum(e.is_boundary for e in bm.edges), flush=True)
    bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if v.is_boundary], dist=0.0016)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.polygons.foreach_set('use_smooth', [True] * len(ob.data.polygons))
    ob.data.update()
    n = len(ob.data.vertices)
    print('blouse', n, 'verts', flush=True)

    # loosen: fill the waist so the cloth drops from the bust, then stand it off the skin
    pos = np.array([v.co for v in ob.data.vertices])
    adj = edge_adjacency(ob.data)
    z = pos[:, 2]
    torso = np.ones(n, bool)
    for side, sign in (('L', 1), ('R', -1)):
        s, d = axes[side]
        along = (pos - s) @ d
        radial = np.linalg.norm((pos - s) - along[:, None] * d, axis=1)
        torso &= ~((pos[:, 0] * sign > 0) & (along > 0.02) & (radial < 0.075))
    below = np.clip((1.215 - z) / 0.08, 0, 1) * torso
    sm = pos.copy()
    for _ in range(110):
        nb = np.array([sm[a].mean(0) if a else sm[i] for i, a in enumerate(adj)])
        sm += (nb - sm) * 0.7 * below[:, None]
    sm[:, 2] = pos[:, 2]
    ob.data.vertices.foreach_set('co', sm.astype(np.float32).ravel())
    ob.data.update()
    normals = np.zeros(n * 3)
    ob.data.vertices.foreach_get('normal', normals)
    normals = normals.reshape(-1, 3)

    # thin over the chest and shoulders where it bears weight, generous below the bust and in the sleeve
    ridge = np.clip((z - 1.27) / 0.05, 0, 1)
    chest = np.clip((1.26 - z) / 0.10, 0, 1)
    off = 0.009 + 0.018 * chest + 0.016 * below
    off = np.where(torso, off, 0.024 * (1 - 0.65 * ridge))
    sm = sm + normals * off[:, None]

    # start outside the wrapper so the hem can hang over it
    from mathutils.bvhtree import BVHTree
    wv = [v.co for v in wrapper.data.vertices]
    tree = BVHTree.FromPolygons(wv, [tuple(p.vertices) for p in wrapper.data.polygons])
    axis = np.array([-0.02, 0.0])
    low = np.nonzero(z < 1.10)[0]
    for _ in range(3):
        for i in low:
            d = sm[i, :2] - axis
            r = np.linalg.norm(d)
            d3 = Vector((d[0] / r, d[1] / r, 0))
            hit = tree.ray_cast(Vector((*(axis + d / r * 0.6), sm[i, 2])), -d3)[0]
            if hit is not None:
                need = np.linalg.norm(np.array(hit[:2]) - axis) + 0.014
                if r < need:
                    sm[i, :2] = axis + d / r * need
        nb = np.array([sm[a].mean(0) if a else sm[i] for i, a in enumerate(adj)])
        sm[low] += (nb[low] - sm[low]) * 0.5
    ob.data.vertices.foreach_set('co', sm.astype(np.float32).ravel())
    ob.data.update()

    edge = geodesic_from_boundary(ob.data)
    pin = ob.vertex_groups.new(name='pin')
    pin.add(np.nonzero((z > 1.27) & (edge < 0.03) & (np.abs(pos[:, 0]) < 0.14))[0].tolist(), 1.0, 'REPLACE')
    return ob


def blouse_uv(ob, axes):
    """Front and back panels from one cloth, sleeves cut across it. Seams fall where a tailor's would."""
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
                uv[ids, 0] = angle * 0.06 / U_PERIOD + 0.13
                uv[ids, 1] = (SLEEVE_END - a) / V_PERIOD + 0.012
        if not sleeve:
            # each panel is flat cloth wrapped on an oval, so measure along the oval from the centre line
            front = c[1] < -0.012
            depth = np.abs(p[:, 1] + 0.012) + 0.03
            u = 0.17 * np.arctan2(p[:, 0], depth * 1.25)
            uv[ids, 0] = u / U_PERIOD + (0.0 if front else 0.5)
            uv[ids, 1] = (p[:, 2] - BLOUSE_HEM_Z) / V_PERIOD + 0.012
    layer.data.foreach_set('uv', uv.ravel())


def blouse_stage():
    body = bpy.data.objects['Body']
    rig = bpy.data.objects['Rig']
    wrapper = bpy.data.objects['Wrapper']
    set_frame(1)
    add_collider(wrapper, outer=0.004)
    if 'Collision' not in body.modifiers:
        add_collider(body)
    col = collection('Figure')
    ob = make_blouse(body, rig, col, wrapper)
    blouse_uv(ob, arm_axes(rig))
    mod = ob.modifiers.new('Cloth', 'CLOTH')
    cotton(mod, mass=0.34, tension=30, compression=30, shear=22, bending=9, pin='pin')
    adj = edge_adjacency(ob.data)
    co = relax(run_sim(ob), adj, 2)
    # the body's fine surface detail should not print through a cotton blouse
    front = (co[:, 1] < -0.04) & (co[:, 2] > 1.10) & (co[:, 2] < 1.30)
    co[front] = relax(co, adj, 24)[front]
    np.save(WORK / 'blouse_final.npy', co)
    set_frame(1)
    freeze(ob, co)
    edge = ob.data.attributes.new('edge_dist', 'FLOAT', 'POINT')
    edge.data.foreach_set('value', np.clip(geodesic_from_boundary(ob.data) / 0.1, 0, 1).astype(np.float32))
    body.modifiers.remove(body.modifiers['Collision'])
    wrapper.modifiers.remove(wrapper.modifiers['Collision'])
    set_frame(posing.POSE_END)
    save('40_cloth.blend')
