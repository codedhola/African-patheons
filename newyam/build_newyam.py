"""Build the New Yam festival (Stage 25, a village arena on the day of the Igbo
New Yam festival) as a game-ready Blender scene.

This uses the same pipeline as the Stormshrine and Ofala. The mesh builder, UV
packing, texture generator, PNG writer, materials and validation all come from
../stormshrine/build_stormshrine.py, imported as `kit`. This script adds what
is specific to the stage: the elder's house with its open bay and carved
posts, the heap of new yams on a raffia mat, the elder roasting the first yam,
palm oil and palm wine, the dancers, drummers and masquerade, the villagers,
the string of young palm fronds, the trees, palms and bushes, the laterite
arena and a midday preview rig.

    blender -b --factory-startup -P build_newyam.py -- [options]

Options (after the "--"):
    --out DIR        output folder (default: the folder holding this script)
    --render LIST    none | all | comma list of: front, side, threequarter,
                     threequarter_back, playerscale, detail, plan  (default: none)
    --samples N      Cycles samples for the renders     (default: 128)
    --res WxH        render size                         (default: 1600x900)
    --skip-textures  reuse the PNGs already in OUT/Textures
    --debug-normals  also render back-face checks (red = a face seen from behind)

Design source: stages/Stage25-NewYam.html (the SVG stage board) and
previews/Stage25-NewYam.png. SVG coordinates in comments come from that file.
README.md next to this script lists the assumptions.

Conventions: 1 Blender unit = 1 m, +Z up, the house faces -Y. Every asset
mesh has identity transforms; their shared origin (0, 0, 0) is the centre of
the house footprint at ground level. UV map "UVMap" is in metres (tiling
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
box_mb, relief_stroke, relief_fill, plane_map = kit.box_mb, kit.relief_stroke, kit.relief_fill, kit.plane_map
lin, translate, rot_z, C = kit.lin, kit.translate, kit.rot_z, kit.C

# ---------------------------------------------------------------------------
# Design constants (from the SVG)
# ---------------------------------------------------------------------------
# At 0.019 m per SVG px the dancers and the drummer, drawn 88 px from the feet
# to the crown, come out 1.67 m tall, and the house's open bay 2.36 m high.
PX = 0.019


def svg_x(px):
    """SVG x -> metres (house centre line x=800)."""
    return (px - 800.0) * PX


def svg_h(py):
    """SVG y -> metres above the house floor (wall foot y=654)."""
    return (654.0 - py) * PX


P = 'NewYam_'
PLINTH_H = 0.25            # assumption: low earth plinth under the house
APRON = 0.50
BASE_BEVEL = 0.04
STEP_H = PLINTH_H / 2      # one half-height step in front of the bay
XE, YE = 300 * PX, 180 * PX            # 5.70 x 3.42 eave half extents: eave x 500..1100, hips run x 500..680
OVERHANG = 40 * PX                     # 0.76: walls x 540..1060
HALF_W, HALF_D = XE - OVERHANG, YE - OVERHANG   # 4.94 x 2.66
WALL_T = 0.40
Z0 = PLINTH_H
WALL_H = svg_h(474)        # 3.42: wall top
Z1 = Z0 + WALL_H
EAVE_H = svg_h(484)        # 3.23: underside of the eave
RIDGE_H = svg_h(360)       # 5.59: ridge (x 680..920)
BAY_HW = 160 * PX          # 3.04: the open bay x 640..960
BAY_TOP = svg_h(530)       # 2.36
POST_XS = [svg_x(x) for x in (640, 800, 960)]   # carved posts, 20 px wide
POST_W = 20 * PX           # 0.38
POST_TOP = svg_h(520)      # 2.55
POST_Y = -HALF_D - POST_W / 2 + 0.02            # standing against the wall, 2 cm into it

MAT_HX, MAT_Y0, MAT_Y1 = 140 * PX, -6.26, -3.96   # raffia mat x 660..940, 2.3 m deep
HEAP_Y = (MAT_Y0 + MAT_Y1) / 2
FIRE = (svg_x(664), -6.75)                         # the small fire, x 664
ELDER = (svg_x(613) - 0.15, -6.75)                 # the elder at x 613, facing the fire
OIL = (svg_x(575) - 0.10, -7.30)                   # palm oil bowl, x 575
WINE = [(svg_x(958) + 0.05, -6.65, 1.0), (svg_x(988) + 0.10, -6.35, 0.75)]   # palm wine gourds, x 958 and 988
# figures in front of the house sit nearer the camera than the house, so their x is drawn in by 0.92
DANCERS = [(svg_x(250) * 0.92, -5.00, 'ClothRed'), (svg_x(310) * 0.92, -5.35, 'ClothYellow'),
           (svg_x(370) * 0.92, -4.95, 'ClothGreen')]
DRUM = (svg_x(1127) * 0.92, -4.60)
DRUMMER = (svg_x(1160) * 0.92 + 0.05, -4.45)
EKWE = (4.55, -6.55)                               # second drummer with a slit drum (assumption)
MASQ = (svg_x(1260) * 0.90, -4.60)                 # the masquerade, x 1214..1306
TREES = [(-7.6, -14.0, 0.0), (7.6, -14.0, math.pi)]   # x, y, yaw: local +x points into the arena
PALMS = [(-10.6, 3.0, 9.0), (10.9, 3.4, 8.4)]
BUSHES = [(-6.7, 4.4), (6.9, 4.1)]
ROPE_Z, ROPE_SAG = 6.0, 0.7
ARENA_CENTRE = (0.0, -10.0)

HEX = dict(wall='#b0542e', plinth='#8a4426', kaolin='#f4efe4', thatch='#a8803e', straw='#e0b070',
           laterite='#b0623a', grass='#5a9a40', hills='#5f9e48', sky_top='#3a86d6', sky_mid='#6aaee8',
           sky_low='#cfe8f6', cloud='#ffffff', skin='#4a2a18')
CROWD = ['ClothRed', 'ClothBlue', 'ClothYellow', 'ClothGreen', 'ClothPurple']


# ---------------------------------------------------------------------------
# Textures
# ---------------------------------------------------------------------------
def tex_earth_wall(T):
    """Red-brown earth plaster, hand-smoothed: the walls, and a darker shade for the plinth."""
    low, mid, fine, tone = T.noise(3.2), T.noise(2.2, 3), T.noise(0.8, 90), T.noise(3.0)
    swirl = T.noise(1.8, 5, sx=3)                      # hand-smoothing strokes
    F1, F2 = T.worley(26)
    crack = np.exp(-((F2 - F1) * T.n / 1.5) ** 2) * np.clip(T.noise(3.0) * 0.8 - 0.4, 0, 1)
    h = low * 1.5e-3 + mid * 0.5e-3 + swirl * 0.35e-3 + fine * 0.08e-3 - crack * 0.7e-3
    var = ((1 + 0.06 * low + 0.04 * mid + 0.03 * swirl + 0.02 * fine) * (1 - 0.3 * crack))[..., None]
    k = (np.clip(0.5 + 0.3 * tone, 0, 1) * 0.3)[..., None]
    cols = dict(BaseColor=(C(HEX['wall']) * (1 - k) + C('#9a4626') * k) * var,
                BaseColorPlinth=(C(HEX['plinth']) * (1 - k) + C('#6e341c') * k) * var)
    rough = np.clip(0.88 + 0.04 * mid + 0.02 * fine + 0.04 * crack, 0, 1)
    return cols, rough, h


def tex_thatch(T):
    """Golden thatch, and a paler straw for the ridge (the board's light ridge line)."""
    strands, clumps = T.noise(1.5, 6, sy=16), T.noise(2.6, 2, sy=5)
    fine, sweep_ = T.noise(1.0, 80, sy=24), T.noise(3.0, sy=3)
    s = 0.55 * strands + 0.35 * clumps + 0.22 * fine
    h = s * 3e-3
    k = np.clip(0.5 + 0.28 * s + 0.1 * sweep_, 0, 1)[..., None]

    def ramp(dark, mid_, hi):
        dark, mid_, hi = C(dark), C(mid_), C(hi)
        return np.where(k < 0.5, dark + (mid_ - dark) * (k / 0.5), mid_ + (hi - mid_) * ((k - 0.5) / 0.5))
    cols = dict(BaseColor=ramp('#5e4220', HEX['thatch'], '#dab474'), BaseColorLight=ramp('#8a6a3a', '#d8aa66', '#f0d29a'))
    rough = np.clip(0.8 - 0.06 * clumps + 0.04 * fine, 0.6, 0.95)
    return cols, rough, h


def tex_laterite(T):
    """Swept red laterite: packed earth with broom streaks, grit and a few footprints."""
    low, mid, fine = T.noise(3.0, 2), T.noise(2.0, 5), T.noise(1.0, 120)
    broom = T.noise(1.0, 12, sx=7)                     # long streaks from the morning sweeping
    grit = T.pebbles(1400, 0.8, 2.2)
    prints = T.pebbles(60, 4.0, 6.0)
    h = low * 2.5e-3 + mid * 0.8e-3 + broom * 0.25e-3 + fine * 0.1e-3 + grit * 0.6e-3 - prints * 1.0e-3
    col = C('#a45632') + (C('#c87a48') - C('#a45632')) * np.clip(0.5 + 0.3 * mid + 0.15 * low, 0, 1)[..., None]
    col = col * (1 + 0.04 * broom + 0.03 * fine)[..., None]
    col = col + (C('#76381e') - col) * (np.clip(grit, 0, 1) * 0.35)[..., None]
    col = col * (1 - 0.1 * np.clip(prints, 0, 1))[..., None]
    rough = np.clip(0.9 + 0.03 * fine - 0.04 * np.clip(broom, 0, 1), 0, 1)
    return dict(BaseColor=col), rough, h


def tex_grass(T):
    """Lush grass at the end of the rains."""
    blades, low, mid = T.noise(1.2, 40, sy=2.5), T.noise(3.0, 4), T.noise(2.0, 6)
    h = blades * 1.5e-3 + low * 0.8e-3
    col = C('#3a7228') + (C('#78ac48') - C('#3a7228')) * np.clip(0.5 + 0.3 * mid + 0.25 * blades, 0, 1)[..., None]
    col = col * (1 + 0.05 * low)[..., None]
    rough = np.clip(0.86 + 0.04 * blades, 0, 1)
    return dict(BaseColor=col), rough, h


def tex_yam(T):
    """Yam skin: rough dark-brown cork with lighter root scars and fine root hairs."""
    low, mid, fine = T.noise(3.0), T.noise(2.0, 6), T.noise(1.0, 80)
    F1, F2 = T.worley(140)
    cork = np.exp(-((F2 - F1) * T.n / 2.0) ** 2)
    scars = T.pebbles(260, 1.5, 3.5)
    hairs = np.clip(T.noise(0.8, 150) - 1.6, 0, 1)
    h = low * 0.6e-3 + mid * 0.3e-3 - cork * 0.4e-3 + scars * 0.5e-3 + hairs * 0.3e-3
    k = np.clip(0.5 + 0.3 * mid + 0.2 * low, 0, 1)[..., None]
    col = C('#5a3a1e') + (C('#8e5e36') - C('#5a3a1e')) * k
    col = col + (C('#b8864e') - col) * (np.clip(scars, 0, 1) * 0.5)[..., None]
    col = col * (1 - 0.25 * cork)[..., None] * (1 + 0.04 * fine)[..., None]
    rough = np.clip(0.86 + 0.05 * cork - 0.03 * scars, 0, 1)
    return dict(BaseColor=col), rough, h


def tex_raffia(T):
    """Woven raffia mat: over-under strips about 3 cm wide."""
    g = (np.arange(T.n) + 0.5) / T.n
    X, Y = np.meshgrid(g, g)
    strips = 32
    warp = 0.5 + 0.5 * np.cos(2 * np.pi * strips * X)
    weft = 0.5 + 0.5 * np.cos(2 * np.pi * strips * Y)
    over = np.sin(np.pi * strips * X) * np.sin(np.pi * strips * Y) > 0
    h = np.where(over, warp, weft) * 0.8e-3 + T.noise(2.0, 4) * 0.2e-3
    shade = np.where(over, 0.55 + 0.45 * warp, 0.55 + 0.45 * weft)
    tone = T.noise(2.5, 3)
    col = C('#b0904e') + (C('#e2c88a') - C('#b0904e')) * np.clip(shade * (0.9 + 0.1 * tone), 0, 1)[..., None]
    rough = np.clip(0.8 + 0.06 * (1 - shade), 0, 1)
    return dict(BaseColor=col), rough, h


def tex_cloth(T):
    """Plain weave for all the cloth: normal and roughness only."""
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
    col = (C('#1e3c18') + (C('#56883e') - C('#1e3c18')) * k) * (1 + 0.1 * low)[..., None]
    rough = np.clip(0.62 - 0.1 * leaf + 0.15 * gap, 0, 1)
    return dict(BaseColor=col), rough, h


def tex_bark(T):
    fiss, plates, fine = T.noise(1.6, 6, sy=10), T.noise(2.4, 3, sy=3), T.noise(1.0, 60)
    ridge = 1 - np.abs(np.clip(fiss, -2.5, 2.5)) / 2.5
    h = ridge * 3e-3 + plates * 1e-3 + fine * 0.2e-3
    k = np.clip(0.5 + 0.3 * plates + 0.4 * (ridge - 0.5), 0, 1)[..., None]
    col = C('#3a2a1e') + (C('#6e5a46') - C('#3a2a1e')) * k
    rough = np.clip(0.86 + 0.04 * fine, 0, 1)
    return dict(BaseColor=col), rough, h


def tex_frond(T):
    """Palm leaflets with parallel veins along v: pale young fronds and green palm leaves share it."""
    u = ((np.arange(T.n) + 0.5) / T.n)[None, :]
    rib = 0.5 + 0.5 * np.cos(2 * np.pi * 24 * u)        # leaflet edges
    veins = T.noise(1.0, 60, sy=40)
    mid = T.noise(2.0, 6)
    h = rib * 0.8e-3 + veins * 0.2e-3
    k = np.clip(0.5 + 0.25 * mid + 0.3 * (rib - 0.5) + 0.1 * veins, 0, 1)[..., None]
    cols = dict(BaseColor=C('#d4c070') + (C('#f6eab4') - C('#d4c070')) * k,
                BaseColorGreen=C('#22501c') + (C('#4e8a36') - C('#22501c')) * k)
    rough = np.clip(0.6 + 0.1 * (1 - rib) + 0.04 * veins, 0, 1)
    return cols, rough, h


def tex_stone(T):
    low, grain, mid = T.noise(3.0), T.noise(1.1, 30), T.noise(2.0, 6)
    pits = T.pebbles(400, 1.0, 3.0)
    h = low * 1.0e-3 + mid * 0.4e-3 + grain * 0.1e-3 - pits * 0.5e-3
    col = C('#6a5e54') + (C('#3e3632') - C('#6a5e54')) * np.clip(0.5 + 0.3 * mid, 0, 1)[..., None]
    col = col * (1 + 0.12 * low + 0.05 * grain)[..., None] * (1 - 0.3 * pits)[..., None]
    rough = np.clip(0.78 + 0.05 * grain + 0.08 * pits, 0, 1)
    return dict(BaseColor=col), rough, h


def tex_ember(T):
    col, rough, h, emis = kit.tex_ember(T)
    return dict(BaseColor=col, Emissive=emis), rough, h


def tex_wood(base, dark):
    def fn(T):
        col, rough, h = kit.tex_wood(T, base, dark)
        return dict(BaseColor=col), rough, h
    return fn


TEXTURE_SETS = {
    # name: (generator, size px, tile m, seed)
    'EarthWall': (tex_earth_wall, 1024, 2.0, 51),
    'Thatch': (tex_thatch, 1024, 2.0, 52),
    'Laterite': (tex_laterite, 1024, 4.0, 53),
    'Grass': (tex_grass, 1024, 6.0, 54),
    'Wood': (tex_wood('#7a4a2a', '#4a2c18'), 512, 1.0, 55),
    'WoodDark': (tex_wood('#5a3418', '#2e1a0c'), 512, 1.0, 56),
    'YamSkin': (tex_yam, 512, 0.5, 57),
    'Raffia': (tex_raffia, 512, 1.0, 58),
    'Cloth': (tex_cloth, 512, 0.5, 59),
    'Leaves': (tex_leaves, 512, 2.0, 60),
    'Bark': (tex_bark, 512, 1.5, 61),
    'Frond': (tex_frond, 512, 1.0, 62),
    'Stone': (tex_stone, 512, 0.6, 63),
    'Ember': (tex_ember, 512, 0.5, 64),
}
MAPS = ('BaseColor', 'BaseColorPlinth', 'BaseColorLight', 'BaseColorGreen', 'Emissive', 'Roughness', 'Normal')


def generate_textures(tex_dir, skip):
    os.makedirs(tex_dir, exist_ok=True)
    out = {}
    for name, (fn, n, tile, seed) in TEXTURE_SETS.items():
        path = lambda m, name=name: os.path.join(tex_dir, 'T_NewYam_%s_%s.png' % (name, m))
        if not skip:
            t0 = time.time()
            T = kit.TexGen(n, tile, seed)
            cols, rough, h = fn(T)
            for m, col in (cols or {}).items():
                kit.write_png(path(m), kit.to_u8(kit.lin_to_srgb(col)))
            kit.write_png(path('Roughness'), kit.to_u8(rough))
            kit.write_png(path('Normal'), kit.to_u8(T.normal(h)))
            print('  texture %-10s %4d px  %.1fs' % (name, n, time.time() - t0))
        out[name] = ({m: path(m) for m in MAPS if os.path.exists(path(m))}, tile)
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

    def tx(name, s, base='BaseColor', **kw):
        return mk(P + name, T(s, base), T(s, 'Roughness'), T(s, 'Normal'), tile(s), **kw)
    tx('EarthWall', 'EarthWall', viewport=lin(HEX['wall']))
    tx('Plinth', 'EarthWall', 'BaseColorPlinth', viewport=lin(HEX['plinth']))
    mk(P + 'Kaolin', HEX['kaolin'], 0.86, T('EarthWall', 'Normal'), tile('EarthWall'), normal_strength=0.6)
    tx('Thatch', 'Thatch', viewport=lin(HEX['thatch']))
    tx('RidgeStraw', 'Thatch', 'BaseColorLight', viewport=lin(HEX['straw']))
    tx('Laterite', 'Laterite', spec=0.4, viewport=lin(HEX['laterite']))
    tx('Grass', 'Grass', viewport=lin(HEX['grass']))
    tx('Wood', 'Wood', viewport=lin('#7a4a2a'))
    tx('WoodDark', 'WoodDark', viewport=lin('#5a3418'))
    tx('YamSkin', 'YamSkin', viewport=lin('#8a5a34'))
    mk(P + 'YamRoasted', '#4a2410', 0.7, T('YamSkin', 'Normal'), tile('YamSkin'), normal_strength=0.8)
    tx('Raffia', 'Raffia', viewport=lin('#d8b878'))
    tx('Leaves', 'Leaves', viewport=lin('#3e7a34'))
    tx('PalmLeaf', 'Frond', 'BaseColorGreen', viewport=lin('#2e6a30'))
    tx('YoungFrond', 'Frond', viewport=lin('#f0e2a0'))
    tx('Bark', 'Bark', viewport=lin('#4a3424'))
    tx('Stone', 'Stone', viewport=lin('#5a5048'))
    mk(P + 'Ember', T('Ember', 'BaseColor'), T('Ember', 'Roughness'), T('Ember', 'Normal'), tile('Ember'),
       emission=T('Ember', 'Emissive'), emission_strength=4.0, viewport=lin('#ff7a2a'))
    mk(P + 'Calabash', '#b08a4a', 0.5, T('Wood', 'Normal'), 1.0, normal_strength=0.3)
    mk(P + 'PalmOil', '#c03c16', 0.08, spec=0.6, coat=0.5)
    mk(P + 'Rope', '#6a4a24', 0.9, T('Cloth', 'Normal'), tile('Cloth'))
    mk(P + 'Hide', '#e6d2aa', 0.55)
    mk(P + 'Skin', HEX['skin'], 0.55, spec=0.4)
    for name, hexc in (('ClothWhite', '#f4efe4'), ('ClothRed', '#c8302a'), ('ClothYellow', '#e0b030'),
                       ('ClothGreen', '#3f7a46'), ('ClothBlue', '#2a4a9a'), ('ClothPurple', '#8a3a8a'),
                       ('ClothBrown', '#6a4424'), ('ClothDark', '#3a2216')):
        mk(P + name, hexc, T('Cloth', 'Roughness'), T('Cloth', 'Normal'), tile('Cloth'), sheen=0.35,
           normal_strength=0.6, viewport=lin(hexc))
    mk(P + 'MaskWhite', '#f2ece0', 0.45, coat=0.2)
    mk(P + 'PaintBlack', '#1a1410', 0.6)
    mk(P + 'PaintRed', '#a8281e', 0.5)
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


def rect_pts(hx, hy, nx, ny):
    """Rectangle points CCW from above, starting at the front-left corner; fixed count 2*(nx+ny)."""
    pts = [(-hx + 2 * hx * k / nx, -hy) for k in range(nx)]
    pts += [(hx, -hy + 2 * hy * k / ny) for k in range(ny)]
    pts += [(hx - 2 * hx * k / nx, hy) for k in range(nx)]
    pts += [(-hx, hy - 2 * hy * k / ny) for k in range(ny)]
    return pts


def leaf_blob(mb, centre, r, rnd, mat, squash=0.72, segs=14, rings=9):
    """A lumpy ball of foliage."""
    sub = MB()
    prof = [(0.0, -1.0)] + [(math.sin(math.pi * k / rings), -math.cos(math.pi * k / rings)) for k in range(1, rings)] \
        + [(0.0, 1.0)]
    lathe(sub, prof, segs, mat)
    ph = [rnd.uniform(0, 6.28) for _ in range(3)]
    cx, cy, cz = centre
    for i, v in enumerate(sub.v):
        d = v.normalized() if v.length > 1e-9 else Vector((0, 0, 1))
        k = 1 + 0.13 * math.sin(3 * d.x + ph[0]) * math.cos(2 * d.y + ph[1]) + 0.08 * math.sin(5 * d.z + ph[2])
        sub.v[i] = Vector((cx + v.x * r * k, cy + v.y * r * k, cz + v.z * r * squash * k))
    mb.merge(sub)


LEAF = [(0.05, 0.0), (0.0, 1.0), (-0.05, 0.0), (0.0, -1.0)]   # flat leaf section: wide along B, thin along N


def along(mb_part, start, end):
    """Turn a part built along +X at the origin so it runs from start toward end."""
    d = (Vector(end) - Vector(start)).normalized()
    R = Vector((1, 0, 0)).rotation_difference(d).to_matrix().to_4x4()
    mb_part.transform(translate(*start) @ R)
    return mb_part


def yam_mb(L, r, rnd, mat):
    """A yam tuber along +X: blunt head, fat middle, tapering tail, slightly bent and lumpy."""
    n = 7
    bend = rnd.uniform(-0.07, 0.07) * L
    path = [Vector((x, bend * (1 - (2 * x / L) ** 2), 0.04 * L * rnd.uniform(-1, 1) * (2 * x / L)))
            for x in ((-0.5 + i / (n - 1)) * L for i in range(n))]
    prof = [0.3, 0.78, 0.97, 1.0, 0.88, 0.58, 0.16]
    radii = [r * p * rnd.uniform(0.94, 1.06) for p in prof]
    ph = [rnd.uniform(0, 6.28) for _ in range(n)]
    sub = MB()
    sweep(sub, path, radii, circle(8), mat, cap_start=True, cap_end=True, ref=Vector((0, 0, 1)),
          radial_fn=lambda i, k: 1 + 0.07 * math.sin(3 * k + ph[i]))
    return sub


# ---------------------------------------------------------------------------
# The elder's house
# ---------------------------------------------------------------------------
def build_base(coll):
    """NewYam_Base: the 0.25 m earth plinth under the house."""
    bm = bmesh.new()
    hx, hy = HALF_W + APRON, HALF_D + APRON
    c = [(-hx, -hy, 0), (hx, -hy, 0), (hx, hy, 0), (-hx, hy, 0), (-hx, -hy, PLINTH_H), (hx, -hy, PLINTH_H),
         (hx, hy, PLINTH_H), (-hx, hy, PLINTH_H)]
    v = [bm.verts.new(p) for p in c]
    for f in ((4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):   # no underside
        bm.faces.new([v[i] for i in f])
    bm.edges.ensure_lookup_table()
    edges = [e for e in bm.edges if len(e.link_faces) == 2]
    bmesh.ops.bevel(bm, geom=edges, offset=BASE_BEVEL, offset_type='OFFSET', segments=2, profile=0.5,
                    affect='EDGES', clamp_overlap=True)
    return kit.bm_to_object(bm, P + 'Base', coll, P + 'Plinth')


def build_step(coll):
    """NewYam_Step: a half-height step in front of the bay (assumption)."""
    mb = MB()
    y1 = -(HALF_D + APRON)
    box_mb(mb, -BAY_HW - 0.25, BAY_HW + 0.25, y1 - 0.40, y1, 0.0, STEP_H, P + 'Plinth', skip=('bottom', 'back'))
    return kit.mb_to_object(mb, P + 'Step', coll)


def build_walls(coll):
    """NewYam_Walls: 0.40 m red-brown earth walls with the wide open bay in the front
    (x 640..960); open at the top (under the roof) and the bottom (on the plinth)."""
    mb = MB()
    wall = P + 'EarthWall'
    doors = [dict(x0=-BAY_HW, x1=BAY_HW, top=Z0 + BAY_TOP)]
    rows = sorted({Z0, Z0 + BAY_TOP, Z1})
    eps = 1e-6

    def outline(hx, hy):
        """CCW plan outline with door edges on the front: (x, y, door index, door top)."""
        pts = [(-hx, -hy, None, Z0)]
        for di, d in enumerate(doors):
            pts += [(d['x0'], -hy, di, d['top']), (d['x1'], -hy, di, d['top'])]
        return pts + [(hx, -hy, None, Z0), (hx, hy, None, Z0), (-hx, hy, None, Z0)]

    def surface(pts, inward):
        isl = mb.island()
        cols = [{z: mb.vert((x, y, z)) for z in rows} for x, y, _, _ in pts]
        n = len(pts)
        u = [0.0]
        for k in range(n):
            a, b = pts[k], pts[(k + 1) % n]
            u.append(u[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        for k in range(n):
            k1 = (k + 1) % n
            A, B = pts[k], pts[k1]
            in_door = A[2] is not None and A[2] == B[2]
            for a0, a1 in zip(rows, rows[1:]):
                if in_door and a0 < A[3] - eps:
                    continue
                quad = [cols[k][a0], cols[k1][a0], cols[k1][a1], cols[k][a1]]
                uvq = [(u[k], a0), (u[k + 1], a0), (u[k + 1], a1), (u[k], a1)]
                if inward:
                    quad, uvq = quad[::-1], uvq[::-1]
                mb.face(quad, uvq, wall, False, isl)
        return cols

    outer_pts = outline(HALF_W, HALF_D)
    oc = surface(outer_pts, False)
    inner_pts = outline(HALF_W - WALL_T, HALF_D - WALL_T)
    ic = surface(inner_pts, True)
    t = WALL_T
    for di, d in enumerate(doors):
        oi = [k for k, p in enumerate(outer_pts) if p[2] == di]
        ii = [k for k, p in enumerate(inner_pts) if p[2] == di]
        jam_rows = [r for r in rows if r <= d['top'] + eps]
        for side, ko, kin in (('left', oi[0], ii[0]), ('right', oi[-1], ii[-1])):
            O, I = oc[ko], ic[kin]
            isl = mb.island()                          # one island per jamb: u across the wall, v up
            for r0, r1 in zip(jam_rows, jam_rows[1:]):
                quad = [O[r0], I[r0], I[r1], O[r1]] if side == 'left' else [I[r0], O[r0], O[r1], I[r1]]
                mb.face(quad, [(0, r0), (t, r0), (t, r1), (0, r1)], wall, False, isl)
        top = d['top']
        a, b, ai, bi = oi[0], oi[-1], ii[0], ii[-1]
        span = outer_pts[b][0] - outer_pts[a][0]
        mb.face([oc[a][top], ic[ai][top], ic[bi][top], oc[b][top]], [(0, 0), (t, 0), (t, span), (0, span)], wall,
                False, mb.island())
    return kit.mb_to_object(mb, P + 'Walls', coll)


def build_posts(coll):
    """NewYam_Posts: the three carved hardwood posts in the open bay (SVG x 630..650,
    790..810, 950..970), square with carved bands and a wider capital."""
    mb = MB()
    r = POST_W / 2 * math.sqrt(2)                      # a 4-sided lathe: corner radius of the square
    H = POST_TOP
    prof = [(r * 0.94, 0.0), (r, 0.10), (r, 0.20), (r * 0.8, 0.24), (r * 0.8, 0.34), (r, 0.38),
            (r, 1.06), (r * 0.82, 1.10), (r * 0.82, 1.28), (r, 1.32),
            (r, H - 0.42), (r * 0.8, H - 0.38), (r * 0.8, H - 0.26), (r, H - 0.22), (r * 1.1, H - 0.12),
            (r * 1.1, H), (0.0, H)]
    for x in POST_XS:
        sub = MB()
        lathe(sub, [(rr, Z0 + z) for rr, z in prof], 4, P + 'Wood', smooth=False, theta0=math.pi / 4)
        sub.transform(translate(x, POST_Y, 0))
        mb.merge(sub)
    return kit.mb_to_object(mb, P + 'Posts', coll)


def build_roof(coll):
    """NewYam_Roof: the thatched hip roof (SVG 500,484 - 680,360 - 920,360 - 1100,484) with
    equal pitch on all four sides, two stepped courses, a pale straw ridge roll, a soffit
    back to the wall line and a flat ceiling inside."""
    mb = MB()
    rnd = random.Random(31)
    th = P + 'Thatch'
    NX, NY = 16, 10
    npt = 2 * (NX + NY)
    z_eb = Z0 + EAVE_H
    z_et = z_eb + 0.2
    z_rg = Z0 + RIDGE_H
    lip = 0.06
    courses = [0.0, 0.42]

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
        mb.face([cen, wl[k1], wl[k]], [(0, 0), (b.x, b.y), (a.x, a.y)], th, False, ci_)
    # the pale straw roll along the ridge (the board's light ridge line)
    xs = [-hx_r - 0.2 + (2 * hx_r + 0.4) * k / 10 for k in range(11)]
    sweep(mb, [Vector((x, 0.0, z_rg - 0.03)) for x in xs], [0.12] * 11, circle(10), P + 'RidgeStraw',
          cap_start=True, cap_end=True, ref=Vector((0, 0, 1)), radial_fn=lambda i, k: 1 + 0.06 * math.sin(2.3 * i + k))
    return kit.mb_to_object(mb, P + 'Roof', coll)


def build_fringe(coll):
    """NewYam_RoofFringe: the sawtooth thatch fringe along the eave (SVG pattern 'fringe',
    14 px wide and 19 px deep), a thin band whose top tucks into the fascia."""
    mb = MB()
    mat = P + 'Thatch'
    z_top = Z0 + EAVE_H + 0.05
    spacing = 0.133
    nx, ny = int(round(2 * XE / spacing)), int(round(2 * YE / spacing))
    rnd = random.Random(5)
    outer = rect_pts(XE + 0.012, YE + 0.012, nx, ny)
    inner = rect_pts(XE - 0.012, YE - 0.012, nx, ny)
    n = len(outer)
    drop = [0.36 * rnd.uniform(0.85, 1.1) if k % 2 == 0 else 0.08 for k in range(n)]
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
    """NewYam_WallPaint: the white kaolin motifs in low relief: a zigzag high on each side
    of the front (SVG x 556..620 and 980..1044, y 506..520) and a column of four dots
    below each (x 560 and 1044, y 560..602). The side and back walls repeat them (assumption)."""
    mb = MB()
    k = P + 'Kaolin'
    z_lo, z_hi = Z0 + svg_h(520), Z0 + svg_h(506)
    half = 16 * PX
    dots_z = [Z0 + svg_h(y) for y in (560, 574, 588, 602)]

    def zig(fm, s0):
        pts = [(s0 + i * half, z_lo if i % 2 == 0 else z_hi) for i in range(5)]
        relief_stroke(mb, pts, 3 * PX, 0.006, fm, k)

    def dots(fm, s):
        for z in dots_z:
            relief_fill(mb, kit.ellipse(s, z, 2.4 * PX, 2.4 * PX, n=10), 0.006, fm, k)
    for fm in (plane_map((0, -HALF_D, 0), (1, 0, 0), (0, 0, 1)), plane_map((0, HALF_D, 0), (-1, 0, 0), (0, 0, 1))):
        zig(fm, svg_x(556))
        zig(fm, svg_x(980))
        dots(fm, svg_x(560))
        dots(fm, svg_x(1044))
    for sign in (1, -1):
        fm = plane_map((sign * HALF_W, 0, 0), (0, sign, 0), (0, 0, 1))
        zig(fm, -2 * half)
        dots(fm, -HALF_D + 0.4)
        dots(fm, HALF_D - 0.4)
    return kit.mb_to_object(mb, P + 'WallPaint', coll)


# ---------------------------------------------------------------------------
# The yams, the fire, palm oil and palm wine
# ---------------------------------------------------------------------------
def build_yam_heap(coll):
    """NewYam_YamHeap: the great heap of new yams (SVG x 674..928, y 550..646): rows of
    five, four, three, two and one on the front face as on the board, built as a stepped
    pile five layers deep in the grooves of the layer below. NewYam_Mat: the raffia mat."""
    rnd = random.Random(77)
    mb = MB()
    layers = [(5, 4), (4, 3), (3, 2), (2, 1), (1, 1)]
    z = 0.02 + 0.145
    for li, (nx, ny) in enumerate(layers):
        for j in range(nx):
            for k in range(ny):
                L, r = rnd.uniform(0.78, 0.96), rnd.uniform(0.13, 0.16)
                yam = yam_mb(L, r, rnd, P + 'YamSkin')
                x = (j - (nx - 1) / 2) * 0.95 + rnd.uniform(-0.04, 0.04)
                y = HEAP_Y + (k - (ny - 1) / 2) * 0.29 + rnd.uniform(-0.02, 0.02)
                yam.transform(translate(x, y, z) @ rot_z(rnd.uniform(-0.12, 0.12) + (math.pi if rnd.random() < 0.5 else 0))
                              @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, 'X'))
                mb.merge(yam)
        z += 0.25 if li < 3 else 0.29            # in the grooves of the layer below; the top yam sits on one
    heap = kit.mb_to_object(mb, P + 'YamHeap', coll)
    mat = MB()
    box_mb(mat, -MAT_HX, MAT_HX, MAT_Y0, MAT_Y1, 0.0, 0.02, P + 'Raffia', skip=('bottom',))
    return heap, kit.mb_to_object(mat, P + 'Mat', coll)


def stool_mb(mb, pos, seat, mat):
    sub = MB()
    lathe(sub, [(0.17, 0.0), (0.17, 0.035), (0.075, 0.07), (0.065, seat - 0.07), (0.17, seat - 0.035),
                (0.17, seat), (0.0, seat)], 14, mat)            # open underneath: it stands on the ground
    sub.transform(translate(pos[0], pos[1], 0))
    mb.merge(sub)


def build_hearth(coll):
    """NewYam_Hearth: the small fire where the first yam roasts (SVG x 648..680, y 640..656):
    three hearth stones, a bed of embers and a few sticks."""
    rnd = random.Random(12)
    mb = MB()
    fx, fy = FIRE
    for a in (90, 210, 330):
        t = math.radians(a)
        st = MB()
        ellipsoid(st, (0, 0, 0), (0.13, 0.11, 0.12), P + 'Stone', segs=9, rings=6)
        ph = [rnd.uniform(0, 6.28) for _ in range(2)]
        st.v = [Vector((v.x * (1 + 0.12 * math.sin(4 * v.y * 9 + ph[0])), v.y, v.z * (1 + 0.1 * math.sin(5 * v.x * 9 + ph[1]))))
                for v in st.v]
        st.transform(translate(fx + 0.21 * math.cos(t), fy + 0.21 * math.sin(t), 0.07) @ rot_z(t))
        mb.merge(st)
    ellipsoid(mb, (fx, fy, 0.012), (0.2, 0.2, 0.045), P + 'Ember', segs=14, rings=6)
    for a in (20, 100, 250, 330):
        t = math.radians(a)
        p0 = Vector((fx + 0.04 * math.cos(t), fy + 0.04 * math.sin(t), 0.045))
        p1 = Vector((fx + 0.55 * math.cos(t), fy + 0.55 * math.sin(t), 0.035))
        sweep(mb, [p0, p0.lerp(p1, 0.5), p1], [0.028, 0.032, 0.03], circle(7), P + 'WoodDark', cap_start=True,
              cap_end=True, ref=Vector((0, 0, 1)))
    stool_mb(mb, ELDER, 0.32, P + 'Wood')
    return kit.mb_to_object(mb, P + 'Hearth', coll)


def build_vessels(coll):
    """NewYam_Vessels: the calabash of red palm oil (SVG x 560..590) and two gourds of
    palm wine stoppered with leaves (x 944..998)."""
    mb = MB()
    bowl = MB()
    lathe(bowl, [(0.0, 0.0), (0.12, 0.005), (0.19, 0.05), (0.22, 0.12), (0.21, 0.13), (0.195, 0.125), (0.0, 0.125)],
          16, [P + 'Calabash'] * 5 + [P + 'PalmOil'])
    bowl.transform(translate(OIL[0], OIL[1], 0))
    mb.merge(bowl)
    for x, y, s in WINE:
        g = MB()
        lathe(g, [(0.0, 0.0), (0.1, 0.01), (0.2, 0.06), (0.24, 0.18), (0.21, 0.32), (0.1, 0.41), (0.055, 0.46),
                  (0.05, 0.58), (0.06, 0.6), (0.045, 0.62), (0.04, 0.66), (0.0, 0.68)], 14,
              [P + 'Calabash'] * 8 + [P + 'Leaves'] * 3)
        g.transform(translate(x, y, 0) @ Matrix.Diagonal((s, s, s, 1.0)))
        mb.merge(g)
    return kit.mb_to_object(mb, P + 'Vessels', coll)


# ---------------------------------------------------------------------------
# Figures (stylized, faceless, generic: no real person is depicted)
# ---------------------------------------------------------------------------
def standing_figure(wrap, upper=None, top=None, top_mat=None, scale=1.0, arms=None, flare=0.0, fans=False):
    """A standing figure built facing -Y, feet at the origin: a wrapper to the waist and a
    top above it. arms: per side (shoulder, elbow, hand); default hanging at the sides."""
    mb = MB()
    skin = P + 'Skin'
    upper = upper or wrap
    body = MB()
    lathe(body, [(0.0, -0.01), (0.2 + flare, -0.01), (0.19 + flare * 0.5, 0.45), (0.17, 0.9), (0.19, 1.12),
                 (0.22, 1.33), (0.19, 1.39), (0.1, 1.43), (0.0, 1.44)], 12, [wrap] * 3 + [upper] * 5)
    body.transform(Matrix.Diagonal((1.0, 0.72, 1.0, 1.0)))
    mb.merge(body)
    cylinder(mb, 0.05, 1.40, 1.50, skin, segs=8)
    ellipsoid(mb, (0, 0, 1.58), (0.1, 0.11, 0.12), skin)
    if top == 'gele':      # the two-lobed head-tie the board draws on its women and villagers
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
        sweep(mb, [Vector(sh), Vector(el), Vector(ha)], [0.055, 0.048, 0.042], circle(8), upper, cap_start=True,
              cap_end=True)
        ellipsoid(mb, ha, (0.045, 0.045, 0.055), skin, segs=6, rings=4)
        if fans:           # the white cloths the board's dancers wave
            ellipsoid(mb, (ha[0] * 1.04, ha[1], ha[2] + 0.09), (0.075, 0.016, 0.095), P + 'ClothWhite', segs=8, rings=5)
    mb.transform(Matrix.Diagonal((scale, scale, scale, 1.0)))
    return mb


def seated_figure(seat, top_mat, wrap_mat, cap_mat=None, arms=None):
    """A figure seated on a stool facing -Y: the lap and shins under a wrapper, feet on the ground."""
    mb = MB()
    skin = P + 'Skin'
    s = seat
    torso = MB()
    lathe(torso, [(0.0, s - 0.01), (0.2, s - 0.01), (0.2, s + 0.15), (0.185, s + 0.32), (0.205, s + 0.47),
                  (0.19, s + 0.53), (0.1, s + 0.58), (0.0, s + 0.59)], 12, [wrap_mat, wrap_mat] + [top_mat] * 5)
    torso.transform(Matrix.Diagonal((1.0, 0.72, 1.0, 1.0)))
    mb.merge(torso)
    lap = [(0.09 * math.cos(a), 0.2 * math.sin(a)) for a in (2 * math.pi * k / 10 for k in range(10))]
    sweep(mb, [Vector((0, -0.05, s + 0.08)), Vector((0, -0.3, s + 0.09)), Vector((0, -0.46, s + 0.06))], [1, 1, 0.95],
          lap, wrap_mat, cap_end=True, ref=Vector((0, 0, 1)))
    shin = [(0.07 * math.cos(a), 0.19 * math.sin(a)) for a in (2 * math.pi * k / 10 for k in range(10))]
    sweep(mb, [Vector((0, -0.44, s + 0.04)), Vector((0, -0.5, (s + 0.05) * 0.55)), Vector((0, -0.5, 0.05))],
          [1, 1.02, 1.05], shin, wrap_mat, cap_start=True, cap_end=True, ref=Vector((0, 1, 0)))
    for sgn in (-1, 1):
        box_mb(mb, sgn * 0.1 - 0.05, sgn * 0.1 + 0.05, -0.64, -0.46, 0.0, 0.07, skin, skip=('bottom',))
    arms = arms or [((sg * 0.2, 0.0, s + 0.47), (sg * 0.23, -0.1, s + 0.27), (sg * 0.16, -0.36, s + 0.17)) for sg in (-1, 1)]
    for sh, el, ha in arms:
        sweep(mb, [Vector(sh), Vector(el), Vector(ha)], [0.06, 0.055, 0.05], circle(8), top_mat, cap_start=True,
              cap_end=True)
        ellipsoid(mb, ha, (0.05, 0.05, 0.045), skin, segs=6, rings=4)
    cylinder(mb, 0.05, s + 0.55, s + 0.65, skin, segs=8)
    ellipsoid(mb, (0, 0, s + 0.72), (0.1, 0.11, 0.115), skin)
    if cap_mat:
        lathe(mb, [(0.094, s + 0.745), (0.106, s + 0.79), (0.095, s + 0.85), (0.05, s + 0.875), (0.0, s + 0.88)], 12,
              cap_mat)
    return mb


def build_elder(coll):
    """NewYam_Elder: the elder in a red cap and white top (SVG x 592..634), seated on a low
    stool and holding the first yam over the fire on a stick."""
    s = 0.32
    rnd = random.Random(8)
    hand = (0.2, -0.48, s + 0.33)
    arms = [((-0.2, 0.0, s + 0.47), (-0.23, -0.1, s + 0.27), (-0.16, -0.36, s + 0.17)),
            ((0.2, 0.0, s + 0.47), (0.27, -0.22, s + 0.38), hand)]
    mb = seated_figure(s, P + 'ClothWhite', P + 'ClothBrown', P + 'ClothRed', arms)
    reach = math.dist(ELDER, FIRE)
    tip = Vector((0.03, -reach - 0.08, 0.27))
    sweep(mb, [Vector(hand), Vector(hand).lerp(tip, 0.5), tip], [0.012, 0.012, 0.01], circle(6), P + 'WoodDark',
          cap_start=True, cap_end=True)
    yam = along(yam_mb(0.3, 0.06, rnd, P + 'YamRoasted'),
                Vector(hand).lerp(tip, 0.83), tip + (tip - Vector(hand)).normalized() * 0.12)   # over the embers
    mb.merge(yam)
    mb.transform(translate(ELDER[0], ELDER[1], 0) @ rot_z(facing(ELDER, FIRE)))
    return kit.mb_to_object(mb, P + 'Elder', coll)


def build_dancers(coll):
    """NewYam_Dancers: three women in red, yellow and green wrappers and head-ties, arms
    raised with white cloths (SVG 'dancer' symbol at x 250, 310 and 370)."""
    rnd = random.Random(23)
    mb = MB()
    for k, (x, y, col) in enumerate(DANCERS):
        lift = rnd.uniform(-0.05, 0.05)
        arms = [((s * 0.21, 0.0, 1.33), (s * 0.37, -0.05, 1.56 + lift * s), (s * 0.47, -0.08, 1.82 + lift * s))
                for s in (-1, 1)]
        f = standing_figure(P + col, upper=P + 'ClothDark', top='gele', top_mat=P + col, arms=arms, flare=0.05,
                            fans=True, scale=rnd.uniform(0.97, 1.02))
        f.transform(translate(x, y) @ rot_z(facing((x, y), ARENA_CENTRE) * 0.5 + rnd.uniform(-0.2, 0.2))
                    @ Matrix.Rotation(rnd.uniform(-0.06, 0.06), 4, 'Y'))
        mb.merge(f)
    return kit.mb_to_object(mb, P + 'Dancers', coll)


def build_drums(coll):
    """NewYam_Drums: the tall standing drum the board's drummer plays (SVG x 1108..1146,
    1.06 m) and a slit drum (ekwe) for a second drummer (assumption), with his stool."""
    mb = MB()
    wood, dark = P + 'Wood', P + 'WoodDark'
    rb, rt, h = 0.36, 0.245, 1.06
    sub = MB()
    lathe(sub, [(rb, 0.0), (rb * 0.97, h * 0.3), (rt * 1.04, h * 0.85), (rt, h - 0.02)], 18, wood)
    lathe(sub, [(rt - 0.02, h - 0.035), (rt + 0.022, h - 0.035), (rt + 0.022, h + 0.01), (rt - 0.02, h + 0.01)], 18,
          dark, closed=True)
    lathe(sub, [(rt + 0.01, h + 0.004), (rt * 0.5, h + 0.006), (0.0, h + 0.006)], 18, P + 'Hide')
    radius_at = lambda z: kit.interp([(0.0, rb), (h * 0.3, rb * 0.97), (h * 0.85, rt * 1.04), (h - 0.02, rt)], z)
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        p = MB()
        box_mb(p, -0.02, 0.02, -0.035, 0.005, h * 0.59, h * 0.66, dark)
        p.transform(rot_z(a + math.pi / 2) @ translate(0, -radius_at(h * 0.62), 0))
        sub.merge(p)
    sub.transform(translate(DRUM[0], DRUM[1], 0))
    mb.merge(sub)
    ek = MB()                                    # the slit drum: a hollowed log on two blocks
    xs = [-0.55 + 1.1 * k / 6 for k in range(7)]
    prof = [0.86, 0.95, 1.0, 1.0, 1.0, 0.95, 0.86]
    sweep(ek, [Vector((x, 0.0, 0.0)) for x in xs], [0.165 * p for p in prof], circle(12), dark, cap_start=True,
          cap_end=True, ref=Vector((0, 0, 1)))
    box_mb(ek, -0.36, 0.36, -0.018, 0.018, 0.155, 0.168, P + 'PaintBlack', skip=('bottom',))   # the slit
    ek.transform(translate(0, 0, 0.12 + 0.165))
    for sx in (-0.36, 0.36):
        box_mb(ek, sx - 0.07, sx + 0.07, -0.14, 0.14, 0.0, 0.14, wood, skip=('bottom',))
    ek.transform(translate(EKWE[0], EKWE[1], 0))
    mb.merge(ek)
    stool_mb(mb, (EKWE[0], EKWE[1] + 0.58), 0.3, wood)
    return kit.mb_to_object(mb, P + 'Drums', coll)


def build_drummers(coll):
    """NewYam_Drummers: the drummer in blue at the tall drum (SVG x 1146..1174) and a
    seated second drummer striking the slit drum."""
    mb = MB()
    arms = [((s * 0.22, 0, 1.33), (s * 0.27, -0.2, 1.14), (s * 0.12, -0.42, 1.08)) for s in (-1, 1)]
    d = standing_figure(P + 'ClothBlue', arms=arms)
    d.transform(translate(*DRUMMER) @ rot_z(facing(DRUMMER, DRUM)))
    mb.merge(d)
    s = 0.3
    arms = [((sg * 0.2, 0.0, s + 0.47), (sg * 0.27, -0.2, s + 0.32), (sg * 0.15, -0.42, s + 0.27)) for sg in (-1, 1)]
    e = seated_figure(s, P + 'ClothYellow', P + 'ClothDark', None, arms)
    for sg in (-1, 1):
        sweep(e, [Vector((sg * 0.15, -0.42, s + 0.27)), Vector((sg * 0.1, -0.58, 0.46))], [0.013, 0.011], circle(6),
              P + 'WoodDark', cap_start=True, cap_end=True)
    e.transform(translate(EKWE[0], EKWE[1] + 0.58, 0))
    mb.merge(e)
    return kit.mb_to_object(mb, P + 'Drummers', coll)


def build_masquerade(coll):
    """NewYam_Masquerade: the daytime masquerade (SVG x 1214..1306, y 448..666): a yellow skirt
    banded in black with white beads at the hem, a green cape, a red top, a white face mask,
    a blue crest and three yellow spikes, 4.1 m tall."""
    mb = MB()
    Y, K = P + 'ClothYellow', P + 'PaintBlack'
    lathe(mb, [(0.0, 0.03), (0.74, 0.03), (0.76, 0.07), (0.70, 0.46), (0.69, 0.51), (0.62, 0.84), (0.61, 0.89),
               (0.55, 1.18), (0.0, 1.18)], 20, [Y, Y, Y, K, Y, K, Y, Y])
    for k in range(12):
        a = 2 * math.pi * (k + 0.5) / 12
        ellipsoid(mb, (0.745 * math.cos(a), 0.745 * math.sin(a), 0.2), (0.035, 0.035, 0.035), P + 'MaskWhite',
                  segs=6, rings=4)
    lathe(mb, [(0.0, 1.06), (0.66, 1.06), (0.68, 1.1), (0.34, 1.75), (0.0, 1.75)], 20, P + 'ClothGreen')
    lathe(mb, [(0.0, 1.6), (0.46, 1.6), (0.47, 1.64), (0.11, 2.24), (0.0, 2.24)], 18, P + 'ClothRed')
    cylinder(mb, 0.1, 2.2, 2.42, P + 'ClothRed', segs=10)
    mc, mr = (0.0, -0.06, 2.6), (0.32, 0.14, 0.38)
    ellipsoid(mb, mc, mr, P + 'MaskWhite', segs=14, rings=10)

    def on_mask(x, z):
        q = 1 - (x / mr[0]) ** 2 - ((z - mc[2]) / mr[2]) ** 2
        return mc[1] - mr[1] * math.sqrt(max(q, 0.0))
    for sx in (-1, 1):
        ellipsoid(mb, (sx * 0.1, on_mask(sx * 0.1, 2.64), 2.64), (0.062, 0.02, 0.024), K, segs=8, rings=5)
    ellipsoid(mb, (0.0, on_mask(0.0, 2.48), 2.48), (0.05, 0.016, 0.018), P + 'PaintRed', segs=8, rings=5)
    lathe(mb, [(0.0, 2.8), (0.37, 2.82), (0.41, 3.0), (0.34, 3.3), (0.19, 3.55), (0.0, 3.7)], 16, P + 'ClothBlue')
    for a, b in (((-0.12, 0.0, 3.58), (-0.42, 0.0, 4.02)), ((0.0, 0.0, 3.64), (0.0, 0.0, 4.15)),
                 ((0.12, 0.0, 3.58), (0.42, 0.0, 4.02))):
        sweep(mb, [Vector(a), Vector(a).lerp(Vector(b), 0.5), Vector(b)], [0.035, 0.024, 0.0], circle(6), Y,
              cap_start=True)
    mb.transform(translate(*MASQ) @ rot_z(facing(MASQ, ARENA_CENTRE) * 0.5))   # half turned, as the board faces it out
    return kit.mb_to_object(mb, P + 'Masquerade', coll)


def build_villagers(coll):
    """NewYam_Villagers: the villagers crowding both edges (SVG 'crowd' symbols at x 40..150
    and 1380..1524), in head-ties and caps, facing the arena."""
    rnd = random.Random(41)
    mb = MB()
    spots = [(-11.6, -2.5), (-12.5, -3.2), (-11.4, -4.1), (-12.6, -4.9), (-11.7, -5.8), (-12.9, -6.5),
             (11.5, -2.4), (12.4, -3.1), (11.3, -4.0), (12.5, -4.8), (11.6, -5.7), (12.8, -6.4)]
    for k, (x, y) in enumerate(spots):
        mat = P + CROWD[k % len(CROWD)]
        top = 'gele' if k % 3 != 1 else 'cap'
        f = standing_figure(mat, top=top, top_mat=mat, scale=rnd.uniform(0.94, 1.04), flare=0.04 if top == 'gele' else 0)
        f.transform(translate(x, y) @ rot_z(facing((x, y), ARENA_CENTRE) + rnd.uniform(-0.25, 0.25)))
        mb.merge(f)
    return kit.mb_to_object(mb, P + 'Villagers', coll)


# ---------------------------------------------------------------------------
# Trees, palms, bushes, the frond string, the arena
# ---------------------------------------------------------------------------
def tree_anchor(k):
    """Where the frond string ties onto tree k: the trunk's arena side, at ROPE_Z."""
    x, y, yaw = TREES[k]
    return translate(x, y, 0) @ rot_z(yaw) @ Vector((0.3, 0.0, ROPE_Z))


def build_trees(coll):
    """NewYam_Trees: the two big shade trees framing the arena (SVG trunks x -20..140 and
    1510..1620, crowns over the top corners), 10 m tall with low crowns leaning outward."""
    mb = MB()
    bark, leaf = P + 'Bark', P + 'Leaves'
    rz = [(-0.2, 0.95), (0.15, 0.74), (0.6, 0.6), (1.8, 0.52), (3.0, 0.46), (4.2, 0.41), (5.2, 0.36), (6.6, 0.3)]
    NS = 16
    for t, (x, y, yaw) in enumerate(TREES):
        rnd = random.Random(17 + t)
        sub = MB()
        ph = rnd.uniform(0, 6)
        noise = lambda th, z, ph=ph: (1 + 0.05 * math.sin(3 * th + ph) + 0.04 * math.sin(5 * th + 0.7 * z)
                                      + 0.02 * math.sin(11 * th + 2 * z))
        sweep(sub, [Vector((0, 0, z)) for z, _ in rz], [r for _, r in rz], circle(NS), bark, ref=Vector((1, 0, 0)),
              cap_end=True, radial_fn=lambda i, k, noise=noise: noise(2 * math.pi * k / NS, rz[i][0]))
        limbs = [((0.0, 0.0, 3.8), (0.4, 0.3, 5.4), (1.2, 0.5, 6.5)), ((0.0, 0.1, 4.0), (-1.9, 0.8, 5.4), (-3.4, 1.2, 6.3)),
                 ((0.0, -0.1, 4.2), (-0.6, -1.6, 5.6), (-0.9, -3.0, 6.5)), ((0.0, 0.1, 4.4), (-0.8, 1.3, 5.9), (-1.3, 2.7, 7.0)),
                 ((0.0, 0.0, 4.8), (-0.4, 0.0, 6.3), (-0.7, 0.2, 7.6))]
        for path in limbs:
            sweep(sub, [Vector(p) for p in path], [0.28, 0.17, 0.07], circle(9), bark, cap_end=True, ref=Vector((0, 0, 1)))
        blobs = [((1.4, 0.5, 6.9), 2.1), ((-3.3, 1.2, 6.8), 2.3), ((-0.9, -3.0, 7.0), 2.2), ((-1.3, 2.7, 7.4), 2.2),
                 ((-0.7, 0.2, 8.1), 2.4), ((1.1, -1.9, 7.4), 1.9), ((-2.8, -1.7, 7.2), 2.0), ((0.7, 2.2, 7.7), 1.8),
                 ((-2.0, 0.0, 6.6), 1.8), ((2.5, -0.5, 6.7), 1.5), ((-4.8, 0.4, 6.6), 1.6)]
        for c, r in blobs:
            leaf_blob(sub, c, r, rnd, leaf)
        sub.transform(translate(x, y, 0) @ rot_z(yaw))
        mb.merge(sub)
    return kit.mb_to_object(mb, P + 'Trees', coll)


def build_palms(coll):
    """NewYam_Palms: two oil palms behind the house (SVG x 296..316 and 1288..1310)."""
    mb = MB()
    bark, frond = P + 'Bark', P + 'PalmLeaf'
    for k, (x, y, height) in enumerate(PALMS):
        rnd = random.Random(60 + k)
        lean = Vector((rnd.uniform(-0.04, 0.04), rnd.uniform(0.0, 0.05), 0.0))
        n = 7
        path = [Vector((x, y, 0.0)) + lean * (height * (i / (n - 1)) ** 1.5) + Vector((0, 0, height * i / (n - 1)))
                for i in range(n)]
        ph = rnd.uniform(0, 6)
        sweep(mb, path, [0.33, 0.27, 0.25, 0.24, 0.23, 0.22, 0.26], circle(10), bark, cap_end=True,
              ref=Vector((1, 0, 0)), radial_fn=lambda i, j, ph=ph: 1 + 0.06 * math.sin(2.1 * i + 3 * j + ph))
        top = path[-1]
        for j in range(14):
            a = 2 * math.pi * j / 14 + rnd.uniform(-0.15, 0.15)
            rise = rnd.uniform(0.25, 0.85)
            L = rnd.uniform(3.0, 3.8)
            d = Vector((math.cos(a), math.sin(a), 0.0))
            pts = [top + d * (L * t) + Vector((0, 0, L * (rise * t - (rise + 0.55) * t * t))) for t in (i / 5 for i in range(6))]
            sweep(mb, pts, [0.0, 0.3, 0.4, 0.36, 0.22, 0.0], LEAF, frond, ref=Vector((0, 0, 1)))
    return kit.mb_to_object(mb, P + 'Palms', coll)


def build_bushes(coll):
    """NewYam_Bushes: the dark bush clumps behind the house (SVG x 380..656 and 964..1240)."""
    mb = MB()
    for k, (x, y) in enumerate(BUSHES):
        rnd = random.Random(90 + k)
        for j in range(5):
            a = 2 * math.pi * j / 5 + rnd.uniform(-0.3, 0.3)
            rr = rnd.uniform(0.6, 1.5)
            leaf_blob(mb, (x + rr * math.cos(a), y + rr * math.sin(a), rnd.uniform(1.4, 2.3)), rnd.uniform(1.3, 1.8), rnd,
                      P + 'Leaves', squash=0.85, segs=12, rings=8)
    return kit.mb_to_object(mb, P + 'Bushes', coll)


def build_frond_string(coll):
    """NewYam_FrondString: the rope of young palm fronds hung between the two big trees
    (SVG path M0 120 Q 800 230 1600 110 with 19 pale fronds)."""
    rnd = random.Random(19)
    mb = MB()
    a, b = tree_anchor(0), tree_anchor(1)
    n = 24
    pts = []
    for i in range(n + 1):
        t = i / n
        p = a.lerp(b, t)
        p.z -= ROPE_SAG * 4 * t * (1 - t)
        pts.append(p)
    sweep(mb, pts, [0.014] * (n + 1), circle(6), P + 'Rope', ref=Vector((0, 0, 1)))
    nf = 19
    for i in range(nf):
        t = (i + 0.5) / nf
        top = a.lerp(b, t)
        top.z -= ROPE_SAG * 4 * t * (1 - t) + 0.01
        L = rnd.uniform(1.0, 1.25)
        sway = Vector((rnd.uniform(-0.06, 0.06), rnd.uniform(-0.08, 0.08), 0.0))
        path = [top] + [top + sway * (k / 4) ** 2 * 2 + Vector((0, 0, -0.04 - (L - 0.04) * k / 4)) for k in range(5)]
        sweep(mb, path, [0.0, 0.11, 0.1, 0.075, 0.04, 0.0], LEAF, P + 'YoungFrond', ref=Vector((0, 1, 0)))
    return kit.mb_to_object(mb, P + 'FrondString', coll)


def build_arena(coll):
    """NewYam_Arena: the swept laterite arena (flat, z = 0), lush grass behind the house and
    beyond 26 m, rolling out to 140 m."""
    mb = MB()
    cx, cy = ARENA_CENTRE
    rings = [0.0, 3, 6, 9, 12, 15, 18, 21, 24, 26, 30, 40, 50, 65, 85, 110, 140]
    segs = 64
    rnd = random.Random(9)
    ph = [rnd.uniform(0, 6.28) for _ in range(3)]

    def height(r, a):
        if r <= 26:
            return 0.0
        k = (r - 26) / (140 - 26)
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
        for j in range(segs):
            j1 = (j + 1) % segs
            f = [A[0], B[j], B[j1]] if len(A) == 1 else [A[j], B[j], B[j1], A[j1]]
            centre = sum((mb.v[k] for k in f), Vector()) / len(f)
            laterite = rings[i + 1] <= 26 and centre.y < 3.5
            mb.face(f, [uv(k) for k in f], P + ('Laterite' if laterite else 'Grass'), True, isl)
    return kit.mb_to_object(mb, P + 'Arena', coll, sharp_angle=60)


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------
def build_markers(coll, root):
    trg = P + 'TriggerVolume'
    vols = {
        'TRG_Bay': (-BAY_HW, BAY_HW, -HALF_D - 0.6, -HALF_D + WALL_T + 0.2, Z0, Z0 + BAY_TOP - 0.05),
        'TRG_Interior': (-(HALF_W - WALL_T) + 0.05, HALF_W - WALL_T - 0.05, -(HALF_D - WALL_T) + 0.05,
                         HALF_D - WALL_T - 0.05, Z0, Z1 - 0.05),
        'TRG_YamHeap': (-MAT_HX - 0.4, MAT_HX + 0.4, MAT_Y0 - 0.4, MAT_Y1 + 0.4, 0.0, 1.8),
        'TRG_FirstYam': (FIRE[0] - 1.7, FIRE[0] + 0.8, FIRE[1] - 0.9, FIRE[1] + 0.45, 0.0, 1.6),
        'TRG_Masquerade': (MASQ[0] - 1.2, MASQ[0] + 1.2, MASQ[1] - 1.2, MASQ[1] + 1.2, 0.0, 4.3),
    }
    for name, (x0, x1, y0, y1, z0, z1) in vols.items():
        mb = MB()
        box_mb(mb, x0, x1, y0, y1, z0, z1, trg)
        ob = kit.mb_to_object(mb, P + name, coll)
        ob.display_type = 'WIRE'
        ob.hide_render = True
        ob.visible_shadow = False
        ob.parent = root
    mid = tree_anchor(0).lerp(tree_anchor(1), 0.5)
    pts = {
        'SPAWN_P1': ((-1.45, -13.0, 0.0), (0, 0, -math.pi / 2), 'SINGLE_ARROW', 0.8, (1, 1, 1)),
        'SPAWN_P2': ((1.50, -13.0, 0.0), (0, 0, math.pi / 2), 'SINGLE_ARROW', 0.8, (1, 1, 1)),
        'VFX_FireSmoke': ((FIRE[0], FIRE[1], 0.5), (0, 0, 0), 'SPHERE', 0.3, (1, 1, 1)),
        'VFX_FireEmbers': ((FIRE[0], FIRE[1], 0.08), (0, 0, 0), 'SPHERE', 0.2, (1, 1, 1)),
        'VFX_Dust': ((0.0, -11.0, 0.3), (0, 0, 0), 'CUBE', 1.0, (6.0, 2.0, 0.5)),
        'VFX_FrondSway': ((mid.x, mid.y, ROPE_Z - ROPE_SAG - 0.4), (0, 0, 0), 'CUBE', 1.0, (8.0, 0.3, 0.8)),
        'SFX_Drums': ((DRUM[0], DRUM[1], 1.0), (0, 0, 0), 'SPHERE', 0.3, (1, 1, 1)),
        'SFX_Ekwe': ((EKWE[0], EKWE[1], 0.5), (0, 0, 0), 'SPHERE', 0.3, (1, 1, 1)),
        'SFX_Dancers': ((DANCERS[1][0], DANCERS[1][1], 1.6), (0, 0, 0), 'SPHERE', 0.3, (1, 1, 1)),
        'SFX_Masquerade': ((MASQ[0], MASQ[1], 2.0), (0, 0, 0), 'SPHERE', 0.3, (1, 1, 1)),
        'SFX_Fire': ((FIRE[0], FIRE[1], 0.3), (0, 0, 0), 'SPHERE', 0.3, (1, 1, 1)),
        'SFX_Crowd_L': ((-12.2, -4.5, 1.6), (0, 0, 0), 'SPHERE', 0.5, (1, 1, 1)),
        'SFX_Crowd_R': ((12.0, -4.4, 1.6), (0, 0, 0), 'SPHERE', 0.5, (1, 1, 1)),
    }
    for name, (loc, rot, kind, size, scale) in pts.items():
        e = bpy.data.objects.new(P + name, None)
        e.empty_display_type = kind
        e.empty_display_size = size
        e.location = loc
        e.rotation_euler = rot
        e.scale = scale
        coll.objects.link(e)
        e.parent = root
        e['newyam_marker'] = name


# ---------------------------------------------------------------------------
# Preview rig (not part of the asset): midday sky, sun, green hills, cameras, player
# ---------------------------------------------------------------------------
SUN_DIR = Vector((-0.12, -0.37, 0.92)).normalized()     # high midday sun, a little to the front left


def setup_world():
    w = bpy.data.worlds.new('Preview_MiddaySky')
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
    stops = [(0.0, '#6a5a3a'), (0.495, '#a89a70'), (0.5, '#e6f2f6'), (0.52, HEX['sky_low']), (0.6, '#8cc2ec'),
             (0.72, HEX['sky_mid']), (1.0, HEX['sky_top'])]
    el[0].position, el[0].color = stops[0][0], (*lin(stops[0][1]), 1)
    el[1].position, el[1].color = stops[-1][0], (*lin(stops[-1][1]), 1)
    for p, h in stops[1:-1]:
        e = el.new(p)
        e.color = (*lin(h), 1)
    noise = nt.nodes.new('ShaderNodeTexNoise')       # puffy cumulus, as on the board
    squash = nt.nodes.new('ShaderNodeMapping')
    squash.inputs['Scale'].default_value = (1.0, 1.0, 2.6)
    nt.links.new(tc.outputs['Generated'], squash.inputs['Vector'])
    nt.links.new(squash.outputs['Vector'], noise.inputs['Vector'])
    noise.inputs['Scale'].default_value = 2.4
    noise.inputs['Detail'].default_value = 6.0
    cl = nt.nodes.new('ShaderNodeValToRGB')
    nt.links.new(noise.outputs['Fac'], cl.inputs['Fac'])
    cl.color_ramp.elements[0].position = 0.58
    cl.color_ramp.elements[0].color = (0, 0, 0, 1)
    cl.color_ramp.elements[1].position = 0.66
    cl.color_ramp.elements[1].color = (0.92, 0.92, 0.92, 1)
    band = nt.nodes.new('ShaderNodeMapRange')
    nt.links.new(sep.outputs['Z'], band.inputs['Value'])
    band.inputs['From Min'].default_value = 0.04
    band.inputs['From Max'].default_value = 0.2
    mul = nt.nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    nt.links.new(cl.outputs['Color'], mul.inputs[0])
    nt.links.new(band.outputs['Result'], mul.inputs[1])
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
    kit.add_light(rig, 'Preview_Light_Sun', 'SUN', tuple(SUN_DIR * 100), (0, 0, 0), 4.4, '#fff2de', 1.0)
    bd = MB()
    rnd = random.Random(12)
    n = 96
    hills = [13 + 8 * math.sin(3 * a + 0.4) + 5 * math.sin(7 * a + 1.9) + rnd.uniform(-1.5, 1.5)
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
        front=kit.add_camera(rig, 'Preview_Cam_Front', (0.0, -27.0, 2.5), (0.0, -2.0, 3.9), 30),
        side=kit.add_camera(rig, 'Preview_Cam_Side', (27.0, -8.0, 4.2), (0.0, -5.5, 2.0), 35),
        threequarter=kit.add_camera(rig, 'Preview_Cam_ThreeQuarter', (14.2, -12.6, 6.0), (-1.0, -4.5, 1.0), 28),   # under the crowns
        threequarter_back=kit.add_camera(rig, 'Preview_Cam_ThreeQuarterBack', (-18.0, 17.0, 10.0), (0.0, -1.0, 2.4), 30),
        playerscale=kit.add_camera(rig, 'Preview_Cam_PlayerScale', (-1.6, -13.4, 1.85), (-0.4, -3.8, 1.45), 30),
        detail=kit.add_camera(rig, 'Preview_Cam_Detail', (-0.7, -9.7, 1.35), (-3.1, -6.4, 0.62), 36),
        plan=kit.add_camera(rig, 'Preview_Cam_Plan', (0.0, -6.5, 90.0), (0.0, -6.5, 0.0), 50, ortho=40.0),
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
        ob.visible_shadow = False
        cu.materials.append(kit.MATS['REF_Label'])
        ref.objects.link(ob)

    mannequin((-1.52, -2.35), Z0, 0.0)
    mannequin((3.35, -4.35), 0.0, math.radians(-15))
    mannequin((-0.7, -9.2), 0.0, math.radians(10))
    yaw = math.radians(-3)
    label('1.8 m player', (-1.52, -3.35, Z0 + 2.0), 0.13, yaw)
    label('open bay 2.36 m high, 2.66 m between posts', (-1.52, -3.35, Z0 + 2.75), 0.12, yaw)
    label('yam heap 1.35 m high', (3.35, -4.7, 2.05), 0.12, yaw)
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
        elif key in PLAN_COLOURS:
            if 'PLAN_' + key not in kit.MATS:
                kit.MATS['PLAN_' + key] = glow_mat('PLAN_' + key, PLAN_COLOURS[key], 0.9)
            mb = MB()
            lathe(mb, [(0.0, 0.0), (0.4, 0.0), (0.4, 0.05), (0.0, 0.05)], 20, 'PLAN_' + key)
            mb.transform(translate(ob.location.x, ob.location.y, 15.0))   # above the trees, so none is hidden
            disc = kit.mb_to_object(mb, 'PLAN_' + ob.name, kit.COLL['Preview_Rig'])
            kit.ASSET_OBJECTS.remove(disc)
            made.append(('delete', disc))
    return made


def render_views(views, cams, out_dir, debug_normals=False):
    sc = bpy.context.scene
    os.makedirs(out_dir, exist_ok=True)
    ref = kit.COLL.get('REF_PlayerScale')
    names = dict(front='NewYam_Front', side='NewYam_Side', threequarter='NewYam_ThreeQuarter',
                 threequarter_back='NewYam_ThreeQuarter_Back', playerscale='NewYam_PlayerScale',
                 detail='NewYam_Detail_FirstYam', plan='NewYam_Plan')
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
    p = argparse.ArgumentParser(prog='build_newyam.py')
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
    print('New Yam build -> %s' % out)
    tex = generate_textures(os.path.join(out, 'Textures'), args.skip_textures)
    build_materials(tex)

    root_c = kit.collection('NewYam')
    c_arch = kit.collection(P + 'Architecture', root_c)
    c_props = kit.collection(P + 'Props', root_c)
    c_fig = kit.collection(P + 'Figures', root_c)
    c_land = kit.collection(P + 'Landmarks', root_c)
    c_terr = kit.collection(P + 'Terrain', root_c)
    c_mark = kit.collection(P + 'Markers', root_c)
    root = bpy.data.objects.new('NewYam', None)
    root.empty_display_type = 'PLAIN_AXES'
    root_c.objects.link(root)

    build_base(c_arch)
    build_step(c_arch)
    build_walls(c_arch)
    build_posts(c_arch)
    build_roof(c_arch)
    build_fringe(c_arch)
    build_wall_paint(c_arch)
    build_yam_heap(c_props)
    build_hearth(c_props)
    build_vessels(c_props)
    build_drums(c_props)
    build_elder(c_fig)
    build_dancers(c_fig)
    build_drummers(c_fig)
    build_masquerade(c_fig)
    build_villagers(c_fig)
    build_trees(c_land)
    build_palms(c_land)
    build_bushes(c_land)
    build_frond_string(c_land)
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
    bpy.context.scene.view_settings.exposure = -0.2
    bpy.context.scene.camera = cams['front']

    blend = os.path.join(out, 'NewYam.blend')
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
