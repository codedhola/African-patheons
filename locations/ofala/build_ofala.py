"""Build Ofala (Stage 21, the palace arena at Onitsha) as a game-ready Blender scene.

This uses the same pipeline as the Stormshrine. The mesh builder, UV packing,
texture generator, PNG writer, materials and validation all come from
../stormshrine/build_stormshrine.py, imported as `kit`. This script adds what
is specific to Ofala: the palace (multi-door walls, a hip roof with a ridge),
the dais, throne and canopy, the benches, figures, drums, the cannon, the shade
tree, the arena and a daylight preview rig.

    blender -b --factory-startup -P build_ofala.py -- [options]

Options (after the "--"):
    --out DIR        output folder (default: the folder holding this script)
    --render LIST    none | all | comma list of: front, side, threequarter,
                     threequarter_back, playerscale, detail, plan  (default: none)
    --samples N      Cycles samples for the renders     (default: 128)
    --res WxH        render size                         (default: 1600x900)
    --skip-textures  reuse the PNGs already in OUT/Textures
    --debug-normals  also render back-face checks (red = a face seen from behind)

Design source: 2d-threejs/stages/Stage21-Ofala.html (the SVG stage board) and
2d-threejs/stages/previews/Stage21-Ofala.png. SVG coordinates in comments come from that file.
README.md next to this script lists the assumptions.

Conventions: 1 Blender unit = 1 m, +Z up, the palace faces -Y. Every asset
mesh has identity transforms; their shared origin (0, 0, 0) is the centre of
the palace footprint at ground level. UV map "UVMap" is in metres (tiling
materials divide by their tile size); "UVLightmap" packs the same islands into 0-1.
"""

import argparse
import math
import os
import random
import sys
import time

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'stormshrine'))
import build_stormshrine as kit  # noqa: E402  (shared mesh / UV / texture / material toolkit)

MB, lathe, sweep, circle = kit.MB, kit.lathe, kit.sweep, kit.circle
box_mb, relief_stroke, plane_map, extrude_shape = kit.box_mb, kit.relief_stroke, kit.plane_map, kit.extrude_shape
bez, lin, translate, rot_z, C = kit.bez, kit.lin, kit.translate, kit.rot_z, kit.C

# ---------------------------------------------------------------------------
# Design constants (from the SVG)
# ---------------------------------------------------------------------------
# At 0.017 m per SVG px the seated chiefs come out life-size (1.07 m from the
# bench to the top of the cap) and the side doors 0.85 m wide by 2.68 m high.
PX = 0.017


def svg_x(px):
    """SVG x -> metres (palace centre line x=800)."""
    return (px - 800.0) * PX


def svg_h(py):
    """SVG y -> metres above the palace floor (wall foot y=644)."""
    return (644.0 - py) * PX


P = 'Ofala_'
PLINTH_H = 0.20            # assumption: low platform the palace stands on; the dais steps match it
APRON = 0.60
BASE_BEVEL = 0.04
HALF_W = 660 * PX          # 11.22: walls x 140..1460
OVERHANG = 40 * PX         # 0.68: eaves x 100..1500
HALF_D = 300 * PX - OVERHANG  # 4.42: the hips run 300 px (equal pitch), minus the overhang
WALL_T = 0.45
Z0 = PLINTH_H
WALL_H = svg_h(396)        # 4.216: wall top
Z1 = Z0 + WALL_H
EAVE_H = svg_h(404)        # 4.08: underside of the eave
RIDGE_H = svg_h(246)       # 6.766: ridge
XE, YE = HALF_W + OVERHANG, HALF_D + OVERHANG   # 11.9 x 5.1 eave half extents; ridge half length XE - YE = 6.8
DADO_H = svg_h(596)        # 0.816: red band, y 596..644
GREAT_HW = 84 * PX         # 1.428: great doorway x 716..884
GREAT_TOP = svg_h(452)     # 3.264
SIDE_ARCHES = [[(270, 500), (270, 482), (320, 482), (320, 500)],   # side doors x 270..320 and 1280..1330
               [(1280, 500), (1280, 482), (1330, 482), (1330, 500)]]
SIDE_SPRING = svg_h(500)   # 2.448 (apex 2.678)

STEP = 0.20                # dais: three tiers (x 620..980, 640..960, 664..936)
DAIS = [(180 * PX, 3.9), (160 * PX, 3.45), (136 * PX, 3.0)]   # (half width, depth from the platform front)
DAIS_BACK = -(HALF_D + APRON)          # -5.02, against the palace platform
DAIS_TOP = 3 * STEP
THRONE_Y = -6.25
CANOPY_X, CANOPY_Y = 105 * PX, -7.70   # posts x 690..700 and 900..910
# The board's canopy top (y 470) is 2.24 m above the dais and its valance hangs to 1.56 m,
# below a standing player's head. It is raised 0.31 m and the valance shortened so its
# lowest edge clears 2.10 m above the dais (assumption, for traversal).
VALANCE_CLEAR = 2.10
CANOPY_TOP = DAIS_TOP + 2.55                       # 3.15: top of the frame
VALANCE_DROP = (CANOPY_TOP - DAIS_TOP - VALANCE_CLEAR, 0.75 * (CANOPY_TOP - DAIS_TOP - VALANCE_CLEAR))   # middle, ends
BENCH_X, BENCH_HL, BENCH_Y, SEAT_H = 325 * PX, 135 * PX, -5.78, 0.42   # benches x 340..610 and 990..1260
CHIEF_X = [svg_x(x) for x in (364, 408, 452, 496, 540, 584)]
DRUMS = [(svg_x(207), -6.70, 0.357, 0.255, 1.09), (svg_x(251), -6.42, 0.255, 0.187, 0.82)]   # x, y, r bottom, r top, h
CANNON_POS, CANNON_YAW = (8.6, -10.8), math.radians(-25)
TREE_POS = (-9.6, -13.0)   # framing the left of the arena, as the board's foreground tree
ARENA_CENTRE = (0.0, -10.0)

HEX = dict(lime='#ece3d0', red='#b8241c', red_dark='#a01e18', black='#1a1410', thatch='#a8803e', earth='#c89a62',
           wood='#7a4a2a', wood_dark='#6a4424', gold='#e8c060', white='#f4efe4', skin='#4a2a18', hide='#e6d2aa',
           ivory='#e8dcc0', iron='#3a3a40', hills='#6a8a54', sky_top='#5f95c8', sky_mid='#7eb0d8',
           sky_low='#f4d8a4', cloud='#fff6e6')
CROWD = ['ClothCrimson', 'ClothBlue', 'ClothYellow', 'ClothGreen', 'ClothPurple']


# ---------------------------------------------------------------------------
# Textures
# ---------------------------------------------------------------------------
def tex_lime(T):
    """Limewashed plaster; three base colours share one surface: white walls, red dado, tan platform."""
    low, mid, fine, tone = T.noise(3.4), T.noise(2.2, 3), T.noise(0.8, 90), T.noise(3.0)
    brush = T.noise(1.6, 4, sx=6)                      # horizontal brush strokes
    F1, F2 = T.worley(30)
    crack = np.exp(-((F2 - F1) * T.n / 1.4) ** 2) * np.clip(T.noise(3.0) * 0.8 - 0.35, 0, 1)
    h = low * 1.2e-3 + mid * 0.4e-3 + brush * 0.25e-3 + fine * 0.06e-3 - crack * 0.6e-3
    var = ((1 + 0.05 * low + 0.03 * mid + 0.025 * brush + 0.02 * fine) * (1 - 0.35 * crack))[..., None]
    k = (np.clip(0.5 + 0.3 * tone, 0, 1) * 0.25)[..., None]
    cols = dict(BaseColor=(C('#ece3d0') * (1 - k) + C('#d6c9ae') * k) * var,
                BaseColorRed=(C('#b8241c') * (1 - k) + C('#9a2a1c') * k) * var,
                BaseColorTan=(C('#d2ad7a') * (1 - k) + C('#bd9462') * k) * var)
    rough = 0.86 + 0.04 * mid + 0.02 * fine + 0.05 * crack
    return cols, rough, h


def tex_thatch_gold(T):
    strands, clumps = T.noise(1.5, 6, sy=16), T.noise(2.6, 2, sy=5)
    fine, sweep_ = T.noise(1.0, 80, sy=24), T.noise(3.0, sy=3)
    s = 0.55 * strands + 0.35 * clumps + 0.22 * fine
    h = s * 3e-3
    k = np.clip(0.5 + 0.28 * s + 0.1 * sweep_, 0, 1)[..., None]
    dark, mid_, hi = C('#5e4220'), C(HEX['thatch']), C('#dab474')
    col = np.where(k < 0.5, dark + (mid_ - dark) * (k / 0.5), mid_ + (hi - mid_) * ((k - 0.5) / 0.5))
    rough = np.clip(0.8 - 0.06 * clumps + 0.04 * fine, 0.6, 0.95)
    return dict(BaseColor=col), rough, h


def tex_arena(T):
    """Beaten earth: compacted, scuffed, footprinted."""
    low, mid, fine, scuff = T.noise(3.0), T.noise(2.0, 5), T.noise(1.0, 120), T.noise(1.8, 6, sx=3)
    peb = T.pebbles(900, 1.0, 3.5)
    prints = T.pebbles(120, 3.0, 5.0)
    h = low * 3e-3 + mid * 1e-3 + fine * 0.12e-3 + peb * 1.5e-3 - prints * 1.2e-3
    col = C('#a87a46') + (C('#d8b07a') - C('#a87a46')) * np.clip(0.5 + 0.3 * mid + 0.15 * low, 0, 1)[..., None]
    col = col * (1 + 0.03 * fine)[..., None]
    col = col + (C('#8a6440') - col) * (np.clip(peb, 0, 1) * 0.4)[..., None]
    col = col * (1 - 0.12 * np.clip(prints, 0, 1))[..., None]
    rough = np.clip(0.9 + 0.03 * fine - 0.05 * np.clip(scuff, 0, 1), 0, 1)
    return dict(BaseColor=col), rough, h


def tex_grass(T):
    """Dry savanna grass beyond the arena."""
    blades, low, mid = T.noise(1.2, 40, sy=2.5), T.noise(3.0, 4), T.noise(2.0, 6)
    h = blades * 1.5e-3 + low * 0.8e-3
    col = C('#6f7a3a') + (C('#b0a05a') - C('#6f7a3a')) * np.clip(0.5 + 0.3 * mid + 0.25 * blades, 0, 1)[..., None]
    col = col * (1 + 0.05 * low)[..., None]
    rough = np.clip(0.88 + 0.04 * blades, 0, 1)
    return dict(BaseColor=col), rough, h


