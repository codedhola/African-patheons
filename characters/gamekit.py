"""Shared steps for turning one of the 3d/ portrait figures into a game character.

A portrait figure is one skinned body in a pose, with everything else frozen round it.
A game character is the other way about: every part skinned, standing in the rest pose,
light enough to draw sixty times a second, and textured with images rather than node
graphs. The steps any figure needs are here; what is one figure's alone is in its own
build script, such as ogun/build_ogun_game.py.

Texture arrays are kept the way Blender keeps them: rows bottom-up, so row 0 is v = 0.
"""
import os
import struct
import sys
import zlib
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector, interpolate
from mathutils.bvhtree import BVHTree

REPO = Path(__file__).resolve().parent.parent
TOOLKIT = REPO / '3d' / 'toolkit'


# ----- scene and mesh helpers ------------------------------------------------

def collection(name):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def link(ob, col):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    col.objects.link(ob)


def append(blend, objects=(), materials=(), images=()):
    """Bring named datablocks in from another .blend. Returns them by the names asked for."""
    with bpy.data.libraries.load(str(blend), link=False) as (src, dst):
        want_o = [n for n in objects if n in src.objects]
        want_m = [n for n in materials if n in src.materials]
        want_i = [n for n in images if n in src.images]
        dst.objects, dst.materials, dst.images = list(want_o), list(want_m), list(want_i)
    out = dict(zip(want_o, dst.objects))
    out.update(zip(want_m, dst.materials))
    out.update(zip(want_i, dst.images))
    return out


def coords(me):
    a = np.empty(len(me.vertices) * 3, np.float64)
    me.vertices.foreach_get('co', a)
    return a.reshape(-1, 3)


def set_coords(me, co):
    me.vertices.foreach_set('co', np.asarray(co, np.float64).ravel())
    me.update()


def world_coords(ob):
    m = np.array(ob.matrix_world)
    return coords(ob.data) @ m[:3, :3].T + m[:3, 3]


def transform(points, m):
    m = np.asarray(m)
    return np.asarray(points) @ m[:3, :3].T + m[:3, 3]


def polygons(me):
    return [tuple(p.vertices) for p in me.polygons]


def new_object(name, verts, faces, col, uv=None, smooth=True):
    """Mesh object from arrays. uv is one pair per vertex, or one per face corner in face order."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in verts], [], [tuple(map(int, f)) for f in faces])
    me.update()
    me.polygons.foreach_set('use_smooth', [smooth] * len(me.polygons))
    if uv is not None:
        layer = me.uv_layers.new(name='UVMap')
        uv = np.asarray(uv, np.float32)
        if len(uv) == len(me.vertices) and len(uv) != len(me.loops):
            loops = np.empty(len(me.loops), np.int32)
            me.loops.foreach_get('vertex_index', loops)
            uv = uv[loops]
        layer.data.foreach_set('uv', uv.ravel())
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    return ob


def loop_uv(me, layer=None):
    layer = me.uv_layers[layer] if layer else me.uv_layers.active
    a = np.empty(len(me.loops) * 2, np.float32)
    layer.data.foreach_get('uv', a)
    return a.reshape(-1, 2)


def set_loop_uv(me, uv, layer=None):
    layer = me.uv_layers[layer] if layer else me.uv_layers.active
    layer.data.foreach_set('uv', np.asarray(uv, np.float32).ravel())


def point_attr(me, name):
    a = np.empty(len(me.vertices), np.float32)
    me.attributes[name].data.foreach_get('value', a)
    return a


def set_point_attr(me, name, values):
    attr = me.attributes.get(name) or me.attributes.new(name, 'FLOAT', 'POINT')
    attr.data.foreach_set('value', np.asarray(values, np.float32))
    return attr


def islands(me):
    """Connected pieces of a mesh, as arrays of vertex indices, in order of their first vertex."""
    n = len(me.vertices)
    parent = np.arange(n)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    ed = np.empty(len(me.edges) * 2, np.int32)
    me.edges.foreach_get('vertices', ed)
    for a, b in ed.reshape(-1, 2):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    roots = np.array([find(i) for i in range(n)])
    order = np.unique(roots)
    return [np.nonzero(roots == r)[0] for r in order]


def drop_broken_vertices(ob):
    """Take out vertices with no position (NaN), and the faces that hang on them. Returns how many."""
    bad = np.isnan(coords(ob.data)).any(1)
    if not bad.any():
        return 0
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in np.nonzero(bad)[0]], context='VERTS')
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return int(bad.sum())


def delete_faces(ob, face_mask):
    """Take faces out of a mesh, and any vertex left with no face."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    gone = [f for f in bm.faces if face_mask[f.index]]
    bmesh.ops.delete(bm, geom=gone, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return len(gone)


def tube(path, radius, sides=6, closed=False, up=(0, 0, 1), turn=0.0):
    """A tube along a path, open at its ends unless the path is closed.

    Returns vertices, quads, and a texture coordinate for each face corner in face order:
    u runs 0 to 1 along the path and v 0 to 1 round it. up may be one vector or one per point.
    """
    path = np.asarray(path, np.float64)
    n = len(path)
    r = np.full(n, radius) if np.isscalar(radius) else np.asarray(radius, np.float64)
    tan = (np.roll(path, -1, 0) - np.roll(path, 1, 0)) if closed else np.gradient(path, axis=0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    up = np.broadcast_to(np.asarray(up, np.float64), path.shape)
    side = np.cross(tan, up)
    bad = np.linalg.norm(side, axis=1) < 1e-6
    side[bad] = np.cross(tan[bad], (1.0, 0, 0))
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    out = np.cross(side, tan)
    a = turn + np.linspace(0, 2 * np.pi, sides, endpoint=False)
    verts = (path[:, None] + (side[:, None] * np.cos(a)[None, :, None] + out[:, None] * np.sin(a)[None, :, None]) * r[:, None, None]).reshape(-1, 3)
    ends = np.vstack([path, path[:1]]) if closed else path
    arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(ends, axis=0), axis=1))])
    arc /= arc[-1]
    faces, uvs = [], []
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        for k in range(sides):
            m = (k + 1) % sides
            faces.append((i * sides + k, j * sides + k, j * sides + m, i * sides + m))
            uvs += [(arc[i], k / sides), (arc[i + 1], k / sides), (arc[i + 1], (k + 1) / sides), (arc[i], (k + 1) / sides)]
    return verts, faces, np.array(uvs)


