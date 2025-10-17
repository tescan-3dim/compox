"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from t3d_server.algorithm_utils.BaseRunner import BaseRunner
from t3d_server.algorithm_utils.io_schemas import ImageSchema
from dependencies.utils import my_function


class Runner(BaseRunner):
    """
    The runner class for the foo algorithm.
    """

    def load_assets(self):
        """
        The assets to load for the foo algorithm.
        """

        self.dummy_large_object = "a" * 1024 * 1024 * 1024

    def preprocess(self, input_data: ImageSchema, args: dict = {}) -> tuple:
        """Preprocess the request data before feeding into model for inference.

        Parameters
        ----------
        input_data : ImageSchema
            The input data.
        args : dict, optional
            The arguments, by default None

        Returns
        -------
        tuple
            The preprocessed data.
        """
        self.log_message("Preprocessing the Foo input data.")
        return input_data, args

    def inference(
        self, model, preprocessed_data: tuple, args: dict = {}
    ) -> dict:
        """Run the inference on the preprocessed data.

        Parameters
        ----------
        model : object
            The model.
        preprocessed_data : tuple
            The preprocessed data.
        args : dict, optional
            The arguments, by default None

        Returns
        -------
        dict
            The inference result.
        """

        self.log_message("Running the Foo inference.")
        return my_function()

    def postprocess(self, inference_output: str, args: dict = {}) -> dict:
        """Postprocess the inference output.

        Parameters
        ----------
        inference_output : dict
            The inference output.
        args : dict, optional
            The arguments, by default None

        Returns
        -------
        dict
            The postprocessed output.
        """

        self.log_message("Postprocessing the Foo inference output.")
        return [inference_output]
