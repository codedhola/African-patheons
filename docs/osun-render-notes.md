# Ọ̀ṣun: realistic render notes

A photoreal Ọ̀ṣun in Blender, following her figure in the Òrìṣà and Alụsị gallery. The page has a hero image, a 36-view turntable, eight close-ups and a sources section: https://claude.ai/artifact/CDxt7bfdX3PF5FrtxNyyT1

In the repo, `osun/osun-of-osogbo.html` is that page, `osun/osun.blend` is the finished scene with its textures packed in, and `osun/blender/` holds what is hers. The shared method lives in `ahiajoku/blender/`, which these scripts import as a toolkit.

## What the sources support

| Element | What the source says | Source |
|---|---|---|
| White cloth | Her priests and priestesses wear white robes in her honour | [Zikoko](https://www.zikoko.com/life/8-interesting-things-about-the-annual-osun-osogbo-festival/) |
| Ìró and bùbá | A wrapper tied at the chest or waist, and a loose or fitted blouse | [Wikipedia: Yoruba women's clothing](https://en.wikipedia.org/wiki/Yoruba_women%27s_clothing) |
| Àgògo | "The exclusive preserve of Osun initiates and priestesses"; photographs show rows rising into rings of braid | [Akintunde Akinleye, Àgògo 1](https://artsandculture.google.com/asset/osun-hairstyles-%C3%80g%C3%B2go-1-akintunde-akinleye/ZgEKrg3lSF1Jyw), [Àgògo 6](https://artsandculture.google.com/asset/osun-hairstyles-%C3%80g%C3%B2go-6-akintunde-akinleye/DwG-VR4jz73QeA) |
| Cockscomb | The style "is made to imitate a cockscomb" | [Oriire](https://oriire.com/article/hairdressing-and-hairstyles-in-yorubaland-history-nature-dynamics-and-significance) |
| Ìkódẹ and Àrẹ́mọ́rùn | Hair adorned with ìkódẹ; the Àrẹ́mọ́rùn choker goes with the style | [Àgògo 6](https://artsandculture.google.com/asset/osun-hairstyles-%C3%80g%C3%B2go-6-akintunde-akinleye/DwG-VR4jz73QeA) |
| Hair ornaments | Parrot feathers, cowries, brass or golden hair sticks | [Pulse](https://www.pulse.ng/story/hairstyles-dedicated-to-the-osun-goddess-and-their-hidden-meanings-2024092615480638696) |
| Abẹ̀bẹ̀ | Priestesses carry brass fans along the river; the fan as relief from anxiety; brass, 14 × 8¾ × 1¼ in | [High Museum of Art: Fan for Osun](https://high.org/collection/fan-for-osun/) |
| Ààjà | A brass or bronze bell used when offering prayers to her; "the bell-like Aja-Osun" | [Zikoko](https://www.zikoko.com/life/8-interesting-things-about-the-annual-osun-osogbo-festival/), [Adunni Olorisha Trust](https://artsandculture.google.com/asset/adedoyin-talabi-faniyi-with-the-aja-osun-abiodun-omotoso/8QGcamhakYi7kQ) |
| Colours and number | Yellow, coral, gold, white; five | [Wikipedia: Oshun](https://en.wikipedia.org/wiki/Oshun) |
| Amber and orange | Both on her list of objects and offerings | [Wikipedia: Oshun](https://en.wikipedia.org/wiki/Oshun) |
| The grove | A meandering river through some of the last primary high forest in southern Nigeria, regarded as her abode | [UNESCO](https://whc.unesco.org/en/list/1118/) |
| Tìróò | A Yorùbá cosmetic used to enhance facial beauty | [Ojo and Boluwatife (2025)](https://pressto.amu.edu.pl/index.php/jgp/article/view/55357) |

## Where the sources disagree

Yellow and gold lead in Cuba and Brazil, while at Òṣogbo her priests wear white. This render follows Òṣogbo for the cloth and gives the gold to the sash.

UNESCO gives the festival twelve days in July and August, Wikipedia about two weeks in August, and the Adunni Olorisha Trust ten to fourteen days in August. The page says only that it falls every August.

One source calls the Àgògo the preserve of Ọ̀ṣun initiates and priestesses; others say it can mark married women or priestesses of other cults, including Ṣàngó, Èṣù and Ọya. It is worn here as the Ọ̀ṣun sources describe it.

## The render's own choices (not from sources)

- Her face, age and build. None of the sources used here describes how she looks.
- Dressing the òrìṣà as her priestesses dress. The sources describe them, not her.
- The two fish on the fan. The High Museum's fan has two birds; its size, coiled rim and ribs are followed here.
- The bell's shape. The sources give its metal, not its form.
- The gold sash, from the gallery figure, in her colours.
- The white aṣọ-òkè strips and their thin gold lines. The strip width follows the Ṣàngó render.
- The crest's exact shape and how many braids it has. Its form follows the photographs; its measurements are by eye.
- The Àrẹ́mọ́rùn choker's colours and the number of strands.
- Tìróò along her lash line.
- The calabash, its burned pattern, and setting out five oranges.
- The morning, and this bend of the river. It is invented. The grove's real sculptures are left out, because they are the works of named artists.

## How it was made

Blender 4.5 Cycles, entirely from Python scripts. The body is MakeHuman's CC0 base mesh, shaping targets and rig from [MPFB2](https://github.com/makehumancommunity/mpfb2). No other third-party assets are used.

The ìró is one sheet of 27,848 vertices, wound round the hips and simulated for 110 frames. The bùbá is cut from the body with its hollows bridged, because woven cloth spans them and does not follow them in, then simulated at 32,772 vertices for 150 frames while the arms rise to the fan and bell. During that run a shape key draws a ring of the blouse in to the waist and lifts it, so the gathers above and below the sash come from the simulation. The sash is a band of the gold cloth with a separate knot and two fringed tails. It is fitted to that drawn-in ring, not to the body, and any torso cloth that pouched over the ring is pressed flat under it and eases out past its edges, as it would under a tied sash. Sleeves are left out of that, so they still fall over it.

The Àgògo is 31 cornrows projected onto the scalp from the hairline to the crest, and 13 rings of thicker braid round the crest, on both faces and over the rim. Each braid is three crossing strands, each strand a bundle of hair curves: 2,688 curves and 358,080 points in all. The two ìkódẹ feathers have 600 barbs between them, and 19 cowries run along the rim.

Each arm is solved to its object. Each finger then closes at all three joints at once, as a real finger does, until it rests on the handle, with the thumb over them. The curl is measured on one fixed axis per finger, because an axis taken from the bone's current direction flips once the finger passes 90 degrees. The fan's relief is one height map on one surface of brass. The cloth maps follow the Akwete's scheme, so the toolkit's cloth material can wear them: eleven strips 10.5 cm wide, on the same woven height map.

The grove is a height field with the river's bend cut through it, 280 trees, 420 shrubs and 240 reed beds. The canopy is too thin to break up the sun on its own, so a sheet only the sun can see, 23 m up, has gaps that turn sunlight into shafts and dapples, and a thin volume of haze makes the shafts visible. As with Ahiajoku, a low lamp lights only the skin, through Cycles light linking.

Ọ̀ṣun needed a few things the toolkit did not have: a choice of cloth maps and edge colours, eye paint in the skin masks, eye sizes, and sleeve ease and flare. Each one defaults to what Ahiajoku already used.

To rebuild, install MPFB2 as a Blender extension and set `AHIAJOKU_WORK` to a scratch folder. Building the scene takes about seven minutes on an 8 GB Apple M1, and the stages save to that folder as they go:

```bash
blender -b --python osun/blender/build.py -- textures body pose wrapper buba sash dress scene
```

Each still then takes two to nine minutes at 96 samples. `osun/blender/render_views.py` lists the camera views:

```bash
blender -b $AHIAJOKU_WORK/60_scene.blend --python osun/blender/shots.py -- --samples 96 hero portrait agogo
```

The 36 turntable views take about four minutes at 32 samples:

```bash
blender -b $AHIAJOKU_WORK/60_scene.blend --python osun/blender/shots.py -- --samples 32 turntable
```

This writes the scene, with its textures packed in, to `osun/osun.blend`:

```bash
blender -b --python osun/blender/build.py -- package
```
