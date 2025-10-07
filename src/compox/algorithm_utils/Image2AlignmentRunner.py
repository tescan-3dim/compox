
"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import numpy as np
from typing import Type

from compox.algorithm_utils.BaseRunner import BaseRunner
from compox.algorithm_utils.io_schemas import ImageSchema, AlignmentSchema, DataSchema


class Image2AlignmentRunner(BaseRunner):
    """
    A child class of BaseRunner that is used to run image to image tasks.
    """

    algorithm_type = "Image2Alignment"

    def fetch_data(self, 
                   file_ids: list[dict],  
                   *keys: str, 
                   parallel: bool = False) -> list[dict]:
        """
        Fetches the data from the database. The data is fetches as a list of dictionaries, where
        each dictionary represents a dataset. Specific keys can be provided to
        fetch from the HDF5 file, if not provided, all keys will be fetched. The
        data is validated using a specific pydantic schema for the particular
        Runner type. In this case, the schema is ImageSchema.

        Parameters
        ----------
        file_ids : list[dict]
            List of the datasets to upload. Each dataset is a defined as a dictionary.
        pydantic_data_schema : Type[DataSchema]
            The pydantic schema of the data. Must inherit from the DataSchema class.
        *keys : str
            Optional keys to fetch from the HDF5 file, if not provided, all keys
            will be fetched.
        parallel : bool, optional
            If True, the data will be fetched in parallel. Default is False.

        Returns
        -------
        list[dict]
            List of the datasets fetched from the database as dictionaries.
        """
        return self.task_handler.fetch_data(file_ids, ImageSchema, *keys, parallel=parallel)

    def post_data(self,
        data: list[dict],
        parallel: bool = False) -> list[str]:
        """
        Uploads a list of datasets to the database. The dataset is a dictionary
        where the keys are the names of the datasets and the values are the
        datasets themselves (e.g. numpy arrays). The data is uploaded as HDF5 files.
        This method is wrapper around the post_data method of the TaskHandler class.
        The data is validated using a specific pydantic schema for the particular
        Runner type. In this case, the schema is AlignmentSchema.

        Parameters
        ----------
        data : list[dict]
            List of the datasets to upload. Each dataset is a defined as a dictionary.
        pydantic_data_schema : Type[DataSchema]
            The pydantic schema of the data. Must inherit from the DataSchema class.
        parallel : bool, optional
            If True, the data will be uploaded in parallel. Default is False.

        Returns
        -------
        list[str]
            List of the identifiers of the uploaded datasets.
        """
        return self.task_handler.post_data(data, AlignmentSchema, parallel)

    def preprocess(self, input_data: dict, args: dict = {}) -> np.ndarray:
        """
        Default Image2Alignment preprocessing method. This method is used to fetch
        the data from the database, preprocess it and pass it to the inference
        method.

        Parameters
        ----------
        input_data: dict
            A dictionary containing the input data. The dictionary should contain
            the following keys:
                - input_dataset_ids: list of dataset ids to be used as input
            We assume that each dataset id corresponds to a 2D image and
            that when a series of such ids is provided, they are stacked
            along the first axis to form a 3D image.
        args : dict, optional
            Optional arguments for the preprocessing method, by default {}
        Returns
        -------
        np.ndarray
            The preprocessed data as a numpy array. The images are stacked
            along the first axis to form a 3D image if a series of dataset ids
            is provided. The images are also converted to a numpy array.
        """
        # this fetches the image data from the data storage as a list of dictionaries
        input_images = self.fetch_data(input_data["input_dataset_ids"], "image")

        # store the number of input images, so we can check if the output corresponds
        # to the input
        self._input_images_count = len(input_images)

        # this extracts the image data from the dictionaries
        for i in range(len(input_images)):
            input_images[i] = input_images[i]["image"]

        # this converts the list of images to a numpy array
        input_images = np.stack(input_images, axis=0)

        return input_images

    def postprocess(self, data: list[np.ndarray], args: dict = {}) -> list[str]:
        """
        Default Image2Alignment postprocessing method. This method expects a list of
        homography matrices as input. The matrices are used to create a list of
        dictionaries, where each dictionary represents a dataset. The dictionaries
        are then posted to the data storage. The method returns a list of the
        identifiers of the uploaded datasets.

        Parameters
        ----------
        data : list[np.ndarray]
            The input data.

        args: dict
            Additional arguments.

        Returns
        -------
        list[str]
            The ids of the output datasets.
        """

        assert isinstance(data, list), (
            "The data returned from the inference should be a list of numpy arrays, "
            f"but the data is of type {type(data)}."
        )
        for i in range(len(data)):
            assert isinstance(data[i], np.ndarray), (
                "The data returned from the inference should be a list of numpy arrays, "
                f"but the element on position {i} of the list is a {type(data[i])}."
            )

        assert len(data) == self._input_images_count - 1, (
            "The number of homography matrices returned from the inference should be "
            f"{self._input_images_count - 1}, but the number of matrices is {len(data)}. "
            "The algorithm expects to find a match between adjacent images, so the number of "
            "homography matrices should be equal to the number of images minus one."
        )

        # this will convert the list of homography matrices to a list of dictionaries
        output_dicts = []

        for i in range(len(data)):
            output_dicts.append(
                {
                    "points1": [],
                    "points2": [],
                    "confidence": [],
                    "transform_matrix": data[i],
                    "translation_matrix": data[i],
                }
            )

        # this will post the data to the data storage and return the ids
        output_dataset_ids = self.post_data(output_dicts)

        return output_dataset_ids
