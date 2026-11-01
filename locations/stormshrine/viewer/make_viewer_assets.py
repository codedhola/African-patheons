"""Assets for the Stormshrine 360° viewer (index.html in this folder), made from Stormshrine.blend.

Run from the repo root:

    blender -b locations/stormshrine/Stormshrine.blend -P locations/stormshrine/viewer/make_viewer_assets.py

Options (after a "--"):
    --out DIR          output folder (default: the folder holding this script)
    --samples N        Cycles samples for the two panoramas (default: 96)
    --skip-panoramas   keep the existing panoramas (they take about 20 minutes on 4 CPU cores)

Writes:
    pano-floor.jpg, pano-doorway.jpg   4096 x 2048 Cycles panoramas at 1.65 m eye height
    sky.jpg                            the storm sky alone, the orbit view's backdrop
    sky-env.jpg                        the same sky facing +X (three.js's equirectangular centre), for reflections
    stormshrine.json, tex/*.jpg        the model as glTF: geometry inlined as base64, JPEG textures

The panoramas use the .blend's own preview rig (sky, lights, far hills, lightning). The .blend is never saved.
"""

import argparse
import base64
import json
import math
import os
import shutil
import sys
import tempfile

import bpy


def parse_args():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    p = argparse.ArgumentParser(prog='make_viewer_assets.py')
    p.add_argument('--out', default=os.path.dirname(os.path.abspath(__file__)))
    p.add_argument('--samples', type=int, default=96)
    p.add_argument('--skip-panoramas', action='store_true')
    return p.parse_args(argv)


def pano_camera(scene, name, location, yaw_deg):
    """Equirectangular camera held level; the image centre looks along +Y turned by yaw_deg."""
    cd = bpy.data.cameras.new(name)
    cd.type = 'PANO'
    try:
        cd.panorama_type = 'EQUIRECTANGULAR'
    except (AttributeError, TypeError):            # older Blender keeps it on the Cycles settings
        cd.cycles.panorama_type = 'EQUIRECTANGULAR'
    cd.clip_start = 0.05
    cd.clip_end = 1000.0
    ob = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(ob)
    ob.location = location
    ob.rotation_euler = (math.pi / 2, 0.0, math.radians(yaw_deg))
    return ob


def render_jpeg(scene, camera, path, width, height, samples):
    scene.camera = camera
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.cycles.samples = samples
    settings = scene.render.image_settings
    settings.file_format = 'JPEG'
    settings.color_mode = 'RGB'
    settings.quality = 86
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('rendered', path, flush=True)


def export_web_model(out):
    """glTF with the preview backdrop (far hills, lightning) but no lights, cameras,
    references or markers. Geometry goes inline as base64 so the page needs only
    JSON and JPEG files, which is all an artifact host or a plain static server is sure to serve."""
    drop = []
    for ob in bpy.data.objects:
        colls = {c.name for c in ob.users_collection}
        if ob.type in {'LIGHT', 'CAMERA', 'FONT'} or colls & {'REF_PlayerScale', 'Stormshrine_Markers'}:
            drop.append(ob)
        elif 'Preview_Rig' in colls and ob.name != 'Preview_Backdrop':
            drop.append(ob)
    for ob in drop:
        bpy.data.objects.remove(ob)
    for me in bpy.data.meshes:                     # the lightmap UVs are no use in a browser
        lm = me.uv_layers.get('UVLightmap')
        if lm:
            me.uv_layers.remove(lm)
    tmp = tempfile.mkdtemp(prefix='stormshrine_gltf_')
    props = {p.identifier for p in bpy.ops.export_scene.gltf.get_rna_type().properties}
    kw = dict(filepath=os.path.join(tmp, 'stormshrine.gltf'), export_format='GLTF_SEPARATE',
              export_texture_dir='tex', use_selection=False, export_cameras=False, export_lights=False,
              export_yup=True)
    if 'export_image_format' in props:
        kw['export_image_format'] = 'JPEG'
    for q in ('export_image_quality', 'export_jpeg_quality'):
        if q in props:
            kw[q] = 82
    if 'use_visible' in props:
        kw['use_visible'] = False
    if 'export_extras' in props:
        kw['export_extras'] = False
    bpy.ops.export_scene.gltf(**kw)

    with open(kw['filepath']) as fh:
        gltf = json.load(fh)
    if len(gltf['buffers']) != 1:
        raise RuntimeError('expected one glTF buffer, got %d' % len(gltf['buffers']))
    with open(os.path.join(tmp, gltf['buffers'][0]['uri']), 'rb') as fh:
        data = fh.read()
    gltf['buffers'][0]['uri'] = 'data:application/octet-stream;base64,' + base64.b64encode(data).decode('ascii')
    with open(os.path.join(out, 'stormshrine.json'), 'w') as fh:
        json.dump(gltf, fh, separators=(',', ':'))
    tex_out = os.path.join(out, 'tex')
    shutil.rmtree(tex_out, ignore_errors=True)
    shutil.copytree(os.path.join(tmp, 'tex'), tex_out)
    shutil.rmtree(tmp, ignore_errors=True)
    print('exported stormshrine.json (%d KB geometry) and %d textures' % (len(data) // 1024, len(gltf['images'])),
          flush=True)


def main():
    args = parse_args()
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    scene = bpy.context.scene
    ref = bpy.data.collections.get('REF_PlayerScale')
    if ref:
        ref.hide_render = True

    if not args.skip_panoramas:
        # Hilltop floor: 10 m in front of the door, between the two fighters' marks, facing the shrine.
        floor = pano_camera(scene, 'Viewer_Pano_Floor', (0.0, -10.0, 1.65), 0.0)
        render_jpeg(scene, floor, os.path.join(out, 'pano-floor.jpg'), 4096, 2048, args.samples)
        # Doorway: just inside the door on the 0.30 m floor, facing out at the storm.
        door = pano_camera(scene, 'Viewer_Pano_Doorway', (0.0, -2.6, 0.30 + 1.65), 180.0)
        render_jpeg(scene, door, os.path.join(out, 'pano-doorway.jpg'), 4096, 2048, args.samples)

    # the storm sky alone: hide every object and let the world shader render
    hidden = [ob for ob in scene.objects if not ob.hide_render]
    for ob in hidden:
        ob.hide_render = True
    sky = pano_camera(scene, 'Viewer_Pano_Sky', (0.0, -4.0, 2.0), 0.0)
    render_jpeg(scene, sky, os.path.join(out, 'sky.jpg'), 2048, 1024, 16)
    # three.js maps an equirectangular map's centre to +X; turn the camera there for the reflection copy
    sky_env = pano_camera(scene, 'Viewer_Pano_SkyEnv', (0.0, -4.0, 2.0), -90.0)
    render_jpeg(scene, sky_env, os.path.join(out, 'sky-env.jpg'), 1024, 512, 16)
    for ob in hidden:
        ob.hide_render = False

    export_web_model(out)


if __name__ == '__main__':
    main()
