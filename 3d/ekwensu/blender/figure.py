"""His body: MPFB's base mesh, shaped as a lean, long-limbed man of about thirty.

No source says how Ekwensu looks. He is the trickster of the market and a war god, so he is
drawn wiry rather than heavy, with high cheekbones, narrowed eyes and the corner of a smile.
The face and build are this study's own.
"""
import body

body.MACRO = dict(gender=1.0, age=0.54, muscle=0.70, weight=0.44, proportions=0.72, height=0.56,
                  cupsize=0.5, firmness=0.5,
                  race=dict(african=1.0, asian=0.0, caucasian=0.0))

# Weights tuned by eye against test renders.
body.TARGETS = {
    'head/head-oval': 0.45,
    'head/head-scale-horiz-decr': 0.15,
    'forehead/forehead-nubian-incr': 0.15,
    'eyebrows/eyebrows-angle-up': 0.30,
    'eyes/l-eye-height2-decr': 0.12,
    'eyes/r-eye-height2-decr': 0.12,
    'eyes/l-eye-corner2-up': 0.20,
    'eyes/r-eye-corner2-up': 0.20,
    'cheek/l-cheek-bones-incr': 0.50,
    'cheek/r-cheek-bones-incr': 0.50,
    'cheek/l-cheek-volume-decr': 0.30,
    'cheek/r-cheek-volume-decr': 0.30,
    'nose/nose-width2-incr': 0.25,
    'nose/nose-flaring-incr': 0.25,
    'nose/nose-scale-vert-incr': 0.15,
    'mouth/mouth-upperlip-volume-incr': 0.10,
    'mouth/mouth-lowerlip-volume-incr': 0.18,
    'mouth/mouth-angles-up': 0.32,
    'mouth/mouth-scale-horiz-incr': 0.30,
    'mouth/mouth-trans-backward': 0.25,          # set the mouth back, so the lips do not push forward into a pout
    'mouth/mouth-scale-depth-decr': 0.20,
    'chin/chin-prominent-incr': 0.18,
    'chin/chin-height-incr': 0.15,
    'neck/measure-neck-height-incr': 0.15,
    'neck/neck-double-decr': 0.6,
    'torso/torso-muscle-pectoral-incr': 0.30,
    'torso/torso-muscle-dorsi-incr': 0.35,
    'torso/torso-vshape-incr': 0.30,
    'stomach/stomach-pregnant-decr': 0.45,
    'arms/l-upperarm-muscle-incr': 0.35,
    'arms/r-upperarm-muscle-incr': 0.35,
    'arms/l-lowerarm-muscle-incr': 0.35,
    'arms/r-lowerarm-muscle-incr': 0.35,
    'legs/l-lowerleg-muscle-incr': 0.30,
    'legs/r-lowerleg-muscle-incr': 0.30,
}


def build():
    body.build()


def darken_lips(skin):
    """The toolkit's lips suit a lighter mouth than his: take them down toward the skin."""
    for node in skin.node_tree.nodes:
        if node.type == 'VALTORGB' and len(node.color_ramp.elements) == 2:
            c0 = tuple(round(c, 3) for c in node.color_ramp.elements[0].color[:3])
            if c0 == (0.08, 0.027, 0.024):
                node.color_ramp.elements[0].color = (0.046, 0.019, 0.014, 1)
                node.color_ramp.elements[1].color = (0.080, 0.032, 0.025, 1)
                return True
    return False
