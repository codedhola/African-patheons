# x

2D fighting-game stage backgrounds (1600×900, SVG in HTML) with Yorùbá and Igbo settings.

- `stages/` — open any `.html` file in a browser. `Main.html` and `FightStage.html` are the original town and fight scenes.
- `previews/` — PNG renders of stages 01–25.
- Stage spec: fighters' ground line at y 772, top 150 px kept clear for the HUD.

See `STAGES.md` for what each stage is based on and its sources.

## Ṣàngó of Ọ̀yọ́

`sango/sango-of-oyo.html` is the photoreal Ṣàngó page: a Blender Cycles render with a 36-view turntable and close-ups. Open it in a browser; images are in `sango/img/`.

## The gods

Two pages in `gods/`, each a single self-contained HTML file. Open either in a browser.

- **`gods/orisa-and-alusi.html`** (*Òrìṣà and Alụsị*): 23 deities, 13 Yoruba òrìṣà and 10 Igbo alụsị, each modelled in 3D with three.js. Every god comes with its cloth, beads and regalia, a myth, the points where sources disagree, and citations. It needs an internet connection the first time it loads, to fetch three.js from jsDelivr and the fonts from Google Fonts.
- **`gods/african-religions-reference.html`** (*Africa's Gods and Ancestors*): a searchable field reference covering the traditional religions of 21 African peoples across 5 regions. It lists 129 deities and spirits, with 137 cited sources.

## Reference notes

Research notes and sources behind the work, in `docs/`:

- [`docs/fighting-stages.md`](docs/fighting-stages.md): the shared stage spec, what each of the 25 stages draws on, which details are design choices, and every source.
- [`docs/sango-render-notes.md`](docs/sango-render-notes.md): which parts of the realistic Ṣàngó come from sources, which are the render's own choices, and how it was made.
