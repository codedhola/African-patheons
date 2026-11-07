"""Paint his ẹ̀tù: very dark indigo aṣọ-òkè with a fine check of light threads.

Ẹ̀tù is named for the guinea fowl, whose dark plumage is speckled white, and the check is what
makes the cloth read so from a little way off. Maps follow the scheme of Ahiajoku's akwete.py,
so materials.akwete can wear them: U repeats every 60.5 cm along the cloth, V covers 1.15 m
across it. Here the cloth is eleven strips 10.5 cm wide, sewn edge to edge, as for Ọ̀ṣun's
aṣọ-òkè: three light threads run down each strip and a light pick crosses them every 2.5 cm.
The spacing is this study's.
"""
import numpy as np

from weave import H, W, paint_weave, save, save_gray

INDIGO = np.array([0.072, 0.082, 0.160])         # sRGB: dyed many times over, near black
INDIGO_WORN = np.array([0.092, 0.110, 0.205])
PALE = np.array([0.360, 0.440, 0.580])           # the light-blue threads
WHITE = np.array([0.720, 0.745, 0.780])
STRIPS = 11


def streaks(rng, width, spans):
    s = rng.normal(0, 1, width).astype(np.float32)
    for size in spans:
        kernel = np.ones(size) / size
        s += 2.2 * np.convolve(np.tile(s, 3), kernel, 'same')[width:2 * width].astype(np.float32)
    return (s - s.mean()) / s.std()


def etu(out):
    rng = np.random.default_rng(23)
    colour = np.empty((H, W, 3), np.float32)
    colour[:] = INDIGO
    height = np.full((H, W), 0.42, np.float32)
    floats = np.zeros((H, W), np.float32)

    # each pass through the dye leaves the warp a little uneven: streaks along U, rows here
    streak = streaks(rng, H, (3, 11, 41))[:, None]
    colour = colour + (INDIGO_WORN - INDIGO)[None, None] * np.clip(0.35 + 0.22 * streak, 0, 1)[:, :, None]
    height += 0.05 * streak / 3

    strip = H / STRIPS
    pos = (np.arange(H) % strip) / strip
    index = (np.arange(H) / strip).astype(int)
    colour *= rng.uniform(0.95, 1.05, STRIPS)[index][:, None, None]

    # single light warp threads run the length of each strip, three to a strip
    px_per_m = H / 1.15
    warp = np.zeros(H, np.float32)
    for centre in (0.21, 0.50, 0.79):
        warp = np.maximum(warp, np.exp(-((pos - centre) * strip / (0.00045 * px_per_m)) ** 2))
    # light weft picks cross them every 2.5 cm along the cloth, 24 to the repeat so it tiles: the check
    period = 0.605 / 24
    u = np.arange(W) / W * 0.605
    pick = (u % period) / period
    weft = np.exp(-((np.minimum(pick, 1 - pick)) * period / 0.00034) ** 2).astype(np.float32)
    # where a light warp crosses a light weft the dot is nearly white: the guinea fowl's speckle
    cross = warp[:, None] * weft[None, :]
    light = np.clip(warp[:, None] * 0.70 + weft[None, :] * 0.45, 0, 1)
    colour = colour * (1 - light[..., None]) + PALE[None, None] * light[..., None]
    colour = colour * (1 - cross[..., None]) + WHITE[None, None] * cross[..., None]
    height += 0.10 * light

    # the seam: two selvedges butted and whip-stitched in dark thread
    seam = np.exp(-(np.minimum(pos, 1 - pos) / 0.010) ** 2)[:, None]
    height = height - 0.30 * seam
    colour *= (1 - 0.30 * seam)[:, :, None]
    stitch = (np.sin(np.arange(W) / W * 2 * np.pi * 150)[None, :] > 0) * (np.minimum(pos, 1 - pos)[:, None] < 0.010)
    height = np.where(stitch, height + 0.32, height)

    rgba = np.dstack([np.clip(colour, 0, 1), np.ones((H, W), np.float32)])
    save(out / 'etu_color.png', rgba)
    save_gray(out / 'etu_height.png', np.clip(height, 0, 1))
    save_gray(out / 'etu_float.png', floats)


def paint(out):
    etu(out)
    paint_weave(out)
