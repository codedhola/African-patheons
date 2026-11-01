"""Paint her aṣọ-òkè: white strip-woven cotton for the ìró and bùbá, gold for the sash.

Maps follow the same scheme as Ahiajoku's akwete.py, so materials.akwete can wear them: U repeats
every 60.5 cm along the cloth, V covers 1.15 m across. The white cloth is eleven strips
10.5 cm wide, sewn edge to edge. Two thin pale-gold lines run down each strip; the strip
width follows the Ṣàngó render and the lines are this study's.
"""
import numpy as np

from weave import CELL, COLS, H, ROWS, W, paint_weave, save, save_gray

WHITE = np.array([0.945, 0.925, 0.875])
PALE_GOLD = np.array([0.900, 0.690, 0.300])
GOLD = np.array([0.905, 0.610, 0.080])
AMBER = np.array([0.700, 0.360, 0.040])
CORAL = np.array([0.760, 0.200, 0.120])
IVORY = np.array([0.950, 0.900, 0.760])
STRIPS = 11


def streaks(rng, width, spans):
    s = rng.normal(0, 1, width).astype(np.float32)
    for size in spans:
        kernel = np.ones(size) / size
        s += 2.2 * np.convolve(np.tile(s, 3), kernel, 'same')[width:2 * width].astype(np.float32)
    return (s - s.mean()) / s.std()


def thread_profile(n, per_cell=3):
    y = np.arange(n)
    return np.abs(np.sin(np.pi * ((y % (CELL / per_cell)) / (CELL / per_cell))))[:, None] ** 0.55


def white(out):
    rng = np.random.default_rng(11)
    colour = np.empty((H, W, 3), np.float32)
    colour[:] = WHITE
    height = np.full((H, W), 0.42, np.float32)
    floats = np.zeros((H, W), np.float32)

    # warp runs along U, so warp streaks are rows here
    streak = streaks(rng, H, (3, 13, 47))[:, None]
    colour *= (1 + 0.008 * streak)[:, :, None]
    height += 0.05 * streak / 3
    bars = streaks(rng, W, (5, 23))[None, :]        # the beat wandering across the strip
    colour *= (1 + 0.004 * bars)[:, :, None]

    strip = H / STRIPS
    pos = (np.arange(H) % strip) / strip
    index = (np.arange(H) / strip).astype(int)
    tone = rng.uniform(0.985, 1.0, STRIPS)[index]        # each strip off a slightly different warp
    colour *= tone[:, None, None]
    # the seam: two selvedges butted and whip-stitched
    seam = np.exp(-(np.minimum(pos, 1 - pos) / 0.012) ** 2)[:, None]
    height = height - 0.30 * seam
    colour *= (1 - 0.17 * seam)[:, :, None]
    stitch = (np.sin(np.arange(W) / W * 2 * np.pi * 150)[None, :] > 0) * (np.minimum(pos, 1 - pos)[:, None] < 0.012)
    height = np.where(stitch, height + 0.34, height)
    # two fine gold lines just inside each selvedge
    for a in (0.095, 0.905):
        band = np.abs(pos - a) < 0.012
        colour[band] = PALE_GOLD
        height[band] += 0.20
        floats[band] = 1

    rgba = np.dstack([np.clip(colour, 0, 1), np.ones((H, W), np.float32)])
    save(out / 'ofi_color.png', rgba)
    save_gray(out / 'ofi_height.png', np.clip(height, 0, 1))
    save_gray(out / 'ofi_float.png', floats)


def gold(out):
    """Rows of stripes in gold, amber, ivory and coral. The sash uses one 27 cm band of this."""
    rng = np.random.default_rng(12)
    cells = np.zeros((ROWS, COLS), np.int8)
    palette = [GOLD, AMBER, IVORY, CORAL]
    # one 64-cell repeat across, mirrored so both selvedges match
    half = [(0, 5), (1, 1), (0, 3), (2, 1), (3, 1), (2, 1), (0, 7), (1, 2), (0, 7), (3, 2), (0, 2)]
    row = []
    for c, n in half:
        row += [c] * n
    row = row + row[::-1]
    for r in range(ROWS):
        cells[r, :] = row[r % len(row)]
    # small lozenges of float in the wide gold bands, every 19 cells along the cloth
    n = len(row)
    for r in range(ROWS):
        for c in range(COLS):
            local = r % n
            for centre in (13, n - 14):
                d = abs(local - centre) + abs((c % 19) - 9)
                if d == 3 or d == 0:
                    cells[r, c] = 2
    expand = np.repeat(np.repeat(cells, CELL, 0), CELL, 1)
    colour = np.empty((H, W, 3), np.float32)
    for k, c in enumerate(palette):
        colour[expand == k] = c
    streak = streaks(rng, H, (3, 13))[:, None]
    profile = thread_profile(W)[::1].T
    colour *= (1 + 0.05 * streak)[:, :, None]
    colour *= (0.86 + 0.20 * np.abs(np.sin(np.arange(H) / H * np.pi * ROWS * 4))[:, None] ** 0.5)[:, :, None]
    height = 0.45 + 0.28 * profile * np.ones((H, 1), np.float32) + 0.05 * streak
    metallic = ((expand == 0) | (expand == 1)).astype(np.float32)
    rgba = np.dstack([np.clip(colour, 0, 1), np.ones((H, W), np.float32)])
    save(out / 'gold_color.png', rgba)
    save_gray(out / 'gold_height.png', np.clip(height, 0, 1))
    save_gray(out / 'gold_float.png', metallic)


def paint(out):
    white(out)
    gold(out)
    paint_weave(out)
