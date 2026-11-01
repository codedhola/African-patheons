"""Paint the Akwete cloth: a cream warp-faced ground with brocade bands in floats.

Everything is built from a grid of 4.2 mm cells, the way supplementary-weft
motifs are counted. The map is one full cloth high (1.15 m, the width of the
loom) and one 60.5 cm repeat across, so U repeats and V does not.

Writes akwete_color.png, akwete_height.png, akwete_float.png, weave_height.png.
"""
import numpy as np

CELL = 14                # pixels per grid cell
ROWS, COLS = 274, 144    # 274 x 4.2 mm = 1.15 m, 144 x 4.2 mm = 60.5 cm
W, H = COLS * CELL, ROWS * CELL

CREAM = np.array([0.905, 0.865, 0.745])
GREEN = np.array([0.150, 0.340, 0.190])
RED = np.array([0.640, 0.170, 0.125])
INDIGO = np.array([0.085, 0.120, 0.270])
COLOURS = [None, GREEN, RED, INDIGO]
G, R, I = 1, 2, 3


def ikaki(grid, cx, cy, shell, heart):
    """The tortoise. Same layout as the gallery's canvas texture."""
    def put(x, y, c):
        grid[(cy + y) % ROWS, (cx + x) % COLS] = c
    for y in range(-6, 7):
        k = 6 - abs(y)
        for x in range(-k, k + 1):
            if (x + y) % 2 == 0:
                put(x, y, shell)
    for y in range(-2, 3):
        k = 2 - abs(y)
        for x in range(-k, k + 1):
            put(x, y, heart)
    for x, y in [(0, -8), (0, -9), (-1, -9), (1, -9), (0, 8), (0, 9)]:
        put(x, y, shell)
    for dx, dy in [(-5, -4), (5, -4), (-5, 4), (5, 4)]:
        sx, sy = np.sign(dx), np.sign(dy)
        put(dx, dy, shell)
        put(dx + sx, dy + sy, shell)
        put(dx + 2 * sx, dy + sy, shell)


def lozenge(grid, cx, cy, r, outer, inner):
    for y in range(-r, r + 1):
        k = r - abs(y)
        for x in range(-k, k + 1):
            edge = abs(x) + abs(y) >= r - 1
            core = abs(x) + abs(y) <= max(1, r - 4)
            if edge:
                grid[(cy + y) % ROWS, (cx + x) % COLS] = outer
            elif core:
                grid[(cy + y) % ROWS, (cx + x) % COLS] = inner


def rule(grid, y, height, c):
    grid[y:y + height, :] = c


def saw(grid, y, amp, c, pitch=12):
    """The saw: a zigzag two cells thick."""
    for x in range(COLS):
        t = (x % pitch) / pitch
        h = int(round(amp * (1 - abs(2 * t - 1))))
        grid[y + h:y + h + 2, x] = c


