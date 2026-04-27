"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import numpy as np
import time
from compox.algorithm_utils.Image2SegmentationRunner import (
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
        my_model_bytesio = self.fetch_asset("my_old_asset.pt")
        self.my_model_str = my_model_bytesio.read().decode()

    def inference(
        self, data: np.ndarray, args: dict | None = None
    ) -> np.ndarray:
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

    def train(
        self, training_data: dict, args: dict | None = None
    ) -> tuple[str, str, str]:
        """
        Trains the algorithm on the provided training data.

        Parameters
        ----------
        training_data : dict
            The training data. The dictionary contains the following keys:
            - "training_data": list of str
                The list of training data ids.
        args : dict
            The arguments for the algorithm.

        Returns
        -------
        tuple[str, str, str]
            The training status, message and the path to the trained model.
        """

        learning_rate = args.get("learning_rate", 0.001)
        batch_size = args.get("batch_size", 4)
        num_epochs = args.get("num_epochs", 10)

        self.log_message(f"Starting training with model: {self.my_model_str}")

        self.log_message(
            f"Starting training with learning rate: {learning_rate}, batch size: {batch_size}, num epochs: {num_epochs}"
        )

        # here we would train the model
        for epoch in range(num_epochs):
            self.log_message(f"Epoch {epoch+1}/{num_epochs}...")
            self.set_progress((epoch + 1) / num_epochs)
            self.set_state(
                {
                    "current_epoch": epoch + 1,
                    "total_epochs": num_epochs,
                }
            )
            checkpoint = {
                "my_old_asset.pt": b"Model bytes from epoch "
                + str(epoch + 1).encode(),
            }
            self.save_checkpoint(
                checkpoint,
                properties={
                    "stage": "intermediate",
                    "epoch": epoch + 1,
                    "loss": 0.01 * (num_epochs - epoch),
                },
            )
            time.sleep(0.1)  # simulate training time

        final_checkpoint = {"my_old_asset.pt": b"Final trained model bytes"}
        self.save_checkpoint(
            final_checkpoint,
            properties={
                "stage": "final",
                "epoch": num_epochs,
                "loss": 0.001,
            },
        )

        new_assets = {"my_old_asset.pt": b"Trained model bytes"}
        return new_assets
