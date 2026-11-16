"""Ògún as a game character: Blender -b --python build_ogun_game.py -- stage [stage ...]

The portrait in 3d/ogun/ogun.blend is the source. Each stage reads the one before from the
work folder (GAME_WORK, or work/ beside this script), and the later ones write into this folder:

    body       his body on the 53-bone game rig, in the rest pose
    source     the portrait's cloth, fronds and iron, carried back to the rest pose
    parts      light versions of each of them, with their texture coordinates
    textures   Textures/: baked from the portrait's own materials, or painted to match
               (only=skin, only=gear, only=blade, only=fronds, only=etu or only=hair for one set)
    assemble   everything skinned and joined: SK_Ogun.blend
    animate    one short clip on the rig, standing guard
    export     Export/: FBX files, and check.json, what an importer gets back from them
    portrait   the portrait's own figure under plain light, for the comparison
    renders    Renders/: views, the wire, the rig put through some poses, and the comparison
               (only=views, only=wire, only=poses or only=compare for one sheet)

Run from the repo root with Blender 4.5 and MPFB2 installed as an extension, as for 3d/.
"""
import os
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
import gamekit as gk  # noqa: E402

WORK = Path(os.environ.get('GAME_WORK', HERE / 'work'))
WORK.mkdir(parents=True, exist_ok=True)
os.environ.setdefault('RENDER_WORK', str(WORK / 'toolkit'))      # where 3d/toolkit keeps its own scratch files
SOURCE = REPO / '3d' / 'ogun' / 'ogun.blend'
FIGURE = REPO / '3d' / 'ogun' / 'blender'
TEX = HERE / 'Textures'

CLOTH = ('Sokoto', 'Mariwo', 'MariwoCord')                      # carried back point by point
ON_HEAD = ('HeadbandCord', 'HeadbandFronds', 'Eye.L', 'Eye.R')  # built in the head's own space
BANGLES = ('IronBangle.L.0', 'IronBangle.L.1', 'IronBangle.L.2', 'IronBangle.R.0', 'IronBangle.R.1')
MACHETE = ('Ada', 'AdaHandle', 'AdaFittings')
HIGH = CLOTH + ON_HEAD + ('Chain',) + BANGLES + MACHETE
STRANDS = ('Brows', 'Lashes')


def save(name):
    path = WORK / name
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
    print('saved', path.name, round(path.stat().st_size / 1e6, 1), 'MB', flush=True)


def open_stage(name):
    bpy.ops.wm.open_mainfile(filepath=str(WORK / name))


def save_model():
    """Write SK_Ogun.blend beside this script, its textures found by path relative to it."""
    path = HERE / 'SK_Ogun.blend'
    bpy.context.preferences.filepaths.save_version = 0      # no .blend1 left in the repo
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile(compress=True)
    return path


# ----- body ------------------------------------------------------------------

def stage_body():
    body, rig = gk.game_body(FIGURE)
    body.name = body.data.name = 'Body'
    rig.name = 'Armature'                      # Unreal leaves out a root node of this name, so 'root' below is the root
    rig.data.name = 'SKEL_Ogun'
    rig.data.bones['Root'].name = 'root'

    # where his hair and beard grow, measured while the mesh still has every face
    import hair
    import dress
    scalp, adj = hair.scalp_mask(body)
    gk.set_point_attr(body.data, 'scalp', scalp)
    # the portrait's beard thins toward its edge hair by hair; here it is the shading on the skin that thins, over three rings
    gk.set_point_attr(body.data, 'beard', dress.soften(hair.beard_mask(body, adj), adj, 3, 0.5))

    # what the portrait's body carries: the skin's regions, and which skin the trousers hide
    pub = gk.append(SOURCE, objects=['Body'])['Body']
    apart = float(np.abs(gk.coords(pub.data) - gk.coords(body.data)).max())
    print('rest pose differs from the portrait by', apart, 'm', flush=True)
    assert apart < 1e-5
    for name in ('mask_a', 'mask_b'):
        a = np.empty(len(pub.data.vertices) * 4, np.float32)
        pub.data.color_attributes[name].data.foreach_get('color', a)
        body.data.color_attributes.new(name, 'FLOAT_COLOR', 'POINT').data.foreach_set('color', a)
    vis = pub.vertex_groups['visible'].index
    shown = np.array([any(g.group == vis for g in v.groups) for v in pub.data.vertices], np.float32)
    gk.set_point_attr(body.data, 'visible', shown)
    print('skin hidden under the trousers:', int((shown < 0.5).sum()), 'vertices', flush=True)
    bpy.data.objects.remove(pub)

    game = gk.collection('Game')
    for ob in (body, rig):
        gk.link(ob, game)
    save('10_body.blend')


# ----- source ----------------------------------------------------------------

def stage_source():
    open_stage('10_body.blend')
    got = gk.append(SOURCE, objects=('Body', 'Rig') + HIGH + STRANDS)
    high = gk.collection('High')
    for ob in got.values():
        gk.link(ob, high)
        if ob.parent is not None and ob.parent.name not in got:
            ob.parent = None                   # the turntable, which stands at the origin
        for m in list(getattr(ob, 'modifiers', [])):
            if ob.name not in ('Body', 'Body.001'):
                ob.modifiers.remove(m)
    bpy.context.view_layer.update()
    for name in HIGH:
        broken = gk.drop_broken_vertices(got[name])
        if broken:
            print(name, 'had', broken, 'vertices with no position; taken out', flush=True)
    pbody, prig = got['Body'], got['Rig']
    un = gk.Unposer(pbody, prig)

    # the transforms worked out here must give the posed skin Blender itself gives
    for m in pbody.modifiers:
        m.show_viewport = m.type == 'ARMATURE'
    dg = bpy.context.evaluated_depsgraph_get()
    ev = pbody.evaluated_get(dg)
    me = ev.to_mesh()
    print('posed skin differs from Blender by', float(np.abs(gk.coords(me) - un.posed).max()), 'm', flush=True)
    ev.to_mesh_clear()

    head_back = np.linalg.inv(un.bone['head'])
    for name in CLOTH:
        ob = got[name]
        gk.set_coords(ob.data, un.points(gk.world_coords(ob), un.trunk))
        ob.matrix_world = Matrix.Identity(4)
    for name in ON_HEAD:
        ob = got[name]
        ob.matrix_world = Matrix((head_back @ np.array(ob.matrix_world)).tolist())
    for name in BANGLES + ('Ada',):
        ob = got[name]
        world = np.array(ob.matrix_world)
        ob.matrix_world = Matrix((un.rigid(world[:3, 3]) @ world).tolist())

    chain = got['Chain']
    co = gk.world_coords(chain)
    pieces = gk.islands(chain.data)
    for idx in pieces:
        co[idx] = gk.transform(co[idx], un.rigid(co[idx].mean(0), un.trunk))
    gk.set_coords(chain.data, co)
    chain.matrix_world = Matrix.Identity(4)
    sizes = [len(i) for i in pieces]
    print('chain pieces', len(pieces), 'of which links (400 vertices)', sizes.count(400), flush=True)

    # brows and lashes were laid on the posed head: keep their points, in the head's rest space
    for name in STRANDS:
        ob = got[name]
        hc = ob.data
        p = np.empty(len(hc.points) * 3, np.float32)
        hc.position_data.foreach_get('vector', p)
        p = gk.transform(gk.transform(p.reshape(-1, 3), np.array(ob.matrix_world)), head_back)
        per = len(hc.points) // len(hc.curves)
        np.save(WORK / f'{name.lower()}.npy', p.reshape(len(hc.curves), per, 3).astype(np.float32))
        print(name, len(hc.curves), 'strands of', per, 'points', flush=True)
        bpy.data.objects.remove(ob)

    # the portrait's pose, as the move of each of its bones, to try on the game rig later
    np.savez(WORK / 'portrait_pose.npz', **un.bone)

    bpy.data.objects['Body'].data.materials.append(pbody.data.materials[0])     # his skin, kept for the bake
    for ob in (pbody, prig):
        bpy.data.objects.remove(ob)
    bpy.context.view_layer.update()
    for name in HIGH:
        ob = got[name]
        lo = gk.world_coords(ob).min(0).round(3).tolist()
        hi = gk.world_coords(ob).max(0).round(3).tolist()
        print(f'  {name:16} {len(ob.data.vertices):6} vertices {len(ob.data.polygons):6} faces  {lo} to {hi}', flush=True)
    save('20_source.blend')


