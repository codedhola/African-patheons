# Ọ̀ṣọ́ọ̀sì: realistic render notes

A photoreal Ọ̀ṣọ́ọ̀sì in Blender, following his figure in the Òrìṣà and Alụsị gallery. The page has a hero image, a 36-view turntable, eight close-ups and a sources section: https://claude.ai/artifact/9Mge2j9BaBXyG1nSDUHWfT

In this folder, `osoosi-of-ketu.html` is that page, `osoosi.blend` is the finished scene with its textures packed in, and `blender/` holds what is his. The shared method lives in [`../toolkit/`](../toolkit/).

## What the sources support

| Element | What the source says | Source |
|---|---|---|
| Hunter and warrior | One of the most important hunter and warrior deities of Yorùbá culture, worshipped in Nigeria, Benin and Togo | [Wikipedia: Oshosi](https://en.wikipedia.org/wiki/Oshosi) |
| Bow and arrow | His main symbols are the bow and arrow, ọrun àti ọfà | [Wikipedia: Oshosi](https://en.wikipedia.org/wiki/Oshosi) |
| Kétu | On the Benin side of Yorùbáland, in Kétu, Ìlíkímu and Ṣábẹ̀ẹ́, he is called Ọ̀ṣọ́ọ̀sìn or Ọ̀tchọ́ọ̀sìn | [Wikipedia: Oshosi](https://en.wikipedia.org/wiki/Oshosi) |
| In Candomblé | The spirit of the hunt, forests, animals and wealth; his colour is blue in the Ketu nation, otherwise green; his ritual garment is blue and his necklace blue beads; he hunts with a bow and arrow, the ofá; goat, cooked pig and guinea fowl are offered to him | [Wikipedia: Oshosi](https://en.wikipedia.org/wiki/Oshosi) |
| The hunter of one arrow | At the yam festival of Olon, king of Ifẹ̀, a huge bird sent by witches who had not been invited flew over the feast. Hunters of twenty, forty and fifty arrows missed it; Oxotokanxoxô, the hunter of a single arrow, struck it full in the breast after his mother, told by a diviner, offered a hen to the witches. The king gave him half his fortune, the other hunters gave him sacks of cowries, and the diviner's song, "Oxowusi!", gave him his name. Souza calls Oxóssi a hunter and king of Ketu | [J. M. Souza, Revista Mosaico (2020), after Verger](https://doi.org/10.18224/mos.v13.n0.7553) |
| The iroko | A large hardwood tree that can live 500 years; the Yorùbá hold that it houses a spirit, Olúwéré, and where it grows it is shunned or revered with offerings | [Wikipedia: Iroko](https://en.wikipedia.org/wiki/Iroko) |

## Where the sources disagree

Wikipedia gives his colour in Candomblé as blue in the Ketu nation and green elsewhere. This figure, of Kétu, wears blue.

## The render's own choices (not from sources)

- His face, age and build. No source used here describes how he looks; he is drawn as a lean young hunter of about twenty-five.
- The moment. He is drawn as the hunter of one arrow, at full draw with his single arrow aimed up into the trees; what he aims at is left out of the picture.
- What he wears follows his gallery figure: a blue tunic over short trousers, three strands of blue beads, and a leather quiver of arrows on his back on a strap over his right shoulder.
- The cloth: handwoven cotton strips dyed in the indigo vat, pale sky blue with deep indigo stripes for the tunic and deep indigo for the trousers. Ògún's ẹ̀tù is the near-black cloth of the series; this one is dyed only a few times.
- The bow, the arrows and the quiver: a self bow of dark hardwood about 1.35 m along its curve, reed arrows with leaf-shaped iron heads, fletched with guinea-fowl feathers, and a quiver of hide closed in a dome at the foot, with a band of zigzags burned in below the mouth. Their forms and the zigzags are this study's.
- The draw: the Mediterranean draw, three fingers on the string with the arrow between the first two, anchored at the corner of his jaw.
- The place and the hour: a clearing in high forest after stage 06 of this repo, with a giant iroko, offerings at its foot, ferns, lianas, a fallen log and blue-green mist, lit from high above through gaps in the canopy.

## How it was made

Blender 4.5 Cycles, entirely from Python scripts. The body is MakeHuman's CC0 base mesh, shaping targets and rig from [MPFB2](https://github.com/makehumancommunity/mpfb2). No other third-party assets are used.

`figure.py` shapes him lean and wiry, about 1.72 m tall. `stance.py` builds the draw. An archer shooting upward bends at the waist and keeps the T of his shoulders and arms, so his spine is tilted 14 degrees along the shot and his head turned 74 degrees to look along it. The drawing hand is placed first: 45 places for the nock are tried round the corner of his jaw, in millimetres from the midpoint between his eyes; for each, the arm is solved, three fingers are hooked on the string with the arrow between the first two, and the posed skin is tested against his face. The place kept is the one where the hooked fingers come closest to his face without pressing into it and the string and arrow stay clear of it. The thumb is left out of that test, since straight it points at his face, and is laid along the top of the index finger last, clear of the face. The bow's grip is then set a full draw ahead of the nock along the shot, and the bow arm solved to reach it, the draw shortened if the arm cannot; here it reaches the full 66 cm.

Re-solving a hand a hundred times over lets the bones' scale creep: each matrix set leaves a little, and down a finger it compounds, until on one run a fingertip was a million times its size and the hand's skin reached kilometres away. The scale is now reset each time the hand is straightened and after every step of the thumb.

`bow.py` builds the bow already bent: each limb an arc from the end of the handle, bent as far as a string of fixed length lets it come back to the nock, which at full draw is about 67 degrees at each tip, with a D section that is flat on the back and round on the belly. The handle is bound in a strip of hide wound round in overlapping turns, and his left hand closes on it finger by finger until each finger rests on the leather; the thumb is swung over the index finger by a coarse search first, as the walk that finishes it cannot get round the grip on its own. The string runs from the top notch through the crooks of his three fingers to the bottom notch. The arrows are reed with three nodes, a leaf-shaped iron head with filed edges bound on with fibre, and two half-vanes of guinea-fowl feather, slate grey with white spots.

The tunic is the toolkit's blouse cut to a man's measure, to the top of his thighs with short sleeves, simulated for 110 frames while his arms rise into the draw, over drawstring trousers cut and simulated as Ògún's were. Their strips run down the body and along the sleeves. The quiver's strap is the section of his body and tunic in a plane through his right shoulder and his left side, pulled taut so it bridges the hollows, and the quiver lies along its run across his back, its mouth behind his right shoulder, six arrows standing in it heads down. Its zigzag band is drawn in the material by distance along the quiver and angle round it. The beads are three strands of turquoise glass laid over the tunic and the strap.

`forest.py` follows Ọ̀ṣun's grove without the river: tall trunks with buttress roots placed round the clearing and kept out of the hero camera's way, an iroko larger than any of them with a gap between two buttresses facing the clearing, a roof of leaves with gaps that the sun comes through as shafts, ferns, lianas, a fallen log mossed on its upper side, fallen leaves thick on the floor, and a blue-green mist that fades the far trunks. The offerings in the iroko's niche are a clay pot, a calabash of kola nuts and cowries on the soil. As for the other figures, a low lamp lights only the skin.

To rebuild, install MPFB2 as a Blender extension and set `RENDER_WORK` to a scratch folder, then run these from the repo root. Building the scene takes about twelve minutes on an 8 GB Apple M1, most of it the two cloth simulations, and the stages save to that folder as they go:

```bash
blender -b --python 3d/osoosi/blender/build.py -- textures body pose trousers tunic dress scene
```

Each still then takes about three minutes at 96 samples. On this Mac the first render of a session can wait a quarter of an hour longer while Cycles compiles its optimized kernels for Metal, so render the stills in one session. `blender/render_views.py` lists the camera views:

```bash
blender -b $RENDER_WORK/60_scene.blend --python 3d/osoosi/blender/shots.py -- --samples 96 hero portrait face
```

The 36 turntable views take about four minutes at 32 samples, under the same lights as the other figures:

```bash
blender -b $RENDER_WORK/60_scene.blend --python 3d/osoosi/blender/shots.py -- --samples 32 turntable
```

This writes the scene, with its textures packed in, to `osoosi.blend`:

```bash
blender -b --python 3d/osoosi/blender/build.py -- package
```
