"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import numpy as np


def scale_and_shift(data: np.ndarray, scale: float, bias: float) -> np.ndarray:
    """
    Apply a simple affine transform used by the generic template.
    """
    return data.astype(np.float32) * scale + bias
