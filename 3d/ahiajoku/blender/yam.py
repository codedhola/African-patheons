"""Ji: white yam tubers (Dioscorea rotundata), modelled from a noise-driven profile.

The same generator makes the hero tuber in her hands, the basket pile and the
tubers tied on the barn frames. FAO gives 5 to 10 kg for a large tuber. The hero
tuber is 41 cm by 14 cm and about 4 kg, a weight she can hold out in both hands.
"""
import numpy as np

from common import obj_from_arrays
from procedural import Noise, add_curves


def profile(t, seed):
    """Radius along the tuber: a chopped head at t=0, a broad blunt foot at t=1."""
    rng = np.random.default_rng(seed)
    knots_t = [0.0, 0.03, 0.10, 0.24, 0.45 + rng.uniform(-.06, .06), 0.70 + rng.uniform(-.05, .05), 0.90, 0.965, 0.992, 1.0]
    knots_r = [0.62, 0.66, 0.76, 0.86, 0.97, 1.0, 0.97, 0.85, 0.52, 0.0]
    r = np.interp(t, knots_t, knots_r)
    kernel = np.array([1, 4, 6, 4, 1], float) / 16
    head = r[0]
    for _ in range(2):
        r = np.convolve(np.pad(r, 2, mode='edge'), kernel, 'valid')
    r[0] = head
    r[-1] = 0
    return r


def tuber(seed=1, length=0.40, radius=0.066, bend=0.05, nt=170, nth=72):
    """Grid of rings along a gently bent axis, capped at the head by a slanted cut.

    Returns verts, faces, uvs, axis, radii, and the face indices of the cut.
    """
    n1, n2 = Noise(seed), Noise(seed + 101)
    rng = np.random.default_rng(seed)
    cap = 7                      # rings used to close the cut face
    s = np.linspace(0, 1, nt - cap)
    t = 0.74 * s + 0.26 * (0.5 - 0.5 * np.cos(np.pi * s))
    r = profile(t, seed) * radius
    ph1, ph2 = rng.uniform(0, 6.28, 2)
    a = np.stack([bend * length * np.sin(2.4 * t + ph1) * 0.5,
                  bend * length * 0.6 * np.sin(4.1 * t + ph2) * 0.5,
                  (t - 0.5) * length], 1)
    tan = np.gradient(a, axis=0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    side = np.cross(tan, [1, 0, 0])
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    up = np.cross(tan, side)

    th = np.linspace(0, 2 * np.pi, nth, endpoint=False)
    n = nt - cap
    T, TH = np.meshgrid(np.arange(n), th, indexing='ij')
    c, sn = np.cos(TH), np.sin(TH)
    tt = t[T]
    # flattened section, a furrow down one flank, and a foot that splays into two lobes
    flat = rng.uniform(0.74, 0.88)
    ang = rng.uniform(0, 6.28)
    fur = TH - ang
    fur = np.arctan2(np.sin(fur), np.cos(fur))
    furrow = np.exp(-(fur / 0.42) ** 2) * np.clip((tt - 0.1) / 0.25, 0, 1)
    lobed = np.clip((tt - 0.62) / 0.34, 0, 1) ** 2 * np.cos(2 * (TH - ang))
    p = np.stack([c * 0.066, sn * 0.066, tt * length], -1)
    lump = n1.fbm(p * 11, 2)                      # lobes a tuber takes from stones in the mound
    bump = n1.fbm(p * 52, 3) * 0.5                # warts and old root bases
    cork = np.abs(n2.fbm(p * 190, 3))             # corky scale
    ring = np.sin(tt * length * 300 + n2(p * 40) * 3.5)
    h = (1 + 0.20 * lump) * (1 - 0.16 * furrow) * (1 + 0.20 * lobed)
    rad = r[T] * h + 0.0032 * bump + 0.0013 * cork * (r[T] > 1e-4) + 0.00035 * ring
    rad = np.maximum(rad, 0) * (r[T] > 1e-5)
    ox = c * rad
    oy = sn * rad * flat
    verts = a[T] + side[T] * ox[..., None] + up[T] * oy[..., None]
    # the head was chopped from the vine with a slanting stroke of the matchet
    slant = 0.30
    verts = verts + tan[T] * (slant * ox * np.exp(-tt / 0.05))[..., None]
    rings = [verts[i] for i in range(n)]

    # close the head: rings walk in to a rough-chopped centre
    first = rings[0]
    centre = first.mean(0)
    capped = []
    for k in range(1, cap + 1):
        f = k / (cap + 0.0)
        ring_k = centre + (first - centre) * (1 - f * 0.985)
        ring_k = ring_k + tan[0] * (0.0016 * n2(ring_k * 95))[..., None]
        capped.append(ring_k)
    all_rings = capped[::-1] + rings
    verts = np.concatenate(all_rings).reshape(-1, 3)

    faces, cap_faces = [], []
    idx = lambda i, j: i * nth + (j % nth)
    for i in range(nt - 1):
        for j in range(nth):
            if i < cap:
                cap_faces.append(len(faces))
            faces.append((idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)))
    vs = np.concatenate([np.zeros(cap), t])
    uv = np.stack([np.tile(th / (2 * np.pi), nt) * 2, np.repeat(vs, nth) * 4], 1)
    return verts, faces, uv, a, r, cap_faces


def rootlets(seed, axis, radii, count, reach=0.05):
    """Fine wiry rootlets, thickest over the head half of the tuber as on a lifted yam."""
    rng = np.random.default_rng(seed)
    nt = len(axis)
    strands = []
    i_pick = (rng.beta(1.2, 1.9, count) * (nt - 4) + 2).astype(int)
    tan = np.gradient(axis, axis=0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    for i in i_pick:
        th = rng.uniform(0, 6.28)
        side = np.cross(tan[i], [1, 0, 0])
        side /= np.linalg.norm(side)
        up = np.cross(tan[i], side)
        d = side * np.cos(th) + up * np.sin(th)
        base = axis[i] + d * radii[i] * 0.98
        L = rng.uniform(0.25, 1.0) ** 2 * reach + 0.004
        wob = rng.normal(0, 1, (6, 3)).cumsum(0) * L * 0.05
        s = np.linspace(0, 1, 6)[:, None]
        pts = base + d * s * L + wob * s + tan[i] * s * s * L * rng.uniform(-.4, .4)
        strands.append(pts)
    return np.array(strands, np.float32)


def yam_object(name, seed, col, length=0.40, radius=0.066, bend=0.05, nt=170, nth=72, roots=0,
               material=None, flesh=None, root_material=None):
    v, f, uv, axis, radii, cut = tuber(seed, length, radius, bend, nt, nth)
    ob = obj_from_arrays(name, v, f, col, uv=uv)
    if material:
        ob.data.materials.append(material)
        ob.data.materials.append(flesh or material)
        index = np.zeros(len(ob.data.polygons), np.int32)
        index[cut] = 1
        ob.data.polygons.foreach_set('material_index', index)
    if roots:
        rc = add_curves(name + '_roots', rootlets(seed + 7, axis, radii, roots), 0.0006, 0.00012, col, root_material)
        rc.parent = ob
    return ob, axis, radii