def into(uv, rect, inset=0.004):
    """Fit texture coordinates that fill 0 to 1 into a rectangle (x0, y0, x1, y1) of an atlas."""
    x0, y0, x1, y1 = rect
    uv = np.asarray(uv, np.float64)
    return np.stack([x0 + inset + uv[:, 0] * (x1 - x0 - 2 * inset), y0 + inset + uv[:, 1] * (y1 - y0 - 2 * inset)], 1)


def face_outward(ob):
    """Make every closed piece of a mesh face outward."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def sharpen(ob, degrees=35):
    """Smooth shading, with a crease kept wherever two faces meet at more than the given angle."""
    limit_ = np.radians(degrees)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for e in bm.edges:
        e.smooth = not (len(e.link_faces) == 2 and e.calc_face_angle() > limit_)
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def decimated(ob, ratio, name, col):
    """A lighter copy of a mesh object, by edge collapse. Texture coordinates come with it."""
    mod = ob.modifiers.new('Decimate', 'DECIMATE')
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.remove(mod)
    me.name = name
    new = bpy.data.objects.new(name, me)
    col.objects.link(new)
    new.matrix_world = ob.matrix_world.copy()
    return new


def join(objs, into_ob):
    """Join mesh objects into one. Vertex groups, texture coordinates and materials merge by name."""
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = into_ob
    bpy.ops.object.join()
    return into_ob


def strip_attributes(me, keep=('position', 'UVMap', 'material_index', 'sharp_edge', 'sharp_face')):
    """Drop the build's own vertex data, which a game mesh has no use for."""
    for name in [a.name for a in me.color_attributes]:
        me.color_attributes.remove(me.color_attributes[name])
    for name in [a.name for a in me.attributes if not a.is_internal and not a.is_required and a.name not in keep
                 and a.data_type in ('FLOAT', 'INT', 'BOOLEAN', 'FLOAT_COLOR', 'BYTE_COLOR') and a.domain in ('POINT', 'FACE', 'CORNER', 'EDGE')]:
        attr = me.attributes.get(name)
        if attr is not None:
            me.attributes.remove(attr)


