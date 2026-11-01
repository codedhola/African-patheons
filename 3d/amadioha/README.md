# Amadioha: realistic render notes

A photoreal Amadioha made after the Òrìṣà and Alụsị gallery, as a companion to the Ṣàngó render. It shows him both ways the sources do: as a titled gentleman, and as the gigantic white ram beside him. The page has a hero image, a 36-view turntable, six close-ups and a sources section: https://claude.ai/artifact/3o8ZvmYhzWFRoEFJ3wmdnT (in this repo: [`amadioha/amadioha-of-ozuzu.html`](../amadioha/amadioha-of-ozuzu.html))

## What the sources support

| Element | What the source says | Source |
|---|---|---|
| Appearance | A fair-skinned, titled gentleman of cool temper; no physical form save a gigantic white ram | [Wikipedia: Amadioha](https://en.wikipedia.org/wiki/Amadioha) |
| Colours | His colour is red; white is his favourite, so a white ram is the preferred sacrifice | [Wikipedia: Amadioha](https://en.wikipedia.org/wiki/Amadioha), [Encyclopedia.com](https://www.encyclopedia.com/history/news-wires-white-papers-and-books/deities-igbo-religion) |
| Mmaagha Kamalu | His sword, believed to glow red near people with evil intentions and to cause tremors when struck on the ground | [Wikipedia: Amadioha](https://en.wikipedia.org/wiki/Amadioha) |
| Isiagụ | "Leopard head"; long or short sleeves; some with gold buttons linked by a chain; usually a breast pocket; worn with a red fez or leopard cap | [Wikipedia: Isiagu](https://en.wikipedia.org/wiki/Isiagu) |
| Isiagụ cut | Usually red, short-sleeved and knee-length, with printed heads | [UmuIgbo](https://umuigbo.com/igbo-traditional-attire/igbo-culture) |
| Okpu mme | The red cap, specific to communities with Nze na Ọzọ members; "blood-red cap" | [UmuIgbo](https://umuigbo.com/igbo-traditional-attire/igbo-culture), [Ozikoro](https://ozikoro.com/the-history-and-significance-of-the-igbo-red-cap-okpu-mme-okpu-ododo) |
| Ugo | Ọzọ titled men affix the eagle feather to their red caps | [My Igbo Name](https://blog.myigboname.com/ugo-in-names-a-feather-in-your-cap) |
| Coral beads | Listed among Igbo jewellery | [UmuIgbo](https://umuigbo.com/igbo-traditional-attire/igbo-culture) |
| Akupe | The central Igbo name for the hand fan; fans of animal skin are commonly used by chiefs | [Love Weddings NG](https://loveweddingsng.com/?p=65727) |
| Ram breed | West African Dwarf sheep: generally white or piebald; rams horned, horns curving back, out and forward again with at most about one and a half coils; a well-developed throat ruff; rams about 37 kg | [Wikipedia: West African Dwarf sheep](https://en.wikipedia.org/wiki/West_African_Dwarf_sheep) |
| Range | West African Dwarf sheep are widely distributed in southern Nigeria and may be all white | [Nigerian Finder](https://nigerianfinder.com/breeds-of-sheep-in-nigeria-their-characteristics) |

Note: the gallery cited "Wikipedia: Igbo regalia and headdresses" for the cap, feathers and fan. That page does not exist on Wikipedia, so this render uses the sources above instead.

## The render's own choices (not from sources)

- His face, age (forties), build and grey-flecked beard. The lighter skin follows "fair-skinned".
- The leopard-head print: an original motif in a half-drop repeat, heads about 6 cm wide; gold embroidery at the neck and placket.
- Three gold buttons down the placket and the chain's route from the top button to the pocket.
- Three eagle feathers, white with dark tips, at the cap's left side (no source gives the number or colour).
- The sword: leaf-shaped forged blade with incised lines, brass collar and pommel, red-and-black leather grip, and how the glow looks.
- The fan: round, tanned hide with burned rings and a zigzag, red leather binding, carved handle.
- The white wrapper, pairing his two colours, as in the gallery figure.
- The ivory bangle (left wrist) and coral bracelet (right wrist).
- The ram's size (about 95 cm at the shoulder) and pose, and the setting: a night storm over damp red laterite, lightning far off.

## How it was made

Blender Cycles (bpy 5.2.3 from pip), reusing the Ṣàngó pipeline. The body is MakeHuman's CC0 base mesh and rig from [MPFB2](https://github.com/makehumancommunity/mpfb2), with Ṣàngó's loader, skin, eye, hair and grip code. The wrapper is one cloth sheet of 3,848 vertices wrapped 1.2 turns round the waist. The isiagụ is one T-shaped pattern of 4,680 vertices, draped with the arms out and simulated into the pose over the wrapper (125 frames). Hair curves: beard 123,300 (17,476 grey), brows and lashes 3,177, scalp 35,206; 1,960 feather barbs; 250 coral beads; 66 chain links. The ram is 55 signed-distance shapes meshed with marching cubes (131,012 vertices), spiral horns with growth ridges, and 266,869 coat curves (230,214 short, 36,655 in the ruff and tail). Stills at 80 samples, turntable views at 20.
