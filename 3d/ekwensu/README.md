# Ekwensu: realistic render notes

A photoreal Ekwensu in Blender, following his figure in the Òrìṣà and Alụsị gallery. The page has a hero image, a 36-view turntable, eight close-ups and a sources section: https://claude.ai/artifact/Hu6eQPzDeKUw3Mt4DiKPxZ

In this folder, `ekwensu-of-the-bargain.html` is that page, `ekwensu.blend` is the finished scene with its textures packed in, and `blender/` holds what is his. The shared method lives in [`../toolkit/`](../toolkit/).

## What the sources support

| Element | What the source says | Source |
|---|---|---|
| His domains | The alụsị of bargains and of the tortoise; a trickster, crafty at trade and negotiation | [Wikipedia: Ekwensu](https://en.wikipedia.org/wiki/Ekwensu) |
| Trade | Often invoked for guidance in difficult mercantile situations | [Wikipedia: Ekwensu](https://en.wikipedia.org/wiki/Ekwensu) |
| War | A war god who guided warriors in battle, and also seen as a spirit that incites violence | [Wikipedia: Ekwensu](https://en.wikipedia.org/wiki/Ekwensu) |
| The moon | Once highly honoured as one of the benevolent lunar deities | [Wikipedia: Ekwensu](https://en.wikipedia.org/wiki/Ekwensu) |
| Okpu agụ | The leopard cap of bravery, tied to Ohafia warrior traditions: a round, slanting cap of knitted wool striped black, white and red. The black and white recall the leopard; the red was reserved for warriors who had taken heads in battle or brought home a strong animal such as a leopard | [Wikipedia: Igbo regalia and headdresses](https://en.wikipedia.org/wiki/Igbo_regalia_and_headdresses) |
| Raffia | Among the traditional weaving fibres; coarse raffia cloth was used for masquerades, warrior garb and ceremonial dress | [Wikipedia: Akwete cloth](https://en.wikipedia.org/wiki/Akwete_cloth) |

## Where the sources disagree

Wikipedia gives two figures. One is the alụsị of the trader and the warrior, honoured among the benevolent lunar deities. The other is a spirit of violence, and the article says that with Christianity his more beneficent aspects were supplanted by missionaries who came to represent him as Satan. This render draws the older figure: a trader and warrior in a market at dusk, not the Devil.

## The render's own choices (not from sources)

- His face, age and build. No source used here describes how he looks; he is drawn as a lean, long-limbed man of about thirty, with a knowing half-smile.
- What he wears follows his gallery figure: short trousers of raffia cloth under a raffia fringe, the okpu agụ, one strand of black, white and red beads, a leather strap over his left shoulder, two iron bangles on each wrist, a machete in his right hand, his left hand on his hip, and the tortoise at his feet.
- The cap's fit and bands: it follows his skull, slants lower over his left ear and rolls at the brim. The order of the bands and the leopard's rosettes on the white are this study's.
- The raffia cloth's weave, its narrow brown stripes and the cut of the trousers.
- The machete's shape, and the pouch on the strap.
- The tortoise: a hinge-back tortoise of the West African forest and farmland, walking.
- The place and the hour: an Igbo market square at dusk, its thatched stalls, the day's wares left on the tables, clay lamps of palm oil, the bush and oil palms beyond, and a young crescent moon over his right shoulder. The moon is drawn about four times its true size so that it reads.

## How it was made

Blender 4.5 Cycles, entirely from Python scripts. The body is MakeHuman's CC0 base mesh, shaping targets and rig from [MPFB2](https://github.com/makehumancommunity/mpfb2). No other third-party assets are used.

`figure.py` shapes him leaner than Ògún, with a narrow face, high cheekbones and the corners of the mouth turned up. He stands with his weight on his right leg and his head turned a little to his left. His left hand is set on his hip: the flank above the hip joint is measured on the posed body, with the arms left out, and the palm is placed on the cloth over it, the fingers forward and down. His right hand is solved to the machete's handle as Ògún's was to his àdá, each finger closing until it rests on the wood. The machete is turned in the fist so that its edge faces out and back and its flat shows from the front.

The trousers are cut from the posed body as Ògún's ṣòkòtò were and simulated for 100 frames at 12,380 vertices while a drawstring draws the waist in. Their raffia cloth is a procedural plain weave of flat fibres two and a half millimetres wide, each its own shade of straw, with a pair of narrow brown stripes every ten centimetres in the warp. The fringe is 300 strips of dry raffia folded over a twisted two-ply cord, falling as a fringe hangs from the hips, gathering in loose bunches, and crinkled every few centimetres.

The okpu agụ is a surface lifted off the skull, worked out in spherical coordinates round the centre of the head, as Ahiajoku's ichafu was. Its lower edge is set by angle round the head: across the middle of the forehead, a centimetre or two over the tops of the ears, and down over the back of the skull, seven degrees lower on his left. The knit is in the material: bands of red, black and white by height on the cap, the leopard's broken rings on the white, columns of stocking-stitch Vs about four to the centimetre, and a soft sheen. Close-cut coiled hair shows below the cap, behind the line of the temples.

The strap lies where a plane from his left shoulder to his right side cuts his body, pulled taut across the hollows, as Ògún's chain did. It crosses his right side above the gathered waistband, where there is room between his flank and the hanging arm, and turns gradually round the corners of its path rather than creasing. The pouch hangs from its front run, in front of his right hip, standing off whatever lies beneath it, with a curved flap closed by a horn toggle. Before the final renders the pouch, strap and bangles were measured against the skin, and they now clear it, apart from a graze of three millimetres at the top of his shoulder that no camera sees. The beads are one strand, black, white and red in turn.

The tortoise is a set of metaballs for its head, neck, legs and tail, joined into one scaly skin under a domed shell whose scutes, grooves and growth rings are painted into its texture.

The market's stalls have roofs sloping down to the square, and their eaves are 14,920 hanging strands of dry palm. Clay lamps burn on the tables nearest him, and one on the ground by his left foot, where a trader set it down. The bush beyond is made of leaf cards, and 26 oil palms stand out of it, kept clear of the moon and below it as seen from the hero camera. The sky is Blender's physical sky with the sun two degrees below the horizon. Ozone is set to three times its usual density, because the ozone layer's absorption is what turns twilight blue. The moon is a card that only adds light, because the twilight lies in the air between us and the moon and its dark part hides nothing. He is lit by a lamp hung out of the picture to his right, the afterglow as a soft sun behind him, the clay lamps, and, as for the other figures, a low lamp only the skin receives.

To rebuild, install MPFB2 as a Blender extension and set `RENDER_WORK` to a scratch folder, then run these from the repo root. Building the scene takes about five minutes on an 8 GB Apple M1, most of it the trousers' simulation, and the stages save to that folder as they go:

```bash
blender -b --python 3d/ekwensu/blender/build.py -- body pose trousers fringe dress scene
```

Each still then takes about a minute and a quarter at 96 samples. `blender/render_views.py` lists the camera views:

```bash
blender -b $RENDER_WORK/60_scene.blend --python 3d/ekwensu/blender/shots.py -- --samples 96 hero portrait cap
```

The 36 turntable views take about four minutes at 32 samples:

```bash
blender -b $RENDER_WORK/60_scene.blend --python 3d/ekwensu/blender/shots.py -- --samples 32 turntable
```

This writes the scene, with its textures packed in, to `ekwensu.blend`:

```bash
blender -b --python 3d/ekwensu/blender/build.py -- package
```
