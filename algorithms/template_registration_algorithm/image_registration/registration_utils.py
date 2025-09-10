import numpy as np


def get_random_translation(image: np.ndarray, max_translation: float = 0.25):
    """
    Get a random translation matrix.

    Parameters
    ----------
    image : np.ndarray
        The image.
    max_translation : float
        The maximum translation.

    Returns
    -------
    np.ndarray
        The translation matrix.
    """

    # get the image dimensions
    height, width = image.shape[:2]
    h = np.eye(3)

    # random translation
    h[0, 2] = np.random.uniform(
        -max_translation * width, max_translation * width
    )
    h[1, 2] = np.random.uniform(
        -max_translation * height, max_translation * height
    )

    return h