def mesh_report(ob, bones=None):
    """Counts a game mesh should pass: what is in it, and what is wrong with it."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    r = dict(vertices=len(bm.verts), triangles=triangles(me),
             ngons=sum(1 for f in bm.faces if len(f.verts) > 4),
             loose_vertices=sum(1 for v in bm.verts if not v.link_faces),
             edges_with_3_faces=sum(1 for e in bm.edges if len(e.link_faces) > 2),
             flipped_neighbours=sum(1 for e in bm.edges if len(e.link_faces) == 2 and not e.is_contiguous),
             zero_area_faces=sum(1 for f in bm.faces if f.calc_area() < 1e-12),
             broken_vertices=int(np.isnan(coords(me)).any(1).sum()))
    bm.free()
    r['materials'] = [s.material.name if s.material else None for s in ob.material_slots]
    r['uv_layers'] = [u.name for u in me.uv_layers]
    r['faces_without_uv_area'] = 0
    if me.uv_layers:
        me.calc_loop_triangles()
        tl = np.empty(len(me.loop_triangles) * 3, np.int32)
        me.loop_triangles.foreach_get('loops', tl)
        q = loop_uv(me)[tl.reshape(-1, 3)]
        e1, e2 = q[:, 1] - q[:, 0], q[:, 2] - q[:, 0]
        r['faces_without_uv_area'] = int((np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]) < 1e-12).sum())
    if bones is not None:
        W = weights(ob, bones)
        count = (W > 1e-5).sum(1)
        r.update(unweighted_vertices=int((count == 0).sum()), most_weights_on_a_vertex=int(count.max()),
                 weights_not_summing_to_one=int((np.abs(W.sum(1) - 1) > 1e-3).sum()),
                 bones_with_weight=int((W.sum(0) > 0).sum()))
    return r


def triangles(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


# ----- skin weights ----------------------------------------------------------

def weights(ob, names):
    """Dense table of vertex weights, one column for each named group."""
    col = {vg.index: names.index(vg.name) for vg in ob.vertex_groups if vg.name in names}
    W = np.zeros((len(ob.data.vertices), len(names)), np.float32)
    for v in ob.data.vertices:
        for g in v.groups:
            j = col.get(g.group)
            if j is not None:
                W[v.index, j] = g.weight
    return W


def limit(W, most=4):
    """Keep each vertex's strongest few weights and make them sum to one."""
    W = np.array(W, np.float64)
    if most and W.shape[1] > most:
        np.put_along_axis(W, np.argpartition(W, -most, axis=1)[:, :-most], 0.0, axis=1)
    total = W.sum(1, keepdims=True)
    return W / np.where(total > 0, total, 1)


def set_weights(ob, W, names, most=4):
    """Replace an object's vertex groups with a weight table."""
    W = limit(W, most)
    ob.vertex_groups.clear()
    for j, name in enumerate(names):
        idx = np.nonzero(W[:, j] > 1e-5)[0]
        if not len(idx):
            continue
        vg = ob.vertex_groups.new(name=name)
        for i in idx:
            vg.add([int(i)], float(W[i, j]), 'REPLACE')
    return W


class Surface:
    """Values held by a mesh's vertices, read at the nearest point of its surface."""

    def __init__(self, co, polys):
        self.co = np.asarray(co, np.float64)
        self.polys = polys
        self.tree = BVHTree.FromPolygons(self.co.tolist(), polys)

    def nearest(self, p):
        loc, _normal, index, _dist = self.tree.find_nearest(Vector(p))
        vs = self.polys[index]
        w = interpolate.poly_3d_calc([Vector(self.co[i]) for i in vs], loc)
        return vs, w, index

    def blend(self, values, points):
        out = np.empty((len(points),) + values.shape[1:], np.float64)
        for k, p in enumerate(points):
            vs, w, _ = self.nearest(p)
            out[k] = sum(wi * values[i] for wi, i in zip(w, vs))
        return out


class Unposer:
    """Carries things standing round a posed, skinned body back to its rest pose.

    Each point takes the skinning transform of the nearest point of the posed skin and
    has it undone. Cloth and cords go back point by point; anything rigid, a bangle or
    a link of chain, goes back in one piece so that it keeps its shape.
    """

    def __init__(self, body, rig, arms=('upperarm', 'lowerarm', 'wrist', 'finger', 'metacarpal')):
        names = [b.name for b in rig.data.bones if b.use_deform]
        W = limit(weights(body, names), 0)
        self.bone = {n: np.array(rig.pose.bones[n].matrix @ rig.data.bones[n].matrix_local.inverted()) for n in names}
        S = np.array([self.bone[n] for n in names])
        self.M = np.einsum('nb,bij->nij', W, S)
        rest = coords(body.data)
        self.posed = np.einsum('nij,nj->ni', self.M, np.c_[rest, np.ones(len(rest))])[:, :3]
        polys = polygons(body.data)
        self.skin = Surface(self.posed, polys)
        # the trunk and legs alone, for what is worn there: a hand hanging by the hip must not claim the cloth beside it
        arm = W[:, [any(k in n for k in arms) for n in names]].sum(1)
        self.trunk = Surface(self.posed, [p for p in polys if all(arm[i] < 0.2 for i in p)])

    def points(self, pts, skin=None):
        pts = np.asarray(pts, np.float64)
        inv = np.linalg.inv((skin or self.skin).blend(self.M, pts))
        return np.einsum('nij,nj->ni', inv, np.c_[pts, np.ones(len(pts))])[:, :3]

    def rigid(self, centre, skin=None):
        """The rigid move from pose to rest for whatever sits at centre."""
        centre = np.asarray(centre, np.float64)
        M = (skin or self.skin).blend(self.M, [centre])[0]
        U, _s, Vt = np.linalg.svd(M[:3, :3])
        R = U @ Vt
        if np.linalg.det(R) < 0:
            U[:, -1] *= -1
            R = U @ Vt
        at = (np.linalg.inv(M) @ np.r_[centre, 1.0])[:3]
        T = np.eye(4)
        T[:3, :3] = R.T
        T[:3, 3] = at - R.T @ centre
        return T


