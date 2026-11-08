"""His body: MPFB's base mesh, shaped as a heavy-shouldered man of about thirty-five.

No source says how Ògún looks. He is the smith, the hunter and the warrior, so he is drawn
with a smith's arms and shoulders and a settled weight, not a bodybuilder's. His face is
this study's own.
"""
import body

body.MACRO = dict(gender=1.0, age=0.58, muscle=0.80, weight=0.60, proportions=0.66, height=0.50,
                  cupsize=0.5, firmness=0.5,
                  race=dict(african=1.0, asian=0.0, caucasian=0.0))

# Weights tuned by eye against test renders.
body.TARGETS = {
    'head/head-square': 0.30,
    'head/head-oval': 0.20,
    'head/head-fat-incr': 0.08,
    'forehead/forehead-nubian-incr': 0.20,
    'forehead/forehead-scale-vert-decr': 0.25,
    'eyebrows/eyebrows-trans-down': 0.25,
    'eyebrows/eyebrows-angle-down': 0.15,
    'nose/nose-width2-incr': 0.35,
    'nose/nose-width3-incr': 0.15,
    'nose/nose-flaring-incr': 0.35,
    'nose/nose-nostrils-width-incr': 0.30,
    'nose/nose-volume-incr': 0.20,
    'nose/nose-point-up': 0.10,
    'nose/nose-compression-compress': 0.10,
    'mouth/mouth-upperlip-volume-incr': 0.35,
    'mouth/mouth-lowerlip-volume-incr': 0.40,
    'mouth/mouth-scale-horiz-incr': 0.25,
    'mouth/mouth-cupidsbow-incr': 0.25,
    'mouth/mouth-angles-down': 0.10,
    'chin/chin-bones-incr': 0.35,
    'chin/chin-width-incr': 0.25,
    'chin/chin-prominent-incr': 0.15,
    'cheek/l-cheek-bones-incr': 0.30,
    'cheek/r-cheek-bones-incr': 0.30,
    'eyes/l-eye-height2-decr': 0.20,
    'eyes/r-eye-height2-decr': 0.20,
    'eyes/l-eye-eyefold-down': 0.20,
    'eyes/r-eye-eyefold-down': 0.20,
    'neck/measure-neck-circ-incr': 0.55,
    'neck/neck-double-decr': 0.6,
    'torso/torso-muscle-pectoral-incr': 0.45,
    'torso/torso-muscle-dorsi-incr': 0.50,
    'torso/torso-vshape-incr': 0.35,
    'torso/measure-shoulder-dist-incr': 0.25,
    'stomach/stomach-pregnant-decr': 0.30,
    'arms/l-upperarm-muscle-incr': 0.45,
    'arms/r-upperarm-muscle-incr': 0.45,
    'arms/l-lowerarm-muscle-incr': 0.45,
    'arms/r-lowerarm-muscle-incr': 0.45,
    'arms/l-upperarm-shoulder-muscle-incr': 0.40,
    'arms/r-upperarm-shoulder-muscle-incr': 0.40,
    'legs/l-upperleg-muscle-incr': 0.30,
    'legs/r-upperleg-muscle-incr': 0.30,
    'legs/l-lowerleg-muscle-incr': 0.35,
    'legs/r-lowerleg-muscle-incr': 0.35,
}


def build():
    body.build()


def face_masks(body, scalp):
    """Rework two of the toolkit's skin regions for him: a faint flush on the cheekbones only, and the whole scalp shaded under the hair."""
    import numpy as np
    me = body.data
    co = np.array([v.co for v in me.vertices])
    info = eval(body['eyes'])
    n = len(co)
    flush = np.zeros(n)
    for side in 'LR':
        e = np.array(info[side]['centre'])
        cheek = e + np.array([0.012 * np.sign(e[0]), 0.010, -0.034])
        flush = np.maximum(flush, np.exp(-(np.linalg.norm(co - cheek, axis=1) / 0.024) ** 2) * 0.16)
    for name, channel, data in (('mask_b', 2, flush), ('mask_a', 3, scalp)):
        ca = me.color_attributes[name]
        a = np.zeros(n * 4, np.float32)
        ca.data.foreach_get('color', a)
        a = a.reshape(-1, 4)
        a[:, channel] = data
        ca.data.foreach_set('color', a.ravel())


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
