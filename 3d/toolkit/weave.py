"""The woven cloth's map grid, its plain-weave height map and the PNG writers.

Cloth maps are built on a grid of 4.2 mm cells, the way supplementary-weft motifs are
counted: one full cloth high (1.15 m, the width of the loom) and one 60.5 cm repeat
across, so U repeats and V does not.
"""
import numpy as np

CELL = 14                # pixels per grid cell
ROWS, COLS = 274, 144    # 274 x 4.2 mm = 1.15 m, 144 x 4.2 mm = 60.5 cm
W, H = COLS * CELL, ROWS * CELL


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