def tex_iron(T):
    low, mid, fine = T.noise(3.0), T.noise(2.0, 6), T.noise(1.0, 80)
    pits = T.pebbles(600, 0.8, 2.5)
    rust = np.clip(0.6 * low + 0.4 * mid - 0.6, 0, 1) ** 0.8
    h = low * 0.4e-3 + fine * 0.08e-3 - pits * 0.4e-3 + rust * 0.2e-3
    col = C(HEX['iron']) * (1 + 0.08 * mid)[..., None]
    col = col + (C('#6a3a20') - col) * rust[..., None]
    rough = np.clip(0.48 + 0.1 * mid + 0.35 * rust + 0.1 * pits, 0, 1)
    return dict(BaseColor=col), rough, h


def tex_cloth(T):
    """Plain weave for all the cloth (robes, curtains, canopy): normal and roughness only."""
    g = (np.arange(T.n) + 0.5) / T.n
    X, Y = np.meshgrid(g, g)
    threads = 64
    warp = 0.5 + 0.5 * np.cos(2 * np.pi * threads * X)
    weft = 0.5 + 0.5 * np.cos(2 * np.pi * threads * Y)
    over = np.sin(np.pi * threads * X) * np.sin(np.pi * threads * Y) > 0
    h = np.where(over, warp, weft) * 0.25e-3 + T.noise(2.0, 4) * 0.3e-3
    rough = np.clip(0.86 + 0.04 * T.noise(1.0, 40), 0, 1)
    return None, rough, h


def tex_leaves(T):
    F1, F2 = T.worley(260)
    leaf = np.clip(1 - F1 * T.n / 14, 0, 1)
    gap = np.exp(-((F2 - F1) * T.n / 1.5) ** 2)
    low, mid = T.noise(3.0), T.noise(2.0, 6)
    h = leaf * 4e-3 - gap * 3e-3
    k = np.clip(0.5 + 0.35 * mid + 0.25 * leaf - 0.4 * gap, 0, 1)[..., None]
    col = (C('#24401c') + (C('#5e8c42') - C('#24401c')) * k) * (1 + 0.1 * low)[..., None]
    rough = np.clip(0.62 - 0.1 * leaf + 0.15 * gap, 0, 1)
    return dict(BaseColor=col), rough, h


def tex_bark_live(T):
    fiss, plates, fine = T.noise(1.6, 6, sy=10), T.noise(2.4, 3, sy=3), T.noise(1.0, 60)
    ridge = 1 - np.abs(np.clip(fiss, -2.5, 2.5)) / 2.5
    h = ridge * 3e-3 + plates * 1e-3 + fine * 0.2e-3
    k = np.clip(0.5 + 0.3 * plates + 0.4 * (ridge - 0.5), 0, 1)[..., None]
    col = C('#3e3024') + (C('#7a6a58') - C('#3e3024')) * k
    rough = np.clip(0.86 + 0.04 * fine, 0, 1)
    return dict(BaseColor=col), rough, h


TEXTURE_SETS = {
    # name: (generator, size px, tile m, seed)
    'LimePlaster': (tex_lime, 1024, 2.0, 21),
    'Thatch': (tex_thatch_gold, 1024, 2.0, 22),
    'ArenaEarth': (tex_arena, 1024, 4.0, 23),
    'Grass': (tex_grass, 1024, 6.0, 24),
    'Wood': (lambda T: (dict(zip(('BaseColor', 'Roughness', 'Height'), kit.tex_wood(T, HEX['wood'], '#4a2c18')))), 512, 1.0, 25),
    'WoodDark': (lambda T: (dict(zip(('BaseColor', 'Roughness', 'Height'), kit.tex_wood(T, HEX['wood_dark'], '#3a2414')))), 512, 1.0, 26),
    'Iron': (tex_iron, 512, 1.0, 27),
    'Cloth': (tex_cloth, 512, 0.5, 28),
    'Leaves': (tex_leaves, 512, 2.0, 29),
    'Bark': (tex_bark_live, 512, 1.5, 30),
}


def generate_textures(tex_dir, skip):
    os.makedirs(tex_dir, exist_ok=True)
    out = {}
    for name, (fn, n, tile, seed) in TEXTURE_SETS.items():
        T = None
        if not skip:
            T = kit.TexGen(n, tile, seed)
            res = fn(T)
            if isinstance(res, dict):               # kit.tex_wood returns (colour, roughness, height)
                cols, rough, h = dict(BaseColor=res['BaseColor']), res['Roughness'], res['Height']
            else:
                cols, rough, h = res
        path = lambda m: os.path.join(tex_dir, 'T_Ofala_%s_%s.png' % (name, m))
        maps = {}
        if T is not None:
            t0 = time.time()
            for m, col in (cols or {}).items():
                kit.write_png(path(m), kit.to_u8(kit.lin_to_srgb(col)))
            kit.write_png(path('Roughness'), kit.to_u8(rough))
            kit.write_png(path('Normal'), kit.to_u8(T.normal(h)))
            print('  texture %-12s %4d px  %.1fs' % (name, n, time.time() - t0))
        for m in ('BaseColor', 'BaseColorRed', 'BaseColorTan', 'Roughness', 'Normal'):
            if os.path.exists(path(m)):
                maps[m] = path(m)
        out[name] = (maps, tile)
    return out


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------
def build_materials(tex):
    def T(s, m):
        return tex[s][0][m]

    def tile(s):
        return tex[s][1]
    mk = kit.make_material
    lp = 'LimePlaster'
    mk(P + 'LimePlaster', T(lp, 'BaseColor'), T(lp, 'Roughness'), T(lp, 'Normal'), tile(lp), viewport=lin(HEX['lime']))
    mk(P + 'RedDado', T(lp, 'BaseColorRed'), T(lp, 'Roughness'), T(lp, 'Normal'), tile(lp), viewport=lin(HEX['red']))
    mk(P + 'TanPlaster', T(lp, 'BaseColorTan'), T(lp, 'Roughness'), T(lp, 'Normal'), tile(lp), viewport=lin('#d2ad7a'))
    mk(P + 'PaintBlack', HEX['black'], 0.8, T(lp, 'Normal'), tile(lp), normal_strength=0.5)
    mk(P + 'PaintRed', HEX['red'], 0.75, T(lp, 'Normal'), tile(lp), normal_strength=0.5)
    for name, s in (('Thatch', 'Thatch'), ('Arena', 'ArenaEarth'), ('Grass', 'Grass'), ('Wood', 'Wood'),
                    ('WoodDark', 'WoodDark'), ('Leaves', 'Leaves'), ('Bark', 'Bark')):
        mk(P + name, T(s, 'BaseColor'), T(s, 'Roughness'), T(s, 'Normal'), tile(s))
    mk(P + 'Iron', T('Iron', 'BaseColor'), T('Iron', 'Roughness'), T('Iron', 'Normal'), tile('Iron'), metallic=0.85,
       viewport=lin(HEX['iron']))
    mk(P + 'Gold', HEX['gold'], 0.32, metallic=1.0)
    for name, hexc in (('ClothRed', HEX['red']), ('ClothRedDark', HEX['red_dark']), ('ClothWhite', HEX['white']),
                       ('ClothYellow', '#f2c230'), ('ClothGreen', '#3f7a46'), ('ClothBlue', '#2a4a9a'),
                       ('ClothPurple', '#8a3a8a'), ('ClothCrimson', '#c8302a')):
        mk(P + name, hexc, T('Cloth', 'Roughness'), T('Cloth', 'Normal'), tile('Cloth'), sheen=0.35, normal_strength=0.6,
           viewport=lin(hexc))
    mk(P + 'Skin', HEX['skin'], 0.55, spec=0.4)
    mk(P + 'Hide', HEX['hide'], 0.55)
    mk(P + 'Ivory', HEX['ivory'], 0.35, coat=0.3)
    trg = mk(P + 'TriggerVolume', '#40ff80', 1.0, viewport=(0.2, 1.0, 0.4))
    trg.diffuse_color = (0.2, 1.0, 0.4, 0.25)


# ---------------------------------------------------------------------------
# Small geometry helpers
# ---------------------------------------------------------------------------
def ellipsoid(mb, centre, radii, mat, segs=10, rings=6, smooth=True):
    prof = [(0.0, -1.0)] + [(math.sin(math.pi * k / rings), -math.cos(math.pi * k / rings)) for k in range(1, rings)] \
        + [(0.0, 1.0)]
    sub = MB()
    lathe(sub, prof, segs, mat, smooth=smooth)
    sub.transform(translate(*centre) @ Matrix.Diagonal((radii[0], radii[1], radii[2], 1.0)))
    mb.merge(sub)
    return sub


def cylinder(mb, r, z0, z1, mat, segs=12, top=True, bottom=True):
    prof = ([(0.0, z0)] if bottom else []) + [(r, z0), (r, z1)] + ([(0.0, z1)] if top else [])
    lathe(mb, prof, segs, mat, smooth=True)


def facing(pos, target):
    """Yaw that turns a figure built facing -Y toward target."""
    dx, dy = target[0] - pos[0], target[1] - pos[1]
    return math.atan2(dx, -dy)


def cloth_panel(mb, x0, x1, zb, zt, y0, fold, thick, mat, nu=24, nv=8):
    """Closed cloth slab hanging in the X-Z plane, front facing -Y.
    zb(x), zt(x): bottom and top edges; fold(x, z): offset along Y."""
    F, K = [], []
    for i in range(nu + 1):
        x = x0 + (x1 - x0) * i / nu
        fr, bk = [], []
        for j in range(nv + 1):
            z = zb(x) + (zt(x) - zb(x)) * j / nv
            y = y0 + fold(x, z)
            fr.append(mb.vert((x, y - thick / 2, z)))
            bk.append(mb.vert((x, y + thick / 2, z)))
        F.append(fr)
        K.append(bk)
    uvf = lambda i, j: (mb.v[F[i][j]].x, mb.v[F[i][j]].z)
    fi, bi, ei = mb.island(), mb.island(), mb.island()
    for i in range(nu):
        for j in range(nv):
            mb.face([F[i][j], F[i + 1][j], F[i + 1][j + 1], F[i][j + 1]],
                    [uvf(i, j), uvf(i + 1, j), uvf(i + 1, j + 1), uvf(i, j + 1)], mat, True, fi)
            mb.face([K[i][j], K[i][j + 1], K[i + 1][j + 1], K[i + 1][j]],
                    [uvf(i, j), uvf(i, j + 1), uvf(i + 1, j + 1), uvf(i + 1, j)], mat, True, bi)
    t = thick
    for i in range(nu):   # bottom and top edges
        a, b = mb.v[F[i][0]].x, mb.v[F[i + 1][0]].x
        mb.face([F[i][0], K[i][0], K[i + 1][0], F[i + 1][0]], [(a, 0), (a, t), (b, t), (b, 0)], mat, False, ei)
        mb.face([F[i][nv], F[i + 1][nv], K[i + 1][nv], K[i][nv]], [(a, 1), (b, 1), (b, 1 + t), (a, 1 + t)], mat, False, ei)
    for j in range(nv):   # left and right edges
        a, b = mb.v[F[0][j]].z, mb.v[F[0][j + 1]].z
        mb.face([F[0][j], F[0][j + 1], K[0][j + 1], K[0][j]], [(5, a), (5, b), (5 + t, b), (5 + t, a)], mat, False, ei)
        a, b = mb.v[F[nu][j]].z, mb.v[F[nu][j + 1]].z
        mb.face([F[nu][j], K[nu][j], K[nu][j + 1], F[nu][j + 1]], [(7, a), (7 + t, a), (7 + t, b), (7, b)], mat, False, ei)
    return mb


