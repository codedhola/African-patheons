"""Paint her akwa miri and the white cloth of her head tie.

Akwa miri, "cloth of the water", is a commonly traded Akwete cloth, woven white or white with
indigo stripes (Wikipedia: Akwete cloth); her gallery figure wears it with the stripes running
down the wrapper, a broad stripe and two fine lines in each group. The spacing is this study's.

Maps follow the scheme of Ahiajoku's akwete.py so materials.akwete can wear them: U repeats
every 60.5 cm along the cloth, round her body, and V covers 1.15 m across it, hem to top.
"""
import numpy as np

from weave import H, W, paint_weave, save, save_gray

WHITE = np.array([0.925, 0.915, 0.885])         # sRGB: bleached cotton, not quite paper white
INDIGO = np.array([0.140, 0.215, 0.430])         # the gallery's indigo
GROUPS = 4                                       # stripe groups in one 60.5 cm repeat: one every 15 cm


def streaks(rng, n, spans):
    s = rng.normal(0, 1, n).astype(np.float32)
    for size in spans:
        kernel = np.ones(size) / size
        s += 2.2 * np.convolve(np.tile(s, 3), kernel, 'same')[n:2 * n].astype(np.float32)
    return (s - s.mean()) / s.std()


def akwamiri(out):
    rng = np.random.default_rng(31)
    u = (np.arange(W) + 0.5) / W * 0.605                 # metres along the cloth
    period = 0.605 / GROUPS
    p = u % period
    soft = lambda d, half: np.clip((half - np.abs(d)) / 0.00035 + 0.5, 0, 1)
    stripe = np.maximum.reduce([soft(p - 0.020, 0.0050), soft(p - 0.037, 0.0011), soft(p - 0.046, 0.0011)])
    # dyed threads take the indigo unevenly, and the white is a little warm in places
    thread = streaks(rng, W, (2, 7))[None, :]
    drift = streaks(rng, H, (25, 120))[:, None]
    colour = np.empty((H, W, 3), np.float32)
    colour[:] = WHITE
    colour = colour * (1 - 0.012 * np.clip(drift, -2, 2))[..., None]
    indigo = INDIGO[None, None] * (1 + 0.08 * np.clip(thread, -2, 2))[..., None]
    colour = colour * (1 - stripe[None, :, None]) + indigo * stripe[None, :, None]
    height = np.full((H, W), 0.45, np.float32) + 0.03 * np.clip(thread, -2, 2) + 0.06 * stripe[None, :]
    floats = np.zeros((H, W), np.float32)
    save(out / 'akwamiri_color.png', np.dstack([np.clip(colour, 0, 1), np.ones((H, W), np.float32)]))
    save_gray(out / 'akwamiri_height.png', np.clip(height, 0, 1))
    save_gray(out / 'akwamiri_float.png', floats)


def ichafu(out):
    """Plain white cotton for the head tie, its threads a little uneven."""
    rng = np.random.default_rng(37)
    colour = np.empty((H, W, 3), np.float32)
    colour[:] = WHITE * 1.01
    warp = streaks(rng, H, (2, 9))[:, None]
    weft = streaks(rng, W, (3, 13))[None, :]
    colour = colour * (1 - 0.010 * np.clip(warp + weft, -3, 3))[..., None]
    height = np.full((H, W), 0.45, np.float32) + 0.03 * np.clip(warp, -2, 2)
    save(out / 'ichafu_color.png', np.dstack([np.clip(colour, 0, 1), np.ones((H, W), np.float32)]))
    save_gray(out / 'ichafu_height.png', np.clip(height, 0, 1))
    save_gray(out / 'ichafu_float.png', np.zeros((H, W), np.float32))


def paint(out):
    akwamiri(out)
    ichafu(out)
    paint_weave(out)
