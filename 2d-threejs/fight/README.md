# Ògún and Ekwensu at the Ofala

A short 2D fight for the browser: Ògún against Ekwensu, machete against machete, in the arena before the Obi's palace. You play Ògún and the page plays Ekwensu. The first to win two rounds wins.

Open [`index.html`](index.html) in a browser. It needs no server and no internet connection. To play on a phone, open **https://codedhola.github.io/African-patheons/**; [Online](#online) says how that copy is kept.

| Key | Does |
|---|---|
| `A` / `D`, or `←` / `→` | Step back and forward |
| `W` or `↑` | Jump. With `A` or `D` held, back or forward |
| `S` or `↓` | Bend down, held |
| `J` or `Z` | Slash: slower, reaches furthest of the blows, takes 14 of 100 |
| `K` or `X` | Kick: quicker, shorter, takes 8 and pushes further |
| `S` + `K` | Sweep: a low kick from the crouch, takes 7 |
| `K` in the air | Flying kick, takes 10 |
| `S`, then `A`, then `J` | Breathe fire: reaches furthest of all, takes 16, then needs 3.5 seconds before the next |
| `L` or `C` | Block, held: a blocked blow takes 15% of what it would, and fire 25% |
| `Enter` or `Space` | Start, and fight again |
| `M` | Sound on and off |

With the arrow keys, fire is `↓`, then `←`, then `Z`. Each key must follow the one before within 0.45 seconds. The mark beside each name fills as that fighter's fire comes back.

On a phone or tablet the keys give way to a stick and four buttons, pressed on the screen:

- **The stick**, bottom left: slide the thumb to step, up to jump, down to bend down. Between two ways it holds both, so up and forward is a jump forward. Down, then round to back, then Slash breathes fire, as on the keys.
- **Slash, Kick, Block and Fire**, bottom right. Each answers its own finger, so Block can be held while the stick moves. Down on the stick with Kick is the sweep. The Fire button fills as the fire comes back.
- **Sound and full screen**, beside the round clock. The full-screen button shows only where the browser offers full screen, as Chrome on Android does.

Held sideways the picture fills the screen and the controls sit over its lower corners. Held upright the controls sit below it, with a short list of the moves. A tap on the picture starts a fight. To see the controls on a computer, add `#touch` to the end of the address.

## Sound

The page makes every sound as it plays, from noise and plain waves. There are no sound files, so the game still needs no internet connection.

- **The fight**: the swish of a blade or a leg, steel ringing on steel when a slash is blocked, the thud of a blow that lands, the roar and crackle of the fire, feet on the dust, and a body falling.
- **The voices**: each fighter shouts as he strikes and cries out when struck ("hah", "hup", "hi-yah", "ugh"), gives a long cry when knocked out, and laughs when he wins a round. Ògún's voice is the deeper; Ekwensu's is higher and rougher, and he sometimes chuckles when he slips a blow. They are cries, not words: a buzz like the voice box's, shaped into vowels the way a mouth shapes them.
- **The Ofala**: a crowd that murmurs, cheers a knockout and claps the winner, and a band of iron bells, a slit drum, a skin drum and a rattle that plays through each round, with more drum when the clock or a fighter's health runs low.

`M`, or the speaker button beside the round clock, turns all of it off. On an iPhone the sound plays even with the phone on silent, as a video's does.

What gets past what:

- **Bending down** lets a slash and the fire pass overhead. A kick, a sweep and a flying kick still land.
- **Jumping** lets a sweep pass underneath. Everything else still lands.
- **Blocking** stops most of every blow, standing only.

A round lasts 60 seconds; when the time runs out the fighter with more health takes it, and a level round is fought again. Ekwensu has every move the player has. He blocks, ducks or jumps about half the blows he sees coming and sometimes answers a miss, so blocking pays and striking without a pause mostly loses.

## What it is made of

