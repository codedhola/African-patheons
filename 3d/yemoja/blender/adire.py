"""Paint her àdìrẹ and the cloth of her gèlè.

Àdìrẹ is indigo cloth patterned by Yorùbá women with a resist: for eleko, cassava paste is
painted on with a feather before dyeing, and where it cracks the dye runs in as fine dark
veins. Abẹ́òkúta, her cult centre, is considered the capital of the craft, and its themes
include plants, animals and tools (Wikipedia: Adire). This cloth is laid out as eleko cloths
often are, in squares, and its motifs are this study's: fish, her children; cowries, her
wealth; ripples, waves, a leaf and a star.

Maps follow the scheme of Ahiajoku's akwete.py so materials.akwete can wear them: U repeats
every 60.5 cm along the cloth and V covers 1.15 m across it.
"""
import numpy as np

from procedural import Noise
from weave import H, W, paint_weave, save, save_gray

INDIGO = np.array([0.045, 0.060, 0.145])          # sRGB: dyed many times over
MID = np.array([0.20, 0.30, 0.50])
PALE = np.array([0.50, 0.60, 0.76])               # where the paste kept most of the dye out
ACROSS, ALONG = 11, 6                             # squares across the cloth, and in one repeat along it
LIGHT_BLUE = np.array([0.56, 0.76, 0.90])         # her colour, for the gèlè


