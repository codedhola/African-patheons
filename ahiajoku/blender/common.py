"""Paths and small helpers shared by the Ahiajoku build scripts.

Set AHIAJOKU_WORK to a scratch folder for .blend files and sims, and install
https://github.com/makehumancommunity/mpfb2 as a Blender extension (see load_mpfb).
"""
import os
import sys
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
WORK = Path(os.environ.get('AHIAJOKU_WORK', HERE / 'work'))
TEX = WORK / 'tex'
OUT = WORK / 'out'
for d in (WORK, TEX, OUT):
    d.mkdir(parents=True, exist_ok=True)


def load_mpfb():
    """Enable MPFB as an extension and hand back its services.

    Link or copy MPFB's src/mpfb into <BLENDER_USER_RESOURCES>/extensions/user_default first.
    """
    import addon_utils
    name = 'bl_ext.user_default.mpfb'
    addon_utils.enable(name, default_set=True, handle_error=None)
    svc = sys.modules[name + '.services.humanservice']
    return (svc.HumanService,
            sys.modules[name + '.services.targetservice'].TargetService,
            sys.modules[name + '.services.locationservice'].LocationService,
            sys.modules[name + '.entities.objectproperties'].HumanObjectProperties)


def collection(name):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def obj_from_arrays(name, verts, faces, col=None, smooth=True, uv=None):
    """Make a mesh object from numpy verts and a list of face index tuples."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in verts], [], [tuple(map(int, f)) for f in faces])
    me.update()
    if smooth:
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    if uv is not None:
        layer = me.uv_layers.new(name='UVMap')
        loops = np.zeros(len(me.loops), np.int32)
        me.loops.foreach_get('vertex_index', loops)
        layer.data.foreach_set('uv', np.asarray(uv, np.float32)[loops].ravel())
    ob = bpy.data.objects.new(name, me)
    (col or bpy.context.scene.collection).objects.link(ob)
    return ob


def verts_world(ob, depsgraph=None):
    """Evaluated vertex positions in world space, as an N x 3 array."""
    dg = depsgraph or bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.zeros(len(me.vertices) * 3, np.float64)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    m = np.array(ev.matrix_world)
    out = co @ m[:3, :3].T + m[:3, 3]
    ev.to_mesh_clear()
    return out


def edge_adjacency(me):
    adj = [[] for _ in me.vertices]
    for e in me.edges:
        a, b = e.vertices
        adj[a].append(b)
        adj[b].append(a)
    return adj


def save(name):
    path = WORK / name
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
    print('saved', path, round(path.stat().st_size / 1e6, 1), 'MB', flush=True)
