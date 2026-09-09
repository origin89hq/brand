"""One height map for Buddy's skeleton, tissue guides, skin and grooming."""
import numpy as np

BODY_RATIO = .84
BODY_JOIN = 1.90
LEG_BASE = .28
LEG_JOIN = 1.18
LEG_RATIO = .60
LEG_DROP = (LEG_JOIN - LEG_BASE) * (1 - LEG_RATIO) * BODY_RATIO
HEAD_OFFSET = BODY_JOIN * (1 - BODY_RATIO) + LEG_DROP


def height(z):
    value = np.asarray(z)
    u = np.clip((value - LEG_BASE) / (LEG_JOIN - LEG_BASE), 0, 1)
    lower = LEG_DROP * u * u * (3 - 2 * u)
    return np.where(value < BODY_JOIN, value * BODY_RATIO,
                    value - BODY_JOIN * (1 - BODY_RATIO)) - lower


_design = np.linspace(-1, 6, 14001)
_compact = height(_design)


def design_height(z):
    return np.interp(z, _compact, _design)
