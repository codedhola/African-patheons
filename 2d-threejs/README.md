# 2D and three.js

Pages that run in the browser. Open any of them directly.

## `stages/`

Twenty-five 2D fighting-game backgrounds (1600 × 900, SVG in HTML) with Yorùbá and Igbo settings, and `Main.html` and `FightStage.html`, the original town and fight scenes. `stages/previews/` has a PNG of each stage.

[`stages/README.md`](stages/README.md) has the shared stage spec, what each stage draws on, which details are design choices, and every source.

## `gods/`

Two pages, each a single self-contained HTML file.

- **[`gods/orisa-and-alusi.html`](gods/orisa-and-alusi.html)** (*Òrìṣà and Alụsị*): 23 deities, 13 Yoruba òrìṣà and 10 Igbo alụsị, each modelled in 3D with three.js. Every god comes with its cloth, beads and regalia, a myth, the points where sources disagree, and citations. It needs an internet connection the first time it loads, to fetch three.js from jsDelivr and the fonts from Google Fonts.
- **[`gods/african-religions-reference.html`](gods/african-religions-reference.html)** (*Africa's Gods and Ancestors*): a searchable field reference covering the traditional religions of 21 African peoples across 5 regions. It lists 129 deities and spirits, with 137 cited sources.