# ----- parts -----------------------------------------------------------------

# where each kind of small thing sits in the gear atlas, as (x0, y0, x1, y1)
GEAR = dict(tools=(0.0, 0.0, 0.74, 0.78), eyes=(0.76, 0.52, 1.0, 0.76), link=(0.52, 0.80, 0.98, 0.87),
            bangle=(0.0, 0.80, 0.50, 0.87), headcord=(0.0, 0.88, 0.60, 0.93), waistcord=(0.0, 0.94, 1.0, 1.0))
BLADE = dict(blade=(0.0, 0.42, 1.0, 1.0), handle=(0.0, 0.0, 0.55, 0.38), ferrule=(0.58, 0.0, 0.80, 0.38), rivet=(0.84, 0.0, 1.0, 0.16))
FROND_COLUMNS = 16       # leaflets across the frond atlas: eight tints, each with and without a midrib
FROND_WIDE = 0.018       # metres of leaflet a column is wide
FROND_LONG = 0.76        # metres of leaflet the atlas is tall; a leaflet's cut end sits at the bottom
WIRE = 0.0039            # radius of the rod the chain's links are bent from
TRUNK = ['spine_02', 'pelvis', 'spine_01', 'spine_03', 'clavicle_l', 'clavicle_r', 'neck_01']
HIPS = ['pelvis', 'thigh_l', 'thigh_r', 'spine_01']


def smoothstep(x, a, b):
    t = np.clip((np.asarray(x, np.float64) - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def tag(ob, slot):
    ob['slot'] = slot
    return ob


def shell(body, mask, lift, name, col, tile):
    """Hair as a thin layer standing off the skin where the mask says it grows, tucked under the skin at its edge."""
    me = body.data
    co = gk.coords(me)
    nor = np.empty(len(me.vertices) * 3, np.float64)
    me.vertex_normals.foreach_get('vector', nor)
    nor = nor.reshape(-1, 3)
    uv_all = gk.loop_uv(me)
    faces, uvs = [], []
    for p in me.polygons:
        if max(mask[i] for i in p.vertices) > 0.55:
            faces.append(tuple(p.vertices))
            uvs += [uv_all[i] * tile for i in p.loop_indices]
    uvs = np.array(uvs)
    uvs -= np.floor(uvs.mean(0))               # the map repeats: keep the numbers small
    used = sorted({i for f in faces for i in f})
    new = {old: k for k, old in enumerate(used)}
    # only the thick of the hair stands off the skin; its thin edge is left to the shading painted on the skin under it
    out = -0.0012 + (lift + 0.0012) * smoothstep(mask[used], 0.55, 0.90)
    ob = gk.new_object(name, co[used] + nor[used] * out[:, None], [tuple(new[i] for i in f) for f in faces], col, uv=np.array(uvs))
    names = [b.name for b in bpy.data.objects['Armature'].data.bones]
    gk.set_weights(ob, gk.weights(body, names)[used], names)
    return tag(ob, 'Hair')


def leaflets(co, tint, rib, rows, name, col, W_rows):
    """Flat ribbons from the portrait's folded strips: the two outer edges, at a few of the rows.

    co is strips x rows x 5 x 3. Each ribbon is drawn from one column of the frond atlas, chosen
    by its tint and whether it kept a midrib, at the leaflet's true width, its cut end at the bottom.
    """
    strips = co.shape[0]
    mid = co[:, :, 2]
    arc = np.concatenate([np.zeros((strips, 1)), np.cumsum(np.linalg.norm(np.diff(mid, axis=1), axis=2), axis=1)], 1)
    pick = co[:, rows][:, :, [0, 4]]
    R = len(rows)
    half = np.minimum(np.linalg.norm(pick[:, :, 1] - pick[:, :, 0], axis=2) / FROND_WIDE / 2, 0.47) / FROND_COLUMNS
    faces, uvs = [], []
    for s in range(strips):
        u = (min(int(tint[s] * 8), 7) + (8 if rib[s] > 0.5 else 0) + 0.5) / FROND_COLUMNS
        v = np.clip((arc[s, -1] - arc[s, rows]) / FROND_LONG, 0, 1)
        for r in range(R - 1):
            a, b = (s * R + r) * 2, (s * R + r + 1) * 2
            faces.append((a, a + 1, b + 1, b))
            uvs += [(u - half[s, r], v[r]), (u + half[s, r], v[r]), (u + half[s, r + 1], v[r + 1]), (u - half[s, r + 1], v[r + 1])]
    ob = gk.new_object(name, pick.reshape(-1, 3), faces, col, uv=np.array(uvs))
    names = [b.name for b in bpy.data.objects['Armature'].data.bones]
    gk.set_weights(ob, np.repeat(W_rows.reshape(strips * R, -1), 2, axis=0), names)
    return tag(ob, 'Mariwo')


def cord(src, segments, radius, rect, name, col):
    """One rope in place of the portrait's two twisted plies, along the line between them."""
    plies = gk.world_coords(src).reshape(2, -1, 8, 3)
    centre = plies.mean(axis=(0, 2))[:-1]              # the last station repeats the first
    at = np.round(np.linspace(0, len(centre), segments, endpoint=False)).astype(int)
    v, f, uv = gk.tube(centre[at], radius, sides=6, closed=True)
    return tag(gk.new_object(name, v, f, col, uv=gk.into(uv, rect)), 'Gear'), centre[at]


def grid_tube(grid, rect, cap_ends=True):
    """Quads over a grid of rings x sides, texture coordinates by length along and girth round, with fan caps."""
    n, m = grid.shape[:2]
    along = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(grid.mean(1), axis=0), axis=1))])
    along /= along[-1]
    if cap_ends:
        along = 0.03 + 0.94 * along            # the two ends of the patch are kept for the caps
    closed = np.concatenate([grid, grid[:, :1]], 1)
    girth = np.concatenate([np.zeros((n, 1)), np.cumsum(np.linalg.norm(np.diff(closed, axis=1), axis=2), axis=1)], 1)
    girth /= girth[:, -1:]
    faces, uvs = [], []
    for i in range(n - 1):
        for j in range(m):
            k = (j + 1) % m
            faces.append((i * m + j, i * m + k, (i + 1) * m + k, (i + 1) * m + j))
            uvs += [(along[i], girth[i, j]), (along[i], girth[i, j + 1]), (along[i + 1], girth[i + 1, j + 1]), (along[i + 1], girth[i + 1, j])]
    if cap_ends:
        for i, order in ((0, range(m - 1, -1, -1)), (n - 1, range(m))):
            order = list(order)
            for a, b in zip(order[1:-1], order[2:]):
                faces.append((i * m + order[0], i * m + a, i * m + b))
                bow = (-1 if i == 0 else 1) * 0.025
                uvs += [(along[i] + bow * np.sin(np.pi * girth[i, c]), girth[i, c]) for c in (order[0], a, b)]
    return grid.reshape(-1, 3), faces, gk.into(np.array(uvs), rect)


