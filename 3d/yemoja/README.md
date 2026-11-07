# Yemọja: realistic render notes

A photoreal Yemọja in Blender, following her figure in the Òrìṣà and Alụsị gallery. The page has a hero image, a 36-view turntable, eight close-ups and a sources section: https://claude.ai/artifact/NH8UMHdZQWA7NHX4cFhXF5

In this folder, `yemoja-of-the-ogun.html` is that page, `yemoja.blend` is the finished scene with its textures packed in, and `blender/` holds what is hers. The shared method lives in [`../toolkit/`](../toolkit/).

## What the sources support

| Element | What the source says | Source |
|---|---|---|
| Her name | A contraction of the Yorùbá words for mother, child and fish: mother whose children are fish | [Wikipedia: Yemọja](https://en.wikipedia.org/wiki/Yem%E1%BB%8Dja) |
| Her river | A mother spirit and patron of women, and the patron spirit of rivers, especially the Ògùn | [Wikipedia: Yemọja](https://en.wikipedia.org/wiki/Yem%E1%BB%8Dja) |
| Abẹ́òkúta | A major cult centre | [Wikipedia: Yemọja](https://en.wikipedia.org/wiki/Yem%E1%BB%8Dja) |
| Colours and beads | Blue and white or crystal; crystalline beads; in Cuba her necklaces run seven blue beads, then seven crystalline | [Wikipedia: Yemọja](https://en.wikipedia.org/wiki/Yem%E1%BB%8Dja) |
| Cowries | Her symbol, standing for her wealth | [Wikipedia: Yemọja](https://en.wikipedia.org/wiki/Yem%E1%BB%8Dja) |
| White jars | White jars or pitchers are among her shrine objects in Brazil | [Wikipedia: Yemọja](https://en.wikipedia.org/wiki/Yem%E1%BB%8Dja) |
| Àdìrẹ | Indigo cloth patterned by Yorùbá women with a resist; for eleko, cassava paste painted on with feathers, calabashes or stencils; Abẹ́òkúta is considered its capital; themes include plants, animals and tools; one design, Olókun, is named for the goddess of the sea | [Wikipedia: Adire](https://en.wikipedia.org/wiki/Adire_(textile_art)) |

## Where the sources disagree

In Nigeria she is a river òrìṣà and Olókun holds the sea; in Brazil and Cuba she is the queen or owner of the ocean. This render keeps her at the Ògùn.

She is often shown as a mermaid, in West Africa as in the Americas. The gallery figure does not use that image, and neither does this render.

## The render's own choices (not from sources)

- Her face, age and build. No source used here describes how she looks; she is drawn as a mother, a full-figured woman of about fifty.
- What she wears follows her gallery figure: an ìró and short-sleeved bùbá of àdìrẹ, a light-blue gèlè, crystal and blue beads, a strand of cowries, three silver bangles on her right wrist, and a white pot at her hip.
- The àdìrẹ's design: squares framed in double lines, with fish, cowries, ripples, waves, a leaf and a star. It is not the Olókun design or any other named one.
- The gèlè's shape: a close wrap tied at the nape, with a band of nine folds standing round the back of the head.
- Stringing all four strands seven and seven, after the Cuban practice the source describes, and the strand of cowries lying below them.
- The pot's shape and its white slip.
- The place: an invented bend of the Ògùn in the late afternoon, its shallows, the fish and the granite domes beyond. Abẹ́òkúta's Olúmọ Rock is not copied.

## How it was made

Blender 4.5 Cycles, entirely from Python scripts. The body is MakeHuman's CC0 base mesh, shaping targets and rig from [MPFB2](https://github.com/makehumancommunity/mpfb2). No other third-party assets are used.

`figure.py` shapes her fuller and older than Ọ̀ṣun. The pot is placed before her arm: against her left hip, measured from the body with the arms left out, clear of the skin by the cloth's thickness, its mouth leaning out. Her left hand is then solved to it, palm on the pot's belly, each finger closing until it rests on the clay. The right arm hangs, its hand loosely curled.

The ìró is the toolkit's wrapper and the bùbá its blouse, cut from the body with its hollows bridged and short sleeves. Both are simulated for 110 frames with the pot as a collider, the bùbá at 28,981 vertices while her arms come down into the pose. The àdìrẹ maps follow the Akwete's scheme, so the toolkit's cloth material wears them: eleven squares across the cloth and six to the repeat along it, each with its motif, double-framed, the pale uneven where the paste was thick or thin and veined where it cracked. They are painted in blocks of rows to keep the work in memory small.

The gèlè's wrap is a surface lifted off the skull, its pleats worked out in spherical coordinates round the knot at the nape, as Ahiajoku's ichafu was, but standing further off the head. Its band of nine rounded folds stands on a ring round the crown, opening outward and tallest behind, and wherever its foot falls inside the wrap it is pushed out onto it. Close-cut hair shows below the wrap at the temples, behind the ears and at the nape.

The beads are laid with the toolkit's strands, each round and a little out of true, light blue and crystal in sevens. The cowries lie with their toothed slits outward. The river is a closed slab of water, so a volume can colour it with depth, over a sandy bed that darkens where it is wet. Cycles does not let direct sunlight through a refractive surface, so shadow rays pass the water: the bed is lit as the caustics would light it on average. The trees' crowns are thousands of small leaf cards, and distant materials fade toward the sky with distance.

To rebuild, install MPFB2 as a Blender extension and set `RENDER_WORK` to a scratch folder, then run these from the repo root. Building the scene takes about eight minutes on an 8 GB Apple M1, most of it the two simulations, and the stages save to that folder as they go:

```bash
blender -b --python 3d/yemoja/blender/build.py -- textures body pose wrapper buba dress scene
```

Each still then takes one to two minutes at 96 samples. `blender/render_views.py` lists the camera views:

```bash
blender -b $RENDER_WORK/60_scene.blend --python 3d/yemoja/blender/shots.py -- --samples 96 hero portrait gele
```

The 36 turntable views take about four minutes at 32 samples:

```bash
blender -b $RENDER_WORK/60_scene.blend --python 3d/yemoja/blender/shots.py -- --samples 32 turntable
```

This writes the scene, with its textures packed in, to `yemoja.blend`:

```bash
blender -b --python 3d/yemoja/blender/build.py -- package
```