def draughts(grid, y, height, c, size=2):
    for r in range(height):
        for x in range(COLS):
            if ((r // size) + (x // size)) % 2 == 0:
                grid[y + r, x] = c


def layout():
    """Row 0 is the hem and rows climb toward the cloth's other edge."""
    grid = np.zeros((ROWS, COLS), np.int8)
    rule(grid, 2, 4, I)
    rule(grid, 8, 1, R)
    draughts(grid, 11, 4, G)
    rule(grid, 17, 1, R)
    for i in range(6):
        ikaki(grid, 12 + i * 24, 31, G, R)
    rule(grid, 43, 1, R)
    saw(grid, 46, 4, I)
    rule(grid, 54, 1, R)
    for row, offset, outer, inner in [(84, 0, R, G), (150, 12, G, R), (216, 0, R, I)]:
        rule(grid, row - 12, 1, G)
        saw(grid, row - 9, 2, R if outer == G else G)
        for i in range(6):
            lozenge(grid, offset + i * 24, row + 5, 8, outer, inner)
        saw(grid, row + 16, 2, R if outer == G else G)
        rule(grid, row + 21, 1, G)
    for row in (118, 184):
        for i in range(6):
            ikaki(grid, (i * 24 + (6 if row == 118 else 18)) % COLS, row, I, R)
    rule(grid, 262, 1, R)
    draughts(grid, 264, 4, G)
    rule(grid, 269, 3, I)
    return grid


def smooth_noise(rng, shape, scale_y, scale_x):
    """Tileable low-frequency noise, summed sines of random phase."""
    h, w = shape
    y, x = np.mgrid[0:h, 0:w]
    out = np.zeros(shape, np.float32)
    for _ in range(14):
        fy = rng.integers(0, 6) * scale_y
        fx = rng.integers(1, 8) * scale_x
        out += np.sin(2 * np.pi * (fy * y / h + fx * x / w) + rng.uniform(0, 6.28)).astype(np.float32)
    return out / 14


def paint(out):
    rng = np.random.default_rng(31)
    grid = layout()
    cells = np.repeat(np.repeat(grid, CELL, 0), CELL, 1)
    colour = np.empty((H, W, 3), np.float32)
    colour[:] = CREAM

    # warp-faced ground: long streaks along the warp and faint bars where the beat wandered
    streak = rng.normal(0, 1, W).astype(np.float32)
    for size in (3, 11, 41):
        kernel = np.ones(size) / size
        streak += 2.2 * np.convolve(np.tile(streak, 3), kernel, 'same')[W:2 * W].astype(np.float32)
    streak = (streak - streak.mean()) / streak.std()
    bars = smooth_noise(rng, (H, 1), 8, 0).reshape(H, 1)
    colour *= (1 + 0.016 * streak)[None, :, None]
    colour *= (1 + 0.03 * bars)[:, :, None]

    # the floats: three threads a cell, tied down every few cells in a brick pattern
    float_mask = (cells > 0).astype(np.float32)
    y = np.arange(H)
    profile = np.abs(np.sin(np.pi * ((y % (CELL / 3)) / (CELL / 3))))[:, None] ** 0.55
    height = 0.30 + 0.05 * (streak / 3)[None, :] * np.ones((H, 1), np.float32)
    height = np.broadcast_to(height, (H, W)).copy()
    height += 0.05 * bars
    thread_tone = rng.uniform(0.88, 1.12, (ROWS * 3 + 3, 1))[(y * 3 // CELL)].astype(np.float32)

    tie = np.zeros((H, W), np.float32)
    for row in range(ROWS * 3):
        y0 = row * CELL // 3
        y1 = (row + 1) * CELL // 3
        step = CELL * 4
        offs = (row * 5 % 4) * CELL
        for x in range(offs, W, step):
            tie[y0:y1, x:x + 3] = 1

    for k, c in enumerate(COLOURS):
        if c is None:
            continue
        m = cells == k
        lit = (0.72 + 0.42 * profile) * thread_tone
        colour[m] = (c[None, None, :] * lit[:, :, None] * np.ones((H, W, 1), np.float32))[m]
    colour[(tie > 0) & (cells > 0)] = CREAM * 0.72
    height = np.where(cells > 0, 0.56 + 0.40 * profile, height)
    height = np.where((tie > 0) & (cells > 0), 0.34, height)

    rgba = np.dstack([np.clip(colour, 0, 1), np.ones((H, W), np.float32)])
    save(out / 'akwete_color.png', rgba)
    save_gray(out / 'akwete_height.png', np.clip(height, 0, 1))
    save_gray(out / 'akwete_float.png', float_mask)
    paint_weave(out)


def paint_weave(out):
    """One plain-weave repeat of 8 x 8 threads, tiled in the shader."""
    n = 256
    yy, xx = np.mgrid[0:n, 0:n] / n * 8
    warp = np.abs(np.sin(np.pi * xx)) ** 0.7
    weft = np.abs(np.sin(np.pi * yy)) ** 0.7
    over = (np.floor(xx) + np.floor(yy)) % 2
    save_gray(out / 'weave_height.png', np.where(over > 0, warp * (0.65 + 0.35 * weft), weft * (0.65 + 0.35 * warp)))


def save(path, rgba):
    import bpy
    h, w = rgba.shape[:2]
    img = bpy.data.images.new(path.stem, w, h, alpha=True, float_buffer=False)
    img.colorspace_settings.name = 'sRGB'
    img.pixels.foreach_set(rgba.astype(np.float32).ravel())
    img.filepath_raw = str(path)
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


def save_gray(path, a):
    rgba = np.dstack([a, a, a, np.ones_like(a)]).astype(np.float32)
    save(path, rgba)
