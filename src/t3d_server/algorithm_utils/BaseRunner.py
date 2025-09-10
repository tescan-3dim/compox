"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import time
from typing import Type
from abc import ABC, abstractmethod

from t3d_server.algorithm_utils.io_schemas import DataSchema
from t3d_server.algorithm_utils.runner_context import current_runner_context
from t3d_server.tasks.context_task_handler import current_task_handler


class BaseRunner(ABC):
    """
    Base class for all runners. Specifies the architecture of a runner and the
    required methods.

    When implementing a new runner, the following methods need to be implemented:
    - preprocess: Preprocess the input data.
    - inference: Run the inference on the output of the preprocessing.
    - postprocess: Postprocess the output of the inference.
    """

    algorithm_type = "Generic"

    def __init__(self): ...

    def initialize(self, device: str = None) -> None:
        """
        Initialize the runner with the given device. This method is called by
        the TaskHandler when the algorithm is fetched. It is used to set the
        device on which the model and inference will be run.

        Parameters
        ----------
        device : str
            The device on which the model and inference will be run. e.g. "cpu", "cuda:0"
            or "cuda:1". This is set during the initialization of the runner.

        """

        if device:
            self._device = device
        current_runner_context.set({})
        self._initializing = True
        self.__init__()
        self._initializing = False

    @property
    def task_handler(self):
        """
        Get the current task handler. This is used to access the task handler
        methods and attributes.
        """
        task_handler = current_task_handler.get(None)
        if task_handler is None:
            raise ValueError("Task handler is not set.")
        return task_handler

    @property
    def runner_context(self):
        """
        Get the current runner context. This is used to access the runner context
        methods and attributes.
        """
        runner_context = current_runner_context.get({})
        return runner_context

    @property
    def device(self):
        """
        Get the device on which the model and inference will be run.
        This is set during the initialization of the runner.
        """
        return self._device

    def __setattr__(self, name, value):
        """
        Set an attribute in the runner context.
        Parameters
        ----------
        name : str
            The name of the attribute to set.
        value : any
            The value of the attribute to set.
        Returns
        -------
        None
        """

        if name in {
            "_locked_attributes",
            "_locking_assets",
            "_device",
            "task_handler",
            "runner_context",
            "device",
            "_initializing",
        }:
            # Allow setting selected internal attributes directly
            super().__setattr__(name, value)
            return

        if getattr(self, "_locking_assets", False):
            # if the assets are being loaded, add their names to the locked attributes
            self._locked_attributes.add(name)
            super().__setattr__(name, value)
            return

        if hasattr(self, "_locked_attributes"):
            if name in self._locked_attributes and getattr(
                self, "_initializing", False
            ):
                # if the runner is being reinitialized, do not overwrite locked attributes
                # but also do not raise an error
                return
            elif name in self._locked_attributes and not getattr(
                self, "_initializing", False
            ):
                # if the attribute is locked, and the runner is not being reinitialized,
                # raise an error
                raise AttributeError(
                    f"Attribute '{name}' is locked and cannot be modified."
                )
        # set the attribute in the runner context
        self.runner_context[name] = value

    def __getattribute__(self, name):
        """
        Get an attribute from the runner context.

        Parameters
        ----------
        name : str
            The name of the attribute to get.

        Returns
        -------
        any
            The value of the attribute.
        """
        runner_context = super().__getattribute__("runner_context")

        if name in runner_context:
            return runner_context[name]
        else:
            return super().__getattribute__(name)

    def __delattr__(self, name):
        if name in self.runner_context:
            del self.runner_context[name]
        else:
            super().__delattr__(name)

    def load_assets(self):
        """
        This method should be overridden to load all necessary assets for the algorithm,
        such as trained models, precomputed data, or other resources.

        Assets must be loaded using `self.fetch_asset()` instead of accessing the file
        system directly. All assets should be stored as attributes on the runner instance.

        WARNING: The attributes set in this method will be protected against reassignment
        in other parts of the code, so they should not be modified after this method is called.
        However, this protection does not hold for mutating mutable types with in-place operations
        (e.g., appending to a list or modifying a dictionary). If you need to modify such attributes,
        consider using a different approach.
        """
        pass

    def _load_assets(self):
        """
        Internal wrapper for the load_assets method. This is supposed to be called
        from the TaskHandler class when fetching the algorithm assets. It is done
        like this because we need to store the attribute names as strings in order
        to prevent modifying the attributes which are shared between threads.

        E.g. the user loads some heave ML model as self.model and the Runner with model gets
        cached in the TaskHandler runner cache. If the developer attempts to modify
        self.model in the algorithm code, we want to raise an error, because
        the model is shared between threads and modifying it would lead to
        unpredictable behavior.
        """
        self._locked_attributes = set()
        self._locking_assets = True
        self.load_assets()
        self._locking_assets = False

    def run(self, input_data: dict, args: dict = {}) -> None:
        """
        Run the algorithm.

        Parameters
        ----------
        input_data : dict
            The input data.

        args : dict
            Additional arguments.

        Returns
        -------
        None

        Raises
        ------
        Exception
            If an error occurs during the execution.

        """
        self.task_handler.logger.info("Starting execution.")
        start = time.time()
        try:
            out = self.postprocess_base(
                self.inference_base(
                    self.preprocess_base(input_data, args), args
                ),
                args,
            )
            self.task_handler.logger.info(
                "Execution completed in {} seconds.".format(
                    round(time.time() - start, 2)
                )
            )
            self.task_handler.mark_as_completed(out)
            return None

        except Exception as e:
            self.task_handler.mark_as_failed(str(e))
            raise e

    def preprocess_base(self, input_data: dict, args: dict = {}):
        """
        Preprocess the input data.

        Parameters
        ----------
        input_data : dict
            The input data.

        Returns
        -------
        dict
            The preprocessed input data.
        """
        start = time.time()
        # update status of the execution to running
        self.task_handler.status = "RUNNING"
        out = self.preprocess(input_data, args)
        end = time.time()
        self.task_handler.logger.info(
            "Data preprocessing finished in {} seconds".format(
                round(end - start, 2)
            )
        )
        self.task_handler.update_log()
        return out

    @abstractmethod
    def preprocess(self, input_data: dict, args: dict = {}):
        """
        Preprocess the input data.

        Parameters
        ----------
        input_data : dict
            The input data.

        args : dict
            Additional arguments.
        """
        raise NotImplementedError

    def inference_base(self, data, args: dict = {}):
        """
        Run the inference.

        Parameters
        ----------
        input_data : dict
            The input data.

        Returns
        -------
        dict
            The output data.
        """
        start = time.time()
        self.task_handler.logger.info("Running inference.")
        out = self.inference(data, args)
        end = time.time()
        self.task_handler.logger.info(
            "Inference finished in {} seconds".format(round(end - start, 2))
        )
        self.task_handler.update_log()

        return out

    @abstractmethod
    def inference(self, data, args: dict = {}):
        """
        Run the inference.

        Parameters
        ----------
        input_data : dict
            The input data.

        Returns
        -------
        dict
            The output data.
        """
        raise NotImplementedError

    def postprocess_base(self, data, args: dict = {}):
        """
        Postprocess the output data.

        Parameters
        ----------
        input_data : dict
            The input data.

        Returns
        -------
        dict
            The output data.
        """
        start = time.time()
        self.task_handler.logger.info("Postprocessing output data.")
        output_dataset_ids = self.postprocess(data, args)
        end = time.time()
        self.task_handler.logger.info(
            "Postprocessing finished in {} seconds".format(
                round(end - start, 2)
            )
        )
        self.task_handler.update_log()
        return output_dataset_ids

    @abstractmethod
    def postprocess(self, data, args: dict = {}):
        """
        Postprocess the output data.

        Parameters
        ----------
        input_data : dict
            The input data.

        Returns
        -------
        dict
            The output data.
        """
        raise NotImplementedError

    def fetch_data(
        self,
        file_ids: list[str],
        pydantic_data_schema: Type[DataSchema],
        *keys: str,
    ) -> list[dict]:
        """
        Fetches the data from the database. A pydantic schema must be provided
        to validate the data. The data is fetches as a list of dictionaries, where
        each dictionary represents a dataset. Specific keys can be provided to
        fetch from the HDF5 file, if not provided, all keys will be fetched. This
        method is wrapper around the fetch_data method of the TaskHandler class.

        Parameters
        ----------
        file_ids : list[str]
            The identifiers of the data files in the database.
        pydantic_data_schema : object
            The pydantic schema of the data. Must inherit from the DataSchema class.
        keys : str
            Optional keys to fetch from the HDF5 file, if not provided, all keys
            will be fetched.

        Returns
        -------
        data : list[dict]
            List of the datasets fetched from the database as dictionaries.
        """
        return self.task_handler.fetch_data(
            file_ids, pydantic_data_schema, *keys
        )

    def save_item_to_session(self, obj: any, key: str) -> None:
        """
        Save an item to the session cache.

        Parameters
        ----------
        obj : any
            The item to save.
        key : str
            The key to save the item.

        Returns
        -------
        None
        """
        self.task_handler.save_item_to_session(obj, key)
        return None

    def load_item_from_session(self, key: str) -> any:
        """
        Fetch an item from the session cache.

        Parameters
        ----------
        key : str
            The key to fetch the item.

        Returns
        -------
        any
            The item fetched from the session cache.
        """
        return self.task_handler.load_item_from_session(key)

    def remove_item_from_session(self, key: str) -> None:
        """
        Remove an item from the session cache.

        Parameters
        ----------
        key : str
            The key to remove the item.

        Returns
        -------
        None
        """
        self.task_handler.remove_item_from_session(key)
        return None

    def post_data(
        self,
        data: list[dict],
        pydantic_data_schema: Type[DataSchema],
        parallel: bool = False,
    ) -> list[str]:
        """
        Uploads a list of datasets to the database. The dataset is a dictionary
        where the keys are the names of the datasets and the values are the
        datasets themselves (e.g. numpy arrays). A pydantic schema must be provided
        to validate the data before uploading. The data is uploaded as HDF5 files.
        This method is wrapper around the post_data method of the TaskHandler class.

        Parameters
        ----------
        data : list[dict]
            List of the datasets to upload. Each dataset is a defined as a dictionary.
        pydantic_data_schema : object
            The pydantic schema of the data. Must inherit from the DataSchema class.
        parallel : bool, optional
            If True, the data will be uploaded in parallel. Default is False.

        Returns
        -------
        list[str]
            List of the identifiers of the uploaded datasets.
        """
        return self.task_handler.post_data(data, pydantic_data_schema)

    def fetch_asset(self, asset_path: str) -> bytes:
        """
        Fetches an asset as bytes from the database by its path relative to the
        algorithm Runner class.

        Parameters
        ----------
        asset_path : str
            TThe path to the asset relative to the algorithm Runner class. e.g.
            "files/weights.pth"

        Returns
        -------
        bytes
            The asset as bytes.
        """
        return self.task_handler.fetch_asset(asset_path)

    def set_progress(self, progress: float) -> None:
        """
        Set the progress of the execution. The progress must be a float between
        0 and 1.

        Parameters
        ----------
        progress : float
            The progress of the execution.
        """
        # check if the progress is a float between 0 and 1
        if not isinstance(progress, float):
            raise ValueError("Progress must be a float.")
        if progress < 0 or progress > 1:
            raise ValueError("Progress must be between 0 and 1.")
        self.task_handler.progress = progress
        return None

    def log_message(self, message: str, logging_level: str = "INFO") -> None:
        """
        Log a message.

        Parameters
        ----------
        message : str
            The message to log.
        logging_level : str
            The logging level as defined in the logging module. Default is "INFO".

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If an invalid logging level is provided.
        """
        if logging_level == "INFO":
            self.task_handler.logger.info(message)
        elif logging_level == "WARNING":
            self.task_handler.logger.warning(message)
        elif logging_level == "ERROR":
            self.task_handler.logger.error(message)
        elif logging_level == "DEBUG":
            self.task_handler.logger.debug(message)
        else:
            raise ValueError("Invalid logging level provided.")
        return None
