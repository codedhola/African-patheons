"""Her body: MPFB's base mesh, shaped as a tall, composed woman of about thirty-five.

No source says how Idemili looks. She is both a river and a goddess, so she is drawn as a
woman of middle years, upright and still, with a long neck, a calm face and full lips. The face
and build are this study's own.
"""
import body

body.MACRO = dict(gender=0.0, age=0.58, muscle=0.46, weight=0.54, proportions=0.66, height=0.56,
                  cupsize=0.56, firmness=0.52,
                  race=dict(african=1.0, asian=0.0, caucasian=0.0))

# Weights tuned by eye against test renders.
body.TARGETS = {
    'head/head-oval': 0.30,
    'forehead/forehead-nubian-incr': 0.12,
    'eyebrows/eyebrows-angle-down': 0.10,
    'eyes/l-eye-height2-decr': 0.08,
    'eyes/r-eye-height2-decr': 0.08,
    'eyes/l-eye-corner2-up': 0.12,
    'eyes/r-eye-corner2-up': 0.12,
    'cheek/l-cheek-bones-incr': 0.30,
    'cheek/r-cheek-bones-incr': 0.30,
    'nose/nose-width2-incr': 0.25,
    'nose/nose-flaring-incr': 0.22,
    'nose/nose-point-up': 0.08,
    'mouth/mouth-upperlip-volume-incr': 0.30,
    'mouth/mouth-lowerlip-volume-incr': 0.35,
    'mouth/mouth-cupidsbow-incr': 0.30,
    'mouth/mouth-scale-horiz-incr': 0.15,
    'mouth/mouth-angles-up': 0.12,
    'chin/chin-prominent-incr': 0.10,
    'neck/measure-neck-height-incr': 0.25,
    'neck/neck-double-decr': 0.5,
    'torso/torso-vshape-decr': 0.10,
    'hip/hip-scale-horiz-incr': 0.10,
}


def build():
    body.build()