def make_machete(col, iron):
    """The àdá in the frame it was forged in: grip at the origin, blade along +Z, edge toward -Y."""
    blade, handle, fittings = (bpy.data.objects[n] for n in MACHETE)
    where = blade.matrix_world.copy()

    co = gk.coords(blade.data)[:150 * 34].reshape(150, 34, 3)
    edge = gk.point_attr(blade.data, 'edge')[:150 * 34].reshape(150, 34)
    stations = sorted(set(np.round(np.linspace(0, 126, 13)).astype(int).tolist() + [132, 137, 141, 144, 146, 148, 149]))
    section = [0, 7, 13, 15, 18, 20, 26]               # edge, end of the bevel, spine, round the spine, and back
    v, f, uv = grid_tube(co[stations][:, section], BLADE['blade'])
    low = gk.new_object('G_AdaBlade', v, f, col, uv=uv)
    gk.set_point_attr(low.data, 'edge', edge[stations][:, section].ravel())
    low.data.materials.append(blade.data.materials[0])
    made = [low]

    co = gk.coords(handle.data)[:60 * 28].reshape(60, 28, 3)
    ten = np.round(np.linspace(0, 28, 10, endpoint=False)).astype(int)
    v, f, uv = grid_tube(co[[0, 8, 17, 25, 34, 42, 51, 59]][:, ten], BLADE['handle'])
    low = gk.new_object('G_AdaHandle', v, f, col, uv=uv)
    low.data.materials.append(handle.data.materials[0])
    made.append(low)

    co = gk.coords(fittings.data)
    v, f, uv = grid_tube(co[:8 * 28].reshape(8, 28, 3)[[0, 3, 7]][:, ten], BLADE['ferrule'], cap_ends=False)
    parts = [(v, f, uv)]
    from dress import sphere
    for k in range(4):
        centre = co[8 * 28 + k * 86: 8 * 28 + (k + 1) * 86].mean(0)
        sv, sf, suv = sphere(0.0034, 4, 6)
        suv = gk.into(suv, BLADE['rivet']) + (k, 0)     # the four share one patch of the map
        loops = np.array([suv[i] for q in sf for i in q])
        parts.append((sv * np.array([0.4, 1, 1]) + centre, sf, loops))
    verts, faces, uvs, base = [], [], [], 0
    for pv, pf, puv in parts:
        verts.append(pv)
        faces += [tuple(i + base for i in q) for q in pf]
        uvs.append(puv)
        base += len(pv)
    low = gk.new_object('G_AdaFittings', np.concatenate(verts), faces, col, uv=np.concatenate(uvs))
    low.data.materials.append(iron)
    made.append(low)
    for ob in made:
        ob.matrix_world = where
        gk.face_outward(ob)
        gk.sharpen(ob, 40)
        tag(ob, 'Ada')
    return made