class Binder:
    """Skin weights for anything worn, taken from the nearest point of the body's skin."""

    def __init__(self, body, rig):
        self.names = [b.name for b in rig.data.bones]
        self.W = limit(weights(body, self.names), 0)
        self.skin = Surface(coords(body.data), polygons(body.data))

    def at(self, points, only=None):
        W = self.skin.blend(self.W, np.asarray(points, np.float64))
        if only:
            keep = np.array([n in only for n in self.names])
            W = W * keep
            empty = W.sum(1) < 1e-6
            W[empty, self.names.index(only[0])] = 1.0
        return W

    def one(self, name, count):
        W = np.zeros((count, len(self.names)))
        W[:, self.names.index(name)] = 1.0
        return W


# ----- the body --------------------------------------------------------------

def game_body(figure_dir, rig_name='game_engine'):
    """The figure's own body from MPFB, on MPFB's game rig, without the helper geometry.

    The shape comes from the figure's figure.py (or the toolkit's body.py where a figure
    has none), so the mesh is vertex for vertex the one in its portrait scene. The rig
    has 53 bones named as Unreal's mannequin names them, with a root on the ground.
    """
    for p in (str(TOOLKIT), str(figure_dir)):
        if p in sys.path:
            sys.path.remove(p)
        sys.path.insert(0, p)
    import body as tk_body
    try:
        import figure  # noqa: F401  (sets tk_body.MACRO and tk_body.TARGETS)
    except ImportError:
        pass
    from common import load_mpfb
    HumanService, TargetService, LocationService, _ = load_mpfb()
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)

    body = HumanService.create_human(macro_detail_dict=dict(tk_body.MACRO), feet_on_ground=True)
    root = LocationService.get_mpfb_data('targets')
    for name, weight in tk_body.TARGETS.items():
        TargetService.load_target(body, os.path.join(root, name + '.target.gz'), weight=weight)
    body.shape_key_add(name='Final', from_mix=True)
    final = np.zeros(len(body.data.vertices) * 3, np.float32)
    body.data.shape_keys.key_blocks['Final'].data.foreach_get('co', final)
    body.shape_key_clear()
    body.data.vertices.foreach_set('co', final)
    body.data.update()

    rig = HumanService.add_builtin_rig(body, rig_name, import_weights=True)
    body['eyes'] = str(tk_body.eye_data(body))

    keep = body.vertex_groups['body'].index
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.verts.ensure_lookup_table()
    helpers = [bm.verts[v.index] for v in body.data.vertices if not any(g.group == keep for g in v.groups)]
    bmesh.ops.delete(bm, geom=helpers, context='VERTS')
    bm.to_mesh(body.data)
    bm.free()
    for m in list(body.modifiers):
        if m.type != 'ARMATURE':
            body.modifiers.remove(m)
    body.data.polygons.foreach_set('use_smooth', [True] * len(body.data.polygons))
    body.data.update()

    names = [b.name for b in rig.data.bones]
    before = weights(body, names)
    set_weights(body, before, names, 4)
    over = int(((before > 1e-4).sum(1) > 4).sum())
    print('game body', len(body.data.vertices), 'vertices,', len(rig.data.bones), 'bones;',
          over, 'vertices cut to four weights', flush=True)
    return body, rig


# ----- images ----------------------------------------------------------------

def to_srgb(a):
    a = np.clip(np.asarray(a, np.float64), 0, 1)
    return np.where(a <= 0.0031308, a * 12.92, 1.055 * a ** (1 / 2.4) - 0.055)


def to_linear(a):
    a = np.clip(np.asarray(a, np.float64), 0, 1)
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def pixels(img):
    """An image's stored values as H x W x 4, bottom-up. Colour images come back sRGB-encoded."""
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(h, w, 4)


def new_image(name, width, height, colour=True):
    old = bpy.data.images.get(name)
    if old:
        bpy.data.images.remove(old)
    img = bpy.data.images.new(name, width, height, alpha=False, float_buffer=False)
    img.colorspace_settings.name = 'sRGB' if colour else 'Non-Color'
    return img


