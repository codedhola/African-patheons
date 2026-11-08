# Idemili: realistic render notes

A photoreal Idemili in Blender, following her figure in the Òrìṣà and Alụsị gallery. The page has a hero image, a 36-view turntable, eight close-ups and a sources section: https://claude.ai/artifact/E5Qjgj2T2dgZpnZhRRWRm9

In this folder, `idemili-of-nnobi.html` is that page, `idemili.blend` is the finished scene with its textures packed in, and `blender/` holds what is hers. The shared method lives in [`../toolkit/`](../toolkit/).

## What the sources support

| Element | What the source says | Source |
|---|---|---|
| River and goddess | In Idemili's cosmology the river is more than water: it is a goddess, who sent the royal python, Eke Idemili, as her messenger | [Idemili North Local Government](https://idemilinorth.an.gov.ng) |
| The python | Pythons are messengers of the gods of Idemili and no one may harm them; one killed by accident is wrapped in white cloth and given a funeral | [R. Okonkwo, Peoples Gazette (2021)](https://gazettengr.com/rudolf-okonkwo-the-changing-fortunes-idemili-pythons/) |
| Her shrine | The great shrine of Idemili is at Nnobi | [R. Okonkwo, Peoples Gazette (2021)](https://gazettengr.com/rudolf-okonkwo-the-changing-fortunes-idemili-pythons/) |
| The royal python | A stocky snake with a small head and smooth scales, up to about 1.8 m; dark brown with light brown blotches on the back and sides, the belly white or cream with black markings; revered by the Igbo as a symbol of the earth | [Wikipedia: Ball python](https://en.wikipedia.org/wiki/Ball_python) |
| Akwa miri | "Cloth of the water", a commonly traded Akwete cloth, woven white or white with indigo stripes | [Wikipedia: Akwete cloth](https://en.wikipedia.org/wiki/Akwete_cloth) |
| Nzu | Sacred white chalk, offered at shrines and tied to purity and the ancestors; priests and diviners mark their foreheads and eyelids with it | [P. Basu with G. Chika-Kanu, [Re:]Entanglements (2020)](https://re-entanglements.net/chalk/) |
| Coral and ivory | Large coral beads are worn round the neck and on the wrists; ivory ornaments, odu, were the insignia of the Otu Odu society of Igbo women, who wear white head ties and white wrappers | [Wikipedia: Igbo regalia and headdresses](https://en.wikipedia.org/wiki/Igbo_regalia_and_headdresses) |

## Where the sources disagree

The Idemili North government calls Idemili a goddess whose messenger is the python; Okonkwo writes of the pythons as messengers of "the gods of Idemili". The page gives both.

The Idemili North site did not load when this page was made. Its wording here is from the gallery, which cites it, and from the site's search listing.

## The render's own choices (not from sources)

- Her face, age and build. No source used here describes how she looks; she is drawn as a tall, composed woman of about thirty-five.
- What she wears follows her gallery figure: a wrapper of akwa miri tied at the chest, a white head tie, white chalk lines on her face, three strands of coral, two ivory bangles on her right wrist, and a clay pot at her hip, with the python rising beside her from the water.
- The spacing of the stripes: one broad indigo stripe and two fine lines every fifteen centimetres, running down the wrapper as on the gallery figure, with a narrow indigo border at its edges.
- The chalk's strokes: a line down the middle of her forehead and a stroke across each cheek, after the gallery figure.
- The head tie's shape: wound high over the crown and tied at the nape, with two short tails. The gallery figure's tie has a band of folds standing behind; here the cloth is built up over the crown instead.
- The python's pose and the layout of its blotches, and the pot's form and its lean on her hip.
- The place and the hour: an invented reach of the Idemili at dawn, mist on the water, raffia palms, oil palms and forest along the banks.

## How it was made

Blender 4.5 Cycles, entirely from Python scripts. The body is MakeHuman's CC0 base mesh, shaping targets and rig from [MPFB2](https://github.com/makehumancommunity/mpfb2). No other third-party assets are used.

`figure.py` shapes her tall and composed. Her pose is Yemọja's: her weight on her left leg under the pot, the pot placed first against her hip with room for the wrapper, and her left hand solved to it, palm on the belly, each finger closing until it rests on the clay. Her arm is long enough that the forearm could cross the pot's shoulder on its way down. So the pot's height on the hip, its lean and where the palm lies are tried together, and the set whose forearm clears the clay is kept: the pot sits low on her hip with its mouth leaning out. It is about 24 cm tall, near the size of the gallery figure's.

The akwa miri is cut from the body as the toolkit's wrapper is, from outlines by angle at each height, but it starts above her bust, under her arms, and below the bust it hangs: an outline may grow over the hips but never draws back in to the waist. The cut is taken from her final pose, so the pinned top edge lies outside the skin once her arms are down. It is simulated for 110 frames at 28,800 vertices while her arms come down onto it and the pot stands against it. Its maps follow the scheme the series' woven cloths share: four groups of stripes in each 60.5 cm repeat, and a narrow indigo border along the cloth's edges.

The ichafu is Yemọja's gèlè without its fan: a surface lifted off the skull, worked out in spherical coordinates round the knot at the nape, built up over the crown in soft pleats, with two short tails below the knot. Close-cut hair shows below it, behind the line of the temples.

The nzu is a thin film laid over the face as it renders, cut from the posed body at its render smoothing and lifted a third of a millimetre off the skin. Its three strokes are set in millimetres from the midpoint between her eyes, thinning to their ends and broken where the chalk ran dry.

The coral is three strands of barrel beads laid with the toolkit's strands, each bead lifted onto the skin where a strand dips into it at the sides of the neck. The ivory bangles are the toolkit's turned rings, sized to her wrist. Before the final renders the pot, coral, bangles, wrapper, head tie and chalk were measured against the skin. The coral, bangles, head tie and chalk clear it; the pot's rim meets her forearm by under a centimetre, and the wrapper's top edge runs under her right arm where the arm rests on it. Neither shows from any of the cameras.

The python is a tube swept along a path of 16 points. It rises out of the water beside her right hand in a gentle S, its head held level and turned toward her, then lies along the bed round in front of her feet, about 1.69 m from neck to tail. Its girth runs from a slim neck to a stocky body and a short tail, its section is flattened on the belly, and its back faces up where it lies and outward where it rears, so its patterned flank faces the front. The pattern is laid out by distance along the body and angle round it: light brown blotches with dark hearts down each flank, saddles over the spine, a cream belly flecked with black, and small smooth scales.

The river is Yemọja's closed slab of water over a muddy bed, its surface letting shadow rays through so the bed is lit. The mist is a volume over the water behind her, thickest at the surface, thinning within a few metres and broken into drifts, lit from behind by the low sun. Raffia palms with short trunks and steep fronds crowd the far bank, with oil palms and forest trees behind them, and as for the other figures a low lamp lights only the skin.

To rebuild, install MPFB2 as a Blender extension and set `RENDER_WORK` to a scratch folder, then run these from the repo root. Building the scene takes about five minutes on an 8 GB Apple M1, most of it the wrapper's simulation, and the stages save to that folder as they go:

```bash
blender -b --python 3d/idemili/blender/build.py -- textures body pose wrapper dress scene
```

Each still then takes about three minutes at 96 samples, the mist making them slower than the other figures'. `blender/render_views.py` lists the camera views:

```bash
blender -b $RENDER_WORK/60_scene.blend --python 3d/idemili/blender/shots.py -- --samples 96 hero portrait python
```

The 36 turntable views take about four minutes at 32 samples:

```bash
blender -b $RENDER_WORK/60_scene.blend --python 3d/idemili/blender/shots.py -- --samples 32 turntable
```

This writes the scene, with its textures packed in, to `idemili.blend`:

```bash
blender -b --python 3d/idemili/blender/build.py -- package
```