def stage_parts():
    open_stage('20_source.blend')
    for p in (str(gk.TOOLKIT), str(FIGURE)):
        sys.path.insert(0, p)
    import math
    from dress import ring_mesh, sphere
    game, weapon = gk.collection('Game'), gk.collection('Weapon')
    body, rig = bpy.data.objects['Body'], bpy.data.objects['Armature']
    names = [b.name for b in rig.data.bones]
    bind = gk.Binder(body, rig)
    iron = bpy.data.materials['Iron']
    tag(body, 'Skin')

    # hair: a cap on the scalp and a layer along the jaw, each from the skin under it
    cap = shell(body, gk.point_attr(body.data, 'scalp'), 0.0042, 'G_HairCap', game, 14.0)
    beard = shell(body, gk.point_attr(body.data, 'beard'), 0.0045, 'G_Beard', game, 14.0)

    # the skin the trousers hide is taken out, as the portrait masks it
    hidden = gk.point_attr(body.data, 'visible') < 0.5
    gone = gk.delete_faces(body, [all(hidden[i] for i in p.vertices) for p in body.data.polygons])
    print('skin faces taken out under the trousers:', gone, flush=True)

    # eyes
    info = eval(body['eyes'])
    for k, side in enumerate('LR'):
        v, f, uv = sphere(info[side]['radius'] * 0.985, 10, 14, bulge=lambda a: 1 + 0.085 * math.exp(-(a / 0.50) ** 2))
        v = gk.transform(v, np.array(bpy.data.objects[f'Eye.{side}'].matrix_world))
        eye = tag(gk.new_object(f'G_Eye_{side}', v, f, game, uv=gk.into(uv, GEAR['eyes']) + (k, 0)), 'Gear')
        # the portrait's eye material reads its picture front-on: a second layer keeps that for the bake
        loops = np.empty(len(eye.data.loops), np.int32)
        eye.data.loops.foreach_get('vertex_index', loops)
        source = eye.data.uv_layers.new(name='Source')
        source.data.foreach_set('uv', np.asarray(uv, np.float32)[loops].ravel())
        source.active_render = True
        eye.data.uv_layers.active = eye.data.uv_layers['UVMap']
        eye.data.materials.append(bpy.data.objects[f'Eye.{side}'].data.materials[0])
        gk.face_outward(eye)
        gk.set_weights(eye, bind.one('head', len(v)), names)

    # trousers: the portrait's own cloth, with fewer faces; its pattern coordinates count picks and strips
    src = bpy.data.objects['Sokoto']
    sokoto = tag(gk.decimated(src, 3200 / gk.triangles(src.data), 'G_Sokoto', game), 'Etu')
    sokoto.data.materials.clear()
    uv = gk.loop_uv(sokoto.data) * (6, 11)
    gk.set_loop_uv(sokoto.data, uv - np.floor(uv.mean(0)))     # the map repeats: keep the numbers small
    sokoto.data.polygons.foreach_set('use_smooth', [True] * len(sokoto.data.polygons))
    gk.set_weights(sokoto, bind.at(gk.coords(sokoto.data), HIPS + ['spine_02', 'calf_l', 'calf_r']), names)

    # the fringe: every strip of the portrait's, as a flat ribbon of ten quads
    src = bpy.data.objects['Mariwo']
    co = gk.coords(src.data).reshape(280, 69, 5, 3)
    tint = gk.point_attr(src.data, 'tint').reshape(280, 69, 5)[:, 0, 0]
    rib = gk.point_attr(src.data, 'rib').reshape(280, 69, 5)[:, 0, 0]
    rows = [0, 4] + [5 + k for k in (0, 6, 14, 23, 32, 41, 50, 58, 63)]
    centre = co[:, rows][:, :, [0, 4]].mean(2)
    W = bind.at(centre.reshape(-1, 3), HIPS).reshape(280, len(rows), -1)
    # below the knee a strip keeps the weights it had above it, so it swings with the thigh
    hold = rig.data.bones['calf_l'].head_local.z + 0.06
    for s in range(280):
        above = np.nonzero(centre[s, :, 2] >= hold)[0]
        W[s, above[-1] + 1:] = W[s, above[-1]]
    # the lower a strip hangs, the more it keeps to the hips: a raised thigh lifts it without carrying it out straight
    lag = (0.35 * smoothstep(centre[:, :1, 2] - centre[:, :, 2], 0.10, 0.50))[..., None]
    hips = np.zeros(len(names))
    hips[names.index('pelvis')] = 1.0
    W = W * (1 - lag) + hips * lag
    fringe = leaflets(co, tint, rib, rows, 'G_Mariwo', game, W)

    # the two cords
    waist, line = cord(bpy.data.objects['MariwoCord'], 48, 0.0085, GEAR['waistcord'], 'G_WaistCord', game)
    gk.set_weights(waist, np.repeat(bind.at(line, HIPS + ['spine_02']), 6, axis=0), names)
    band, line = cord(bpy.data.objects['HeadbandCord'], 32, 0.0062, GEAR['headcord'], 'G_HeadCord', game)
    gk.set_weights(band, bind.one('head', len(band.data.vertices)), names)

    # the leaflet ends standing from the headband
    src = bpy.data.objects['HeadbandFronds']
    co = gk.world_coords(src).reshape(40, 22, 5, 3)
    tint = gk.point_attr(src.data, 'tint').reshape(40, 22, 5)[:, 0, 0]
    rib = gk.point_attr(src.data, 'rib').reshape(40, 22, 5)[:, 0, 0]
    rows = [0, 5, 10, 15, 19, 21]
    fronds = leaflets(co, tint, rib, rows, 'G_HeadFronds', game, np.tile(bind.one('head', 1), (40, len(rows), 1)))

    # the chain: each link again, from ten points of its rod and a square section
    src = bpy.data.objects['Chain']
    co = gk.coords(src.data)
    pieces = gk.islands(src.data)
    links = [i for i in pieces if len(i) == 400]
    verts, faces, uvs, weights, base = [], [], [], [], 0
    for n, idx in enumerate(links):
        rod = co[idx].reshape(40, 10, 3).mean(1)
        flat = np.linalg.svd(rod - rod.mean(0))[2][2]
        v, f, uv = gk.tube(rod[np.round(np.linspace(0, 40, 10, endpoint=False)).astype(int)], WIRE, sides=4, closed=True, up=flat, turn=np.pi / 4)
        verts.append(v)
        faces += [tuple(i + base for i in q) for q in f]
        uvs.append(gk.into(uv, GEAR['link']) + (n, 0))   # every link is drawn from the one patch
        weights.append(np.repeat(gk.limit(bind.at([rod.mean(0)], TRUNK), 2), len(v), axis=0))
        base += len(v)
    chain = tag(gk.new_object('G_Chain', np.concatenate(verts), faces, game, uv=np.concatenate(uvs)), 'Gear')
    chain.data.materials.append(iron)
    gk.face_outward(chain)
    gk.set_weights(chain, np.concatenate(weights), names)

    # the six small tools and the rings that carry them: the portrait's, thinned
    only = src.copy()
    only.data = src.data.copy()
    gk.collection('High').objects.link(only)
    gk.delete_faces(only, [p.vertices[0] in set(np.concatenate(links).tolist()) for p in only.data.polygons])
    bpy.context.view_layer.update()
    tools = tag(gk.decimated(only, 0.5, 'G_Tools', game), 'Gear')
    bpy.data.objects.remove(only)
    if not tools.data.uv_layers:
        tools.data.uv_layers.new(name='UVMap')
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    tools.select_set(True)
    bpy.context.view_layer.objects.active = tools
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(85), island_margin=0.01)
    bpy.ops.object.mode_set(mode='OBJECT')
    gk.set_loop_uv(tools.data, gk.into(gk.loop_uv(tools.data), GEAR['tools']))
    gk.sharpen(tools, 40)
    co = gk.coords(tools.data)
    W = np.zeros((len(co), len(names)))
    for idx in gk.islands(tools.data):
        W[idx] = gk.limit(bind.at([co[idx].mean(0)], TRUNK), 2)
    gk.set_weights(tools, W, names)

    # bangles: the toolkit's ring at a quarter of its faces, turned the right way out
    for n, name in enumerate(BANGLES):
        _, side, k = name.split('.')
        v, f = ring_mesh(0.0355, 0.0355 + 0.0085, 0.0098, 300 + int(k) + (0 if side == 'L' else 10), rows=6, cols=20)
        uv = []
        for j in range(20):
            for i in range(6):
                uv += [(j / 20, i / 6), ((j + 1) / 20, i / 6), ((j + 1) / 20, (i + 1) / 6), (j / 20, (i + 1) / 6)]
        f = [(q[0], q[3], q[2], q[1]) for q in f]
        v = gk.transform(v, np.array(bpy.data.objects[name].matrix_world))
        ring = tag(gk.new_object('G_Bangle_' + side + k, v, f, game, uv=gk.into(np.array(uv), GEAR['bangle']) + (n, 0)), 'Gear')
        ring.data.materials.append(iron)
        gk.set_weights(ring, bind.one('lowerarm_l' if side == 'L' else 'lowerarm_r', len(v)), names)

    make_machete(weapon, iron)

    total = 0
    for ob in list(game.objects) + list(weapon.objects):
        if ob.type == 'MESH':
            t = gk.triangles(ob.data)
            total += t if ob.name in game.objects else 0
            print(f'  {ob.name:14} {t:6} triangles  {ob.get("slot")}', flush=True)
    print('character', total, 'triangles', flush=True)
    save('30_parts.blend')


# ----- textures --------------------------------------------------------------

HAIR = (0.008, 0.006, 0.005)                 # the portrait's hair colour, linear
COILS = (0.017, 0.011, 0.008)                # how his coils read from a little way off: warmer and lighter than one hair
SKIN_DEEPEN = 0.90                           # the portrait's skin scatters light under its surface; a plain surface reads paler
SCALE = (0.035, 0.033, 0.032)                # black fire scale on forged iron
CORD = (0.355, 0.389, 0.124)                 # what the portrait's palm material gives its cords, linear
THROUGH = (0.55, 0.60, 0.10)                 # the colour of light coming through a frond


def filled(name, width, height, value, colour):
    img = gk.new_image(name, width, height, colour)
    a = np.empty((height, width, 4), np.float32)
    a[:] = (*value, 1.0)
    img.pixels.foreach_set(a.ravel())
    return img


def rgb(img):
    return gk.pixels(img)[..., :3].astype(np.float64)


