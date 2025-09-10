from skimage.restoration import (
    denoise_tv_chambolle,
)


def denoise_image(image, weight=0.1):
    """
    Denoise the image using the total variation denoising algorithm.

    Parameters
    ----------
    image : np.ndarray
        The image to denoise.
    weight: float
        The weight parameter for the denoising algorithm.
    Returns
    -------
    np.ndarray
        The denoised image.
    """

    return denoise_tv_chambolle(image, weight=weight)
