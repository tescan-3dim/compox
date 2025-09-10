"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from typing import Type
import numpy as np

from t3d_server.algorithm_utils.BaseRunner import BaseRunner
from t3d_server.algorithm_utils.io_schemas import ImageSchema
from t3d_server.algorithm_utils.io_schemas import DataSchema


class Image2ImageRunner(BaseRunner):
    """
    A child class of BaseRunner that is used to run image to image tasks.
    """

    algorithm_type = "Image2Image"

    def fetch_data(
        self, file_ids: list[str], *keys: str, parallel: bool = False
    ) -> list[dict]:
        """
        Fetches the data from the database. The fetched data is a list of dictionaries, where
        each dictionary represents a dataset. Specific keys can be provided to
        fetch from the HDF5 file, if not provided, all keys will be fetched. The
        data is validated using a specific pydantic schema for the particular
        Runner type. In this case, the schema is ImageSchema.

        Parameters
        ----------
        file_ids : list[dict]
            List of the datasets to download. Each dataset is a defined as a dictionary.
        keys : str
            Optional keys to fetch from the HDF5 file, if not provided, all keys
            will be fetched.
        parallel: bool
            If True, the data will be fetched in parallel. Default is False.

        Returns
        -------
        Returns
        -------
        data : list[dict]
            List of the datasets fetched from the database as dictionaries.
        """
        return self.task_handler.fetch_data(
            file_ids, ImageSchema, *keys, parallel=parallel
        )

    def post_data(
        self,
        data: list[dict],
        pydantic_data_schema: Type[DataSchema] = ImageSchema,
        parallel: bool = False,
    ) -> list[str]:
        """
        Uploads a list of datasets to the database. The dataset is a dictionary
        where the keys are the names of the datasets and the values are the
        datasets themselves (e.g. numpy arrays). The data is uploaded as HDF5 files.
        This method is wrapper around the post_data method of the TaskHandler class.
        The data is validated using a specific pydantic schema for the particular
        Runner type. In this case, the schema is ImageSchema.

        Parameters
        ----------
        data : list[dict]
            List of the datasets to upload. Each dataset is a defined as a dictionary.
        pydantic_data_schema : Type[DataSchema], optional
            The pydantic schema to validate the data.
        parallel : bool, optional
            If True, the data will be uploaded in parallel. Default is False.

        Returns
        -------
        list[str]
            List of the identifiers of the uploaded datasets.
        """
        return self.task_handler.post_data(data, ImageSchema)

    def preprocess(self, input_data: dict, args: dict = {}) -> np.ndarray:
        """
        Default Image2Image preprocessing method. This method is used to fetch
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

    def postprocess(self, data: np.ndarray, args: dict = {}) -> list[str]:
        """
        Default Image2Image postprocessing method. This method is used to
        postprocess the data after the inference method has been called. It
        expects that the inference method outputs a numpy array. The
        postprocessing method will convert the numpy array to a list of
        dictionaries, where each dictionary represents a dataset. The
        postprocessing method will also upload the data to the database using
        the post_data method of the TaskHandler class. The data is validated
        using a specific pydantic schema for the particular Runner type. In
        this case, the schema is ImageSchema.

        Parameters
        ----------
        data : np.ndarray
            The data to be postprocessed. The data is a numpy array.
        args : dict, optional
            Optional arguments for the postprocessing method, by default {}

        Returns
        -------
        list[dict]
            The postprocessed data as a list of dictionaries. Each dictionary
            represents a dataset.
        """
        assert isinstance(
            data, np.ndarray
        ), "Data is not a numpy array, please make sure that the inference method returns a numpy array."

        # check if the first dimension of the data is equal to the number of input images
        if data.shape[0] != self._input_images_count:
            raise ValueError(
                "The first dimension of the numpy array output by the inference"
                f"method is {data.shape[0]}, but the number of input images "
                f"is {self._input_images_count}. Please make sure that the inference "
                "method returns a numpy array with the same number of images as the input."
            )
        # this converts the numpy array to a list of dictionaries
        output_dicts = [{"image": data[i]} for i in range(data.shape[0])]
        output_dataset_ids = self.post_data(output_dicts)
        return output_dataset_ids

    def inference(self, data: np.ndarray, args: dict = {}) -> np.ndarray:
        """
        Default Image2Image inference method. This method is used to run the
        inference on the data. The data is a numpy array. The inference method
        will be called by the run method of the BaseRunner class.

        Parameters
        ----------
        data : np.ndarray
            The data to be processed. The data is a numpy array.

        args : dict, optional
            Optional arguments for the inference method, by default {}

        Returns
        -------
        np.ndarray
            The processed data as a numpy array.
        """
        # this is just a placeholder method that should be implemented in the
        # child class
        raise NotImplementedError(
            "The inference method is not implemented. Please implement the "
            "inference method in the algorithm Runner class."
        )
