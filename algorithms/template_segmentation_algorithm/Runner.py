"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import numpy as np
from t3d_server.algorithm_utils.Image2SegmentationRunner import (
    Image2SegmentationRunner,
)
from image_segmentation.segmentation_utils import threshold_image


class Runner(Image2SegmentationRunner):
    """
    The runner class for the segmentation algorithm.
    """

    def load_assets(self):
        """
        Here you can load the assets needed for the algorithm. This can be
        the model, the weights, etc. The assets are loaded upon the first
        call of the algorithm and are cached with the algorithm instance.
        """
        pass

    def inference(self, data: np.ndarray, args: dict = {}) -> np.ndarray:
        """
        Run the inference.

        Parameters
        ----------
        data : np.ndarray
            The images to be segmented.
        args : dict
            The arguments for the algorithm.

        Returns
        -------
        np.ndarray
            The segmented images.
        """

        # now we retrieve the input data
        thresholding_algorithm = args.get("thresholding_algorithm", "otsu")
        # we can post messages to the log
        self.log_message(
            f"Starting inference with thresholding algorithm: {thresholding_algorithm}"
        )

        # here we will threshold the images
        mask = threshold_image(data, thresholding_algorithm)

        # we can also log progress
        self.set_progress(0.5)

        # pass the mask to the postprocess
        return mask