def write_png(path, a):
    """8-bit PNG from H x W (grey), H x W x 3 or H x W x 4, given bottom-up, floats 0 to 1 or bytes."""
    a = np.asarray(a)
    if a.dtype != np.uint8:
        a = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    a = a[::-1]
    if a.ndim == 2:
        a = a[..., None]
    h, w, c = a.shape
    raw = a.reshape(h, w * c).astype(np.int16)
    # each row is stored as its difference from the row above or from the pixel to its left, whichever is smaller
    up = raw.copy()
    up[1:] -= raw[:-1]
    left = raw.copy()
    left[:, c:] -= raw[:, :-c]

    def cost(d):
        d = d & 0xFF
        return np.minimum(d, 256 - d).sum(1)
    use_up = cost(up) <= cost(left)
    rows = np.where(use_up[:, None], up, left) & 0xFF
    data = np.empty((h, w * c + 1), np.uint8)
    data[:, 0] = np.where(use_up, 2, 1)
    data[:, 1:] = rows

    def chunk(tag, payload):
        return struct.pack('>I', len(payload)) + tag + payload + struct.pack('>I', zlib.crc32(tag + payload) & 0xFFFFFFFF)
    kind = {1: 0, 3: 2, 4: 6}[c]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, kind, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(data.tobytes(), 9)) + chunk(b'IEND', b''))


