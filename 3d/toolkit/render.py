"""Cycles settings, the camera and the stills, shared by each figure's shots.py.

A figure keeps its cameras in its own render_views.py, which has to be on sys.path first.
"""
import sys
from pathlib import Path

import bpy
from mathutils import Vector

from common import OUT
from render_views import VIEWS


def engine(samples):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == 'METAL'
    cy = sc.cycles
    cy.device = 'GPU'
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.02
    cy.use_denoising = True
    cy.denoiser = 'OPENIMAGEDENOISE'
    cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    cy.denoising_prefilter = 'ACCURATE'
    cy.max_bounces = 8
    cy.diffuse_bounces = 3
    cy.glossy_bounces = 3
    cy.transmission_bounces = 6
    cy.volume_bounces = 0
    cy.transparent_max_bounces = 6
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.sample_clamp_indirect = 8
    cy.film_transparent = False
    sc.render.use_persistent_data = True
    sc.render.dither_intensity = 1.0
    sc.render.image_settings.file_format = 'WEBP'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.image_settings.quality = 96        # lower, and the dither in the dusk sky turns to blocks
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.view_settings.exposure = 0.0


def use_collection(name, on):
    col = bpy.data.collections.get(name)
    if col is None:
        return
    for ob in list(col.all_objects):
        ob.hide_render = not on


def aim(cam_ob, loc, target, lens):
    cam_ob.location = loc
    cam_ob.data.lens = lens
    cam_ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()


def still(name, outdir, scale):
    loc, target, lens, w, h, stop, focus = VIEWS[name]
    sc = bpy.context.scene
    cam = bpy.data.objects['Camera']
    sc.camera = cam
    aim(cam, loc, target, lens)
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = stop
    f = Vector(focus or target) - Vector(loc)
    view = (Vector(target) - Vector(loc)).normalized()
    cam.data.dof.focus_distance = f.dot(view)
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = scale
    sc.render.filepath = str(outdir / f'{name}.webp')
    bpy.ops.render.render(write_still=True)


def options(samples):
    """Read the command line after '--': the options, then what is left, the views to render."""
    args = sys.argv[sys.argv.index('--') + 1:]
    scale, outdir = 100, OUT
    while args and args[0].startswith('--'):
        key = args.pop(0)
        if key == '--samples':
            samples = int(args.pop(0))
        elif key == '--scale':
            scale = int(args.pop(0))
        elif key == '--out':
            outdir = Path(args.pop(0))
    outdir.mkdir(parents=True, exist_ok=True)
    return samples, scale, outdir, args
