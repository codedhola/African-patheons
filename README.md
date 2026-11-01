# African Pantheons

Yorùbá and Igbo gods and places, made for a fighting game and as studies in their own right. Each piece records what comes from sources and what was designed.

## Where things are

| Folder | What it holds |
|---|---|
| [`3d/`](3d/) | Photoreal Blender renders of Ṣàngó, Amadioha, Ahiajoku and Ọ̀ṣun, and the toolkit that builds them |
| [`2d-threejs/`](2d-threejs/) | Pages that run in the browser: 25 SVG fighting stages, a three.js gallery of 23 deities, and a reference to the religions of 21 African peoples |
| [`locations/`](locations/) | Game-ready Blender models of three stages, each with a three.js 360° viewer |

```
3d/
  toolkit/        shared Blender scripts
  sango/          Ṣàngó of Ọ̀yọ́
  amadioha/       Amadioha of Ozuzu
  ahiajoku/       Ahiajoku of the Yam
  osun/           Ọ̀ṣun of Òṣogbo
2d-threejs/
  stages/         the SVG stages, their previews and research notes
  gods/           the three.js gallery and the religions reference
locations/
  stormshrine/    stage 11, Ṣàngó's storm hill
  ofala/          stage 21, the Ofala palace arena
  newyam/         stage 25, the New Yam festival
```

Every deity, stage set and location keeps its pages, images, scripts and notes together. The `README.md` in each folder is its notes: what the sources support, what was designed, and how it was made.

## Opening the work

The pages in `3d/` and `2d-threejs/` open directly in a browser. `2d-threejs/gods/orisa-and-alusi.html` needs an internet connection the first time, to fetch three.js and the fonts.

The 360° viewers load files from their own folder, so serve that folder, then open the address it prints:

```bash
cd locations/ofala/viewer && python3 -m http.server
```
