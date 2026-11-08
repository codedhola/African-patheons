"""Paint his cloth: handwoven cotton strips dyed in the aró (indigo) vat, pale for the tunic, deep for the trousers.

Blue is his colour in Kétu (Wikipedia: Oshosi), and his gallery figure wears a blue tunic over
short trousers. Ògún's ẹ̀tù is dyed until it is nearly black; this cloth goes into the vat only a
few times, so it stays a pale sky blue, and the trousers are dyed deeper. Maps follow the scheme
of Ahiajoku's akwete.py, so materials.akwete can wear them: U repeats every 60.5 cm along the
cloth, V covers 1.15 m across it, and here the cloth is eleven strips 10.5 cm wide, sewn edge to
edge, as for Ògún's ẹ̀tù. The stripes in each strip are this study's.
"""
import numpy as np

from weave import H, W, paint_weave, save, save_gray

STRIPS = 11


def streaks(rng, width, spans):
    s = rng.normal(0, 1, width).astype(np.float32)
    for size in spans:
        kernel = np.ones(size) / size
        s += 2.2 * np.convolve(np.tile(s, 3), kernel, 'same')[width:2 * width].astype(np.float32)
    return (s - s.mean()) / s.std()


def strip_cloth(out, name, ground, worn, stripes, seed):
    """A strip cloth: a ground dyed unevenly along the warp, warp stripes in each strip, whip-stitched seams.

    stripes: (centre across the strip 0..1, width in mm, colour) for each stripe of warp.
    """
    rng = np.random.default_rng(seed)
    colour = np.empty((H, W, 3), np.float32)
    colour[:] = ground
    height = np.full((H, W), 0.42, np.float32)

    # each dip leaves the warp a little uneven, and handspun weft is thicker in places: streaks both ways
    streak = streaks(rng, H, (3, 11, 41))[:, None]
    slub = streaks(rng, W, (2, 7))[None, :]
    mix = np.clip(0.35 + 0.22 * streak + 0.06 * slub, 0, 1)
    colour = colour + (np.asarray(worn) - np.asarray(ground))[None, None] * mix[:, :, None]
    height += 0.05 * streak / 3 + 0.03 * slub / 3

    strip = H / STRIPS
    pos = (np.arange(H) % strip) / strip
    index = (np.arange(H) / strip).astype(int)
    colour *= rng.uniform(0.94, 1.06, STRIPS)[index][:, None, None]       # each strip from its own dye bath

    px_per_m = H / 1.15
    for centre, width_mm, stripe_colour in stripes:
        band = np.abs(pos - centre) * strip / px_per_m < width_mm / 2000
        soft = np.exp(-((pos - centre) * strip / px_per_m / (width_mm / 2000 + 0.0002)) ** 8)
        weight = np.maximum(band.astype(np.float32), soft)[:, None]
        colour = colour * (1 - weight[..., None]) + np.asarray(stripe_colour)[None, None] * weight[..., None]
        height += 0.06 * weight

    # the seam: two selvedges butted and whip-stitched in dark thread
    seam = np.exp(-(np.minimum(pos, 1 - pos) / 0.010) ** 2)[:, None]
    height = height - 0.30 * seam
    colour *= (1 - 0.30 * seam)[:, :, None]
    stitch = (np.sin(np.arange(W) / W * 2 * np.pi * 150)[None, :] > 0) * (np.minimum(pos, 1 - pos)[:, None] < 0.010)
    height = np.where(stitch, height + 0.32, height)

    rgba = np.dstack([np.clip(colour, 0, 1), np.ones((H, W), np.float32)])
    save(out / f'{name}_color.png', rgba)
    save_gray(out / f'{name}_height.png', np.clip(height, 0, 1))
    save_gray(out / f'{name}_float.png', np.zeros((H, W), np.float32))


def paint(out):
    deep = (0.075, 0.110, 0.230)
    white = (0.80, 0.82, 0.84)
    # the tunic: pale sky blue, a pair of deep indigo stripes near each edge of the strip and a white one down its middle
    strip_cloth(out, 'aro', (0.42, 0.58, 0.70), (0.50, 0.65, 0.76),
                [(0.10, 3.0, deep), (0.16, 1.5, deep), (0.50, 1.0, white), (0.84, 1.5, deep), (0.90, 3.0, deep)], 31)
    # the trousers: deep indigo, with a pale pinstripe either side of the middle of each strip
    strip_cloth(out, 'aro_deep', (0.090, 0.125, 0.245), (0.120, 0.165, 0.300),
                [(0.45, 0.8, (0.42, 0.56, 0.70)), (0.55, 0.8, (0.42, 0.56, 0.70))], 32)
    paint_weave(out)
