"""His body: MPFB's base mesh, shaped as a lean young hunter of about twenty-five.

No source says how Ọ̀ṣọ́ọ̀sì looks. His gallery figure is a young hunter, and the hunter of a
single arrow is quick and sure, so he is drawn light and wiry rather than heavy, with a long
neck, a narrow waist and an open, intent face. The face and build are this study's own.
"""
import body

body.MACRO = dict(gender=1.0, age=0.45, muscle=0.66, weight=0.40, proportions=0.70, height=0.42,
                  cupsize=0.5, firmness=0.5,
                  race=dict(african=1.0, asian=0.0, caucasian=0.0))

# Weights tuned by eye against test renders.
body.TARGETS = {
    'head/head-oval': 0.30,
    'forehead/forehead-nubian-incr': 0.10,
    'eyebrows/eyebrows-angle-down': 0.08,
    'eyes/l-eye-height2-decr': 0.06,
    'eyes/r-eye-height2-decr': 0.06,
    'cheek/l-cheek-bones-incr': 0.30,
    'cheek/r-cheek-bones-incr': 0.30,
    'cheek/l-cheek-volume-decr': 0.15,
    'cheek/r-cheek-volume-decr': 0.15,
    'nose/nose-width2-incr': 0.30,
    'nose/nose-flaring-incr': 0.25,
    'mouth/mouth-upperlip-volume-incr': 0.15,
    'mouth/mouth-lowerlip-volume-incr': 0.20,
    'mouth/mouth-scale-horiz-incr': 0.20,
    'mouth/mouth-trans-backward': 0.15,
    'chin/chin-prominent-incr': 0.12,
    'neck/measure-neck-height-incr': 0.20,
    'neck/neck-double-decr': 0.6,
    'torso/torso-muscle-pectoral-incr': 0.25,
    'torso/torso-muscle-dorsi-incr': 0.40,
    'torso/torso-vshape-incr': 0.40,
    'stomach/stomach-pregnant-decr': 0.50,
    'arms/l-upperarm-muscle-incr': 0.40,
    'arms/r-upperarm-muscle-incr': 0.40,
    'arms/l-lowerarm-muscle-incr': 0.35,
    'arms/r-lowerarm-muscle-incr': 0.35,
    'legs/l-lowerleg-muscle-incr': 0.35,
    'legs/r-lowerleg-muscle-incr': 0.35,
}


def build():
    body.build()


def darken_lips(skin):
    """The toolkit's lips suit a lighter mouth than his: take them down toward the skin."""
    for node in skin.node_tree.nodes:
        if node.type == 'VALTORGB' and len(node.color_ramp.elements) == 2:
            c0 = tuple(round(c, 3) for c in node.color_ramp.elements[0].color[:3])
            if c0 == (0.08, 0.027, 0.024):
                node.color_ramp.elements[0].color = (0.050, 0.020, 0.015, 1)
                node.color_ramp.elements[1].color = (0.085, 0.034, 0.027, 1)
                return True
    return False


def face_masks(body, scalp):
    """The whole scalp shaded under his close-cut hair, as Ògún's is."""
    import numpy as np
    me = body.data
    n = len(me.vertices)
    ca = me.color_attributes['mask_a']
    a = np.zeros(n * 4, np.float32)
    ca.data.foreach_get('color', a)
    a = a.reshape(-1, 4)
    a[:, 3] = scalp
    ca.data.foreach_set('color', a.ravel())