def paint_strands(colour, strands, body, tint, strength):
    """Draw hair curves that lie on the skin into its colour map, each where the skin under it is drawn."""
    me = body.data
    skin = gk.Surface(gk.coords(me), gk.polygons(me))
    uv_all = gk.loop_uv(me)
    loops = [list(p.loop_indices) for p in me.polygons]
    h, w = colour.shape[:2]
    cover = np.zeros((h, w))
    for strand in strands:
        uv = []
        for p in strand:
            _vs, wt, index = skin.nearest(p)
            uv.append(sum(wi * uv_all[li] for wi, li in zip(wt, loops[index])))
        for a, b in zip(uv[:-1], uv[1:]):
            reach = float(np.abs(b - a).max())
            if reach > 0.02:
                continue                     # the curve crosses a seam of the map
            t = np.linspace(0, 1, max(int(reach * w * 2), 1) + 1)[:, None]
            q = a + (b - a) * t
            np.add.at(cover, (np.clip((q[:, 1] * h).astype(int), 0, h - 1), np.clip((q[:, 0] * w).astype(int), 0, w - 1)), 0.5)
    # a hair is thinner than a texel: spread each a little, and let hairs that cross build up
    for _ in range(2):
        cover = (cover * 2 + np.roll(cover, 1, 0) + np.roll(cover, -1, 0) + np.roll(cover, 1, 1) + np.roll(cover, -1, 1)) / 6
    alpha = 0.8 * (1 - np.exp(-cover * strength))[..., None]
    return colour * (1 - alpha) + np.array(tint) * alpha


