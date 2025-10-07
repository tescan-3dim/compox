"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import numpy as np
from compox.algorithm_utils.Image2ImageRunner import Image2ImageRunner


class Runner(Image2ImageRunner):
    """
    The runner class for the dummy algorithm.
    """

    def load_assets(self):
        """
        Here you can load the assets needed for the algorithm. This can be
        the model, the weights, etc. The assets are loaded upon the first
        call of the algorithm and are cached with the algorithm instance.
        """
        pass

    def preprocess(self, input_data: dict, args: dict = {}) -> tuple:
        """Preprocess the request data before feeding into model for inference.

        Parameters
        ----------
        input_data : dict
            The input data.
        args : dict, optional
            The arguments, by default None

        Returns
        -------
        tuple
            The preprocessed data.
        """

        # this fetches the image data from the data storage as a list of dictionaries
        input_images = self.fetch_data(input_data["input_dataset_ids"], "image")

        # now we will pass the images and the denoising weight to the inference method
        return input_images

    def inference(self, data, args: dict = {}) -> dict:
        """
        Run the inference.

        Parameters
        ----------
        input_data : dict
            The input data.

        Returns
        -------
        torch.Tensor
            The output data.
        """
        return data

    def postprocess(self, data: np.array, args: dict = {}) -> list[str]:
        """
        Postprocess the output data.

        Parameters
        ----------
        data : np.array
            The input data.

        Returns
        -------
        list[str]
            The ids of the output datasets.

        """

        # this will post the data to the data storage and return the ids
        output_dataset_ids = self.post_data(data)
        return output_dataset_ids
