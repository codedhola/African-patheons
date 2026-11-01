"""Her body: MPFB's base mesh, shaped younger and softer than Ahiajoku's.

No source says how Ọ̀ṣun looks, so her face and build are this study's. Beauty is one
of her domains, so she is drawn as a graceful woman of about thirty, with a slight smile.
"""
import numpy as np

import body
from common import edge_adjacency
from dress import smoothstep

body.MACRO = dict(gender=0.0, age=0.50, muscle=0.46, weight=0.52, proportions=0.68, height=0.47,
                  cupsize=0.42, firmness=0.66,
                  race=dict(african=1.0, asian=0.0, caucasian=0.0))

# Weights tuned by eye against test renders.
body.TARGETS = {
    'head/head-oval': 0.55,
    'head/head-scale-horiz-decr': 0.35,
    'forehead/forehead-nubian-incr': 0.20,
    'forehead/forehead-scale-vert-decr': 0.20,
    'nose/nose-width2-incr': 0.12,
    'nose/nose-point-up': 0.18,
    'nose/nose-compression-compress': 0.12,
    'nose/nose-flaring-incr': 0.15,
    'mouth/mouth-cupidsbow-incr': 0.45,
    'mouth/mouth-angles-up': 0.75,
    'mouth/mouth-scale-depth-decr': 1.0,
    'mouth/mouth-trans-backward': 0.55,
    'mouth/mouth-scale-horiz-incr': 0.40,
    'mouth/mouth-upperlip-height-decr': 0.35,
    'mouth/mouth-lowerlip-height-decr': 0.20,
    'chin/chin-prognathism-incr': 0.35,
    'chin/chin-prominent-incr': 0.10,
    'chin/chin-width-decr': 0.28,
    'neck/measure-neck-height-incr': 0.10,
    'neck/neck-double-decr': 0.6,
    'breast/breast-point-decr': 0.9,
    'cheek/l-cheek-bones-incr': 0.22,
    'cheek/r-cheek-bones-incr': 0.22,
    'eyes/l-eye-scale-incr': 0.10,
    'eyes/r-eye-scale-incr': 0.10,
    'eyes/l-eye-height2-decr': 0.25,
    'eyes/r-eye-height2-decr': 0.25,
    'eyes/l-eye-corner2-up': 0.20,
    'eyes/r-eye-corner2-up': 0.20,
}


def build():
    body.build()


def soften_chest(ob):
    """Smooth the chest under the bùbá: nothing of this shows, and cloth should not catch on it."""
    me = ob.data
    co = np.array([v.co for v in me.vertices])
    adj = edge_adjacency(me)
    w = smoothstep(co[:, 2], 1.095, 1.135) * smoothstep(co[:, 2], 1.335, 1.295) * smoothstep(co[:, 1], -0.020, -0.055) * smoothstep(np.abs(co[:, 0]), 0.185, 0.150)
    p = co.copy()
    for _ in range(70):
        nb = np.array([p[a].mean(0) if a else p[i] for i, a in enumerate(adj)])
        p += (nb - p) * (0.65 * w)[:, None]
    me.vertices.foreach_set('co', p.astype(np.float32).ravel())
    me.update()
