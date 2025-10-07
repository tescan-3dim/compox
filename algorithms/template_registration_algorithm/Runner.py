"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import numpy as np

from compox.algorithm_utils.Image2AlignmentRunner import (
    Image2AlignmentRunner,
)
from image_registration.registration_utils import get_random_translation


class Runner(Image2AlignmentRunner):
    """
    The runner class for the denoiser algorithm.
    """

    def load_assets(self):
        """
        Here you can load the assets needed for the algorithm. This can be
        the model, the weights, etc. The assets are loaded upon the first
        call of the algorithm and are cached with the algorithm instance.
        """
        pass

    def inference(self, data: np.ndarray, args: dict = {}) -> list[np.ndarray]:
        """
        Run the inference.

        Parameters
        ----------
        data : np.ndarray
            The input images

        Returns
        -------
        list[np.ndarray]
            The output homography matrices.
        """
        self.log_message("Starting inference.")
        # now we retrieve the input data
        max_translation = args.get("max_translation", 0.25)
        # we can post messages to the log
        self.log_message(f"Registering {data.shape[0]} images.")

        # we will denoise the images
        matrices = []
        for i in range(data.shape[0] - 1):
            matrix = get_random_translation(
                data[i], max_translation=max_translation
            )
            matrices.append(matrix)
            self.set_progress(i / data.shape[0])
        # we will pass the homography matrices to the output
        return matrices
