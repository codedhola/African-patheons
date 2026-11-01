# x

2D fighting-game stage backgrounds (1600×900, SVG in HTML) with Yorùbá and Igbo settings.

- `stages/` — open any `.html` file in a browser. `Main.html` and `FightStage.html` are the original town and fight scenes.
- `previews/` — PNG renders of stages 01–25.
- Stage spec: fighters' ground line at y 772, top 150 px kept clear for the HUD.

See `STAGES.md` for what each stage is based on and its sources.

## Ṣàngó of Ọ̀yọ́

`sango/sango-of-oyo.html` is the photoreal Ṣàngó page: a Blender Cycles render with a 36-view turntable and close-ups. Open it in a browser; images are in `sango/img/`.

## Amadioha of Ozuzu

`amadioha/amadioha-of-ozuzu.html` is the photoreal Amadioha page, a companion to the Ṣàngó render. It shows him both ways the sources do: as a fair-skinned titled gentleman in a red isiagụ, white wrapper and red cap with eagle feathers, holding his glowing sword Mmaagha Kamalu and an akupe fan, and as the gigantic white ram beside him. It has a hero render, a 36-view turntable, six close-ups and a list of what is sourced and what is designed. Open it in a browser; images are in `amadioha/img/`.

## Ahiajoku of the Yam

`ahiajoku/ahiajoku-of-the-yam.html` is the photoreal Ahiajoku page. It shows the Igbo yam deity at dusk on her festival, in a matching Akwete wrapper, blouse and head tie with coral and ivory, holding out a new yam as the full moon rises over a yam field and barn. It has a hero render, a 36-view turntable, eight close-ups and a list of what is sourced and what is designed. Open it in a browser; images are in `ahiajoku/img/`. The finished scene is `ahiajoku/ahiajoku.blend`, and the scripts that generate it are in `ahiajoku/blender/`.

## Stormshrine (3D)

`stormshrine/` holds a game-ready Blender model of stage 11, Ṣàngó's storm hill, built from the stage board and scaled for a 1.8 m player. It contains `Stormshrine.blend`, the script `build_stormshrine.py` that generates it, PNG textures and preview renders. Its README lists the assumptions and the files it was based on.

`stormshrine/viewer/index.html` is a 360° viewer for the model: look around from the hilltop or the shrine's doorway, or orbit the real-time model. It loads files from its folder, so serve the folder (for example with `python3 -m http.server`) rather than opening the file directly.

## Ofala (3D)

`ofala/` holds a game-ready Blender model of stage 21, the Ofala palace arena at Onitsha. It was built from the stage board the same way as the Stormshrine, with the same toolkit, and scaled for a 1.8 m player. It contains `Ofala.blend`, the script `build_ofala.py` that generates it, PNG textures and preview renders. Its README lists the assumptions and the files it was based on.

`ofala/viewer/index.html` is its 360° viewer. You can look around from the arena or from the dais in front of the empty throne, or orbit the real-time model while the cannon fires the festival's 21-gun salute. Serve its folder over HTTP, as with the Stormshrine viewer.

## New Yam festival (3D)

`newyam/` holds a game-ready Blender model of stage 25, the New Yam festival. It was built from the stage board with the same toolkit and scaled for a 1.8 m player. It shows the elder's thatched house with its open bay and carved posts, the heap of new yams on a raffia mat, and the elder roasting the first yam. Around them are dancers, drummers, a masquerade, villagers and a string of young palm fronds between two shade trees. The folder contains `NewYam.blend`, the script `build_newyam.py` that generates it, PNG textures and preview renders. Its README lists the assumptions and the files it was based on.

`newyam/viewer/index.html` is its 360° viewer. You can look around from the arena or from the elder's open bay over the yams, or orbit the real-time model while the masquerade and dancers move and the first yam's fire smokes. Serve its folder over HTTP, as with the other viewers.

## The gods

Two pages in `gods/`, each a single self-contained HTML file. Open either in a browser.

- **`gods/orisa-and-alusi.html`** (*Òrìṣà and Alụsị*): 23 deities, 13 Yoruba òrìṣà and 10 Igbo alụsị, each modelled in 3D with three.js. Every god comes with its cloth, beads and regalia, a myth, the points where sources disagree, and citations. It needs an internet connection the first time it loads, to fetch three.js from jsDelivr and the fonts from Google Fonts.
- **`gods/african-religions-reference.html`** (*Africa's Gods and Ancestors*): a searchable field reference covering the traditional religions of 21 African peoples across 5 regions. It lists 129 deities and spirits, with 137 cited sources.

## Reference notes

Research notes and sources behind the work, in `docs/`:

- [`docs/fighting-stages.md`](docs/fighting-stages.md): the shared stage spec, what each of the 25 stages draws on, which details are design choices, and every source.
- [`docs/sango-render-notes.md`](docs/sango-render-notes.md): which parts of the realistic Ṣàngó come from sources, which are the render's own choices, and how it was made.
- [`docs/amadioha-render-notes.md`](docs/amadioha-render-notes.md): the same for the realistic Amadioha and his ram.
- [`docs/ahiajoku-render-notes.md`](docs/ahiajoku-render-notes.md): the same for the realistic Ahiajoku, plus how to rebuild the scene.
