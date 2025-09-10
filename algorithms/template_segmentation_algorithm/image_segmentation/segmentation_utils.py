import skimage.filters as skif


def threshold_image(image, thresholding_algorithm):
    """
    Threshold the image using the specified thresholding algorithm.

    Parameters
    ----------
    image : np.ndarray
        The image to threshold.
    thresholding_algorithm : str
        The thresholding algorithm to use.

    Returns
    -------
    np.ndarray
        The thresholded image.
    """
    if thresholding_algorithm == "otsu":
        threshold = skif.threshold_otsu(image)
    elif thresholding_algorithm == "yen":
        threshold = skif.threshold_yen(image)
    elif thresholding_algorithm == "li":
        threshold = skif.threshold_li(image)
    elif thresholding_algorithm == "minimum":
        threshold = skif.threshold_minimum(image)
    elif thresholding_algorithm == "mean":
        threshold = skif.threshold_mean(image)
    elif thresholding_algorithm == "triangle":
        threshold = skif.threshold_triangle(image)
    elif thresholding_algorithm == "isodata":
        threshold = skif.threshold_isodata(image)
    elif thresholding_algorithm == "local":
        threshold = skif.threshold_local(image)
    else:
        raise ValueError(
            f"Invalid thresholding algorithm: {thresholding_algorithm}"
        )

    return image > threshold
