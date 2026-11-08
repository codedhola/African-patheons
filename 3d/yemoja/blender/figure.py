"""Her body: MPFB's base mesh, shaped as a full-figured woman of about fifty.

No source says how Yemọja looks. She is the mother of the òrìṣà, the patron of women and of
mothers, so she is drawn as a mature woman with a full figure and a calm, kind face. The
face and build are this study's own.
"""
import body

body.MACRO = dict(gender=0.0, age=0.66, muscle=0.42, weight=0.72, proportions=0.56, height=0.46,
                  cupsize=0.66, firmness=0.42,
                  race=dict(african=1.0, asian=0.0, caucasian=0.0))

# Weights tuned by eye against test renders.
body.TARGETS = {
    'head/head-round': 0.35,
    'head/head-fat-incr': 0.18,
    'forehead/forehead-nubian-incr': 0.15,
    'nose/nose-width2-incr': 0.28,
    'nose/nose-flaring-incr': 0.25,
    'nose/nose-volume-incr': 0.15,
    'nose/nose-point-up': 0.12,
    'mouth/mouth-upperlip-volume-incr': 0.30,
    'mouth/mouth-lowerlip-volume-incr': 0.35,
    'mouth/mouth-cupidsbow-incr': 0.35,
    'mouth/mouth-angles-up': 0.45,
    'mouth/mouth-scale-horiz-incr': 0.20,
    'cheek/l-cheek-volume-incr': 0.30,
    'cheek/r-cheek-volume-incr': 0.30,
    'cheek/l-cheek-bones-incr': 0.15,
    'cheek/r-cheek-bones-incr': 0.15,
    'chin/chin-width-incr': 0.10,
    'eyes/l-eye-height2-decr': 0.15,
    'eyes/r-eye-height2-decr': 0.15,
    'eyes/l-eye-bag-incr': 0.20,
    'eyes/r-eye-bag-incr': 0.20,
    'neck/neck-double-incr': 0.15,
    'neck/measure-neck-height-decr': 0.10,
    'arms/l-upperarm-fat-incr': 0.25,
    'arms/r-upperarm-fat-incr': 0.25,
    'stomach/stomach-pregnant-incr': 0.15,
    'hip/hip-scale-horiz-incr': 0.15,
}


def build():
    body.build()
