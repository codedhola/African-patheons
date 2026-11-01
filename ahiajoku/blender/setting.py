"""Her surroundings: a tilled yam field at dusk with a yam barn and the moon rising.

The festival falls on a full moon, and a full moon rises as the sun sets, straight
opposite it. So the camera looks east at the moon and the last warm light comes
from behind the camera. The barn follows FAO's account: posts 5 to 10 cm thick
about a metre apart, lighter cross members, tubers tied on one by one.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

import materials as mats
from common import TEX, obj_from_arrays
from yam import Noise, tuber, yam_object


def sweep(path, radius, sides=6, flat=1.0, up=(0, 0, 1)):
    """Tube along a polyline. radius may be a number or one value per point."""
    path = np.asarray(path, np.float64)
    n = len(path)
    r = np.full(n, radius) if np.isscalar(radius) else np.asarray(radius)
    tan = np.gradient(path, axis=0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    side = np.cross(tan, up)
    bad = np.linalg.norm(side, axis=1) < 1e-6
    side[bad] = np.cross(tan[bad], (1, 0, 0))
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    nrm = np.cross(side, tan)
    a = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    ca, sa = np.cos(a), np.sin(a)
    v = path[:, None] + (side[:, None] * ca[None, :, None] + nrm[:, None] * sa[None, :, None] * flat) * r[:, None, None]
    f = []
    for i in range(n - 1):
        for j in range(sides):
            k = (j + 1) % sides
            f.append((i * sides + j, i * sides + k, (i + 1) * sides + k, (i + 1) * sides + j))
    return v.reshape(-1, 3), f


def merged(parts):
    verts, faces, base = [], [], 0
    for v, f in parts:
        verts.append(v)
        faces += [tuple(i + base for i in q) for q in f]
        base += len(v)
    return np.concatenate(verts), faces


def basket_profile(h, rb=0.165, rt=0.285):
    return rb + (rt - rb) * np.sin(np.clip(h, 0, 1) * np.pi / 2) ** 0.75


def make_basket(col):
    """A wide cane basket: stakes rising from the base, a weft passing over and under them."""
    H = 0.25
    stakes, wefts = 46, 27
    rng = np.random.default_rng(14)
    parts, shade = [], []
    # stakes
    for k in range(stakes):
        a = k / stakes * 2 * np.pi + rng.normal(0, 0.006)
        s = np.linspace(0, 1, 30)
        base = np.stack([np.cos(a) * s[:10] / s[9] * 0.165, np.sin(a) * s[:10] / s[9] * 0.165, np.full(10, 0.012)], 1)
        hh = np.linspace(0.03, 1.0, 20)
        r = basket_profile(hh)
        wall = np.stack([np.cos(a) * r, np.sin(a) * r, 0.012 + hh * H], 1)
        v, f = sweep(np.vstack([base, wall]), 0.0048, 6, 0.42, up=(np.cos(a + 1.57), np.sin(a + 1.57), 0))
        parts.append((v, f))
        shade.append(rng.random())
    # weft rows, flat strips passing in and out of the stakes
    for row in range(wefts):
        hh = (row + 0.8) / wefts
        z = 0.012 + hh * H
        r0 = basket_profile(hh)
        n = stakes * 8
        a = np.linspace(0, 2 * np.pi, n, endpoint=False) + rng.uniform(0, 0.2)
        wob = 0.0032 * np.sin(a * stakes / 2 * 2 / 2 * 2 + (row % 2) * np.pi)
        wobz = 0.0012 * np.sin(a * 3 + row)
        p = np.stack([np.cos(a) * (r0 + wob), np.sin(a) * (r0 + wob), np.full(n, z) + wobz], 1)
        p = np.vstack([p, p[:1]])
        v, f = sweep(p, 0.0050, 6, 0.36, up=(0, 0, 1))
        parts.append((v, f))
        shade.append(rng.random())
    # spiral weft across the base
    a = np.linspace(0, 2 * np.pi * 18, 1500)
    r = np.linspace(0.008, 0.165, 1500)
    p = np.stack([np.cos(a) * r, np.sin(a) * r, 0.012 + 0.002 * np.sin(a * stakes / 2)], 1)
    parts.append(sweep(p, 0.0046, 6, 0.4))
    shade.append(0.5)
    # rim: a rod bound round with a strip
    a = np.linspace(0, 2 * np.pi, 220, endpoint=False)
    z = 0.012 + H + 0.008
    rim = np.stack([np.cos(a) * 0.288, np.sin(a) * 0.288, np.full(220, z)], 1)
    parts.append(sweep(np.vstack([rim, rim[:1]]), 0.0115, 10))
    shade.append(0.3)
    t = np.linspace(0, 2 * np.pi, 3600)
    turns = 150
    bind = np.stack([np.cos(t) * (0.288 + 0.0128 * np.cos(t * turns)), np.sin(t) * (0.288 + 0.0128 * np.cos(t * turns)),
                     z + 0.0128 * np.sin(t * turns)], 1)
    parts.append(sweep(bind, 0.0034, 5, 0.5))
    shade.append(0.7)

    verts, faces = merged(parts)
    ob = obj_from_arrays('Basket', verts, faces, col)
    attr = ob.data.attributes.new('strand', 'FLOAT', 'POINT')
    attr.data.foreach_set('value', np.concatenate([np.full(len(v), s, np.float32) for (v, _), s in zip(parts, shade)]))
    ob.data.materials.append(mats.cane())
    return ob


def fill_basket(basket, col, skin, flesh, root):
    """Drop the yams in with rigid-body physics so they lie the way a heap lies."""
    sc = bpy.context.scene

    def body(ob, kind):
        bpy.context.view_layer.objects.active = ob
        bpy.ops.rigidbody.object_add(type=kind)

    # thin mesh walls let tubers through, so the basket is stood in for by solid blocks: a raised
    # floor, unseen, so the heap stands proud of the rim, and three rings of slabs following the wall
    bpy.ops.rigidbody.world_add()
    world = sc.rigidbody_world
    world.collection = bpy.data.collections.new('Bodies')
    world.substeps_per_frame = 10
    world.solver_iterations = 30
    world.point_cache.frame_start = 1
    world.point_cache.frame_end = 200
    blocks = []

    def block(size, at, rot):
        sx, sy, sz = size
        v = [(x * sx / 2, y * sy / 2, z * sz / 2) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
        f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        ob = obj_from_arrays('Block', v, f, col, smooth=False)
        ob.location = at
        ob.rotation_euler = rot
        bpy.context.view_layer.update()
        body(ob, 'PASSIVE')
        ob.rigid_body.collision_shape = 'BOX'
        blocks.append(ob)

    block((0.8, 0.8, 0.2), (0, 0, 0.012), (0, 0, 0))
    segments = 28
    for z0, z1 in ((0.012, 0.10), (0.10, 0.19), (0.19, 0.30)):
        r0, r1 = basket_profile((z0 - 0.012) / 0.25), basket_profile(min((z1 - 0.012) / 0.25, 1.0))
        tilt = math.atan2(r1 - r0, z1 - z0)
        for k in range(segments):
            a = k / segments * 2 * math.pi
            wall = 0.10
            r = (r0 + r1) / 2 - 0.004 + wall / 2 * math.cos(tilt)
            block((wall, 2 * math.pi * (r0 + r1) / 2 / segments * 1.5, (z1 - z0) / math.cos(tilt) * 1.25),
                  (math.cos(a) * r, math.sin(a) * r, (z0 + z1) / 2 - wall / 2 * math.sin(tilt)), (0, tilt, a))

    rng = np.random.default_rng(5)
    made = []
    for i in range(14):
        seed = 11 + i
        L, R = rng.uniform(0.22, 0.30), rng.uniform(0.050, 0.060)
        ob, _, _ = yam_object(f'BasketYam.{seed}', seed, col, length=L, radius=R, nt=84, nth=36, roots=90,
                              material=skin, flesh=flesh, root_material=root)
        ob.location = (rng.uniform(-0.07, 0.07), rng.uniform(-0.07, 0.07), 0.24 + i * 0.105)
        ob.rotation_euler = (1.5 + rng.uniform(-0.25, 0.25), rng.uniform(-0.3, 0.3), rng.uniform(0, 6.28))
        body(ob, 'ACTIVE')
        ob.rigid_body.collision_shape = 'CONVEX_HULL'
        ob.rigid_body.mass = 3.0
        ob.rigid_body.friction = 0.95
        ob.rigid_body.linear_damping = 0.35
        ob.rigid_body.angular_damping = 0.4
        made.append(ob)
    for f in range(1, 201):
        sc.frame_set(f)
    bpy.context.view_layer.update()
    final = [ob.matrix_world.copy() for ob in made]
    bodies = world.collection
    for ob in made + blocks:
        bpy.context.view_layer.objects.active = ob
        bpy.ops.rigidbody.object_remove()
    for ob in blocks:
        bpy.data.objects.remove(ob)
    bpy.ops.rigidbody.world_remove()
    bpy.data.collections.remove(bodies)
    kept = []
    for ob, m in zip(made, final):
        co = np.zeros(len(ob.data.vertices) * 3)
        ob.data.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3) @ np.array(m)[:3, :3].T + np.array(m)[:3, 3]
        low = co[:, 2] < 0.262
        wall = basket_profile((co[low, 2] - 0.012) / 0.25)
        # a tuber that pushed out through the wall or rolled clear is simply left out
        if co[:, 2].min() < 0.03 or (low.any() and (np.hypot(co[low, 0], co[low, 1]) - wall).max() > 0.002):
            print('dropped a tuber that left the basket', ob.name, flush=True)
            for child in list(ob.children):
                bpy.data.objects.remove(child)
            bpy.data.objects.remove(ob)
            continue
        ob.parent = basket
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.matrix_world = m
        kept.append(ob)
    print('yams in the basket:', len(kept), flush=True)
    return kept


def paint_moon():
    """The near side of the moon, with the seas placed by hand from the real map."""
    n = 1024
    y, x = np.mgrid[0:n, 0:n] / (n - 1) * 2 - 1
    y = -y
    r2 = x * x + y * y
    noise = Noise(77)
    z = np.sqrt(np.clip(1 - r2, 0, 1))
    p = np.stack([x, y, z], -1)
    highlands = noise.fbm(p * 7, 6, 0.55)
    craters = np.abs(noise.fbm(p * 26, 4, 0.5))
    seas = [(-0.26, 0.42, 0.40), (0.20, 0.42, 0.25), (0.42, 0.14, 0.29), (0.73, 0.28, 0.15), (-0.60, 0.14, 0.42),
            (-0.72, 0.50, 0.24), (-0.34, -0.10, 0.35), (-0.56, -0.42, 0.18), (0.62, -0.08, 0.17), (0.50, -0.24, 0.15),
            (-0.14, 0.14, 0.20), (0.04, 0.60, 0.15), (0.16, 0.06, 0.16)]
    sea = np.zeros_like(x)
    edge = 0.16 * noise.fbm(p * 9, 4, 0.55)
    for cx, cy, s in seas:
        sea = np.maximum(sea, np.exp(-(((x - cx) ** 2 + (y - cy) ** 2) / (s * s)) ** 1.6))
    sea = np.clip((sea + edge - 0.32) / 0.22, 0, 1)
    tone = 0.76 + 0.09 * highlands - 0.09 * craters - 0.30 * sea * (0.85 + 0.3 * noise.fbm(p * 14, 3, 0.5))
    # Tycho and its rays, low on the disc
    tx, ty = -0.10, -0.70
    d = np.hypot(x - tx, y - ty)
    ang = np.arctan2(y - ty, x - tx)
    rays = np.maximum(np.sin(ang * 9 + 1.2) * np.sin(ang * 23 + 0.4), 0) ** 3
    tone = tone + 0.22 * rays * np.exp(-d / 0.55) * (1 - 0.6 * sea) + 0.30 * np.exp(-(d / 0.035) ** 2)
    limb = np.clip(z, 0, 1) ** 0.22
    tone = np.clip(tone * limb, 0, 1)
    tint = np.array([1.0, 0.66, 0.36])
    rgb = tone[..., None] * tint
    alpha = (r2 <= 1).astype(np.float32)
    rgba = np.dstack([np.clip(rgb, 0, 1) ** (1 / 2.2), alpha])
    from akwete import save
    save(TEX / 'moon.png', rgba)


def make_moon(col, at, size, tilt_deg=68):
    """A disc facing the camera, its north leaning to the left as it does at this latitude."""
    paint_moon()
    n = 96
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    v = np.vstack([[[0, 0, 0]], np.stack([np.cos(a), np.zeros(n), np.sin(a)], 1)]) * size
    f = [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]
    uv = v[:, [0, 2]] / size / 2 + 0.5
    ob = obj_from_arrays('Moon', v, f, col, uv=uv)
    ob.data.materials.append(mats.moon())
    ob.location = at
    ob.rotation_euler = (0, math.radians(tilt_deg), 0)
    ob.visible_shadow = False
    return ob


def height_field(x, y):
    """Bare swept earth round her, mounds in rows beyond."""
    n = Noise(3)
    p = np.stack([x, y, np.zeros_like(x)], -1)
    h = 0.018 * n.fbm(p * 2.4, 4) + 0.0065 * n.fbm(p * 11, 3)
    d = np.hypot(x - 0.2, y)
    keep = np.clip((d - 1.1) / 1.6, 0, 1)
    h = h * keep
    gx, gy = 1.25, 1.30
    cx = np.round(x / gx) * gx + 0.25 * np.sin(np.round(y / gy) * 2.1)
    cy = np.round(y / gy) * gy
    r = np.hypot(x - cx, y - cy)
    mound = np.clip(1 - r / 0.62, 0, 1) ** 1.25 * 0.52
    mound *= 1 + 0.25 * n(np.stack([cx * 3, cy * 3, np.zeros_like(x)], -1))
    mask = np.clip((y - 2.3) / 1.0, 0, 1)
    return h + mound * mask


def make_ground(col, size=300, grid=460):
    xs = np.sign(np.linspace(-1, 1, grid)) * np.abs(np.linspace(-1, 1, grid)) ** 2.6 * size / 2
    ys = xs + 7
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    Z = height_field(X, Y)
    verts = np.stack([X, Y, Z], -1).reshape(-1, 3)
    idx = lambda i, j: i * grid + j
    # the middle is cut out: the near patch sits there
    def inside(i, j):
        return NEAR[0] + 0.15 < X[i, j] < NEAR[1] - 0.15 and NEAR[2] + 0.15 < Y[i, j] < NEAR[3] - 0.15
    faces = [(idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)) for i in range(grid - 1) for j in range(grid - 1)
             if not (inside(i, j) and inside(i + 1, j + 1))]
    ob = obj_from_arrays('Ground', verts, faces, col)
    ob.data.materials.append(mats.soil(False))
    return ob


NEAR = (-3.2, 3.8, -3.6, 2.2)    # x0, x1, y0, y1 of the finely modelled earth round her
BASKET_AT = (0.66, -0.24)


def rock_mesh(seed):
    n = Noise(seed)
    rows, cols = 9, 12
    verts = []
    for i in range(rows):
        a = math.pi * i / (rows - 1)
        for j in range(cols):
            b = 2 * math.pi * j / cols
            d = np.array([math.sin(a) * math.cos(b), math.sin(a) * math.sin(b), math.cos(a)])
            verts.append(d * (1 + 0.36 * float(n.fbm(d * 1.3 + seed, 3))) * np.array([1, 0.8, 0.62]))
    faces = [(i * cols + j, i * cols + (j + 1) % cols, (i + 1) * cols + (j + 1) % cols, (i + 1) * cols + j) for i in range(rows - 1) for j in range(cols)]
    return np.array(verts, np.float32), faces


def make_near_ground(col):
    """Worn earth under her feet, fine enough for the close-ups: clods, grit, stones, dead leaves."""
    x0, x1, y0, y1 = NEAR
    nx, ny = int((x1 - x0) / 0.016), int((y1 - y0) / 0.016)
    xs, ys = np.linspace(x0, x1, nx), np.linspace(y0, y1, ny)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    n1, n2 = Noise(44), Noise(45)
    p = np.stack([X, Y, np.zeros_like(X)], -1)
    clod = np.abs(n1.fbm(p * 13, 4, 0.55)) * 0.018 + n2.fbm(p * 42, 4, 0.55) * 0.0045
    edge = np.minimum.reduce([X - x0, x1 - X, Y - y0, y1 - Y])
    fade = np.clip(edge / 0.35, 0, 1)
    d = np.hypot(X - 0.25, Y + 0.05)
    worn = 0.35 + 0.65 * np.clip((d - 0.9) / 1.2, 0, 1)       # trodden flatter where she stands
    Z = height_field(X, Y) + clod * fade * worn
    verts = np.stack([X, Y, Z], -1).reshape(-1, 3)
    idx = lambda i, j: i * ny + j
    faces = [(idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)) for i in range(nx - 1) for j in range(ny - 1)]
    ob = obj_from_arrays('NearGround', verts, faces, col)
    ob.data.materials.append(mats.soil(True))

    def ground_z(x, y):
        return float(height_field(np.array([x]), np.array([y]))[0])

    rng = np.random.default_rng(77)
    stone_m = mats.stone()
    rocks = []
    for s in range(7):
        v, f = rock_mesh(300 + s)
        r = obj_from_arrays(f'Rock.{s}', v, f, col)
        r.data.materials.append(stone_m)
        sub = r.modifiers.new('Smooth', 'SUBSURF')
        sub.levels = sub.render_levels = 1
        r.hide_render = r.hide_viewport = True
        rocks.append(r)
    for _ in range(760):
        x, y = rng.uniform(x0 + 0.4, x1 - 0.4), rng.uniform(y0 + 0.4, y1 - 0.4)
        if math.hypot(x, y) < 0.32 or math.hypot(x - BASKET_AT[0], y - BASKET_AT[1]) < 0.34:
            continue
        s = float(np.clip(rng.lognormal(math.log(0.0055), 0.62), 0.002, 0.03))
        src = rocks[int(rng.integers(0, len(rocks)))]
        inst = bpy.data.objects.new('Rock', src.data)
        col.objects.link(inst)
        inst.modifiers.new('Smooth', 'SUBSURF').render_levels = 1
        inst.location = (x, y, ground_z(x, y) + s * 0.25)
        inst.rotation_euler = tuple(rng.uniform(0, 6.28, 3))
        inst.scale = (s, s, s)

    lv, lf = leaf_mesh()
    litter = obj_from_arrays('Litter', lv, lf, col)
    litter.data.materials.append(mats.dry_leaf())
    litter.hide_render = litter.hide_viewport = True
    for _ in range(90):
        x, y = rng.uniform(x0 + 0.5, x1 - 0.5), rng.uniform(y0 + 0.5, y1 - 0.5)
        if math.hypot(x, y) < 0.32 or math.hypot(x - BASKET_AT[0], y - BASKET_AT[1]) < 0.36:
            continue
        s = rng.uniform(0.04, 0.075)
        inst = bpy.data.objects.new('Leaf', litter.data)
        col.objects.link(inst)
        inst.location = (x, y, ground_z(x, y) + 0.008)
        inst.rotation_euler = (rng.normal(0, 0.28), rng.normal(0, 0.28), rng.uniform(0, 6.28))
        inst.scale = (s, s, s)
    return ob


def leaf_mesh():
    """A heart-shaped yam leaf, slightly folded along its midrib."""
    n = 12
    verts, faces = [], []
    for i in range(n):
        t = i / (n - 1)
        w = math.sin(math.pi * min(t * 1.06, 1)) ** 0.7 * 0.5 * (1 + 0.5 * (1 - t) ** 2)
        z = -0.25 * t * t
        for s in (-1, 0, 1):
            verts.append((s * w, t * 1.0 - 0.08 * (abs(s)), z + 0.12 * abs(s) * w))
    for i in range(n - 1):
        for j in range(2):
            a = i * 3 + j
            faces.append((a, a + 1, a + 4, a + 3))
    return np.array(verts, np.float32), faces


def make_vine(col, leaf_material, seed=1, height=2.0):
    """One staked yam plant: a pole, a twining stem, heart leaves. Duplicated across the field."""
    rng = np.random.default_rng(seed)
    t = np.linspace(0, 1, 120)
    turns = 7
    path = np.stack([np.cos(t * turns * 6.28) * 0.03, np.sin(t * turns * 6.28) * 0.03, t * height], 1)
    pole, pf = sweep(np.stack([rng.normal(0, 0.012, 8).cumsum() * 0.3, rng.normal(0, 0.012, 8).cumsum() * 0.3, np.linspace(0, height * 1.03, 8)], 1), 0.016, 6)
    stem, sf = sweep(path, 0.0022, 5)
    lv, lf = leaf_mesh()
    parts = []
    for _ in range(150):
        i = int(rng.integers(12, 120))
        p = path[i]
        a = rng.uniform(0, 6.28)
        s = rng.uniform(0.06, 0.11) * (1.2 - t[i] * 0.5)
        d = np.array([math.cos(a), math.sin(a), 0])
        o = p + d * rng.uniform(0.02, 0.10)
        droop = rng.uniform(0.3, 1.1)
        y = d * math.cos(droop) + np.array([0, 0, -math.sin(droop)])
        x = np.cross(y, (0, 0, 1))
        x /= np.linalg.norm(x) + 1e-9
        z = np.cross(x, y)
        parts.append((lv[:, 0, None] * x * s + lv[:, 1, None] * y * s + lv[:, 2, None] * z * s + o, lf))
    v, f = merged(parts)
    ob = obj_from_arrays(f'VineLeaves.{seed}', v, f, col)
    ob.data.materials.append(leaf_material)
    stake_v, stake_f = merged([(pole, pf), (stem, sf)])
    stake = obj_from_arrays(f'VineStake.{seed}', stake_v, stake_f, col)
    stake.data.materials.append(mats.bark_pole())
    return ob, stake


def make_field(col, ground_h):
    leaf_mat = mats.leaf()
    vines = [make_vine(col, leaf_mat, s) for s in (1, 2, 3)]
    rng = np.random.default_rng(9)
    for ob, stake in vines:
        ob.hide_render = stake.hide_render = True
        ob.hide_viewport = stake.hide_viewport = True
    gx, gy = 1.25, 1.30
    for iy in range(6, 26):
        for ix in range(-26, 27):
            y = iy * gy
            x = ix * gx + 0.25 * math.sin(iy * 2.1)
            if rng.random() > 0.42:
                continue
            base, stake = vines[int(rng.integers(0, 3))]
            z = float(ground_h(np.array([x]), np.array([y]))[0]) - 0.06
            for src in (base, stake):
                inst = bpy.data.objects.new(src.name + '.i', src.data)
                col.objects.link(inst)
                inst.location = (x + rng.normal(0, 0.05), y + rng.normal(0, 0.05), z)
                inst.rotation_euler = (0, 0, rng.uniform(0, 6.28))
                sc = rng.uniform(0.85, 1.15)
                inst.scale = (sc, sc, rng.uniform(0.92, 1.1))


def make_barn(col, skin, flesh, at=(-4.5, 4.9, 0.0), yaw=11):
    """One long frame of the yam barn with its tubers tied on, standing to her right and behind her."""
    rng = np.random.default_rng(31)
    root = bpy.data.objects.new('Barn', None)
    col.objects.link(root)
    root.location = at
    root.rotation_euler = (0, 0, math.radians(yaw))
    poles, cross = [], []
    length, height = 5.0, 2.5
    posts = 6
    for k in range(posts):
        x = -length / 2 + k * length / (posts - 1)
        path = np.stack([x + rng.normal(0, 0.01, 7).cumsum() * 0.6, rng.normal(0, 0.012, 7).cumsum(), np.linspace(-0.1, height + rng.uniform(-0.1, 0.25), 7)], 1)
        poles.append(sweep(path, np.linspace(0.05, 0.034, 7), 8))
    rails = [0.45, 0.85, 1.25, 1.65, 2.05, 2.42]
    for z in rails:
        for side in (-0.045, 0.045):
            n = 12
            path = np.stack([np.linspace(-length / 2 - 0.1, length / 2 + 0.1, n), np.full(n, side) + rng.normal(0, 0.006, n), z + rng.normal(0, 0.008, n)], 1)
            cross.append(sweep(path, 0.015, 6))
    sticks = int(length / 0.34)
    for k in range(sticks):
        x = -length / 2 + (k + 0.5) * length / sticks
        path = np.stack([np.full(6, x) + rng.normal(0, 0.006, 6), np.full(6, -0.065), np.linspace(0.05, 2.46, 6)], 1)
        cross.append(sweep(path, 0.0095, 5))
    v, f = merged(poles + cross)
    ob = obj_from_arrays('BarnFrame', v, f, col)
    ob.data.materials.append(mats.bark_pole())
    ob.parent = root

    # tubers tied on one by one, heads up, from a handful of shapes
    variants = []
    for s in range(8):
        vv, ff, uv, _, _, cut = tuber(200 + s, rng.uniform(0.25, 0.36), rng.uniform(0.050, 0.068), 0.09, 120, 44)
        m = obj_from_arrays(f'TiedYam.{s}', vv, ff, col, uv=uv)
        m.data.materials.append(skin)
        m.data.materials.append(flesh)
        index = np.zeros(len(m.data.polygons), np.int32)
        index[cut] = 1
        m.data.polygons.foreach_set('material_index', index)
        m.hide_render = m.hide_viewport = True
        variants.append(m)
    tie = obj_from_arrays('Tie', *sweep(np.stack([0.03 * np.cos(np.linspace(0, 6.28, 16)), 0.05 + 0.05 * np.sin(np.linspace(0, 6.28, 16)), np.zeros(16)], 1), 0.0035, 5), col)
    tie.data.materials.append(mats.raffia())
    tie.hide_render = tie.hide_viewport = True
    count = 0
    for z in rails[:-1]:
        for k in range(sticks):
            for side in (-1, 1):
                if rng.random() < 0.13:
                    continue
                x = -length / 2 + (k + 0.5) * length / sticks + rng.normal(0, 0.02)
                src = variants[int(rng.integers(0, len(variants)))]
                inst = bpy.data.objects.new('TiedYam', src.data)
                col.objects.link(inst)
                inst.parent = root
                inst.location = (x, side * 0.115, z + 0.10 + rng.normal(0, 0.012))
                inst.rotation_euler = (math.radians(180 + rng.normal(0, 7) + side * 8), math.radians(rng.normal(0, 7)), rng.uniform(0, 6.28))
                count += 1
                band = bpy.data.objects.new('Tie', tie.data)
                col.objects.link(band)
                band.parent = root
                band.location = (x, side * 0.055, z + 0.11)
    print('tubers tied on the barn:', count, flush=True)
    # shoots from the live posts
    leaf_mat = bpy.data.materials.get('Leaf') or mats.leaf()
    lv, lf = leaf_mesh()
    parts = []
    for k in range(posts):
        x = -length / 2 + k * length / (posts - 1)
        for _ in range(240):
            a, up = rng.uniform(0, 6.28), rng.uniform(0.15, 1.0)
            o = np.array([x + math.cos(a) * rng.uniform(0.05, 0.55), math.sin(a) * rng.uniform(0.05, 0.35), height + 0.2 + rng.uniform(-0.45, 0.60)])
            s = rng.uniform(0.07, 0.14)
            y = np.array([math.cos(a) * up, math.sin(a) * up, -rng.uniform(0.3, 0.9)])
            y /= np.linalg.norm(y)
            xx = np.cross(y, (0, 0, 1))
            xx /= np.linalg.norm(xx)
            zz = np.cross(xx, y)
            parts.append((lv[:, 0, None] * xx * s + lv[:, 1, None] * y * s + lv[:, 2, None] * zz * s + o, lf))
    v, f = merged(parts)
    tops = obj_from_arrays('BarnShoots', v, f, col)
    tops.data.materials.append(leaf_mat)
    tops.parent = root
    return root


def palm_tree(col, leaf_material, seed, height=11.0):
    """A distant oil palm, seen only as a shape against the sky."""
    rng = np.random.default_rng(seed)
    bend = rng.uniform(-0.5, 0.5)
    t = np.linspace(0, 1, 14)
    trunk = np.stack([bend * t * t * 1.6, 0 * t, t * height], 1)
    parts = [sweep(trunk, np.linspace(0.26, 0.17, 14), 8)]
    top = trunk[-1]
    for k in range(26):
        a = k / 26 * 6.28 + rng.uniform(-0.1, 0.1)
        rise = rng.uniform(-0.1, 0.9)
        L = rng.uniform(3.0, 4.2)
        s = np.linspace(0, 1, 14)
        d = np.array([math.cos(a), math.sin(a), 0])
        rib = top + d[None] * (s[:, None] * L * math.cos(rise * 0.7)) + np.array([0, 0, 1])[None] * (s[:, None] * L * math.sin(rise * 0.7) - s[:, None] ** 2 * L * 0.62)
        parts.append(sweep(rib, np.linspace(0.05, 0.012, 14), 4))
        for i in range(3, 14):
            for side in (-1, 1):
                w = np.cross(d, (0, 0, 1)) * side
                tip = rib[i] + w * (0.75 * math.sin(s[i] * 3.14) ** 0.6 + 0.12) + np.array([0, 0, -0.35])
                parts.append(sweep(np.stack([rib[i], (rib[i] + tip) / 2, tip]), 0.034, 3, 0.3))
    v, f = merged(parts)
    ob = obj_from_arrays(f'Palm.{seed}', v, f, col)
    ob.data.materials.append(leaf_material)
    return ob


def make_palms(col, clear):
    """Oil palms on the far side of the field. clear(x, y) keeps them off the moon and her head."""
    m = mats.leaf('PalmDark', (0.012, 0.018, 0.014))
    rng = np.random.default_rng(19)
    src = [palm_tree(col, m, s, rng.uniform(10, 14)) for s in (1, 2, 3)]
    for ob in src:
        ob.hide_render = ob.hide_viewport = True
    placed = 0
    while placed < 30:
        x, y = rng.uniform(-90, 90), rng.uniform(62, 110)
        if not clear(x, y):
            continue
        ob = bpy.data.objects.new('Palm', src[placed % 3].data)
        col.objects.link(ob)
        ob.location = (x, y, -0.4)
        ob.rotation_euler = (0, 0, rng.uniform(0, 6.28))
        s = rng.uniform(0.85, 1.25)
        ob.scale = (s, s, s)
        placed += 1


def make_treeline(col):
    """Two low bands of bush along the horizon, the farther one paler with haze."""
    n = Noise(61)
    for name, y, base, rise, colour, seed in (('BushFar', 165, 5.0, 2.2, (0.052, 0.050, 0.078), 2.0), ('BushNear', 120, 3.6, 1.5, (0.020, 0.021, 0.033), 7.0)):
        x = np.linspace(-260, 260, 1400)
        q = np.stack([x * 0.11, np.full_like(x, seed), np.zeros_like(x)], -1)
        top = base + rise * n.fbm(q, 6, 0.62)
        verts = np.concatenate([np.stack([x, np.full_like(x, y), top], 1), np.stack([x, np.full_like(x, y), np.full_like(x, -2.0)], 1)])
        m = len(x)
        faces = [(i, i + 1, m + i + 1, m + i) for i in range(m - 1)]
        ob = obj_from_arrays(name, verts, faces, col, smooth=False)
        g = mats.Graph(name)
        glow = g.node('Emission', Color=(*colour, 1), Strength=1.0)
        ob.data.materials.append(g.finish(glow.outputs[0]))


def make_sky(sun_dir=(-0.70, -0.70, 0.12), moon_dir=None):
    """Dusk seen looking away from the sun: Earth's shadow low down, the pink band above it."""
    w = bpy.data.worlds.get('Dusk') or bpy.data.worlds.new('Dusk')
    w.use_nodes = True
    t = w.node_tree
    t.nodes.clear()
    out = t.nodes.new('ShaderNodeOutputWorld')
    bg = t.nodes.new('ShaderNodeBackground')
    coord = t.nodes.new('ShaderNodeTexCoord')
    sep = t.nodes.new('ShaderNodeSeparateXYZ')
    vec_norm = t.nodes.new('ShaderNodeVectorMath')
    vec_norm.operation = 'NORMALIZE'
    t.links.new(coord.outputs['Generated'], vec_norm.inputs[0])
    t.links.new(vec_norm.outputs[0], sep.inputs[0])
    ramp = t.nodes.new('ShaderNodeValToRGB')
    t.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    stops = [(0.00, (0.034, 0.040, 0.066)), (0.020, (0.046, 0.051, 0.082)), (0.048, (0.082, 0.070, 0.098)), (0.085, (0.26, 0.145, 0.150)),
             (0.135, (0.31, 0.190, 0.185)), (0.21, (0.170, 0.165, 0.225)), (0.36, (0.060, 0.082, 0.160)), (1.0, (0.012, 0.022, 0.055))]
    cr = ramp.color_ramp
    while len(cr.elements) < len(stops):
        cr.elements.new(0)
    for el, (p, c) in zip(cr.elements, stops):
        el.position = p
        el.color = (*c, 1)
    sun = t.nodes.new('ShaderNodeVectorMath')
    sun.operation = 'DOT_PRODUCT'
    sun.inputs[1].default_value = Vector(sun_dir).normalized()
    t.links.new(vec_norm.outputs[0], sun.inputs[0])
    glowramp = t.nodes.new('ShaderNodeValToRGB')
    t.links.new(sun.outputs['Value'], glowramp.inputs['Fac'])
    gr = glowramp.color_ramp
    gr.elements[0].position = 0.55
    gr.elements[0].color = (0, 0, 0, 1)
    gr.elements[1].position = 1.0
    gr.elements[1].color = (2.6, 1.05, 0.34, 1)
    add = t.nodes.new('ShaderNodeMix')
    add.data_type = 'RGBA'
    add.blend_type = 'ADD'
    add.inputs[0].default_value = 1.0
    t.links.new(ramp.outputs['Color'], add.inputs[6])
    t.links.new(glowramp.outputs['Color'], add.inputs[7])
    last = add
    if moon_dir is not None:
        # the haze round a low moon
        dot = t.nodes.new('ShaderNodeVectorMath')
        dot.operation = 'DOT_PRODUCT'
        dot.inputs[1].default_value = Vector(moon_dir).normalized()
        t.links.new(vec_norm.outputs[0], dot.inputs[0])
        halo = t.nodes.new('ShaderNodeValToRGB')
        t.links.new(dot.outputs['Value'], halo.inputs['Fac'])
        hr = halo.color_ramp
        hr.interpolation = 'EASE'
        hr.elements[0].position = 0.9955
        hr.elements[0].color = (0, 0, 0, 1)
        hr.elements[1].position = 0.9995
        hr.elements[1].color = (0.10, 0.058, 0.032, 1)
        add2 = t.nodes.new('ShaderNodeMix')
        add2.data_type = 'RGBA'
        add2.blend_type = 'ADD'
        add2.inputs[0].default_value = 1.0
        t.links.new(add.outputs[2], add2.inputs[6])
        t.links.new(halo.outputs['Color'], add2.inputs[7])
        last = add2
    t.links.new(last.outputs[2], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 1.0
    t.links.new(bg.outputs[0], out.inputs['Surface'])
    bpy.context.scene.world = w
    return w