def normal_map(height, strength=1.0, wrap=True):
    """Tangent-space normal map (OpenGL, green up) from a height map, slopes scaled by strength."""
    h = np.asarray(height, np.float64)
    if wrap:
        dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / 2
        dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / 2
    else:
        dy, dx = np.gradient(h)
    n = np.dstack([-dx * strength, -dy * strength, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


def resize(a, height, width):
    """Area-average or bilinear resample of H x W x C, with wrap-free edges."""
    a = np.asarray(a, np.float64)
    if a.ndim == 2:
        a = a[..., None]
    h, w = a.shape[:2]
    ys = (np.arange(height) + 0.5) * h / height - 0.5
    xs = (np.arange(width) + 0.5) * w / width - 0.5
    if h >= height * 2 and w >= width * 2 and h % height == 0 and w % width == 0:
        return a.reshape(height, h // height, width, w // width, -1).mean((1, 3))
    y0 = np.clip(np.floor(ys).astype(int), 0, h - 1)
    x0 = np.clip(np.floor(xs).astype(int), 0, w - 1)
    y1, x1 = np.clip(y0 + 1, 0, h - 1), np.clip(x0 + 1, 0, w - 1)
    fy = np.clip(ys - y0, 0, 1)[:, None, None]
    fx = np.clip(xs - x0, 0, 1)[None, :, None]
    top = a[y0][:, x0] * (1 - fx) + a[y0][:, x1] * fx
    bottom = a[y1][:, x0] * (1 - fx) + a[y1][:, x1] * fx
    return top * (1 - fy) + bottom * fy


# ----- baking ----------------------------------------------------------------

def _materials(objs):
    seen = []
    for ob in objs:
        for slot in ob.material_slots:
            if slot.material and slot.material not in seen:
                seen.append(slot.material)
    return seen


def _bake(objs, image, kind, samples, margin, clear):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    bk = sc.render.bake
    bk.target = 'IMAGE_TEXTURES'
    bk.use_selected_to_active = False
    bk.margin = margin
    bk.margin_type = 'EXTEND'
    bk.use_clear = clear
    bk.normal_space = 'TANGENT'
    bk.normal_r, bk.normal_g, bk.normal_b = 'POS_X', 'POS_Y', 'POS_Z'
    made = []
    for mat in _materials(objs):
        node = mat.node_tree.nodes.new('ShaderNodeTexImage')
        node.image = image
        mat.node_tree.nodes.active = node
        made.append((mat, node))
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    for ob in objs:
        ob.hide_render = False
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.bake(type=kind)
    for mat, node in made:
        mat.node_tree.nodes.remove(node)


def bake_pass(objs, image, kind, samples=8, margin=8, clear=False):
    """Bake one of Cycles' own passes ('NORMAL', 'AO') from the objects' materials as they stand."""
    _bake(objs, image, kind, samples, margin, clear)


def bake_input(objs, image, input_name, samples=4, margin=8, clear=False):
    """Bake whatever feeds one input of each material's Principled BSDF.

    For the length of the bake the value is wired to an emitter, so the map holds the
    material's own base colour, roughness or metal, whatever else the surface is made of.
    """
    undo = []
    for mat in _materials(objs):
        nt = mat.node_tree
        out = next(n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial' and n.is_active_output)
        bsdf = next((n for n in nt.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled'), None)
        if bsdf is None:
            continue
        em = nt.nodes.new('ShaderNodeEmission')
        sock = bsdf.inputs[input_name]
        if sock.is_linked:
            nt.links.new(sock.links[0].from_socket, em.inputs['Color'])
        else:
            v = sock.default_value
            em.inputs['Color'].default_value = (v, v, v, 1) if isinstance(v, float) else tuple(v)
        was = out.inputs['Surface'].links[0].from_socket if out.inputs['Surface'].is_linked else None
        nt.links.new(em.outputs[0], out.inputs['Surface'])
        undo.append((nt, out, was, em))
    _bake(objs, image, 'EMIT', samples, margin, clear)
    for nt, out, was, em in undo:
        if was is not None:
            nt.links.new(was, out.inputs['Surface'])
        nt.nodes.remove(em)


def orm(ao, rough, metal):
    """Pack occlusion, roughness and metal into the red, green and blue of one map."""
    def grey(a):
        a = np.asarray(a)
        return a[..., 0] if a.ndim == 3 else a
    return np.dstack([grey(ao), grey(rough), grey(metal)])


# ----- posing ----------------------------------------------------------------

def bones_in_order(rig):
    out = []

    def walk(b):
        out.append(b.name)
        for c in b.children:
            walk(c)
    for b in rig.data.bones:
        if b.parent is None:
            walk(b)
    return out


def clear_pose(rig):
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def apply_skin_pose(rig, moves):
    """Pose a rig from skinning transforms given in armature space, one for each named bone.

    Two rigs fitted to the same body share its rest pose, so a move measured on one
    bone of one rig can be given to the matching bone of the other.
    """
    clear_pose(rig)
    for name in bones_in_order(rig):
        if name in moves:
            rig.pose.bones[name].matrix = Matrix(np.asarray(moves[name]).tolist()) @ rig.data.bones[name].matrix_local
            bpy.context.view_layer.update()


def aim(pb, direction):
    """Turn a pose bone the shortest way so that it points along direction, in armature space."""
    M = pb.matrix.copy()
    cur = (M.to_3x3() @ Vector((0, 1, 0))).normalized()
    q = cur.rotation_difference(Vector(direction).normalized())
    pivot = M.translation.copy()
    pb.matrix = Matrix.Translation(pivot) @ q.to_matrix().to_4x4() @ Matrix.Translation(-pivot) @ M
    bpy.context.view_layer.update()


def spin(pb, axis, degrees):
    """Rotate a pose bone about an armature-space axis through its head."""
    M = pb.matrix.copy()
    pivot = M.translation.copy()
    R = Matrix.Rotation(np.radians(degrees), 4, Vector(axis).normalized())
    pb.matrix = Matrix.Translation(pivot) @ R @ Matrix.Translation(-pivot) @ M
    bpy.context.view_layer.update()


# ----- animation ---------------------------------------------------------------

def fcurves(action):
    """Every curve of an action, whether Blender keeps them on the action or in its layers."""
    found = []
    for layer in getattr(action, 'layers', []):
        for strip in layer.strips:
            for bag in getattr(strip, 'channelbags', []):
                found += list(bag.fcurves)
    return found or list(action.fcurves)


def key_pose(rig, frame, moved=('pelvis',)):
    """Key every bone's turn at a frame, and the place of the bones that are free to move."""
    for pb in rig.pose.bones:
        last = pb.get('_last')
        q = pb.rotation_quaternion.copy()
        if last is not None and sum(a * b for a, b in zip(q, last)) < 0:
            q.negate()                         # the same turn, written the way the last key wrote it
            pb.rotation_quaternion = q
        pb['_last'] = list(q)
        pb.keyframe_insert('rotation_quaternion', frame=frame)
        if pb.name in moved:
            pb.keyframe_insert('location', frame=frame)


def use_action(rig, action):
    rig.animation_data_create()
    rig.animation_data.action = action
    slots = getattr(action, 'slots', None)
    if slots and getattr(rig.animation_data, 'action_slot', None) is None:
        rig.animation_data.action_slot = slots[0]


# ----- export ----------------------------------------------------------------

def to_centimetres(rig, meshes):
    """Scale the data itself by 100 and call the scene's unit a centimetre, for the length of an export.

    Unreal counts in centimetres. Blender's FBX exporter can convert a scene kept in metres, but
    it does so by putting a scale of 100 on the armature, which Unreal then carries on the root
    of the skeleton. Scaling the bones and vertices instead leaves every transform at one.
    """
    from mathutils import Matrix as M
    bpy.context.scene.unit_settings.scale_length = 0.01
    grow = M.Scale(100, 4)
    for ob in meshes:
        ob.data.transform(grow)
        ob.data.update()
    if rig is not None:
        rig.data.transform(grow)
        for action in bpy.data.actions:
            for fc in fcurves(action):
                if fc.data_path.endswith('location'):
                    for k in fc.keyframe_points:
                        k.co.y *= 100
                        k.handle_left.y *= 100
                        k.handle_right.y *= 100
    bpy.context.view_layer.update()


def export_fbx(path, objects, animation=False):
    """FBX as Unreal's importer expects one: triangles with tangents, no leaf bones, centimetres."""
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    for ob in objects:
        ob.hide_set(False)
        ob.select_set(True)
    bpy.context.view_layer.objects.active = next((ob for ob in objects if ob.type == 'ARMATURE'), objects[0])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.fbx(
        filepath=str(path), use_selection=True, object_types={'ARMATURE', 'MESH'},
        use_mesh_modifiers=True, mesh_smooth_type='FACE', use_tspace=True, use_triangles=True,
        add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X', use_armature_deform_only=False,
        bake_anim=animation, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0,
        axis_forward='-Z', axis_up='Y', apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
        path_mode='RELATIVE', embed_textures=False)
    return Path(path).stat().st_size


def fbx_report(path):
    """Read an FBX back into an empty scene and say what an importer is given."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    bpy.context.view_layer.update()
    r = dict(file=Path(path).name, megabytes=round(Path(path).stat().st_size / 1e6, 2), objects={})
    for ob in bpy.data.objects:
        r['objects'][ob.type] = r['objects'].get(ob.type, 0) + 1
    rigs = [ob for ob in bpy.data.objects if ob.type == 'ARMATURE']
    meshes = [ob for ob in bpy.data.objects if ob.type == 'MESH']
    names = None
    if rigs:
        rig = rigs[0]
        names = [b.name for b in rig.data.bones]
        r.update(bones=len(names), root_bones=[b.name for b in rig.data.bones if b.parent is None],
                 armature_scale=[round(v, 4) for v in rig.scale],
                 actions=[(a.name, [round(v) for v in a.frame_range]) for a in bpy.data.actions])
    lo, hi = np.full(3, 1e9), np.full(3, -1e9)
    for ob in meshes:
        co = world_coords(ob)
        lo, hi = np.minimum(lo, co.min(0)), np.maximum(hi, co.max(0))
        rep = mesh_report(ob, names)
        rep['skinned'] = any(m.type == 'ARMATURE' for m in ob.modifiers)
        tex = {}
        for slot in ob.material_slots:
            nodes = slot.material.node_tree.nodes if slot.material and slot.material.use_nodes else []
            tex[slot.material.name] = sorted({n.image.name + ('' if n.image.size[0] else ' (not found)') for n in nodes if n.bl_idname == 'ShaderNodeTexImage' and n.image})
        rep['textures'] = tex
        r[ob.name] = rep
    if meshes:
        r['size_m'] = [round(float(v), 3) for v in (hi - lo)]
        r['lowest_point_m'] = round(float(lo[2]), 4)
    return r


# ----- stances, for trying a rig -----------------------------------------------

def _two_bone(a, c, la, lb, pole):
    d = c - a
    reach = min(d.length, la + lb - 1e-4)
    x = (la * la - lb * lb + reach * reach) / (2 * reach)
    h = max(la * la - x * x, 0.0) ** 0.5
    n = d.normalized()
    side = (pole - pole.dot(n) * n).normalized()
    return a + n * x + side * h, a + n * reach


def reach_limb(rig, upper, lower, end, target, pole):
    """Bend a two-bone limb of the game rig so that its end bone starts at target, the joint toward pole."""
    P, B = rig.pose.bones, rig.data.bones
    la = (B[lower].head_local - B[upper].head_local).length
    lb = (B[end].head_local - B[lower].head_local).length
    start = P[upper].matrix.translation.copy()
    joint, tip = _two_bone(start, Vector(target), la, lb, Vector(pole))
    aim(P[upper], joint - start)
    aim(P[lower], tip - P[lower].matrix.translation)


def level_foot(rig, side, yaw=0.0):
    """Put a foot back to the attitude it has in the rest pose, turned out by yaw degrees."""
    foot = rig.pose.bones['foot_' + side]
    rest = rig.data.bones['foot_' + side].matrix_local
    head = foot.matrix.translation.copy()
    foot.matrix = Matrix.Translation(head) @ Matrix.Rotation(np.radians(yaw), 4, 'Z') @ rest.to_3x3().to_4x4()
    bpy.context.view_layer.update()


def close_hand(rig, side, degrees=72, thumb=35):
    """Curl the fingers of the game rig toward the palm."""
    P = rig.pose.bones
    wrist = P['hand_' + side].matrix.translation
    along = (P['middle_01_' + side].matrix.translation - wrist).normalized()
    across = (P['pinky_01_' + side].matrix.translation - P['index_01_' + side].matrix.translation).normalized()
    palm = (along.cross(across) if side == 'r' else across.cross(along)).normalized()
    for finger in ('index', 'middle', 'ring', 'pinky', 'thumb'):
        for k in (1, 2, 3):
            pb = P[f'{finger}_0{k}_{side}']
            y = pb.matrix.to_3x3() @ Vector((0, 1, 0))
            axis = y.cross(palm)
            if axis.length > 1e-4:
                spin(pb, axis, thumb if finger == 'thumb' else degrees)


def stance_guard(rig):
    """A fighter's guard: left side forward, knees bent, hands up."""
    clear_pose(rig)
    P = rig.pose.bones
    pelvis = P['pelvis']
    pelvis.matrix = Matrix.Translation((0, 0, -0.075)) @ pelvis.matrix
    bpy.context.view_layer.update()
    spin(pelvis, (0, 0, 1), -32)
    spin(P['spine_02'], (0, 0, 1), 10)
    spin(P['spine_03'], (1, 0, 0), 6)
    reach_limb(rig, 'thigh_l', 'calf_l', 'foot_l', (0.20, -0.30, 0.085), (0.25, -1, 0))
    level_foot(rig, 'l', -8)
    reach_limb(rig, 'thigh_r', 'calf_r', 'foot_r', (-0.22, 0.30, 0.085), (-0.6, -1, 0))
    level_foot(rig, 'r', -48)
    reach_limb(rig, 'upperarm_l', 'lowerarm_l', 'hand_l', (0.16, -0.46, 1.50), (0.4, 0.2, -1))
    reach_limb(rig, 'upperarm_r', 'lowerarm_r', 'hand_r', (-0.20, -0.20, 1.40), (-0.5, 0.4, -1))
    spin(P['head'], (0, 0, 1), 22)
    for side in 'lr':
        close_hand(rig, side)


def stance_kick(rig):
    """A front kick with the right leg, to stretch the hip, the knee and whatever hangs from the waist."""
    clear_pose(rig)
    P = rig.pose.bones
    spin(P['pelvis'], (1, 0, 0), -10)
    spin(P['spine_02'], (1, 0, 0), -6)
    reach_limb(rig, 'thigh_l', 'calf_l', 'foot_l', (0.12, 0.10, 0.10), (0.2, -1, 0))
    level_foot(rig, 'l', 20)
    reach_limb(rig, 'thigh_r', 'calf_r', 'foot_r', (-0.13, -0.86, 1.05), (0, -0.3, 1))
    reach_limb(rig, 'upperarm_l', 'lowerarm_l', 'hand_l', (0.26, -0.32, 1.42), (0.5, 0.2, -1))
    reach_limb(rig, 'upperarm_r', 'lowerarm_r', 'hand_r', (-0.42, 0.10, 1.10), (-0.4, 0.6, -0.4))
    for side in 'lr':
        close_hand(rig, side)


# ----- looking at the result ---------------------------------------------------

def studio(samples=64):
    """Plain light for judging a model: a soft key, a fill, a rim, a grey floor. Returns the camera."""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'AgX'           # a filmic curve, as a game's tone mapper has
    sc.view_settings.look = 'None'
    world = bpy.data.worlds.new('Studio')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.20, 0.21, 0.23, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9
    sc.world = world
    col = collection('Studio')
    for name, at, watts, colour, size in (('Key', (-2.4, -3.4, 3.2), 900, (1.0, 0.95, 0.88), 2.4),
                                          ('Fill', (3.0, -2.4, 1.5), 260, (0.86, 0.92, 1.0), 2.6),
                                          ('Rim', (1.5, 3.4, 2.9), 700, (1.0, 0.97, 0.92), 1.6)):
        ob = bpy.data.objects.new(name, bpy.data.lights.new(name, 'AREA'))
        col.objects.link(ob)
        ob.data.energy, ob.data.color, ob.data.shape, ob.data.size = watts, colour, 'DISK', size
        ob.location = at
        ob.rotation_euler = (Vector((0, 0, 1.0)) - Vector(at)).to_track_quat('-Z', 'Y').to_euler()
    floor = new_object('Floor', [(-15, -15, -0.002), (15, -15, -0.002), (15, 15, -0.002), (-15, 15, -0.002)], [(0, 1, 2, 3)], col)
    grey = bpy.data.materials.new('StudioFloor')
    grey.use_nodes = True
    bsdf = grey.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (0.22, 0.22, 0.23, 1)
    bsdf.inputs['Roughness'].default_value = 0.85
    floor.data.materials.append(grey)
    cam = bpy.data.objects.new('ViewCamera', bpy.data.cameras.new('ViewCamera'))
    col.objects.link(cam)
    sc.camera = cam
    return cam


def shoot(path, cam, at, target, lens=85, width=520, height=760):
    sc = bpy.context.scene
    cam.location = at
    cam.rotation_euler = (Vector(target) - Vector(at)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    sc.render.resolution_x, sc.render.resolution_y = width, height
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path


def around(target, degrees, distance, rise=0.0):
    """A camera position on a circle round target: 0 degrees is in front of a figure that faces -Y."""
    a = np.radians(degrees)
    return (target[0] + np.sin(a) * distance, target[1] - np.cos(a) * distance, target[2] + rise)


def sheet(paths, out, gap=6, remove=True):
    """Stand pictures of one height side by side."""
    tiles = []
    for p in paths:
        img = bpy.data.images.load(str(p))
        tiles.append(pixels(img)[..., :3].copy())
        bpy.data.images.remove(img)
        if remove:
            os.remove(p)
    h = tiles[0].shape[0]
    spacer = np.ones((h, gap, 3), np.float32)
    row = []
    for t in tiles:
        row += [t, spacer]
    write_png(out, np.concatenate(row[:-1], axis=1))
