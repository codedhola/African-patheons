# Ahiajoku: realistic render notes

A photoreal Ahiajoku in Blender, following her figure in the Òrìṣà and Alụsị gallery. The page has a hero image, a 36-view turntable, eight close-ups and a sources section: https://claude.ai/artifact/GCPLXEsS3MpgExsPhUzYWW

In this folder, `ahiajoku-of-the-yam.html` is that page, `ahiajoku.blend` is the finished scene with its textures packed in, and `blender/` holds what is hers. The shared method lives in [`../toolkit/`](../toolkit/).

It follows the method and page layout of the Ṣàngó and Amadioha renders, with its own scripts because theirs are not in the repo. Ògún has no Blender render yet; he exists only as a three.js figure in the gallery.

## What the sources support

| Element | What the source says | Source |
|---|---|---|
| Who she is | The deity responsible for yams, also called Ifejioku and Aha Njoku; her name was invoked to settle disputes over farmland | [Wikipedia: Ahia Njoku](https://en.wikipedia.org/wiki/Ahia_Njoku) |
| Full moon | Her festival is on a full moon before the New Yam festival, and new yams may not be eaten until the ceremony is done | [Wikipedia: Ahia Njoku](https://en.wikipedia.org/wiki/Ahia_Njoku) |
| Akwete pair | Woven and sold in identical pairs: one a wrapper, the other a stole, a second wrapper or a blouse | [Wikipedia: Akwete cloth](https://en.wikipedia.org/wiki/Akwete_cloth) |
| Cloth width | Most Akwete is 40 to 50 inches wide; the cloth map is 1.15 m | [Wikipedia: Akwete cloth](https://en.wikipedia.org/wiki/Akwete_cloth) |
| Cloth structure | Supplementary weft on a warp-faced plain weave, on a vertical loom; a white-ground wrapper with lozenges | [The Met: Wrapper, Akwete women's cooperative](https://www.metmuseum.org/art/collection/search/318452) |
| Motifs | Weavers claim over a hundred, usually three or four on a cloth; ikaki (tortoise), saw and draughts are named | [Wikipedia: Akwete cloth](https://en.wikipedia.org/wiki/Akwete_cloth) |
| Ichafu | A headcloth tied flat on the head, worn with wrappers and blouses | [Wikipedia: Igbo regalia and headdresses](https://en.wikipedia.org/wiki/Igbo_regalia_and_headdresses) |
| Coral | Large coral beads (nkalari) at the neck and wrists and as earrings | [Wikipedia: Igbo regalia and headdresses](https://en.wikipedia.org/wiki/Igbo_regalia_and_headdresses) |
| Ivory | Odu aka at the wrists and odu ukwu at the ankles, the regalia of Otu Odu women | [Wikipedia: Igbo regalia and headdresses](https://en.wikipedia.org/wiki/Igbo_regalia_and_headdresses) |
| Yam barn | Vertical frames 1 to 2 m high (up to 4 m), posts 5 to 10 cm thick about 1 m apart, lighter cross members, tubers tied on individually with string or raffia, live poles sprouting shoots for shade | [Lancaster and Coursey, FAO Bulletin 59 (1984)](https://www.fao.org/4/x5045e/x5045E07.htm) |
| Tuber size | Large tubers often weigh 5 to 10 kg | [Lancaster and Coursey, FAO Bulletin 59 (1984)](https://www.fao.org/4/x5045e/x5045E07.htm) |

## Where the sources disagree

Wikipedia calls Ahia Njoku a goddess and treats [Njoku Ji](https://en.wikipedia.org/wiki/Njoku_Ji), the guardian deity of the yam, in a separate entry; a 2009 comment on [its talk page](https://en.wikipedia.org/wiki/Talk:Ahia_Njoku) calls Ahia Njoku the goddess of the yam and Njoku Ji the god. [Oriire](https://oriire.com/article/deities-in-igboland-from-myth-to-culture) calls Ahiajoku the yam god, a son of Ibo whose flesh germinated into yam. The render stays with the gallery and shows a goddess.

None of these sources describes an image of her, gives her colours or says what she wears. As the gallery's respect notes say of the Igbo figures, this is an interpretation in Igbo dress, not a cult image.

## The render's own choices (not from sources)

- Her face, age and build.
- The cloth's colours, carried over from the gallery figure: cream ground, green, red and indigo floats.
- The layout of the cloth: bands of ikaki and lozenge, the saw between them, a draughts border at the hem. The ikaki was once reserved for royalty according to the gallery's glossary, and it is used here for a deity.
- The ivory. The source ties it to Otu Odu women; she wears it as a mark of standing.
- The ichafu's folds and the knot behind her left ear. The gallery figure wears a taller wrap; the regalia source says an ichafu is tied flat, so this one is.
- The pose: both hands presenting the yam, with her weight on her right leg.
- The evening. A full moon rises at sunset, opposite the sun, so the camera looks east with the last warm light behind it. The moon's disc is about seven times its true apparent size so that it reads in the picture. Its tilt suits a moonrise at Igbo latitudes.
- The basket, the field of staked vines and where the barn stands.
- The indigo binding and red stitching on the blouse's neck, cuffs and hem.

## How it was made

Blender 4.5 Cycles, entirely from Python scripts. The body is MakeHuman's CC0 base mesh, shaping targets and rig from [MPFB2](https://github.com/makehumancommunity/mpfb2). No other third-party assets are used.

The wrapper is one sheet of 27,848 vertices, wound round the hips with its outer edge down the front. The blouse is cut from the body, loosened, and simulated at 26,530 vertices while the arms come down to hold the yam. Both run for 110 frames. The Akwete is painted float by float on a 4.2 mm grid: one cloth width of 1.15 m, repeating every 60.5 cm along its length.

The ichafu is a 60,000-vertex surface lifted off the skull, with its pleats worked out in spherical coordinates around the knot. The coral is 235 beads, laid on the chest as three nested ovals, with earrings and wrist strands. The ten yams in the basket were dropped in with rigid-body physics; four tubers that broke through were left out. The barn carries 125 tubers from eight shapes, built to the source's measurements.

The skin has a low soft lamp that only the skin receives, through Cycles light linking, because deep skin beside cream cloth needs more light than the cloth can take. Skin under the cloth is masked out so it cannot show through.

To rebuild, install MPFB2 as a Blender extension and set `RENDER_WORK` to a scratch folder, then run these from the repo root. Building the scene takes about six minutes on an 8 GB Apple M1, and the stages save to that folder as they go:

```bash
blender -b --python 3d/ahiajoku/blender/build.py -- textures body pose wrapper blouse dress scene
```

Each still then takes about a minute at 96 samples. `blender/render_views.py` lists the camera views:

```bash
blender -b $RENDER_WORK/60_scene.blend --python 3d/ahiajoku/blender/shots.py -- --samples 96 hero portrait hands
```

The 36 turntable views take about eight minutes at 32 samples:

```bash
blender -b $RENDER_WORK/60_scene.blend --python 3d/ahiajoku/blender/shots.py -- --samples 32 turntable
```

This writes the scene, with its textures packed in, to `ahiajoku.blend`:

```bash
blender -b --python 3d/ahiajoku/blender/build.py -- package
```
