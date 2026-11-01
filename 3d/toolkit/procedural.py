"""Procedural pieces any figure or setting can use: noise, hair curves, swept tubes and rocks."""
import math

import bpy
import numpy as np


class Noise:
    """3D value noise in numpy, so whole meshes can be sampled at once."""

    def __init__(self, seed):
        rng = np.random.default_rng(seed)
        self.table = rng.random(512, np.float32)
        self.perm = rng.permutation(256)
        self.perm = np.concatenate([self.perm, self.perm, self.perm])

    def __call__(self, p):
        p = np.asarray(p, np.float32)
        i = np.floor(p).astype(np.int64)
        f = p - i
        u = f * f * (3 - 2 * f)
        i &= 255
        pm, tb = self.perm, self.table

        def corner(dx, dy, dz):
            return tb[pm[pm[pm[i[..., 0] + dx] + i[..., 1] + dy] + i[..., 2] + dz]]

        x00 = corner(0, 0, 0) * (1 - u[..., 0]) + corner(1, 0, 0) * u[..., 0]
        x10 = corner(0, 1, 0) * (1 - u[..., 0]) + corner(1, 1, 0) * u[..., 0]
        x01 = corner(0, 0, 1) * (1 - u[..., 0]) + corner(1, 0, 1) * u[..., 0]
        x11 = corner(0, 1, 1) * (1 - u[..., 0]) + corner(1, 1, 1) * u[..., 0]
        y0 = x00 * (1 - u[..., 1]) + x10 * u[..., 1]
        y1 = x01 * (1 - u[..., 1]) + x11 * u[..., 1]
        return (y0 * (1 - u[..., 2]) + y1 * u[..., 2]) * 2 - 1

    def fbm(self, p, octaves=4, gain=0.5):
        out, amp, freq = 0, 1, 1
        for k in range(octaves):
            out = out + amp * self(np.asarray(p) * freq + 17.3 * k)
            amp *= gain
            freq *= 2.03
        return out


def add_curves(name, strands, radius_root, radius_tip, col, material=None):
    """Hair curves object from an array N x points x 3, tapering root to tip."""
    n, m = strands.shape[:2]
    hc = bpy.data.hair_curves.new(name)
    hc.add_curves([m] * n)
    hc.position_data.foreach_set('vector', strands.ravel())
    rad = hc.attributes.get('radius') or hc.attributes.new('radius', 'FLOAT', 'POINT')
    t = np.tile(np.linspace(0, 1, m), n)
    rad.data.foreach_set('value', (radius_root + (radius_tip - radius_root) * t).astype(np.float32))
    ob = bpy.data.objects.new(name, hc)
    col.objects.link(ob)
    if material:
        hc.materials.append(material)
    return ob


def sweep(path, radius, sides=6, flat=1.0, up=(0, 0, 1)):
    """Tube along a polyline. radius may be a number or one value per point."""
    path = np.asarray(path, np.float64)
    n = len(path)
    r = np.full(n, radius) if np.isscalar(radius) else np.asarray(radius)
    tan = np.gradient(path, axis=0)
    tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    side = np.cross(tan, up)
    bad = np.linalg.norm(side, axis=1) < 1e-6
    side[bad] = np.cross(tan[bad], (1, 0, 0))
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    nrm = np.cross(side, tan)
    a = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    ca, sa = np.cos(a), np.sin(a)
    v = path[:, None] + (side[:, None] * ca[None, :, None] + nrm[:, None] * sa[None, :, None] * flat) * r[:, None, None]
    f = []
    for i in range(n - 1):
        for j in range(sides):
            k = (j + 1) % sides
            f.append((i * sides + j, i * sides + k, (i + 1) * sides + k, (i + 1) * sides + j))
    return v.reshape(-1, 3), f


def merged(parts):
    verts, faces, base = [], [], 0
    for v, f in parts:
        verts.append(v)
        faces += [tuple(i + base for i in q) for q in f]
        base += len(v)
    return np.concatenate(verts), faces


def rock_mesh(seed):
    n = Noise(seed)
    rows, cols = 9, 12
    verts = []
    for i in range(rows):
        a = math.pi * i / (rows - 1)
        for j in range(cols):
            b = 2 * math.pi * j / cols
            d = np.array([math.sin(a) * math.cos(b), math.sin(a) * math.sin(b), math.cos(a)])
            verts.append(d * (1 + 0.36 * float(n.fbm(d * 1.3 + seed, 3))) * np.array([1, 0.8, 0.62]))
    faces = [(i * cols + j, i * cols + (j + 1) % cols, (i + 1) * cols + (j + 1) % cols, (i + 1) * cols + j) for i in range(rows - 1) for j in range(cols)]
    return np.array(verts, np.float32), faces
