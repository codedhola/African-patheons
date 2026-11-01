"""Render the stills and the turntable from 60_scene.blend, with the toolkit's render settings.

Blender -b 60_scene.blend --python shots.py -- hero portrait ... | turntable [first last]
Options before the view names: --samples N, --scale PERCENT, --out DIR
"""
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(HERE.parent.parent / 'toolkit'))
os.environ.setdefault('RENDER_WORK', str(HERE / 'work'))

import dress  # noqa: E402
import render as toolkit  # noqa: E402
from render_views import TURN_VIEW, VIEWS  # noqa: E402


def aim_eyes(target):
    """Each still has her meet its camera, as far as the eyes turn in the head."""
    M = dress.head_matrix(bpy.data.objects['Rig'])
    fwd = (M.to_3x3() @ Vector((0, -1, 0))).normalized()
    for side in 'LR':
        ob = bpy.data.objects[f'Eye.{side}']
        c = ob.matrix_world.translation.copy()
        q = fwd.rotation_difference((Vector(target) - c).normalized())
        q = Quaternion(q.axis, min(q.angle, math.radians(16)))
        ob.matrix_world = Matrix.Translation(c) @ (q @ M.to_quaternion()).to_matrix().to_4x4()
    bpy.context.view_layer.update()


def lights_for_stage():
    """Put out the grove and bring up the dark stage used for the other figures' turntables."""
    toolkit.use_collection('Setting', False)
    toolkit.use_collection('Near', False)
    toolkit.use_collection('Studio', True)
    for name in ('Sun', 'Fill', 'SkinLift'):
        bpy.data.objects[name].hide_render = True
    bpy.data.worlds['Morning'].node_tree.nodes['Background'].inputs['Strength'].default_value = 0.0


def turntable(outdir, first, last, scale):
    sc = bpy.context.scene
    lights_for_stage()
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
    samples, scale, outdir, args = toolkit.options(96)
    toolkit.engine(samples)
    if args and args[0] == 'turntable':
        first = int(args[1]) if len(args) > 1 else 0
        last = int(args[2]) if len(args) > 2 else 35
        turntable(outdir, first, last, scale)
        return
    toolkit.use_collection('Studio', False)
    for name in args:
        aim_eyes(VIEWS[name][0])
        toolkit.still(name, outdir, scale)


if __name__ == '__main__':
    main()
