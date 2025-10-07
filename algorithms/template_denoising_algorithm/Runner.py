"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from image_denoising.denoising_utils import denoise_image
import numpy as np

from compox.algorithm_utils.Image2ImageRunner import Image2ImageRunner


class Runner(Image2ImageRunner):
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

    def inference(self, data: np.ndarray, args: dict = {}) -> np.ndarray:
        """
        Run the inference.

        Parameters
        ----------
        input_data : dict
            The input data.

        Returns
        -------
        np.ndarray
            The denoised images.
        """
        self.log_message("Starting inference.")
        # now we retrieve the input data
        # we will min max normalize the images
        min_val = np.min(data)
        max_val = np.max(data)
        images = (data - min_val) / (max_val - min_val)

        # here we will get the optional argument of denoising weight
        denosing_weight = args.get("denoising_weight", 0.1)

        # we can post messages to the log
        self.log_message(
            f"Starting denoising of {images.shape[0]} images with weight {denosing_weight}."
        )

        # we will denoise the images
        denoised_images = np.zeros_like(images)
        for i in range(images.shape[0]):
            denoised_images[i] = denoise_image(
                images[i], weight=denosing_weight
            )
            # this will update the progress bar
            self.set_progress(i / images.shape[0])

        # we will nromalize the output
        denoised_images = (denoised_images - denoised_images.min()) / (
            denoised_images.max() - denoised_images.min()
        )
        denoised_images = denoised_images.astype(np.float32)

        # we will pass the denoised images to the postprocess method
        return denoised_images
