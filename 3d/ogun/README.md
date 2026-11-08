# Ògún: realistic render notes

A photoreal Ògún in Blender, following his figure in the Òrìṣà and Alụsị gallery. The page has a hero image, a 36-view turntable, eight close-ups and a sources section: https://claude.ai/artifact/7RmYcg3KaL3DVwLpGrDZ3A

In this folder, `ogun-of-ire.html` is that page, `ogun.blend` is the finished scene with its textures packed in, and `blender/` holds what is his. The shared method lives in [`../toolkit/`](../toolkit/).

## What the sources support

| Element | What the source says | Source |
|---|---|---|
| Iron | His primary emblem; his followers wear chains of iron implements | [Wikipedia: Ogun](https://en.wikipedia.org/wiki/Ogun) |
| The dog and the palm frond | With iron, his three primary symbols; dogs are the traditional companions of hunters | [Wikipedia: Ogun](https://en.wikipedia.org/wiki/Ogun) |
| Màrìwò | Young unwilted palm fronds, tied round the body at festivals such as Ọlọ́jọ́ by Ògún's worshippers | [Wiktionary: màrìwò](https://en.wiktionary.org/wiki/mariwo) |
| The machete | In some traditions he cleared a path for the other òrìṣà with a metal machete, helped by a dog | [Wikipedia: Ogun](https://en.wikipedia.org/wiki/Ogun) |
| Ẹ̀tù | Very dark indigo strip weave with a fine check of lighter threads, named for the guinea fowl's speckled plumage | [Adire African Textiles](https://adireafricantextiles.blogspot.com/2014/05/cloth-of-month-early-indigo-dyed-aso.html), [Guardian Nigeria](https://guardian.ng/life/the-rich-colours-of-aso-oke/) |
| His followers | Hunters, blacksmiths and warriors | [Wikipedia: Ogun](https://en.wikipedia.org/wiki/Ogun) |
| Ìrẹ̀ | The first king of Ìrẹ̀; his followers believe he went into the earth at Ìrẹ̀-Èkìtì | [Wikipedia: Ogun](https://en.wikipedia.org/wiki/Ogun) |
| Colours and day in Candomblé | Red, black and green in Rio de Janeiro, blue in Bahia; Tuesday | [Wikipedia: Ogun](https://en.wikipedia.org/wiki/Ogun) |

## Where the sources disagree

Wikipedia tells two endings at Ìrẹ̀. In some stories he killed the subjects who failed to show him respect, then himself with his own sword; his followers believe he went into the earth instead of dying. The page gives both.

The gallery gives green and black as his colours in Cuba, but the Wikipedia article as read for this page gives colours only for Candomblé, so the page names those. The gallery gives his day as the third of the Yorùbá four-day week, and Candomblé consecrates Tuesday to him.

## The render's own choices (not from sources)

- His face, age and build, and his close-cut hair and short beard. None of the sources used here describes how he looks.
- What he wears follows his gallery figure: short trousers of ẹ̀tù under a fringe of màrìwò, a band of fronds on his head, iron bangles (three on the left wrist, two on the right), and the dog at his side.
- The six tools on the chain (hoe, hammer, àdá, tongs, spearhead and ring) and their forms. The gallery figure carries a hoe, a hammer, a blade and a ring.
- The àdá's shape: about 58 cm, widening to a rounded point, the edge ground bright.
- The cut of the trousers, and the check in the ẹ̀tù: three light threads down each 10.5 cm strip and a light pick every 2.5 cm.
- How the fronds are split, folded over the cord and tied, and the crown of leaflets standing up from the head band.
- The dog: a short-coated tan village dog with white on its chest and paws, lying with its head up. Stage 08 has its dog asleep; this one is awake so it reads at a distance.
- The forge. Its layout follows stage 08 in this repo (`2d-threejs/stages/Stage08-Forge.html`); the clay hearth, pot bellows, tuyère and anvil are generic forms, not a record of a real smithy.
- The night, the moonlight through the open side of the shed, and the smoke.

## How it was made

Blender 4.5 Cycles, entirely from Python scripts. The body is MakeHuman's CC0 base mesh, shaping targets and rig from [MPFB2](https://github.com/makehumancommunity/mpfb2). No other third-party assets are used.

He is the first male figure on the toolkit. `figure.py` sets a man's build on `body.MACRO` and `body.TARGETS`, as Ọ̀ṣun's sets hers. The right arm is solved to the àdá, and each finger closes at all three joints until it rests on the handle. The thumb's target is the outside of the index finger's middle bone, which lies across the far side of a handle this thick. The left hand rests: its fingers drawn together and a little curled, the thumb walked to the side of the index finger.

The ṣòkòtò are cut from the posed body between the waist and just above the knees. The fork of the legs is smoothed over and dropped a little, because woven cloth bridges it, then the trousers stand off the skin with less ease on the inside of each leg, so the legs do not meet. A drawstring shape key draws the top in to the waist while the trousers settle for 100 frames at 13,766 vertices, so the gathers below it come from the simulation. The strips of the cloth run down the legs, and the ẹ̀tù maps follow the scheme of Ahiajoku's akwete, so the toolkit's cloth material wears them.

The màrìwò is 280 strips of frond on a twisted two-ply cord. Each strip folds over the top of the cord, then falls as a fringe hangs from the hips: below its widest it may spread but never draws in, which is worked out as a support outline of the body and trousers by angle at each height. Within that, the strips gather in loose bunches, twist and part, and their ends lift. The head band carries 40 leaflet ends standing up and bending over at the tip.

His hair and beard are coils, scattered evenly over the faces of the mesh. MPFB's scalp region runs down the forehead to the brows, so the hairline is drawn in millimetres from the eye centres, as is the beard's line on the cheek and under the jaw. The scalp under the hair is shaded and the lips are darkened from the toolkit's.

The chain lies where a plane from his left shoulder to his right side cuts his body, as the convex hull of that section, because a chain pulled by its tools bridges the hollows it crosses. Its links alternate flat and on edge, and each tool hangs from a ring through a link until it meets his chest.

The dog is a set of metaballs in its own frame, joined into one skin, with ears of cupped skin added and eyes pushed out until they show under the lids. Its coat is 197,141 hair curves, combed from nose to tail, down the legs and up the ears, with white, fawn and a darker saddle carried from the skin to each hair.

The forge is lit by its fire: a point light over the coals and a hotter one low in them, and a small one at the glowing bar on the anvil. The coals and the bar glow by their own emission, with blackbody colour. A cool sun comes through the open side of the shed as moonlight. As with Ahiajoku and Ọ̀ṣun, a low lamp lights only the skin, through Cycles light linking, and a wide soft lamp stands for the firelight thrown back off the floor.

To rebuild, install MPFB2 as a Blender extension and set `RENDER_WORK` to a scratch folder, then run these from the repo root. Building the scene takes about seven minutes on an 8 GB Apple M1, most of it the trousers' simulation, and the stages save to that folder as they go:

```bash
blender -b --python 3d/ogun/blender/build.py -- textures body pose sokoto mariwo dress scene
```

Each still then takes three to six minutes at 96 samples. `blender/render_views.py` lists the camera views:

```bash
blender -b $RENDER_WORK/60_scene.blend --python 3d/ogun/blender/shots.py -- --samples 96 hero portrait chain
```

The 36 turntable views take about ten minutes at 32 samples:

```bash
blender -b $RENDER_WORK/60_scene.blend --python 3d/ogun/blender/shots.py -- --samples 32 turntable
```

This writes the scene, with its textures packed in, to `ogun.blend`:

```bash
blender -b --python 3d/ogun/blender/build.py -- package
```
