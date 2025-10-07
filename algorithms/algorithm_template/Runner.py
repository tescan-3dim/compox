"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import torch
from compox.algorithm_utils.BaseRunner import BaseRunner
import compox.algorithm_utils.io_schemas as schemas
from dependencies.utils import my_function


class Runner(BaseRunner):
    """
    The runner class for the foo algorithm.
    """

    def __init__(self, task_handler, device: str = "cpu"):
        """
        The foo runner.
        """
        super().__init__(task_handler, device)

    def load_assets(self):
        """
        The assets to load for the foo algorithm.
        """

        state_dict = self.fetch_asset("files/state_dict.pt")
        self.model = torch.load(state_dict)

    def preprocess(self, input_data, args: dict = {}) -> tuple:
        """Preprocess the request data before feeding into model for inference.

        Parameters
        ----------
        input_data : data
            The input data.
        args : dict, optional
            The arguments, by default None

        Returns
        -------
        tuple
            The preprocessed data.
        """
        self.log_message("Preprocessing the Foo input data.")

        input_data = self.fetch_data(
            input_data["input_dataset_ids"], schemas.DataSchema
        )
        input_data = my_function(input_data)

        return input_data, args

    def inference(self, model, preprocessed_data: tuple, args: dict = {}) -> dict:
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

        output_data = self.model(preprocessed_data)

        return output_data

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

        output_dataset_ids = self.post_data(inference_output, schemas.DataSchema)

        return output_dataset_ids
