# Characters

Game-ready fighters, each made from its portrait in [`3d/`](../3d/). A portrait is one skinned body in a pose with everything else frozen round it; a fighter is every part skinned, in the rest pose, on a game skeleton, with image textures.

| Character | Blender model | FBX | From |
|---|---|---|---|
| [Ògún](ogun/) | `ogun/SK_Ogun.blend` | `ogun/Export/` | `3d/ogun/ogun.blend` |

Ògún is the pilot: the first figure taken the whole way, to find out what the way is. His folder holds the model, the FBX files, the textures, preview renders and the script that makes them all from the portrait. Its README lists what was built, what was measured, and what is approximate.

## How a portrait becomes a fighter

[`gamekit.py`](gamekit.py) holds the steps any figure needs, and each character's build script holds what is its alone.

1. **Body.** The figure's own shape from MPFB, on MPFB's `game_engine` rig: 53 bones named as Unreal's mannequin names them, with a root on the ground. The mesh is vertex for vertex the portrait's.
2. **Back to the rest pose.** Each thing the portrait wears takes the skinning transform of the skin nearest it and has it undone. Cloth goes back point by point; a bangle or a link of chain goes back in one piece.
3. **Light versions.** Cloth is thinned, strips become ribbons, chains and rings are rebuilt from a few of their own points, hair becomes a thin layer over shaded skin.
4. **Textures.** The portrait's node materials are baked to colour, normal and a packed occlusion, roughness and metal map, or painted to match where a bake cannot follow.
5. **Skin weights.** Everything worn takes its weights from the nearest skin; rigid things take one set for the whole piece.
6. **Export and check.** FBX in centimetres, read back into an empty scene and counted.

The pilot's stances and its one clip are there to try the rig, not as the game's animation.

## Rebuilding

Install Blender 4.5 and [MPFB2](https://github.com/makehumancommunity/mpfb2) as a Blender extension, as for `3d/`. Run a character's commands from the repo root; they are in its README. Set `GAME_WORK` to a scratch folder for the stages in between. If it isn't set, each character uses a `work/` folder beside its script, which git ignores.
