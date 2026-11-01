# 3D: photoreal deities

Blender Cycles renders of the deities. Each page has a hero render, a 36-view turntable, close-ups and a list of what is sourced and what is designed. Open a page in a browser.

| Deity | Page | Scene and scripts |
|---|---|---|
| Ṣàngó of Ọ̀yọ́ | [`sango/sango-of-oyo.html`](sango/sango-of-oyo.html) | Not in this repo |
| Amadioha of Ozuzu | [`amadioha/amadioha-of-ozuzu.html`](amadioha/amadioha-of-ozuzu.html) | Not in this repo |
| Ahiajoku of the Yam | [`ahiajoku/ahiajoku-of-the-yam.html`](ahiajoku/ahiajoku-of-the-yam.html) | `ahiajoku/ahiajoku.blend`, `ahiajoku/blender/` |
| Ọ̀ṣun of Òṣogbo | [`osun/osun-of-osogbo.html`](osun/osun-of-osogbo.html) | `osun/osun.blend`, `osun/blender/` |

The README in each folder has the notes: what the sources support, the render's own choices, and how it was made.

- **Ṣàngó** is the thunder king in full regalia: a red aso-oke agbádá that hangs from his raised arm, a beaded crown with its veil, the double axe held high and the gourd rattle in his other hand.
- **Amadioha** is shown both ways the sources do: as a fair-skinned titled gentleman in a red isiagụ, white wrapper and red cap with eagle feathers, holding his glowing sword Mmaagha Kamalu and an akupe fan, and as the gigantic white ram beside him.
- **Ahiajoku** is the Igbo yam deity at dusk on her festival, in a matching Akwete wrapper, blouse and head tie with coral and ivory, holding out a new yam as the full moon rises over a yam field and barn.
- **Ọ̀ṣun** is the river òrìṣà on a morning in her grove, in white ìró and bùbá with a gold sash, the Àgògo braids of her initiates, coral and amber beads, a brass fan and an ààjà bell.

## The toolkit

`toolkit/` holds what the figures share, so that one figure never imports from another.

| Module | What it does |
|---|---|
| `common.py` | The work folder, MPFB, and small mesh helpers |
| `body.py` | The MakeHuman body, its shape targets and rig |
| `pose.py` | Bone moves, two-bone solving and keying the arms |
| `cloth.py` | Cutting and simulating the wrapper and blouse |
| `dress.py` | Skin masks, eyes, brows, lashes, beads, earrings and bangles |
| `materials.py` | The node-graph helper, and skin, eye, hair, coral, ivory and woven cloth |
| `procedural.py` | Noise, hair curves, swept tubes and rocks |
| `weave.py` | The cloth map grid, the plain-weave height map and the PNG writers |
| `render.py` | Cycles settings, the camera, stills and command-line options |

## What a figure's `blender/` folder holds

| File | What it does |
|---|---|
| `build.py` | Runs the named stages, from textures to the packed scene |
| `stance.py` | Her pose |
| `render_views.py` | Her cameras |
| `shots.py` | Renders her stills and turntable |

The rest of the folder is what is hers alone: her cloth, regalia and setting. To add a figure, give it the same shape, with `3d/toolkit` on `sys.path` after its own folder. `osun/blender/` is the closest example.

## Rebuilding

Install Blender 4.5 and [MPFB2](https://github.com/makehumancommunity/mpfb2) as a Blender extension. Run the commands in the figure's README from the repo root.

Set `RENDER_WORK` to a scratch folder for the build stages, the simulations and the renders. If it isn't set, each figure uses a `work/` folder beside its scripts, which git ignores.