# ---------------------------------------------------------------------------
# The palace
# ---------------------------------------------------------------------------
def build_base(coll):
    """Ofala_Base: the 0.20 m platform under the palace."""
    bm = bmesh.new()
    hx, hy = HALF_W + APRON, HALF_D + APRON
    c = [(-hx, -hy, 0), (hx, -hy, 0), (hx, hy, 0), (-hx, hy, 0), (-hx, -hy, PLINTH_H), (hx, -hy, PLINTH_H),
         (hx, hy, PLINTH_H), (-hx, hy, PLINTH_H)]
    v = [bm.verts.new(p) for p in c]
    for f in ((4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):   # no underside
        bm.faces.new([v[i] for i in f])
    bm.edges.ensure_lookup_table()
    edges = [e for e in bm.edges if len(e.link_faces) == 2]
    bmesh.ops.bevel(bm, geom=edges, offset=BASE_BEVEL, offset_type='OFFSET', segments=2, profile=0.5, affect='EDGES',
                    clamp_overlap=True)
    return kit.bm_to_object(bm, P + 'Base', coll, P + 'TanPlaster')


def door_list():
    """Doors on the front wall, left to right: kind, x0, x1, top z, arch points."""
    doors = []
    for arch in SIDE_ARCHES:
        pts = [(svg_x(x), Z0 + svg_h(y)) for x, y in (bez(arch, k / 10) for k in range(11))]
        doors.append(dict(kind='arch', x0=pts[0][0], x1=pts[-1][0], top=Z0 + SIDE_SPRING, arch=pts))
    doors.insert(1, dict(kind='rect', x0=-GREAT_HW, x1=GREAT_HW, top=Z0 + GREAT_TOP, arch=None))
    return doors


def build_walls(coll):
    """Ofala_Walls: 0.45 m limewashed walls with a red dado, two arched side doors and
    the great doorway; open at the top (under the roof) and bottom (on the platform)."""
    mb = MB()
    white, red = P + 'LimePlaster', P + 'RedDado'
    doors = door_list()
    rows = sorted({Z0, Z0 + DADO_H, Z0 + SIDE_SPRING, Z0 + GREAT_TOP, Z1})
    eps = 1e-6

    def outline(hx, hy):
        """CCW plan outline with door columns on the front: (x, y, kind, door, z_bottom)."""
        pts = [(-hx, -hy, 'full', None, Z0)]
        for di, d in enumerate(doors):
            pts.append((d['x0'], -hy, 'edge', di, d['top']))
            if d['arch']:
                pts += [(x, -hy, 'arch', di, z) for x, z in d['arch'][1:-1]]
            pts.append((d['x1'], -hy, 'edge', di, d['top']))
        pts += [(hx, -hy, 'full', None, Z0), (hx, hy, 'full', None, Z0), (-hx, hy, 'full', None, Z0)]
        return pts

    def surface(pts, inward, mat_fn):
        isl = mb.island()
        cols = []
        for x, y, kind, di, zb in pts:
            zs = rows if kind != 'arch' else [zb] + [r for r in rows if r > zb + eps]
            cols.append({z: mb.vert((x, y, z)) for z in zs})
        n = len(pts)
        u = [0.0]
        for k in range(n):
            a, b = pts[k], pts[(k + 1) % n]
            u.append(u[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        for k in range(n):
            k1 = (k + 1) % n
            A, B = pts[k], pts[k1]
            in_door = (A[3] is not None and A[3] == B[3] and not (A[2] == 'edge' and B[2] == 'edge' and
                                                                  doors[A[3]]['arch'] and A[0] > B[0]))
            if in_door and A[0] < B[0]:
                ba = A[4] if A[2] != 'full' else Z0
                bb = B[4] if B[2] != 'full' else Z0
                ups = [r for r in rows if r > max(ba, bb) + eps]
                bands = [((ba, bb), (ups[0], ups[0]))] + [((ups[i], ups[i]), (ups[i + 1], ups[i + 1]))
                                                         for i in range(len(ups) - 1)]
            else:
                bands = [((rows[i], rows[i]), (rows[i + 1], rows[i + 1])) for i in range(len(rows) - 1)]
            for (a0, b0), (a1, b1) in bands:
                quad = [cols[k][a0], cols[k1][b0], cols[k1][b1], cols[k][a1]]
                uvq = [(u[k], a0), (u[k + 1], b0), (u[k + 1], b1), (u[k], a1)]
                if inward:
                    quad, uvq = quad[::-1], uvq[::-1]
                mb.face(quad, uvq, mat_fn(max(a1, b1)), False, isl)
        return cols

    paint = lambda ztop: red if ztop <= Z0 + DADO_H + eps else white
    outer_pts = outline(HALF_W, HALF_D)
    oc = surface(outer_pts, False, paint)
    inner_pts = outline(HALF_W - WALL_T, HALF_D - WALL_T)
    ic = surface(inner_pts, True, lambda z: white)

    # door reveals: jambs, arch soffits and the great doorway's head
    t = WALL_T
    for di, d in enumerate(doors):
        oi = [k for k, p in enumerate(outer_pts) if p[3] == di]
        ii = [k for k, p in enumerate(inner_pts) if p[3] == di]
        jam_rows = [r for r in rows if r <= d['top'] + eps]
        for side, (ko, kin) in (('left', (oi[0], ii[0])), ('right', (oi[-1], ii[-1]))):
            O, I = oc[ko], ic[kin]
            isl = mb.island()                          # one island per jamb: u across the wall, v up
            for r0, r1 in zip(jam_rows, jam_rows[1:]):
                uv = [(0, r0), (t, r0), (t, r1), (0, r1)]
                quad = [O[r0], I[r0], I[r1], O[r1]] if side == 'left' else [I[r0], O[r0], O[r1], I[r1]]
                mb.face(quad, uv, paint(r1), False, isl)
        # the head of the opening, edge to edge through the wall; v runs along the arch
        isl = mb.island()
        seq_o = [oc[k] for k in oi]
        seq_i = [ic[k] for k in ii]
        bottoms = [outer_pts[k][4] for k in oi]
        s_acc = 0.0
        for k in range(len(seq_o) - 1):
            za, zb = bottoms[k], bottoms[k + 1]
            seg = math.hypot(outer_pts[oi[k + 1]][0] - outer_pts[oi[k]][0], zb - za)
            mb.face([seq_o[k][za], seq_i[k][za], seq_i[k + 1][zb], seq_o[k + 1][zb]],
                    [(0, s_acc), (t, s_acc), (t, s_acc + seg), (0, s_acc + seg)], white, False, isl)
            s_acc += seg
    return kit.mb_to_object(mb, P + 'Walls', coll)


def rect_pts(hx, hy, nx, ny):
    """Rectangle points CCW from above, starting at the front-left corner; fixed count 2*(nx+ny)."""
    pts = [(-hx + 2 * hx * k / nx, -hy) for k in range(nx)]
    pts += [(hx, -hy + 2 * hy * k / ny) for k in range(ny)]
    pts += [(hx - 2 * hx * k / nx, hy) for k in range(nx)]
    pts += [(-hx, hy - 2 * hy * k / ny) for k in range(ny)]
    return pts


def build_roof(coll):
    """Ofala_Roof: the great thatched hip roof (SVG 100,404 - 400,246 - 1200,246 - 1500,404).
    Equal pitch on all four sides, so the hip ends run 300 px like the drawing; the two
    drawn course lines (y 360 and 306) are stepped courses; soffit back to the wall
    line and a flat ceiling inside."""
    mb = MB()
    rnd = random.Random(31)
    th, ceil = P + 'Thatch', P + 'LimePlaster'
    NX, NY = 28, 12
    npt = 2 * (NX + NY)
    z_eb = Z0 + EAVE_H
    z_et = z_eb + 0.22
    z_rg = Z0 + RIDGE_H
    lip = 0.06
    courses = [0.0, (404 - 360) / 158.0, (404 - 306) / 158.0]

    def ring(t, z_off, jitter=0.0):
        d = t * YE
        z = z_et + t * (z_rg - z_et) + z_off
        return (t, z, [mb.vert((x, y, z + (rnd.uniform(-jitter, jitter) if jitter else 0.0)))
                       for x, y in rect_pts(XE - d, YE - d, NX, NY)])
    ring_eb = [mb.vert((x, y, z_eb)) for x, y in rect_pts(XE, YE, NX, NY)]
    tops = [ring(0.0, lip)]
    for t in courses[1:]:
        tops.append(ring(t, 0.0))
        tops.append(ring(t, lip * rnd.uniform(0.85, 1.2), jitter=0.02))
    hx_r = XE - YE
    ridge = [mb.vert((-hx_r + 2 * hx_r * k / NX, 0.0, z_rg)) for k in range(NX + 1)]

    def to_ridge(i):
        if i < NX:
            return ridge[i]
        if i < NX + NY:
            return ridge[NX]
        if i < 2 * NX + NY:
            return ridge[NX - (i - NX - NY)]
        return ridge[0]

    def side_of(i):
        return 'front' if i < NX else 'right' if i < NX + NY else 'back' if i < 2 * NX + NY else 'left'
    side_isl = {s: mb.island() for s in ('front', 'right', 'back', 'left')}
    proj = dict(front=lambda p: p.x, back=lambda p: -p.x, right=lambda p: p.y, left=lambda p: -p.y)
    line = [(YE * (1 - t), z) for t, z, _ in tops] + [(0.0, z_rg)]
    vpos = [0.0]
    for a, b in zip(line, line[1:]):
        vpos.append(vpos[-1] + math.dist(a, b))
    for r, (_, _, A) in enumerate(tops):
        last = r == len(tops) - 1
        for i in range(npt):
            j = (i + 1) % npt
            s = side_of(i)
            pr = proj[s]
            va, vb = vpos[r], vpos[r + 1]
            ua, ua1 = pr(mb.v[A[i]]), pr(mb.v[A[j]])
            if last:
                ci, di_ = to_ridge(j), to_ridge(i)
                if ci == di_:
                    mb.face([A[i], A[j], ci], [(ua, va), (ua1, va), ((ua + ua1) / 2, vb)], th, False, side_isl[s])
                else:
                    mb.face([A[i], A[j], ci, di_], [(ua, va), (ua1, va), (pr(mb.v[ci]), vb), (pr(mb.v[di_]), vb)], th,
                            False, side_isl[s])
            else:
                Bv = tops[r + 1][2]
                mb.face([A[i], A[j], Bv[j], Bv[i]],
                        [(ua, va), (ua1, va), (pr(mb.v[Bv[j]]), vb), (pr(mb.v[Bv[i]]), vb)], th, False, side_isl[s])
    # fascia, soffit and ceiling
    top0 = tops[0][2]
    fi, si, ci_ = mb.island(), mb.island(), mb.island()
    wl = [mb.vert((x, y, Z1)) for x, y in rect_pts(HALF_W, HALF_D, NX, NY)]
    acc = 0.0
    for k in range(npt):
        k1 = (k + 1) % npt
        d = (mb.v[ring_eb[k1]] - mb.v[ring_eb[k]]).length
        mb.face([ring_eb[k], ring_eb[k1], top0[k1], top0[k]],
                [(acc, z_eb), (acc + d, z_eb), (acc + d, z_et + lip), (acc, z_et + lip)], th, False, fi)
        mb.face([ring_eb[k], wl[k], wl[k1], ring_eb[k1]],
                [(acc, 0), (acc, OVERHANG), (acc + d, OVERHANG), (acc + d, 0)], th, False, si)
        acc += d
    cen = mb.vert((0.0, 0.0, Z1))
    for k in range(npt):
        k1 = (k + 1) % npt
        a, b = mb.v[wl[k]], mb.v[wl[k1]]
        mb.face([cen, wl[k1], wl[k]], [(0, 0), (b.x, b.y), (a.x, a.y)], ceil, False, ci_)
    return kit.mb_to_object(mb, P + 'Roof', coll)


def build_fringe(coll):
    """Ofala_RoofFringe: the sawtooth thatch fringe along the eave (SVG pattern 'fringe',
    triangles 14 px wide and 19 px deep), a thin band whose top tucks into the fascia."""
    mb = MB()
    mat = P + 'Thatch'
    z_top = Z0 + EAVE_H + 0.05
    spacing = 0.13
    nx, ny = int(round(2 * XE / spacing)), int(round(2 * YE / spacing))
    rnd = random.Random(5)
    outer = rect_pts(XE + 0.012, YE + 0.012, nx, ny)
    inner = rect_pts(XE - 0.012, YE - 0.012, nx, ny)
    n = len(outer)
    drop = [0.32 * rnd.uniform(0.85, 1.1) if k % 2 == 0 else 0.07 for k in range(n)]
    ot = [mb.vert((x, y, z_top)) for x, y in outer]
    ob = [mb.vert((x, y, Z0 + EAVE_H - drop[k])) for k, (x, y) in enumerate(outer)]
    it = [mb.vert((x, y, z_top)) for x, y in inner]
    ib = [mb.vert((x, y, Z0 + EAVE_H - drop[k])) for k, (x, y) in enumerate(inner)]
    oi, ii, bi = mb.island(), mb.island(), mb.island()
    acc = 0.0
    for k in range(n):
        k1 = (k + 1) % n
        d = math.dist(outer[k], outer[k1])
        zb0, zb1 = mb.v[ob[k]].z, mb.v[ob[k1]].z
        mb.face([ob[k], ob[k1], ot[k1], ot[k]], [(acc, zb0), (acc + d, zb1), (acc + d, z_top), (acc, z_top)], mat, False, oi)
        mb.face([ib[k], it[k], it[k1], ib[k1]], [(acc, zb0), (acc, z_top), (acc + d, z_top), (acc + d, zb1)], mat, False, ii)
        mb.face([ob[k], ib[k], ib[k1], ob[k1]], [(acc, 0), (acc, 0.024), (acc + d, 0.024), (acc + d, 0)], mat, False, bi)
        acc += d
    return kit.mb_to_object(mb, P + 'RoofFringe', coll)


def build_wall_paint(coll):
    """Ofala_WallPaint: the black zigzag frieze under the eaves and the red line below it
    (SVG y 424..440 and 450), on the front either side of the canopy (x 150..670 and
    930..1450). The unseen side and back walls carry the same band (assumption)."""
    mb = MB()
    black, red = P + 'PaintBlack', P + 'PaintRed'
    z_lo, z_hi, z_line = Z0 + svg_h(440), Z0 + svg_h(424), Z0 + svg_h(450)
    half = 20 * PX                                      # zigzag half period (20 px)

    def band(fm, s0, s1):
        n = int((s1 - s0) / half)
        pts = [(s0 + k * half, z_lo if k % 2 == 0 else z_hi) for k in range(n + 1)]
        relief_stroke(mb, pts, 0.06, 0.006, fm, black)
        relief_stroke(mb, [(s0, z_line), (s0 + n * half, z_line)], 0.04, 0.005, fm, red)
    front = plane_map((0, -HALF_D, 0), (1, 0, 0), (0, 0, 1))
    band(front, svg_x(150), svg_x(670))
    band(front, svg_x(930), svg_x(1450))
    band(plane_map((0, HALF_D, 0), (-1, 0, 0), (0, 0, 1)), -HALF_W + 0.17, HALF_W - 0.17)
    for sign in (1, -1):
        band(plane_map((sign * HALF_W, 0, 0), (0, sign, 0), (0, 0, 1)), -HALF_D + 0.15, HALF_D - 0.15)
    return kit.mb_to_object(mb, P + 'WallPaint', coll)


def build_doorway(coll):
    """Ofala_DoorLintel: the wooden lintel over the great doorway (SVG rect 700,438 200x18).
    Ofala_DoorCurtains: the closed red curtains inside it (x 724..876), folded; a separate
    object so a game can draw them open or turn off their collision."""
    mb = MB()
    zb, zt = Z0 + svg_h(456), Z0 + svg_h(438)
    box_mb(mb, -100 * PX, 100 * PX, -HALF_D - 0.12, -HALF_D + 0.02, zb, zt, P + 'WoodDark')
    lintel = kit.mb_to_object(mb, P + 'DoorLintel', coll)
    cur = MB()
    y_c = -HALF_D + 0.20
    for x0, x1, mat, ph in ((-GREAT_HW + 0.008, -0.004, P + 'ClothRed', 0.0), (0.004, GREAT_HW - 0.008, P + 'ClothRedDark', 1.3)):
        cloth_panel(cur, x0, x1, lambda x: Z0 + 0.01, lambda x: Z0 + GREAT_TOP - 0.01, y_c,
                    lambda x, z, ph=ph: 0.035 * math.sin(2 * math.pi * x / 0.24 + ph), 0.012, mat, nu=24, nv=6)
    return lintel, kit.mb_to_object(cur, P + 'DoorCurtains', coll)


# ---------------------------------------------------------------------------
# Dais, throne, canopy, benches
# ---------------------------------------------------------------------------
def build_dais(coll):
    """Ofala_Dais: three 0.20 m tiers in front of the great doorway; the first is level with the platform."""
    mb = MB()
    for k, (hw, depth) in enumerate(DAIS):
        skip = ('bottom', 'back') if k == 0 else ('bottom',)
        back = DAIS_BACK + (BASE_BEVEL if k == 0 else 0.0)   # tier 1 runs over the platform's bevel
        box_mb(mb, -hw, hw, DAIS_BACK - depth, back, k * STEP, (k + 1) * STEP, P + 'TanPlaster', skip=skip)
    return kit.mb_to_object(mb, P + 'Dais', coll)


def build_throne(coll):
    """Ofala_Throne: the empty carved throne (SVG x 758..842, y 505..602): seat block, red
    cushion, tall back with a rounded top, gold knob and two gold lines."""
    mb = MB()
    wood, red, gold = P + 'Wood', P + 'ClothRed', P + 'Gold'
    z = DAIS_TOP
    seat_top = z + svg_h(578) - svg_h(602)
    box_mb(mb, -40 * PX, 40 * PX, THRONE_Y - 0.36, THRONE_Y + 0.38, z, seat_top, wood, skip=('bottom',))
    box_mb(mb, -34 * PX, 34 * PX, THRONE_Y - 0.32, THRONE_Y + 0.30, seat_top, seat_top + svg_h(566) - svg_h(578), red,
           skip=('bottom',))
    back = [(svg_x(x), z + svg_h(y) - svg_h(602)) for x, y in
            [(770, 603)] + kit.bez_path([((770, 520), (770, 500), (830, 500), (830, 520))], 10) + [(830, 603)]]
    sub = MB()
    extrude_shape(sub, back, 0.12, wood, wood)
    y_back = THRONE_Y + 0.40
    sub.transform(translate(0, y_back, 0))
    mb.merge(sub)
    front = plane_map((0, y_back - 0.06, 0), (1, 0, 0), (0, 0, 1))
    for y, x0, x1 in ((530, 780, 820), (546, 782, 818)):
        relief_stroke(mb, [(svg_x(x0), z + svg_h(y) - svg_h(602)), (svg_x(x1), z + svg_h(y) - svg_h(602))], 0.04, 0.008,
                      front, gold)
    ellipsoid(mb, (0, y_back - 0.07, z + svg_h(512) - svg_h(602)), (0.12, 0.08, 0.12), gold, segs=14, rings=8)
    return kit.mb_to_object(mb, P + 'Throne', coll)


def build_canopy(coll):
    """Ofala_Canopy: two posts (SVG x 690..700, 900..910), a frame back to the wall, a red
    cloth roof and the red valance that hangs lower in the middle (y 470..510)."""
    mb = MB()
    wood, red = P + 'WoodDark', P + 'ClothRed'
    top = CANOPY_TOP
    for sx in (-1, 1):
        x = sx * CANOPY_X
        box_mb(mb, x - 0.08, x + 0.08, CANOPY_Y - 0.08, CANOPY_Y + 0.08, DAIS_TOP, top + 0.12, wood, skip=('bottom',))
        box_mb(mb, x - 0.06, x + 0.06, CANOPY_Y, -HALF_D + 0.02, top - 0.04, top + 0.10, wood)   # starts inside the post
    box_mb(mb, -CANOPY_X - 0.11, CANOPY_X + 0.11, CANOPY_Y - 0.06, CANOPY_Y + 0.06, top - 0.03, top + 0.09, wood)
    box_mb(mb, -CANOPY_X, CANOPY_X, -HALF_D - 0.12, -HALF_D + 0.03, top - 0.02, top + 0.08, wood)   # ledger on the wall
    vx = 114 * PX                                      # valance x 686..914
    drop_mid, drop_end = VALANCE_DROP                  # board: 40 px in the middle, 30 px at the ends
    cloth_panel(mb, -vx, vx, lambda x: top - drop_end - (drop_mid - drop_end) * (1 - (x / vx) ** 2), lambda x: top + 0.12,
                CANOPY_Y - 0.12, lambda x, z: 0.02 * math.sin(2 * math.pi * x / 0.35), 0.01, red, nu=36, nv=4)
    for sx in (-1, 1):                                 # side valances
        side = MB()
        L = -HALF_D - (CANOPY_Y - 0.12) + 0.02         # tucks 2 cm into the wall
        cloth_panel(side, 0.0, L, lambda x: top - drop_end * 0.8, lambda x: top + 0.105, 0.0,
                    lambda x, z: 0.015 * math.sin(2 * math.pi * x / 0.35), 0.01, red, nu=14, nv=3)
        side.transform(translate(sx * (vx - 0.01), CANOPY_Y - 0.12, 0) @ rot_z(math.pi / 2))   # runs back to the wall
        mb.merge(side)
    roof = MB()                                       # the cloth roof, sagging a little between the beams
    depth = -HALF_D - CANOPY_Y + 0.03                 # tucks 3 cm into the wall
    cloth_panel(roof, -vx + 0.02, vx - 0.02, lambda x: 0.0, lambda x: depth, 0.0,
                lambda x, z: 0.06 * math.sin(math.pi * z / depth) * math.cos(math.pi * x / (2 * vx)), 0.012, red,
                nu=16, nv=10)
    roof.transform(translate(0, CANOPY_Y, top + 0.115) @ Matrix.Rotation(-math.pi / 2, 4, 'X'))   # local z -> +y, fold sags
    mb.merge(roof)
    return kit.mb_to_object(mb, P + 'Canopy', coll)


def build_benches(coll):
    """Ofala_Benches: two long wooden benches for the chiefs (SVG x 340..610 and 990..1260)."""
    mb = MB()
    wood = P + 'Wood'
    for sx in (-1, 1):
        cx = sx * BENCH_X
        box_mb(mb, cx - BENCH_HL, cx + BENCH_HL, BENCH_Y - 0.21, BENCH_Y + 0.21, SEAT_H - 0.06, SEAT_H, wood)
        for lx in (-BENCH_HL + 0.12, 0.0, BENCH_HL - 0.12):
            for ly in (-0.13, 0.13):
                box_mb(mb, cx + lx - 0.04, cx + lx + 0.04, BENCH_Y + ly - 0.04, BENCH_Y + ly + 0.04, 0.0, SEAT_H - 0.06,
                       wood, skip=('bottom', 'top'))
    return kit.mb_to_object(mb, P + 'Benches', coll)


def build_drums(coll):
    """Ofala_Drums: the two royal drums by the left door (SVG x 186..228 and 236..266)."""
    mb = MB()
    for i, (x, y, rb, rt, h) in enumerate(DRUMS):
        sub = MB()
        wood = P + ('Wood' if i == 0 else 'WoodDark')
        lathe(sub, [(rb, 0.0), (rb * 0.97, h * 0.3), (rt * 1.04, h * 0.85), (rt, h - 0.02)], 18, wood)
        lathe(sub, [(rt - 0.02, h - 0.035), (rt + 0.022, h - 0.035), (rt + 0.022, h + 0.01), (rt - 0.02, h + 0.01)], 18,
              wood, closed=True)
        lathe(sub, [(rt + 0.01, h + 0.004), (rt * 0.5, h + 0.006), (0.0, h + 0.006)], 18, P + 'Hide')
        peg = MB()                                     # eight tuning pegs round the waist
        for k in range(8):
            a = 2 * math.pi * (k + 0.5) / 8
            r = interp_r(rb, rt, h, h * 0.62)
            p = MB()
            box_mb(p, -0.02, 0.02, -0.035, 0.005, h * 0.59, h * 0.66, P + 'WoodDark')
            p.transform(rot_z(a + math.pi / 2) @ translate(0, -r, 0))
            peg.merge(p)
        sub.merge(peg)
        sub.transform(translate(x, y, 0))
        mb.merge(sub)
    return kit.mb_to_object(mb, P + 'Drums', coll)


def interp_r(rb, rt, h, z):
    return kit.interp([(0.0, rb), (h * 0.3, rb * 0.97), (h * 0.85, rt * 1.04), (h - 0.02, rt)], z)


# ---------------------------------------------------------------------------
# Figures (stylized, faceless, generic: no real person is depicted)
# ---------------------------------------------------------------------------
def standing_figure(garment, top=None, top_mat=None, scale=1.0, arms=None, robe_flare=0.0):
    """A standing figure built facing -Y, feet at the origin. arms: per side
    (shoulder, elbow, hand) points, default hanging at the sides."""
    mb = MB()
    skin = P + 'Skin'
    body = MB()
    lathe(body, [(0.0, -0.01), (0.2 + robe_flare, -0.01), (0.19 + robe_flare * 0.5, 0.45), (0.17, 0.9), (0.19, 1.12),
                 (0.22, 1.33), (0.19, 1.39), (0.1, 1.43), (0.0, 1.44)], 12, garment)
    body.transform(Matrix.Diagonal((1.0, 0.72, 1.0, 1.0)))
    mb.merge(body)
    cylinder(mb, 0.05, 1.40, 1.50, skin, segs=8)
    ellipsoid(mb, (0, 0, 1.58), (0.1, 0.11, 0.12), skin)
    if top == 'gele':      # the two-lobed head-tie of the drawing's crowd
        for sgn in (-1, 1):
            lobe = MB()
            ellipsoid(lobe, (0, 0, 0), (0.12, 0.085, 0.075), top_mat, segs=8, rings=5)
            lobe.transform(translate(sgn * 0.065, 0.01, 1.68) @ Matrix.Rotation(-sgn * 0.5, 4, 'Y'))
            mb.merge(lobe)
        lathe(mb, [(0.098, 1.6), (0.106, 1.62), (0.104, 1.66), (0.0, 1.69)], 12, top_mat)
    elif top == 'cap':
        lathe(mb, [(0.096, 1.6), (0.108, 1.64), (0.096, 1.70), (0.05, 1.725), (0.0, 1.73)], 12, top_mat)
    arms = arms or [((s * 0.22, 0, 1.33), (s * 0.25, 0.0, 1.06), (s * 0.24, -0.04, 0.82)) for s in (-1, 1)]
    for sh, el, ha in arms:
        sweep(mb, [Vector(sh), Vector(el), Vector(ha)], [0.055, 0.048, 0.042], circle(8), garment, cap_start=True,
              cap_end=True)
        ellipsoid(mb, ha, (0.045, 0.045, 0.055), skin, segs=6, rings=4)
    mb.transform(Matrix.Diagonal((scale, scale, scale, 1.0)))
    return mb


def seated_chief(seat):
    """A red-cap chief (Ndichie) in a white robe with a gold trim, seated facing -Y
    (the drawing's 'chief' symbol); feet on the ground at y -0.5."""
    mb = MB()
    robe, skin, red, gold = P + 'ClothWhite', P + 'Skin', P + 'ClothRed', P + 'Gold'
    s = seat
    torso = MB()
    lathe(torso, [(0.0, s - 0.01), (0.2, s - 0.01), (0.2, s + 0.15), (0.185, s + 0.32), (0.205, s + 0.47),
                  (0.19, s + 0.53), (0.1, s + 0.58), (0.0, s + 0.59)], 12, robe)
    lathe(torso, [(0.17, s + 0.30), (0.198, s + 0.30), (0.198, s + 0.335), (0.17, s + 0.335)], 12, gold, closed=True)
    torso.transform(Matrix.Diagonal((1.0, 0.72, 1.0, 1.0)))
    mb.merge(torso)
    lap = [(0.09 * math.cos(a), 0.2 * math.sin(a)) for a in (2 * math.pi * k / 10 for k in range(10))]
    sweep(mb, [Vector((0, -0.05, s + 0.08)), Vector((0, -0.3, s + 0.09)), Vector((0, -0.46, s + 0.06))], [1, 1, 0.95],
          lap, robe, cap_end=True, ref=Vector((0, 0, 1)))
    shin = [(0.07 * math.cos(a), 0.19 * math.sin(a)) for a in (2 * math.pi * k / 10 for k in range(10))]
    sweep(mb, [Vector((0, -0.44, s + 0.04)), Vector((0, -0.5, 0.26)), Vector((0, -0.5, 0.05))], [1, 1.02, 1.05], shin,
          robe, cap_start=True, cap_end=True, ref=Vector((0, 1, 0)))   # closed: its top shows in front of the lap
    for sgn in (-1, 1):
        box_mb(mb, sgn * 0.1 - 0.05, sgn * 0.1 + 0.05, -0.64, -0.46, 0.0, 0.07, skin, skip=('bottom',))
        sweep(mb, [Vector((sgn * 0.2, 0.0, s + 0.47)), Vector((sgn * 0.23, -0.1, s + 0.27)),
                   Vector((sgn * 0.16, -0.36, s + 0.17))], [0.06, 0.055, 0.05], circle(8), robe, cap_start=True,
              cap_end=True)                              # closed sleeve: the hand is narrower than the cuff
        ellipsoid(mb, (sgn * 0.15, -0.40, s + 0.16), (0.045, 0.06, 0.035), skin, segs=6, rings=4)
    cylinder(mb, 0.05, s + 0.55, s + 0.65, skin, segs=8)
    ellipsoid(mb, (0, 0, s + 0.72), (0.1, 0.11, 0.115), skin)
    lathe(mb, [(0.094, s + 0.745), (0.106, s + 0.79), (0.095, s + 0.85), (0.05, s + 0.875), (0.0, s + 0.88)], 12, red)
    return mb


def build_figures(coll):
    """Ofala_Chiefs, Ofala_Musicians, Ofala_Crowd: stylized stand-ins for the people on the board."""
    rnd = random.Random(41)
    chiefs = MB()
    for sx in (-1, 1):
        for x in CHIEF_X:
            f = seated_chief(SEAT_H)
            f.transform(translate(-x if sx > 0 else x, BENCH_Y, 0))
            chiefs.merge(f)
    a = kit.mb_to_object(chiefs, P + 'Chiefs', coll)

    mus = MB()
    yellow, white, ivory = P + 'ClothYellow', P + 'ClothWhite', P + 'Ivory'
    # drummer (yellow robe, SVG x 148..180) beating the tall drum with two sticks
    pos = (svg_x(164) - 0.2, -6.45)
    arms = [((s * 0.22, 0, 1.33), (s * 0.26, -0.2, 1.12), (s * 0.12, -0.42, 1.08)) for s in (-1, 1)]
    d = standing_figure(yellow, arms=arms)
    for s in (-1, 1):
        sweep(d, [Vector((s * 0.12, -0.42, 1.08)), Vector((s * 0.1, -0.72, 1.12))], [0.014, 0.012], circle(6),
              P + 'WoodDark', cap_start=True, cap_end=True)
    d.transform(translate(*pos) @ rot_z(facing(pos, DRUMS[0][:2])))
    mus.merge(d)
    # horn player (white robe, SVG x 286..314) with the curved ivory horn raised to the right
    pos = (svg_x(300) + 0.6, -7.3)                       # just clear of the door's approach
    arms = [((-0.22, 0, 1.33), (-0.2, -0.25, 1.30), (0.02, -0.17, 1.52)),
            ((0.22, 0, 1.33), (0.3, -0.2, 1.28), (0.3, -0.33, 1.62))]
    t = standing_figure(white, top='cap', top_mat=P + 'ClothRed', arms=arms)
    horn = [Vector(p) for p in ((0.02, -0.12, 1.55), (0.2, -0.28, 1.62), (0.42, -0.4, 1.8), (0.62, -0.46, 2.04))]
    sweep(t, horn, [0.022, 0.035, 0.05, 0.065], circle(10), ivory, cap_start=True, cap_end=True)
    t.transform(translate(*pos) @ rot_z(math.radians(20)))
    mus.merge(t)
    b = kit.mb_to_object(mus, P + 'Musicians', coll)

    crowd = MB()
    spots = [(-11.9, -6.0), (-12.6, -6.9), (-11.8, -7.8), (-12.5, -8.7), (-11.7, -9.6), (-12.9, -10.4),
             (-13.4, -7.8), (-13.5, -9.5), (11.0, -6.4), (11.9, -7.2), (10.9, -8.1), (11.8, -9.0),
             (12.8, -7.7), (13.0, -9.5), (11.6, -11.6), (12.6, -12.4)]
    for k, (x, y) in enumerate(spots):
        mat = P + CROWD[k % len(CROWD)]
        top = 'gele' if k % 3 != 2 else 'cap'
        f = standing_figure(mat, top=top, top_mat=mat, scale=rnd.uniform(0.94, 1.04), robe_flare=0.04 if top == 'gele' else 0)
        f.transform(translate(x, y) @ rot_z(facing((x, y), ARENA_CENTRE) + rnd.uniform(-0.25, 0.25)))
        crowd.merge(f)
    near = (((2.45, -25.6), 'ClothCrimson'), ((3.2, -25.0), 'ClothBlue'), ((4.4, -25.3), 'ClothYellow'),
            ((5.3, -26.0), 'ClothGreen'))
    for k, ((x, y), mat) in enumerate(near):                   # near spectators with their backs to the camera
        f = standing_figure(P + mat, top='gele' if k != 2 else 'cap', top_mat=P + mat, robe_flare=0.04,
                            scale=rnd.uniform(0.95, 1.03))
        f.transform(translate(x, y) @ rot_z(facing((x, y), (0.0, -6.0)) + rnd.uniform(-0.1, 0.1)))
        crowd.merge(f)
    c = kit.mb_to_object(crowd, P + 'Crowd', coll)
    return a, b, c


# ---------------------------------------------------------------------------
# Cannon, tree, arena
# ---------------------------------------------------------------------------
def build_cannon(coll):
    """Ofala_Cannon: an old iron muzzle-loader on a wooden carriage (SVG x 1260..1390, y 666..722),
    raised for a salute."""
    mb = MB()
    iron, wood = P + 'Iron', P + 'WoodDark'
    barrel = MB()
    lathe(barrel, [(0.0, -0.14), (0.06, -0.13), (0.07, -0.09), (0.04, -0.05), (0.2, -0.02), (0.215, 0.06),
                   (0.195, 0.1), (0.18, 0.78), (0.195, 0.81), (0.195, 0.86), (0.172, 0.89), (0.158, 1.42),
                   (0.185, 1.5), (0.185, 1.58), (0.075, 1.58), (0.075, 1.2), (0.0, 1.2)], 16, iron)
    trunnion = MB()
    lathe(trunnion, [(0.0, -0.3), (0.06, -0.3), (0.06, 0.3), (0.0, 0.3)], 10, iron)
    trunnion.transform(translate(0, 0, 0.62) @ Matrix.Rotation(math.pi / 2, 4, 'Y'))
    barrel.merge(trunnion)
    axle_h = 0.30
    pivot = Vector((0, 0, axle_h + 0.32))
    elev = math.radians(24)
    # barrel along +X, pivoting on the trunnions
    barrel.transform(translate(*pivot) @ Matrix.Rotation(-elev, 4, 'Y') @ Matrix.Rotation(math.pi / 2, 4, 'Y')
                     @ translate(0, 0, -0.62))
    mb.merge(barrel)
    for sy in (-1, 1):         # carriage cheeks
        cheek = MB()
        outline = [(-1.2, 0.02), (0.3, 0.32), (0.32, axle_h + 0.38), (-0.25, axle_h + 0.3), (-1.25, 0.12)]
        extrude_shape(cheek, outline, 0.08, wood, wood)
        cheek.transform(translate(0, sy * 0.24, 0))
        mb.merge(cheek)
    for sy in (-1, 1):         # wheels
        wheel = MB()
        lathe(wheel, [(0.0, -0.05), (0.08, -0.06), (0.1, -0.035), (0.27, -0.035), (0.3, -0.03), (0.3, 0.03),
                      (0.27, 0.035), (0.1, 0.035), (0.08, 0.06), (0.0, 0.05)], 20, wood)
        wheel.transform(translate(0.05, sy * 0.38, axle_h) @ Matrix.Rotation(math.pi / 2, 4, 'X'))
        mb.merge(wheel)
    axle = MB()
    lathe(axle, [(0.0, -0.44), (0.045, -0.44), (0.045, 0.44), (0.0, 0.44)], 10, iron)
    axle.transform(translate(0.05, 0, axle_h) @ Matrix.Rotation(math.pi / 2, 4, 'X'))
    mb.merge(axle)
    mb.transform(translate(*CANNON_POS) @ rot_z(CANNON_YAW))
    return kit.mb_to_object(mb, P + 'Cannon', coll)


def muzzle_point():
    axle_h, elev = 0.30, math.radians(24)
    local = Vector((0, 0, axle_h + 0.32)) + Vector((math.cos(elev), 0, math.sin(elev))) * (1.58 - 0.62)
    return translate(*CANNON_POS) @ rot_z(CANNON_YAW) @ local


def build_tree(coll):
    """Ofala_ShadeTree (SVG x -60..400): a broad shade tree framing the left of the arena."""
    mb = MB()
    bark, leaf = P + 'Bark', P + 'Leaves'
    rnd = random.Random(17)
    rz = [(-0.2, 0.95), (0.15, 0.72), (0.5, 0.6), (1.5, 0.55), (3.0, 0.5), (4.3, 0.45)]
    NS = 16
    noise = lambda th, z: 1 + 0.05 * math.sin(3 * th + 1) + 0.04 * math.sin(5 * th + 0.7 * z) + 0.02 * math.sin(11 * th + 2 * z)
    sweep(mb, [Vector((0, 0, z)) for z, _ in rz], [r for _, r in rz], circle(NS), bark, ref=Vector((1, 0, 0)),
          cap_end=True, radial_fn=lambda i, k: noise(2 * math.pi * k / NS, rz[i][0]))
    limbs = [((0.0, 0.0, 3.6), (1.6, 0.4, 6.0), (3.4, 0.8, 7.6)), ((0.1, 0.1, 3.9), (-1.5, 0.9, 6.3), (-3.6, 1.2, 7.8)),
             ((0.0, -0.1, 4.0), (0.4, -1.8, 6.6), (0.9, -3.6, 8.1)), ((0.0, 0.0, 4.1), (-0.3, 1.0, 7.0), (-0.6, 2.8, 9.0)),
             ((0.0, 0.0, 4.1), (0.2, 0.0, 7.4), (0.3, 0.2, 9.6))]
    for path in limbs:
        sweep(mb, [Vector(p) for p in path], [0.3, 0.19, 0.08], circle(9), bark, cap_end=True, ref=Vector((0, 0, 1)))
    blobs = [((3.4, 0.8, 8.4), 2.6), ((-3.6, 1.2, 8.6), 2.7), ((0.9, -3.6, 8.8), 2.5), ((-0.6, 2.8, 9.6), 2.6),
             ((0.3, 0.2, 10.3), 2.8), ((2.5, -2.0, 9.5), 2.2), ((-2.4, -1.8, 9.3), 2.3), ((1.5, 2.6, 9.9), 2.1),
             ((-1.6, 0.0, 8.1), 2.0), ((4.8, -0.6, 8.0), 1.8), ((-5.0, 0.5, 8.1), 1.8), ((0.0, -1.0, 10.9), 2.0)]
    for (cx, cy, cz), r in blobs:
        sub = MB()
        prof = [(0.0, -1.0)] + [(math.sin(math.pi * k / 9), -math.cos(math.pi * k / 9)) for k in range(1, 9)] + [(0.0, 1.0)]
        lathe(sub, prof, 14, leaf)
        ph = [rnd.uniform(0, 6.28) for _ in range(3)]
        for i, v in enumerate(sub.v):
            d = v.normalized() if v.length > 1e-9 else Vector((0, 0, 1))
            k = 1 + 0.13 * math.sin(3 * d.x + ph[0]) * math.cos(2 * d.y + ph[1]) + 0.08 * math.sin(5 * d.z + ph[2])
            sub.v[i] = Vector((cx + v.x * r * k, cy + v.y * r * k, cz + v.z * r * 0.72 * k))
        mb.merge(sub)
    mb.transform(translate(*TREE_POS) @ rot_z(math.radians(15)))
    return kit.mb_to_object(mb, P + 'ShadeTree', coll)


def build_arena(coll):
    """Ofala_Arena: the beaten-earth arena (flat, z = 0), fading into dry grass beyond 34 m."""
    mb = MB()
    cx, cy = ARENA_CENTRE
    rings = [0.0, 3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 34, 40, 50, 65, 85, 110, 140]
    segs = 64
    rnd = random.Random(9)
    ph = [rnd.uniform(0, 6.28) for _ in range(3)]

    def height(r, a):
        if r <= 34:
            return 0.0
        k = (r - 34) / (140 - 34)
        return k * (0.6 * math.sin(3 * a + ph[0]) + 0.4 * math.sin(7 * a + ph[1]) + 0.8 * k)
    vid = []
    for r in rings:
        if r == 0:
            vid.append([mb.vert((cx, cy, 0.0))])
            continue
        vid.append([mb.vert((cx + r * math.cos(2 * math.pi * j / segs), cy + r * math.sin(2 * math.pi * j / segs),
                             height(r, 2 * math.pi * j / segs))) for j in range(segs)])
    isl = mb.island()
    uv = lambda i: (mb.v[i].x, mb.v[i].y)
    for i in range(len(rings) - 1):
        A, B = vid[i], vid[i + 1]
        mat = P + ('Arena' if rings[i + 1] <= 34 else 'Grass')
        for j in range(segs):
            j1 = (j + 1) % segs
            f = [A[0], B[j], B[j1]] if len(A) == 1 else [A[j], B[j], B[j1], A[j1]]
            mb.face(f, [uv(k) for k in f], mat, True, isl)
    return kit.mb_to_object(mb, P + 'Arena', coll, sharp_angle=60)


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------
def build_markers(coll, root):
    trg = P + 'TriggerVolume'
    tiers = DAIS[2]
    vols = {
        'TRG_Throne': (-tiers[0], tiers[0], DAIS_BACK - tiers[1], DAIS_BACK, DAIS_TOP, DAIS_TOP + 2.0),
        'TRG_GreatDoor': (-GREAT_HW, GREAT_HW, -HALF_D - 0.4, -HALF_D + 0.15, Z0, Z0 + 2.8),
        'TRG_SideDoor_L': (-8.585 - 0.425, -8.585 + 0.425, -HALF_D - 0.6, -HALF_D + WALL_T + 0.3, Z0, Z0 + 2.4),
        'TRG_SideDoor_R': (8.585 - 0.425, 8.585 + 0.425, -HALF_D - 0.6, -HALF_D + WALL_T + 0.3, Z0, Z0 + 2.4),
        'TRG_Interior': (-(HALF_W - WALL_T) + 0.05, HALF_W - WALL_T - 0.05, -(HALF_D - WALL_T) + 0.05,
                         HALF_D - WALL_T - 0.05, Z0, Z1 - 0.05),
        'TRG_Cannon': (CANNON_POS[0] - 1.6, CANNON_POS[0] + 1.6, CANNON_POS[1] - 1.4, CANNON_POS[1] + 1.4, 0.0, 2.0),
    }
    for name, (x0, x1, y0, y1, z0, z1) in vols.items():
        mb = MB()
        box_mb(mb, x0, x1, y0, y1, z0, z1, trg)
        ob = kit.mb_to_object(mb, P + name, coll)
        ob.display_type = 'WIRE'
        ob.hide_render = True
        ob.visible_shadow = False
        ob.parent = root
    pts = {
        'SPAWN_P1': ((-1.45, -13.0, 0.0), (0, 0, -math.pi / 2), 'SINGLE_ARROW', 0.8),
        'SPAWN_P2': ((1.50, -13.0, 0.0), (0, 0, math.pi / 2), 'SINGLE_ARROW', 0.8),
        'VFX_CannonSmoke': (tuple(muzzle_point()), (0, 0, 0), 'SPHERE', 0.4),
        'VFX_Dust_L': ((svg_x(400), -11.0, 0.3), (0, 0, 0), 'CUBE', 1.0),
        'VFX_Dust_R': ((svg_x(1100), -11.0, 0.3), (0, 0, 0), 'CUBE', 1.0),
        'SFX_Drums': ((DRUMS[0][0] + 0.4, DRUMS[0][1], 1.0), (0, 0, 0), 'SPHERE', 0.3),
        'SFX_Horn': ((svg_x(300) + 1.0, -7.6, 2.0), (0, 0, 0), 'SPHERE', 0.3),
        'SFX_Crowd_L': ((-12.0, -8.6, 1.6), (0, 0, 0), 'SPHERE', 0.5),
        'SFX_Crowd_R': ((11.9, -8.4, 1.6), (0, 0, 0), 'SPHERE', 0.5),
        'SFX_Cannon': ((CANNON_POS[0], CANNON_POS[1], 0.8), (0, 0, 0), 'SPHERE', 0.3),
    }
    for name, (loc, rot, kind, size) in pts.items():
        e = bpy.data.objects.new(P + name, None)
        e.empty_display_type = kind
        e.empty_display_size = size
        e.location = loc
        e.rotation_euler = rot
        if name.startswith('VFX_Dust'):
            e.scale = (4.0, 1.5, 0.6)
        coll.objects.link(e)
        e.parent = root
        e['ofala_marker'] = name


# ---------------------------------------------------------------------------
# Preview rig (not part of the asset): late-afternoon sky, sun, hills, cameras, player
# ---------------------------------------------------------------------------
SUN_DIR = Vector((0.62, -0.70, 0.36)).normalized()     # low sun from the front right


def setup_world():
    w = bpy.data.worlds.new('Preview_AfternoonSky')
    bpy.context.scene.world = w
    nt = kit.node_tree(w)
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    mr = nt.nodes.new('ShaderNodeMapRange')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    nt.links.new(tc.outputs['Generated'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
    mr.inputs['From Min'].default_value = -1.0
    mr.inputs['From Max'].default_value = 1.0
    nt.links.new(mr.outputs['Result'], ramp.inputs['Fac'])
    el = ramp.color_ramp.elements
    stops = [(0.0, '#8a7a5a'), (0.495, '#c8b088'), (0.5, HEX['sky_low']), (0.525, '#d6dcd4'), (0.585, HEX['sky_mid']),
             (0.7, HEX['sky_top']), (1.0, '#3a72b8')]
    el[0].position, el[0].color = stops[0][0], (*lin(stops[0][1]), 1)
    el[1].position, el[1].color = stops[-1][0], (*lin(stops[-1][1]), 1)
    for p, h in stops[1:-1]:
        e = el.new(p)
        e.color = (*lin(h), 1)
    noise = nt.nodes.new('ShaderNodeTexNoise')       # thin cloud streaks, as on the board
    stretch = nt.nodes.new('ShaderNodeMapping')
    stretch.inputs['Scale'].default_value = (1.0, 1.0, 7.0)
    nt.links.new(tc.outputs['Generated'], stretch.inputs['Vector'])
    nt.links.new(stretch.outputs['Vector'], noise.inputs['Vector'])
    noise.inputs['Scale'].default_value = 1.8
    noise.inputs['Detail'].default_value = 5.0
    cl = nt.nodes.new('ShaderNodeValToRGB')
    nt.links.new(noise.outputs['Fac'], cl.inputs['Fac'])
    cl.color_ramp.elements[0].position = 0.54
    cl.color_ramp.elements[0].color = (0, 0, 0, 1)
    cl.color_ramp.elements[1].position = 0.66
    cl.color_ramp.elements[1].color = (0.85, 0.85, 0.85, 1)
    up = nt.nodes.new('ShaderNodeMapRange')
    nt.links.new(sep.outputs['Z'], up.inputs['Value'])
    up.inputs['From Min'].default_value = 0.03
    up.inputs['From Max'].default_value = 0.25
    mul = nt.nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    nt.links.new(cl.outputs['Color'], mul.inputs[0])
    nt.links.new(up.outputs['Result'], mul.inputs[1])
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    nt.links.new(mul.outputs['Value'], kit.mix_socket(mix, 'Factor', 'VALUE'))
    nt.links.new(ramp.outputs['Color'], kit.mix_socket(mix, 'A'))
    kit.mix_socket(mix, 'B').default_value = (*lin(HEX['cloud']), 1)
    nt.links.new(kit.mix_socket(mix, 'Result', out=True), bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 1.0
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])


def build_preview_rig():
    rig = kit.collection('Preview_Rig')
    setup_world()
    kit.add_light(rig, 'Preview_Light_Sun', 'SUN', tuple(SUN_DIR * 100), (0, 0, 0), 4.2, '#ffd9a8', 1.2)
    bd = MB()
    rnd = random.Random(12)
    n = 96
    hills = [12 + 7 * math.sin(3 * a + 0.4) + 5 * math.sin(7 * a + 1.9) + rnd.uniform(-1.5, 1.5)
             for a in (2 * math.pi * k / n for k in range(n))]
    # the hills start under the grass edge (r 140), so no gap opens between the ground and the hills
    lo = [bd.vert((136 * math.cos(2 * math.pi * k / n), 136 * math.sin(2 * math.pi * k / n), -1.5)) for k in range(n)]
    hi = [bd.vert((170 * math.cos(2 * math.pi * k / n), 170 * math.sin(2 * math.pi * k / n), hills[k])) for k in range(n)]
    isl = bd.island()
    for k in range(n):
        k1 = (k + 1) % n
        bd.face([lo[k], hi[k], hi[k1], lo[k1]], [(k, 0), (k, 1), (k + 1, 1), (k + 1, 0)], 'Preview_Hills', True, isl)
    kit.make_material('Preview_Hills', HEX['hills'], 0.9)
    ob = kit.mb_to_object(bd, 'Preview_Backdrop', rig)
    kit.ASSET_OBJECTS.remove(ob)
    cams = dict(
        front=kit.add_camera(rig, 'Preview_Cam_Front', (0.0, -30.5, 2.6), (0.0, -2.0, 3.0), 32),
        side=kit.add_camera(rig, 'Preview_Cam_Side', (36.0, -9.0, 4.5), (0.0, -8.0, 2.6), 35),
        threequarter=kit.add_camera(rig, 'Preview_Cam_ThreeQuarter', (22.0, -31.0, 14.0), (0.0, -6.5, 2.0), 30),
        threequarter_back=kit.add_camera(rig, 'Preview_Cam_ThreeQuarterBack', (-24.0, 24.0, 12.0), (0.0, 0.0, 2.5), 30),
        playerscale=kit.add_camera(rig, 'Preview_Cam_PlayerScale', (-3.6, -17.8, 2.0), (-3.6, -6.0, 1.6), 30),
        detail=kit.add_camera(rig, 'Preview_Cam_Detail', (1.7, -11.5, 1.9), (0.0, -6.3, 1.4), 40),
        plan=kit.add_camera(rig, 'Preview_Cam_Plan', (0.0, -9.0, 90.0), (0.0, -9.0, 0.0), 50, ortho=48.0),
    )
    cams['plan'].rotation_euler = (0.0, 0.0, 0.0)
    return rig, cams


def build_player_reference():
    """REF_PlayerScale (not part of the asset): 1.8 m mannequins and labels."""
    ref = kit.collection('REF_PlayerScale')
    kit.make_material('REF_Mannequin', '#9aa3ad', 0.55)
    kit.make_material('REF_Label', '#ffffff', 0.5, emission='#ffffff', emission_strength=2.0)

    def mannequin(pos, z, yaw):
        mb = MB()
        m = 'REF_Mannequin'
        for sx in (-1, 1):
            sweep(mb, [Vector((sx * 0.1, 0, 0.93)), Vector((sx * 0.105, 0.01, 0.5)), Vector((sx * 0.11, 0, 0.09))],
                  [0.075, 0.058, 0.048], circle(10), m, cap_start=True, cap_end=True)
            box_mb(mb, sx * 0.1 - 0.05, sx * 0.1 + 0.05, -0.17, 0.06, 0.0, 0.09, m)
            sweep(mb, [Vector((sx * 0.215, 0, 1.43)), Vector((sx * 0.27, 0.0, 1.13)), Vector((sx * 0.3, -0.03, 0.83))],
                  [0.048, 0.04, 0.035], circle(8), m, cap_start=True, cap_end=True)
        lathe(mb, [(0.0, 0.88), (0.16, 0.9), (0.17, 1.02), (0.145, 1.18), (0.2, 1.38), (0.21, 1.44), (0.12, 1.5),
                   (0.055, 1.53), (0.055, 1.59), (0.0, 1.59)], 14, m)
        lathe(mb, [(0.0, 1.58)] + [(0.105 * math.sin(math.pi * k / 8), 1.69 - 0.11 * math.cos(math.pi * k / 8))
                                   for k in range(1, 8)] + [(0.0, 1.80)], 14, m)
        mb.transform(translate(pos[0], pos[1], z) @ rot_z(yaw))
        ob = kit.mb_to_object(mb, 'REF_Player_1.8m', ref)
        kit.ASSET_OBJECTS.remove(ob)

    def label(text, loc, size=0.16, yaw=0.0):
        cu = bpy.data.curves.new('REF_Label', 'FONT')
        cu.body = text
        cu.size = size
        cu.align_x = 'CENTER'
        ob = bpy.data.objects.new('REF_Label', cu)
        ob.location = loc
        ob.rotation_euler = (math.pi / 2, 0, yaw)
        ob.visible_shadow = False                   # the low sun would print the text on the wall
        cu.materials.append(kit.MATS['REF_Label'])
        ref.objects.link(ob)

    mannequin((-8.585, -4.75), Z0, 0.0)
    mannequin((-1.25, -7.25), DAIS_TOP, math.radians(-10))
    mannequin((-3.9, -9.2), 0.0, math.radians(15))
    yaw = math.radians(-3)
    label('1.8 m player', (-8.585, -4.95, Z0 + 1.95), 0.15, yaw)
    label('side door 0.85 m wide, 2.68 m high', (-8.585, -4.95, Z0 + 3.0), 0.13, yaw)
    label('dais: three 0.20 m steps', (2.4, -9.3, 0.25), 0.13, yaw)
    label('throne back 1.65 m; canopy valance clears 2.10 m', (-0.6, -8.1, DAIS_TOP + 2.95), 0.12, yaw)
    return ref


# ---------------------------------------------------------------------------
# Render, main
# ---------------------------------------------------------------------------
PLAN_COLOURS = dict(TRG='#3cff7a', SPAWN='#3cd6ff', VFX='#ffd23c', SFX='#ff5ad2')


def plan_overlay():
    """Render-only overlay for the plan view (the .blend is saved before this runs)."""
    made = []

    def glow_mat(name, hexc, alpha):
        m = bpy.data.materials.new(name)
        nt = kit.node_tree(m)
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (*lin(hexc), 1)
        em.inputs['Strength'].default_value = 2.0
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        mx = nt.nodes.new('ShaderNodeMixShader')
        mx.inputs['Fac'].default_value = alpha
        nt.links.new(tr.outputs['BSDF'], mx.inputs[1])
        nt.links.new(em.outputs['Emission'], mx.inputs[2])
        nt.links.new(mx.outputs['Shader'], out.inputs['Surface'])
        return m
    trg = glow_mat('PLAN_Trigger', PLAN_COLOURS['TRG'], 0.35)
    for ob in kit.COLL[P + 'Markers'].objects:
        key = ob.name[len(P):].split('_')[0]
        if ob.type == 'MESH':
            if ob.name == P + 'TRG_Interior':
                continue
            ob.hide_render = False
            ob.data.materials[0] = trg
            made.append(('restore', ob))
        elif key in PLAN_COLOURS and ob.location.z < 8:
            if 'PLAN_' + key not in kit.MATS:
                kit.MATS['PLAN_' + key] = glow_mat('PLAN_' + key, PLAN_COLOURS[key], 0.9)
            mb = MB()
            lathe(mb, [(0.0, 0.0), (0.4, 0.0), (0.4, 0.05), (0.0, 0.05)], 20, 'PLAN_' + key)
            mb.transform(translate(ob.location.x, ob.location.y, 13.0))   # above the tree, so none is hidden
            disc = kit.mb_to_object(mb, 'PLAN_' + ob.name, kit.COLL['Preview_Rig'])
            kit.ASSET_OBJECTS.remove(disc)
            made.append(('delete', disc))
    return made


def render_views(views, cams, out_dir, debug_normals=False):
    sc = bpy.context.scene
    os.makedirs(out_dir, exist_ok=True)
    ref = kit.COLL.get('REF_PlayerScale')
    names = dict(front='Ofala_Front', side='Ofala_Side', threequarter='Ofala_ThreeQuarter',
                 threequarter_back='Ofala_ThreeQuarter_Back', playerscale='Ofala_PlayerScale',
                 detail='Ofala_Detail_Throne', plan='Ofala_Plan')
    for v in views:
        if ref:
            ref.hide_render = v != 'playerscale'
        overlay = plan_overlay() if v == 'plan' else []
        sc.camera = cams[v]
        sc.render.filepath = os.path.join(out_dir, names[v] + '.png')
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print('  rendered %-14s %.0fs' % (v, time.time() - t0), flush=True)
        for what, ob in overlay:
            if what == 'restore':
                ob.hide_render = True
                ob.data.materials[0] = kit.MATS[P + 'TriggerVolume']
            else:
                bpy.data.objects.remove(ob)
    if ref:
        ref.hide_render = True
    if debug_normals:
        mat = bpy.data.materials.new('DEBUG_Backfacing')
        nt = kit.node_tree(mat)
        nt.nodes.clear()
        geo = nt.nodes.new('ShaderNodeNewGeometry')
        mix = nt.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        em = nt.nodes.new('ShaderNodeEmission')
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        kit.mix_socket(mix, 'A').default_value = (0.1, 0.3, 1.0, 1)
        kit.mix_socket(mix, 'B').default_value = (1.0, 0.0, 0.0, 1)
        nt.links.new(geo.outputs['Backfacing'], kit.mix_socket(mix, 'Factor', 'VALUE'))
        nt.links.new(kit.mix_socket(mix, 'Result', out=True), em.inputs['Color'])
        nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
        vl = bpy.context.view_layer
        vl.material_override = mat
        old = sc.cycles.samples
        sc.cycles.samples = 4
        for v in ('front', 'threequarter', 'side', 'detail'):
            sc.camera = cams[v]
            sc.render.filepath = os.path.join(out_dir, 'DEBUG_normals_%s.png' % v)
            bpy.ops.render.render(write_still=True)
        vl.material_override = None
        sc.cycles.samples = old


def parse_args():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    p = argparse.ArgumentParser(prog='build_ofala.py')
    p.add_argument('--out', default=os.path.dirname(os.path.abspath(__file__)))
    p.add_argument('--render', default='none')
    p.add_argument('--samples', type=int, default=128)
    p.add_argument('--res', default='1600x900')
    p.add_argument('--skip-textures', action='store_true')
    p.add_argument('--debug-normals', action='store_true')
    return p.parse_args(argv)


def main():
    args = parse_args()
    t_start = time.time()
    out = os.path.abspath(args.out)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    print('Ofala build -> %s' % out)
    tex = generate_textures(os.path.join(out, 'Textures'), args.skip_textures)
    build_materials(tex)

    root_c = kit.collection('Ofala')
    c_arch = kit.collection(P + 'Architecture', root_c)
    c_props = kit.collection(P + 'Props', root_c)
    c_fig = kit.collection(P + 'Figures', root_c)
    c_land = kit.collection(P + 'Landmarks', root_c)
    c_terr = kit.collection(P + 'Terrain', root_c)
    c_mark = kit.collection(P + 'Markers', root_c)
    root = bpy.data.objects.new('Ofala', None)
    root.empty_display_type = 'PLAIN_AXES'
    root_c.objects.link(root)

    build_base(c_arch)
    build_walls(c_arch)
    build_roof(c_arch)
    build_fringe(c_arch)
    build_wall_paint(c_arch)
    build_doorway(c_arch)
    build_dais(c_arch)
    build_throne(c_props)
    build_canopy(c_props)
    build_benches(c_props)
    build_drums(c_props)
    build_cannon(c_props)
    build_figures(c_fig)
    build_tree(c_land)
    build_arena(c_terr)
    asset_meshes = list(kit.ASSET_OBJECTS)
    build_markers(c_mark, root)
    for ob in asset_meshes:
        ob.parent = root
    for ob in kit.ASSET_OBJECTS:
        kit.add_lightmap_uv(ob)

    rows, total = kit.validate(kit.ASSET_OBJECTS)
    print('\n%-30s %7s %6s %6s %5s %5s %5s %s' % ('object', 'tris', 'ovUV', 'ovLM', 'nonM', 'flip', 'degen', 'closed vol'))
    for r in rows:
        print('%-30s %7d %6d %6d %5d %5d %5d %s %s' % (r['name'], r['tris'], r['overlap_UVMap'], r['overlap_UVLightmap'],
                                                      r['nonmanifold'], r['inconsistent_winding'], r['degenerate'],
                                                      r.get('closed_volume', '-'), '' if r['identity'] else 'NOT-IDENTITY'))
    asset_tris = sum(r['tris'] for r in rows if '_TRG_' not in r['name'])
    print('asset triangles (excluding trigger volumes): %d   with triggers: %d' % (asset_tris, total))

    _, cams = build_preview_rig()
    ref = build_player_reference()
    ref.hide_render = True
    kit.setup_scene(args.samples, args.res)
    bpy.context.scene.view_settings.exposure = 0.0
    bpy.context.scene.camera = cams['front']

    blend = os.path.join(out, 'Ofala.blend')
    bpy.ops.wm.save_as_mainfile(filepath=blend, relative_remap=True, compress=True)
    print('saved %s' % blend)

    views = [] if args.render == 'none' else (
        ['front', 'side', 'threequarter', 'threequarter_back', 'playerscale', 'detail', 'plan']
        if args.render == 'all' else [v.strip() for v in args.render.split(',') if v.strip()])
    if views or args.debug_normals:
        render_views(views, cams, os.path.join(out, 'Renders'), args.debug_normals)
    print('done in %.0fs' % (time.time() - t_start))


if __name__ == '__main__':
    main()
