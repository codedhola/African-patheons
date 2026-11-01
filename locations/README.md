# Locations

Game-ready Blender models of three fighting stages, built from the stage boards in [`2d-threejs/stages/`](../2d-threejs/stages/) and scaled for a 1.8 m player.

| Location | Stage | Blender model | 360° viewer |
|---|---|---|---|
| [Stormshrine](stormshrine/) | 11, Ṣàngó's storm hill | `stormshrine/Stormshrine.blend` | `stormshrine/viewer/` |
| [Ofala](ofala/) | 21, the Ofala palace arena at Onitsha | `ofala/Ofala.blend` | `ofala/viewer/` |
| [New Yam festival](newyam/) | 25, the New Yam festival | `newyam/NewYam.blend` | `newyam/viewer/` |

Each folder holds the `.blend`, the script that generates it, PNG textures and preview renders. Its README lists the assumptions and the files it was based on, and how to rebuild it.

- **Stormshrine**: look around from the hilltop or the shrine's doorway, or orbit the real-time model.
- **Ofala**: look around from the arena or from the dais in front of the empty throne, or orbit the real-time model while the cannon fires the festival's 21-gun salute.
- **New Yam festival**: the elder's thatched house with its open bay and carved posts, the heap of new yams on a raffia mat, and the elder roasting the first yam. Around them are dancers, drummers, a masquerade, villagers and a string of young palm fronds between two shade trees. Look around from the arena or from the elder's open bay, or orbit the real-time model while the masquerade and dancers move and the first yam's fire smokes.

## Opening a viewer

Each viewer loads files from its own folder, so serve the folder rather than opening the file directly:

```bash
cd locations/stormshrine/viewer && python3 -m http.server
```

## Moving things

`ofala/` and `newyam/` import `stormshrine/build_stormshrine.py` as their shared kit, so these three folders have to stay side by side. Each build script writes its `.blend`, `Textures/` and `Renders/` beside itself.
