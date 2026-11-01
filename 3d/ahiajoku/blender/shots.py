"""Render Ahiajoku's stills and turntable from 60_scene.blend.

Blender -b 60_scene.blend --python shots.py -- hero portrait ... | turntable [first last]
Options before the view names: --samples N, --scale PERCENT, --out DIR
"""
import math
import os
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(HERE.parent.parent / 'toolkit'))
os.environ.setdefault('RENDER_WORK', str(HERE / 'work'))

import render as toolkit  # noqa: E402
from render_views import TURN_VIEW  # noqa: E402


def turntable(outdir, first, last, scale):
    sc = bpy.context.scene
    toolkit.use_collection('Setting', False)
    toolkit.use_collection('Studio', True)
    bpy.data.objects['Sun'].hide_render = True
    bpy.data.objects['Fill'].hide_render = True
    bpy.data.objects['SkinLift'].hide_render = True
    for ob in bpy.data.collections['Near'].objects:     # the basket swings round: only bare earth stays
        if ob.name.startswith(('Rock', 'Leaf')):
            ob.hide_render = True
    bpy.data.objects['Moon'].hide_render = True
    bpy.data.worlds['Dusk'].node_tree.nodes['Background'].inputs['Strength'].default_value = 0.0
    root = bpy.data.objects['Turntable']
    cam = bpy.data.objects['Camera']
    sc.camera = cam
    loc, target, lens, w, h = TURN_VIEW
    toolkit.aim(cam, loc, target, lens)
    cam.data.dof.use_dof = False
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = scale
    sc.render.image_settings.quality = 90
    for i in range(first, last + 1):
        root.rotation_euler.z = math.radians(i * 10)
        sc.render.filepath = str(outdir / f'turn_{i:02d}.webp')
        bpy.ops.render.render(write_still=True)
    root.rotation_euler.z = 0


def main():
    samples, scale, outdir, args = toolkit.options(80)
    toolkit.engine(samples)
    if args and args[0] == 'turntable':
        first = int(args[1]) if len(args) > 1 else 0
        last = int(args[2]) if len(args) > 2 else 35
        turntable(outdir, first, last, scale)
        return
    toolkit.use_collection('Studio', False)
    for name in args:
        toolkit.still(name, outdir, scale)


if __name__ == '__main__':
    main()