def ss(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def line(d, width):
    """Coverage of a painted line from an unsigned distance in the square's units."""
    return ss(width - d, -0.006, 0.006)


def motif(kind, u, v):
    """Pale coverage of one motif in a square, from local coordinates -1 to 1."""
    r = np.hypot(u, v)
    a = np.arctan2(v, u)
    w = 0.022
    if kind == 0:          # fish: a body, a tail, an eye, scales
        body = np.hypot(u / 0.62, v / 0.30)
        out = line(np.abs(body - 1) * 0.30, w)
        tail = (u < -0.58) & (u > -0.90) & (np.abs(v) < (-(u + 0.58)) * 0.95)
        out = np.maximum(out, line(np.abs(np.abs(v) - (-(u + 0.58)) * 0.95) * 0.7, w) * (u < -0.56) * (u > -0.90))
        out = np.maximum(out, line(np.abs(u + 0.90), w) * (np.abs(v) < 0.31))
        out = np.maximum(out, ss(0.06 - np.hypot(u - 0.36, v - 0.06), -0.01, 0.01))
        scales = (body < 0.9) & (u < 0.25) & (u > -0.5)
        arcs = np.abs(((u * 6 + np.abs(v) * 3) % 1) - 0.5) * 0.16
        out = np.maximum(out, line(arcs, w * 0.6) * scales)
        return np.maximum(out, tail * 0.0)
    if kind == 1:          # a cowrie: an oval with a toothed slit
        oval = np.hypot(u / 0.42, v / 0.62)
        out = line(np.abs(oval - 1) * 0.42, w)
        out = np.maximum(out, line(np.abs(u), w * 0.8) * (np.abs(v) < 0.48))
        teeth = (np.abs(u) < 0.12) & (np.abs(v) < 0.44)
        out = np.maximum(out, line(np.abs(((v * 9) % 1) - 0.5) * 0.11, w * 0.5) * teeth)
        return out
    if kind == 2:          # ripples
        out = np.zeros_like(u)
        for rad in (0.16, 0.38, 0.60, 0.82):
            out = np.maximum(out, line(np.abs(r - rad), w))
        return np.maximum(out, ss(0.07 - r, -0.01, 0.01))
    if kind == 3:          # a leaf, its midrib and veins
        lens = np.abs(v) - 0.38 * np.cos(np.clip(u, -1, 1) * np.pi / 2) ** 0.8
        out = line(np.abs(lens), w) * (np.abs(u) < 0.95)
        out = np.maximum(out, line(np.abs(v), w * 0.8) * (np.abs(u) < 0.92))
        veins = line(np.abs(((u - np.abs(v) * 0.9) * 4) % 1 - 0.5) * 0.25, w * 0.6) * (lens < -0.02) * (np.abs(u) < 0.8)
        return np.maximum(out, veins)
    if kind == 4:          # a star of strokes round a ring
        spokes = line(np.abs(np.sin(a * 6)) * r * 0.5, w * 0.8) * (r > 0.28) * (r < 0.86)
        return np.maximum(spokes, line(np.abs(r - 0.2), w))
    # waves
    out = np.zeros_like(u)
    for k, off in enumerate((-0.5, 0.0, 0.5)):
        out = np.maximum(out, line(np.abs(v - off - 0.14 * np.sin(u * np.pi * 2.5 + k)), w) * (np.abs(u) < 0.88))
    return out


def adire_block(y0, y1, n1, n2):
    """Colour and height of rows y0 to y1: painted in blocks, so the whole cloth never sits in memory at once."""
    y, x = np.mgrid[y0:y1, 0:W].astype(np.float32)
    pos = np.stack([x / W * 6, y / H * 11, np.zeros_like(x)], -1)
    # a hand-painted line wanders: displace the grid a little with smooth noise
    gx = x / W * ALONG + n1.fbm(pos * 1.7, 2) * 0.10
    gy = y / H * ACROSS + n1.fbm(pos * 1.7 + 9.1, 2) * 0.10
    i, j = np.floor(gx), np.floor(gy)
    u = (gx - i) * 2 - 1
    v = (gy - j) * 2 - 1
    kinds = ((i.astype(int) % ALONG) * 5 + (j.astype(int) % ACROSS) * 2) % 6
    pale = np.zeros(x.shape, np.float32)
    for k in range(6):
        m = kinds == k
        if not m.any():
            continue
        uu, vv = u[m] * 1.18, v[m] * 1.18
        # turn alternate squares a quarter turn, as a painter working along a row might
        flip = ((i[m] + j[m]) % 2) == 1
        uu, vv = np.where(flip, vv, uu), np.where(flip, -uu, vv)
        pale[m] = motif(k, uu, vv)
    # each square framed by a double line
    edge = np.minimum(1 - np.abs(u), 1 - np.abs(v))
    pale = np.maximum(pale, line(np.abs(edge - 0.035), 0.014))
    pale = np.maximum(pale, line(np.abs(edge - 0.090), 0.009))
    # paste laid thick or thin: the pale is never quite even
    pale = pale * (0.62 + 0.38 * (n2.fbm(pos * 6.0, 2) * 0.5 + 0.5))
    # cracks in the dried paste let the dye in as fine veins
    crack = np.abs(n2.fbm(pos * np.array([38.0, 38.0, 1.0], np.float32), 2))
    veins = ss(0.035 - crack, 0.0, 0.02) * (pale > 0.3)
    colour = INDIGO[None, None] * (1 - pale[..., None]) + PALE[None, None] * pale[..., None]
    colour = colour * (1 - veins[..., None] * 0.55) + MID[None, None] * veins[..., None] * 0.55
    # the dye's own unevenness from bath to bath
    blot = n1.fbm(pos * np.array([2.2, 1.4, 1.0], np.float32) + 4.0, 2)
    colour = colour * (1 + 0.06 * blot[..., None])
    return np.clip(colour, 0, 1).astype(np.float32), (0.45 + 0.04 * blot).astype(np.float32)


def adire(out):
    n1, n2 = Noise(3), Noise(8)
    colour = np.empty((H, W, 3), np.float32)
    height = np.empty((H, W), np.float32)
    for y0 in range(0, H, 320):
        y1 = min(y0 + 320, H)
        colour[y0:y1], height[y0:y1] = adire_block(y0, y1, n1, n2)
    rgba = np.dstack([colour, np.ones((H, W), np.float32)])
    save(out / 'adire_color.png', rgba)
    save_gray(out / 'adire_height.png', np.clip(height, 0, 1))
    save_gray(out / 'adire_float.png', np.zeros((H, W), np.float32))


def gele(out):
    """Light blue, stiff and a little shiny, with a woven damask lattice of floats."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    gx = x / W * 12
    gy = y / H * 24
    u = (gx % 1) * 2 - 1
    v = (gy % 1) * 2 - 1
    lozenge = np.abs(u) + np.abs(v)
    floats = np.maximum(line(np.abs(lozenge - 0.85), 0.07), ss(0.22 - np.hypot(u, v), -0.02, 0.02))
    colour = LIGHT_BLUE[None, None] * (1 + 0.07 * floats[..., None])
    height = 0.42 + 0.20 * floats
    rgba = np.dstack([np.clip(colour, 0, 1), np.ones((H, W), np.float32)])
    save(out / 'gele_color.png', rgba)
    save_gray(out / 'gele_height.png', np.clip(height, 0, 1))
    save_gray(out / 'gele_float.png', floats.astype(np.float32))


def paint(out):
    adire(out)
    gele(out)
    paint_weave(out)