- **The fighters** are pictures of the 3D figures, seventeen poses each, in [`img/ogun.webp`](img/ogun.webp) and [`img/ekwensu.webp`](img/ekwensu.webp). Ògún is his game model from [`characters/ogun/`](../../characters/ogun/). Ekwensu has no game model yet, so [`make_sprites.py`](make_sprites.py) puts one together for these pictures alone: the parts of his portrait in [`3d/ekwensu/`](../../3d/ekwensu/), carried back to the rest pose and hung on the skeleton all fighters share. It renders well and is far too heavy for a game engine.
- **The poses** are written once, in `make_sprites.py`, and given to both fighters. That is the shared skeleton of [`characters/`](../../characters/README.md#sharing-movement) at work: the places are measured on Ògún and brought to Ekwensu's size.
- **The arena** is [`locations/ofala/Renders/Ofala_Front.png`](../../locations/ofala/Renders/Ofala_Front.png), the front view of the Ofala model, as [`img/ofala.webp`](img/ofala.webp).
- **The game** is one page, [`index.html`](index.html), drawing on a 1600 × 900 canvas with no library. The feet stand on the ground line at y 772, as the [stage spec](../stages/README.md#shared-stage-spec) has it.
- **The sound** is made by the same page with the browser's Web Audio. The drums, the bells and the steel are worked out once, while the title shows; the voices, the fire and the crowd are shaped afresh each time, so no two blows sound quite alike.

## Designed, not from sources

- **The meeting itself.** Ògún is a Yorùbá òrìṣà and Ekwensu an Igbo alusi. No source has them meet, and none sets a fight at the Ofala, which is the Obi of Onitsha's festival. The pairing is the game's.
- **Every move.** The guard, the slash, the kicks and the rest are plain fighting-game poses. They are not drawn from any account of either god, or from a martial tradition.
- **The fire.** Nothing in this repo's sources has either god breathe fire. It is a fighting-game special move, the same for both, drawn by the page as a stream of light from the mouth.
- **The numbers.** Health, reach, timing and how Ekwensu chooses what to do were set by trying the game.
- **The voices.** No source gives either god a voice. The cries, the laughs and Ekwensu's chuckle are the game's.
- **The band.** It is made up for the game, loosely after the iron bell (ogene) and slit drum (ekwe) of Igbo music, with the bell playing the twelve-pulse figure heard across West Africa. It is not a rhythm of the Ofala, and none of it is a recording.

## Online

GitHub Pages serves the game at https://codedhola.github.io/African-patheons/ from the `gh-pages` branch. That branch holds only `index.html`, the three pictures and an empty `.nojekyll`, at its root, so a change made here reaches the phone only when the branch is updated. From the repo root:

```bash
git worktree add ../fight-pages gh-pages
cp 2d-threejs/fight/index.html ../fight-pages/ && cp 2d-threejs/fight/img/*.webp ../fight-pages/img/
git -C ../fight-pages commit -am "Update the fight" && git -C ../fight-pages push origin gh-pages
git worktree remove ../fight-pages
```

Pages takes a minute or so to publish each push. On an iPhone, Safari's Share menu, then Add to Home Screen, opens the game without the browser's bars.

## Making the pictures again

Install Blender 4.5 and [MPFB2](https://github.com/makehumancommunity/mpfb2) as for `3d/`, set `GAME_WORK` to a scratch folder, and run this from the repo root. It takes several minutes on an 8 GB Apple M1:

```bash
blender -b --factory-startup --python 2d-threejs/fight/make_sprites.py -- ekwensu frames sheets backdrop
```

Each sheet is six cells across and three down, seventeen of them filled. A cell is 616 × 539 pixels at 220 pixels to the metre, the fighter facing right, with the feet at (264, 528) in the cell. `index.html` holds the same numbers, and where each fighter's mouth is in the fire pose, which the `frames` stage prints.

## What it does not do

- One player against the page. There is no second player.
- Each move is one or two pictures, so the movement is stepped, not smooth.
- The mouths do not open: the figures have no face bones, so the fire comes from closed lips.
- Ekwensu is drawn by turning his pictures to face left, so his machete changes hands with them.
- The raffia and the palm fronds follow the hips and have no swing of their own.
- No one speaks: the fighters only cry out, and there is no announcer calling the rounds.