def skin_textures(body, others):
    size = 2048
    skin = body.data.materials[0]
    nt = skin.node_tree
    bsdf = next(n for n in nt.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled')
    # the beard shades the skin under it, as the portrait's scalp is shaded under its hair
    was = bsdf.inputs['Base Color'].links[0].from_socket
    attr = nt.nodes.new('ShaderNodeAttribute')
    attr.attribute_name, attr.attribute_type = 'beard', 'GEOMETRY'
    amount = nt.nodes.new('ShaderNodeMath')
    amount.operation = 'MULTIPLY'
    amount.inputs[1].default_value = 0.85
    nt.links.new(attr.outputs['Fac'], amount.inputs[0])
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    nt.links.new(amount.outputs[0], mix.inputs[0])
    nt.links.new(was, mix.inputs[6])
    mix.inputs[7].default_value = (*(c * 0.9 for c in COILS), 1)
    nt.links.new(mix.outputs[2], bsdf.inputs['Base Color'])

    bc = filled('bake_skin_bc', size, size, (0.25, 0.14, 0.10), True)
    gk.bake_input([body], bc, 'Base Color', samples=4)
    ro = filled('bake_skin_ro', size, size, (0.55, 0.55, 0.55), False)
    gk.bake_input([body], ro, 'Roughness', samples=4)
    no = filled('bake_skin_no', size, size, (0.5, 0.5, 1.0), False)
    gk.bake_pass([body], no, 'NORMAL', samples=12)
    # occlusion of the body by itself alone, at half size: it is soft, and what he wears moves
    for ob in others:
        ob.hide_render = True
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new('World')
    sc.world.light_settings.distance = 0.25
    ao = filled('bake_skin_ao', size // 2, size // 2, (1, 1, 1), False)
    gk.bake_pass([body], ao, 'AO', samples=24)
    for ob in others:
        ob.hide_render = False

    colour = rgb(bc)
    dark = gk.to_srgb(HAIR)
    colour = gk.to_srgb(gk.to_linear(colour) * SKIN_DEEPEN)
    colour = paint_strands(colour, np.load(WORK / 'brows.npy'), body, dark, 0.9)
    colour = paint_strands(colour, np.load(WORK / 'lashes.npy')[:, :2], body, dark, 6.0)   # only where each lash leaves the lid
    gk.write_png(TEX / 'T_Ogun_Skin_BaseColor.png', colour)
    gk.write_png(TEX / 'T_Ogun_Skin_Normal.png', rgb(no))
    occ = gk.resize(rgb(ao)[..., :1], size, size)[..., 0]
    gk.write_png(TEX / 'T_Ogun_Skin_ORM.png', gk.orm(0.3 + 0.7 * occ, rgb(ro), np.zeros((size, size))))


def rope(colour, rough, normal, rect, length, pitch):
    """Paint a two-ply twisted cord into its patch of the gear atlas."""
    size = colour.shape[0]
    x0, y0, x1, y1 = (int(round(v * size)) for v in rect)
    v, u = np.mgrid[0:y1 - y0, 0:x1 - x0]
    ridge = np.abs(np.sin(np.pi * (u / (x1 - x0) * round(length / pitch * 2) + v / (y1 - y0) * 2)))
    colour[y0:y1, x0:x1] = gk.to_srgb(CORD) * (0.70 + 0.30 * ridge[..., None])
    rough[y0:y1, x0:x1] = 0.62
    normal[y0:y1, x0:x1] = gk.normal_map(ridge, 1.6)


def gear_textures(game):
    size = 1024
    baked = [ob for ob in game.objects if ob.get('slot') == 'Gear' and len(ob.data.materials)]
    bc = filled('bake_gear_bc', size, size, tuple(gk.to_srgb(CORD)), True)
    ro = filled('bake_gear_ro', size, size, (0.6, 0.6, 0.6), False)
    mt = filled('bake_gear_mt', size, size, (0, 0, 0), False)
    no = filled('bake_gear_no', size, size, (0.5, 0.5, 1.0), False)
    gk.bake_input(baked, bc, 'Base Color', samples=8, margin=3)
    gk.bake_input(baked, ro, 'Roughness', samples=8, margin=3)
    gk.bake_input(baked, mt, 'Metallic', samples=8, margin=3)
    gk.bake_pass(baked, no, 'NORMAL', samples=12, margin=3)
    colour, rough, metal, normal = rgb(bc), rgb(ro)[..., 0], rgb(mt)[..., 0], rgb(no)
    # the bake finds every link's neighbours close and rusts them through: take most of the rust back to black scale
    lin = gk.to_linear(colour)
    rust = 0.7 * np.clip((lin[..., 0] - lin[..., 2]) / np.maximum(lin[..., 0], 1e-4), 0, 1) * (metal + rough > 0.61)
    x0, y0, x1, y1 = (int(round(v * size)) for v in GEAR['eyes'])
    rust[y0:y1, x0:x1] = 0
    colour = gk.to_srgb(lin * (1 - rust[..., None]) + np.array(SCALE) * rust[..., None])
    rough = rough * (1 - rust) + 0.62 * rust
    metal = metal * (1 - rust) + 0.30 * rust
    for name, patch in (('G_WaistCord', 'waistcord'), ('G_HeadCord', 'headcord')):
        ob = bpy.data.objects[name]
        ring = gk.coords(ob.data).reshape(-1, 6, 3).mean(1)
        length = float(np.linalg.norm(np.roll(ring, -1, 0) - ring, axis=1).sum())
        rope(colour, rough, normal, GEAR[patch], length, 0.022 if patch == 'waistcord' else 0.018)
    x0, y0, x1, y1 = (int(round(v * size)) for v in GEAR['eyes'])
    rough[y0:y1, x0:x1] = 0.12                # the eye's wet coat, which a game material has no layer for
    gk.write_png(TEX / 'T_Ogun_Gear_BaseColor.png', colour)
    gk.write_png(TEX / 'T_Ogun_Gear_Normal.png', normal)
    gk.write_png(TEX / 'T_Ogun_Gear_ORM.png', gk.orm(np.ones((size, size)), rough, metal))


def blade_textures(weapon):
    w, h = 1024, 512
    baked = list(weapon.objects)
    bc = filled('bake_ada_bc', w, h, (0.1, 0.1, 0.1), True)
    ro = filled('bake_ada_ro', w, h, (0.6, 0.6, 0.6), False)
    mt = filled('bake_ada_mt', w, h, (0, 0, 0), False)
    no = filled('bake_ada_no', w, h, (0.5, 0.5, 1.0), False)
    gk.bake_input(baked, bc, 'Base Color', samples=8, margin=4)
    gk.bake_input(baked, ro, 'Roughness', samples=8, margin=4)
    gk.bake_input(baked, mt, 'Metallic', samples=8, margin=4)
    gk.bake_pass(baked, no, 'NORMAL', samples=12, margin=4)
    gk.write_png(TEX / 'T_Ogun_Ada_BaseColor.png', rgb(bc))
    gk.write_png(TEX / 'T_Ogun_Ada_Normal.png', rgb(no))
    gk.write_png(TEX / 'T_Ogun_Ada_ORM.png', gk.orm(np.ones((h, w)), rgb(ro), rgb(mt)))


def frond_textures(col):
    """One leaflet for each column of the atlas, baked from the portrait's palm material at its true size."""
    size = 1024
    verts, faces, metres, atlas, tint, rib, tip = [], [], [], [], [], [], []
    dry = 0.06 / FROND_LONG
    for k in range(FROND_COLUMNS):
        for r, v in enumerate((1.0, dry, 0.0)):
            for c in (0, 1):
                verts.append(((k + c) * FROND_WIDE, v * FROND_LONG, 0.0))
                metres.append(((1 - v) * FROND_LONG, (c - 0.5) * FROND_WIDE))
                atlas.append(((k + c) / FROND_COLUMNS, v))
                tint.append(((k % 8) + 0.5) / 8)
                rib.append(float(k >= 8))
                tip.append(0.65 if r == 2 else 0.0)
        b = k * 6
        faces += [(b, b + 2, b + 3, b + 1), (b + 2, b + 4, b + 5, b + 3)]
    card = gk.new_object('BakeFronds', verts, faces, col, uv=np.array(metres))
    me = card.data
    layer = me.uv_layers.new(name='Atlas')
    loops = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', loops)
    layer.data.foreach_set('uv', np.array(atlas, np.float32)[loops].ravel())
    me.uv_layers['UVMap'].active_render = True      # the material reads the metres
    me.uv_layers.active = layer                     # the bake writes to the atlas
    for name, data in (('tint', tint), ('rib', rib), ('tip', tip)):
        gk.set_point_attr(me, name, data)
    me.materials.append(bpy.data.materials['Mariwo'])
    bc = filled('bake_frond_bc', size, size, (0.5, 0.55, 0.3), True)
    ro = filled('bake_frond_ro', size, size, (0.4, 0.4, 0.4), False)
    no = filled('bake_frond_no', size, size, (0.5, 0.5, 1.0), False)
    gk.bake_input([card], bc, 'Base Color', samples=8, margin=0)
    gk.bake_input([card], ro, 'Roughness', samples=8, margin=0)
    gk.bake_pass([card], no, 'NORMAL', samples=12, margin=0)
    bpy.data.objects.remove(card)
    # a frond lets light through, which a game's surface does not: a share of that light goes into its colour
    colour = gk.to_srgb(gk.to_linear(rgb(bc)) * 0.92 + np.array(THROUGH) * 0.08)
    gk.write_png(TEX / 'T_Ogun_Mariwo_BaseColor.png', colour)
    gk.write_png(TEX / 'T_Ogun_Mariwo_Normal.png', rgb(no))
    gk.write_png(TEX / 'T_Ogun_Mariwo_ORM.png', gk.orm(np.ones((size, size)), rgb(ro), np.zeros((size, size))))


def etu_textures():
    """One strip of his ẹ̀tù, four picks long, cut from the portrait's cloth maps so that it repeats."""
    size = 512
    colour = gk.to_linear(rgb(bpy.data.images['etu_color.png']))
    height = rgb(bpy.data.images['etu_height.png'])[..., 0]
    rows, cols = colour.shape[:2]                  # eleven strips up the map, six lots of four picks along it
    r0, r1, c1 = int(round(5 * rows / 11)), int(round(6 * rows / 11)), cols // 6
    colour = gk.resize(colour[r0:r1, :c1], size, size)
    height = gk.resize(height[r0:r1, :c1], size, size)[..., 0]
    # the plain weave under the pattern: eight threads to 5.2 mm, as the portrait's material lays it
    weave = rgb(bpy.data.images['weave_height.png'])[..., 0]
    y, x = np.mgrid[0:size, 0:size]
    n = weave.shape[0]
    thread = weave[(y * 20 * n // size) % n, (x * 19 * n // size) % n]
    colour = colour * (1 - 0.14 * thread[..., None] * (1 - np.array([0.34, 0.31, 0.25])))
    gk.write_png(TEX / 'T_Ogun_Etu_BaseColor.png', gk.to_srgb(colour))
    gk.write_png(TEX / 'T_Ogun_Etu_Normal.png', gk.normal_map(height * 0.75 + thread * 0.20, 5.6))
    gk.write_png(TEX / 'T_Ogun_Etu_ORM.png', np.tile(np.array([1.0, 0.84, 0.0]), (4, 4, 1)))


def hair_textures():
    """Close-cut coils as a repeating patch: small rings of hair catching the light over the dark between them."""
    size = 512
    rng = np.random.default_rng(41)
    height = np.zeros((size, size))
    k = np.arange(-5, 6)
    yy, xx = np.meshgrid(k, k, indexing='ij')
    for _ in range(9000):
        cx, cy, r = rng.uniform(0, size), rng.uniform(0, size), rng.uniform(2.2, 3.6)
        ring = np.exp(-((np.hypot(xx - (cx % 1), yy - (cy % 1)) - r) / 0.9) ** 2) * rng.uniform(0.5, 1.0)
        np.add.at(height, ((int(cy) + yy) % size, (int(cx) + xx) % size), ring)
    height = np.clip(height / 2.2, 0, 1)
    colour = np.array(COILS)[None, None] * (0.55 + 0.9 * height[..., None])
    gk.write_png(TEX / 'T_Ogun_Hair_BaseColor.png', gk.to_srgb(colour))
    gk.write_png(TEX / 'T_Ogun_Hair_Normal.png', gk.normal_map(height, 3.0))
    gk.write_png(TEX / 'T_Ogun_Hair_ORM.png', np.tile(np.array([1.0, 0.92, 0.0]), (4, 4, 1)))


def stage_textures():
    import time
    open_stage('30_parts.blend')
    game, weapon, high = (gk.collection(n) for n in ('Game', 'Weapon', 'High'))
    for ob in high.objects:
        ob.hide_render = True                  # the portrait's own parts must not shade the light ones
    body = bpy.data.objects['Body']
    which = sys.argv[sys.argv.index('--') + 1:]
    jobs = (('skin', lambda: skin_textures(body, [ob for ob in list(game.objects) + list(weapon.objects) if ob is not body and ob.type == 'MESH'])),
            ('gear', lambda: gear_textures(game)), ('blade', lambda: blade_textures(weapon)),
            ('fronds', lambda: frond_textures(game)), ('etu', etu_textures), ('hair', hair_textures))
    for name, job in jobs:
        if any(w.startswith('only=') for w in which) and f'only={name}' not in which:
            continue
        t = time.time()
        job()
        print('textures:', name, round(time.time() - t, 1), 's', flush=True)
    for path in sorted(TEX.glob('T_Ogun_*.png')):
        print(f'  {path.name:34} {path.stat().st_size / 1e6:6.2f} MB', flush=True)


# ----- assemble --------------------------------------------------------------

SPECULAR = dict(Skin=0.36, Hair=0.15)       # the portrait's own value for skin; coils barely shine


def game_material(name, two_sided=False):
    """A game material over its three maps: colour, normal, and occlusion, roughness and metal in one."""
    mat = bpy.data.materials.new('M_Ogun_' + name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bsdf.outputs[0], out.inputs['Surface'])
    bsdf.inputs['Specular IOR Level'].default_value = SPECULAR.get(name, 0.5)

    def image(kind, colour):
        node = nt.nodes.new('ShaderNodeTexImage')
        node.image = bpy.data.images.load(str(TEX / f'T_Ogun_{name}_{kind}.png'), check_existing=True)
        node.image.colorspace_settings.name = 'sRGB' if colour else 'Non-Color'
        return node
    nt.links.new(image('BaseColor', True).outputs['Color'], bsdf.inputs['Base Color'])
    bump = nt.nodes.new('ShaderNodeNormalMap')
    nt.links.new(image('Normal', False).outputs['Color'], bump.inputs['Color'])
    nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    split = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(image('ORM', False).outputs['Color'], split.inputs['Color'])
    nt.links.new(split.outputs['Green'], bsdf.inputs['Roughness'])
    nt.links.new(split.outputs['Blue'], bsdf.inputs['Metallic'])
    mat.use_backface_culling = not two_sided
    return mat


def stage_assemble():
    from mathutils import Vector
    open_stage('30_parts.blend')
    game, weapon = gk.collection('Game'), gk.collection('Weapon')
    rig = bpy.data.objects['Armature']
    body = bpy.data.objects['Body']
    names = [b.name for b in rig.data.bones]
    mats = {n: game_material(n, two_sided=n in ('Etu', 'Mariwo')) for n in ('Skin', 'Gear', 'Etu', 'Mariwo', 'Hair', 'Ada')}

    parts = [ob for ob in game.objects if ob.type == 'MESH']
    for ob in parts + list(weapon.objects):
        for layer in [u for u in ob.data.uv_layers if u.name != 'UVMap']:
            ob.data.uv_layers.remove(layer)
        ob.data.uv_layers['UVMap'].active_render = True
        if ob['slot'] in ('Gear', 'Ada'):
            # links, bangles, eyes and rivets were baked one unit apart so that only the first of each was drawn;
            # in the game they lie exactly over one another, with no large numbers for an engine to round
            uv = gk.loop_uv(ob.data)
            uv[:, 0] -= np.floor(uv[:, 0])
            gk.set_loop_uv(ob.data, uv)
        ob.data.materials.clear()
        ob.data.materials.append(mats[ob['slot']])
        gk.strip_attributes(ob.data)
    order = ['Body'] + sorted(ob.name for ob in parts if ob is not body)
    mesh = gk.join([bpy.data.objects[n] for n in order], body)
    mesh.name = mesh.data.name = 'SK_Ogun'
    mesh.parent = rig
    for m in mesh.modifiers:
        if m.type == 'ARMATURE':
            m.object = rig
    gk.set_weights(mesh, gk.weights(mesh, names), names)        # one clean table: four weights at most, summing to one

    # the àdá: its own mesh, held by a bone that carries its grip, blade along the bone and edge toward the bone's Z
    blade = gk.join(list(weapon.objects), bpy.data.objects['G_AdaBlade'])
    blade.name = blade.data.name = 'SM_Ogun_Ada'
    grip = blade.matrix_world.copy()
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    eb = rig.data.edit_bones.new('weapon_r')
    eb.head = grip.translation
    eb.tail = grip.translation + grip.to_3x3() @ Vector((0, 0, 0.10))
    eb.align_roll(grip.to_3x3() @ Vector((0, -1, 0)))
    eb.parent = rig.data.edit_bones['hand_r']
    eb.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    blade.parent = rig
    blade.parent_type = 'BONE'
    blade.parent_bone = 'weapon_r'
    bpy.context.view_layer.update()
    blade.matrix_world = grip

    for name in ('High', 'Weapon'):
        col = bpy.data.collections[name]
        for ob in list(col.objects):
            if ob is blade:
                gk.link(ob, game)
            else:
                bpy.data.objects.remove(ob)
        bpy.data.collections.remove(col)
    game.name = 'Ogun'
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

    for ob, bones in ((mesh, names), (blade, None)):
        print(ob.name, gk.mesh_report(ob, bones), flush=True)
    print('bones', len(rig.data.bones), 'root', [b.name for b in rig.data.bones if b.parent is None], flush=True)
    path = save_model()
    print('saved', path.name, round(path.stat().st_size / 1e6, 2), 'MB', flush=True)


# ----- animate ---------------------------------------------------------------

def stage_animate():
    """Two seconds of standing guard, breathing: one clip, to take an animation down the same road as the mesh."""
    from mathutils import Vector
    path = HERE / 'SK_Ogun.blend'
    bpy.ops.wm.open_mainfile(filepath=str(path))
    rig = bpy.data.objects['Armature']
    P = rig.pose.bones
    sc = bpy.context.scene
    sc.render.fps = 30
    sc.frame_start, sc.frame_end = 0, 60
    for old in [a for a in bpy.data.actions if a.name == 'A_Ogun_GuardIdle']:
        bpy.data.actions.remove(old)
    for pb in P:
        pb.rotation_mode = 'QUATERNION'
    action = bpy.data.actions.new('A_Ogun_GuardIdle')
    gk.use_action(rig, action)
    for frame in (0, 15, 30, 45, 60):
        breath = float(np.sin(2 * np.pi * frame / 60))
        gk.stance_guard(rig)
        for name, lift in (('spine_02', -1.4), ('spine_03', -1.2), ('clavicle_l', 1.0), ('clavicle_r', 1.0), ('head', 0.8)):
            across = P[name].matrix.to_3x3() @ Vector((1, 0, 0))
            gk.spin(P[name], across, lift * breath)
        for name in ('lowerarm_l', 'lowerarm_r'):
            gk.spin(P[name], (1, 0, 0), 1.5 * breath)
        gk.key_pose(rig, frame)
    for pb in P:
        if '_last' in pb:
            del pb['_last']
    action.use_fake_user = True
    rig.animation_data.action = None
    gk.clear_pose(rig)
    sc.frame_set(0)
    save_model()
    print('animated', action.name, [round(v) for v in action.frame_range], 'frames at', sc.render.fps, 'a second;',
          len(gk.fcurves(action)), 'curves', flush=True)


# ----- export ----------------------------------------------------------------

def stage_export():
    import json
    out = HERE / 'Export'
    bpy.ops.wm.open_mainfile(filepath=str(HERE / 'SK_Ogun.blend'))
    rig, mesh, blade = (bpy.data.objects[n] for n in ('Armature', 'SK_Ogun', 'SM_Ogun_Ada'))
    # the àdá leaves the hand for its own file: grip at the origin, blade along +Z
    blade.parent = None
    blade.matrix_world = Matrix.Identity(4)
    gk.to_centimetres(rig, [mesh, blade])
    sizes = {'SK_Ogun.fbx': gk.export_fbx(out / 'SK_Ogun.fbx', [rig, mesh]),
             'SM_Ogun_Ada.fbx': gk.export_fbx(out / 'SM_Ogun_Ada.fbx', [blade])}
    # each clip goes out on the skeleton alone, as Unreal takes an animation for a mesh it already has
    for action in [a for a in bpy.data.actions if a.name.startswith('A_Ogun_')]:
        gk.use_action(rig, action)
        sc = bpy.context.scene
        sc.frame_start, sc.frame_end = (int(round(v)) for v in action.frame_range)
        sizes[action.name + '.fbx'] = gk.export_fbx(out / (action.name + '.fbx'), [rig], animation=True)
    print('exported', {k: round(v / 1e6, 2) for k, v in sizes.items()}, 'MB', flush=True)
    report = [gk.fbx_report(out / name) for name in sizes]
    (out / 'check.json').write_text(json.dumps(report, indent=1))
    for r in report:
        print(json.dumps(r), flush=True)


# ----- renders ---------------------------------------------------------------

# which bone of the portrait's rig each bone of the game rig takes its move from
PORTRAIT = {'pelvis': 'root', 'spine_01': 'spine05', 'spine_02': 'spine04', 'spine_03': 'spine02', 'neck_01': 'neck01', 'head': 'head'}
for _s, _S in (('l', 'L'), ('r', 'R')):
    PORTRAIT.update({f'clavicle_{_s}': f'clavicle.{_S}', f'upperarm_{_s}': f'upperarm01.{_S}', f'lowerarm_{_s}': f'lowerarm01.{_S}',
                     f'hand_{_s}': f'wrist.{_S}', f'thigh_{_s}': f'upperleg01.{_S}', f'calf_{_s}': f'lowerleg01.{_S}',
                     f'foot_{_s}': f'foot.{_S}', f'ball_{_s}': f'toe1-1.{_S}'})
    for _k, _f in enumerate(('thumb', 'index', 'middle', 'ring', 'pinky'), 1):
        PORTRAIT.update({f'{_f}_0{_j}_{_s}': f'finger{_k}-{_j}.{_S}' for _j in (1, 2, 3)})
LOOK = (0.0, -0.05, 0.93)        # the middle of him, for the cameras


def portrait_pose(rig):
    moves = np.load(WORK / 'portrait_pose.npz')
    gk.apply_skin_pose(rig, {ours: moves[theirs] for ours, theirs in PORTRAIT.items() if theirs in moves.files})


def stage_portrait():
    """The portrait's own figure under the studio's light, from the camera the comparison uses."""
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    shown = set(bpy.data.collections['Figure'].objects) | {bpy.data.objects[n] for n in MACHETE}
    for ob in bpy.data.objects:
        ob.hide_render = ob not in shown
    cam = gk.studio(96)
    gk.shoot(WORK / 'portrait_view.png', cam, gk.around(LOOK, 28, 5.0), LOOK)
    gk.shoot(WORK / 'portrait_close.png', cam, gk.around((0, -0.05, 1.50), 20, 1.9), (0, -0.05, 1.50))


def stage_renders():
    out = HERE / 'Renders'
    out.mkdir(exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(HERE / 'SK_Ogun.blend'))
    rig, mesh = bpy.data.objects['Armature'], bpy.data.objects['SK_Ogun']
    cam = gk.studio(96)
    which = sys.argv[sys.argv.index('--') + 1:]

    def wanted(name):
        return not any(w.startswith('only=') for w in which) or f'only={name}' in which

    if wanted('views'):
        gk.sheet([gk.shoot(out / f'_view{k}.png', cam, gk.around(LOOK, turn, 5.0), LOOK) for k, turn in enumerate((0, 90, 180, 35))],
                 out / 'Ogun_Views.png')

    if wanted('wire'):
        clay = bpy.data.materials.new('Clay')
        clay.use_nodes = True
        clay.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.62, 0.62, 0.62, 1)
        clay.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.7
        ink = bpy.data.materials.new('Ink')
        ink.use_nodes = True
        ink.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.01, 0.01, 0.01, 1)
        copies = []
        for material, wire in ((clay, False), (ink, True)):
            ob = mesh.copy()
            ob.data = mesh.data.copy()
            mesh.users_collection[0].objects.link(ob)
            for slot in ob.material_slots:
                slot.material = material
            if wire:
                mod = ob.modifiers.new('Wire', 'WIREFRAME')
                mod.thickness = 0.0012
                mod.use_replace = True
            copies.append(ob)
        mesh.hide_render = True
        gk.sheet([gk.shoot(out / f'_wire{k}.png', cam, at, look) for k, (at, look) in enumerate((
            (gk.around(LOOK, 0, 5.0), LOOK), (gk.around(LOOK, 35, 5.0), LOOK),
            (gk.around((0, -0.05, 1.50), 20, 1.9), (0, -0.05, 1.50))))], out / 'Ogun_Wire.png')
        for ob in copies:
            bpy.data.objects.remove(ob)
        mesh.hide_render = False

    if wanted('poses'):
        shots = []
        for name, pose in (('portrait', portrait_pose), ('guard', gk.stance_guard), ('kick', gk.stance_kick)):
            pose(rig)
            shots.append(gk.shoot(out / f'_pose_{name}_a.png', cam, gk.around(LOOK, 28, 5.0), LOOK))
            shots.append(gk.shoot(out / f'_pose_{name}_b.png', cam, gk.around(LOOK, -75, 5.0), LOOK))
        gk.sheet(shots, out / 'Ogun_Poses.png')

    if wanted('compare'):
        portrait_pose(rig)
        mine = gk.shoot(out / '_compare_game.png', cam, gk.around(LOOK, 28, 5.0), LOOK)
        close = gk.shoot(out / '_close_game.png', cam, gk.around((0, -0.05, 1.50), 20, 1.9), (0, -0.05, 1.50))
        import shutil
        theirs = []
        for name in ('portrait_view.png', 'portrait_close.png'):
            if (WORK / name).exists():
                shutil.copy(WORK / name, out / ('_' + name))
                theirs.append(out / ('_' + name))
        if len(theirs) == 2:
            gk.sheet([theirs[0], mine, theirs[1], close], out / 'Ogun_Compare.png')
        else:
            gk.sheet([mine, close], out / 'Ogun_Compare.png')
    gk.clear_pose(rig)


STAGES = dict(body=stage_body, source=stage_source, parts=stage_parts, textures=stage_textures, assemble=stage_assemble,
              animate=stage_animate, export=stage_export, portrait=stage_portrait, renders=stage_renders)

if __name__ == '__main__':
    for stage in sys.argv[sys.argv.index('--') + 1:]:
        if stage in STAGES:                    # anything else is an option for a stage, such as only=skin
            print('=====', stage, flush=True)
            STAGES[stage]()
