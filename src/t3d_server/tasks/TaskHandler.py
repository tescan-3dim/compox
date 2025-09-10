"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import io
import h5py
import json
import traceback
from typing import Type, Union
import time
from datetime import datetime
from loguru import logger
from concurrent.futures import ThreadPoolExecutor
from t3d_server.server_utils import (
    find_algorithm_by_id,
    generate_uuid,
    ZipImporter,
    algorithm_cache,
    check_system_gpu_availability,
    check_mps_availability,
)
from t3d_server.algorithm_utils.io_schemas import DataSchema
from t3d_server.session.TaskSession import TaskSession
from t3d_server.database_connection.S3Connection import S3Connection


class TaskHandler:
    """
    Task handler class for the execution task. This class is used to update
    the progress, status and log of the execution task. Also contains methods
    to fetch the algorithm, assets and data from the database server of choice.

    Parameters
    ----------
    task_id : str
        The identifier of the task. Typically a UUID.
    database_connection : object
        The database connection object instance. Must inherit from the
        BaseConnection class and implement the required methods.
    database_update : bool, optional
        Whether to the execution record in the database, by default True.
        Can be set to False for example when debugging locally.
    task_session : TaskSession, optional
        The task session object instance. Must inherit from the TaskSession
        class, by default None.
    """

    def __init__(
        self,
        task_id: str,
        database_connection: S3Connection,
        database_update: bool = True,
        task_session: Type[Union[TaskSession, None]] = None,
    ):
        """
        Parameters
        ----------
        task_id : str
            The identifier of the task. Typically a UUID.
        database_connection : object
            The database connection object instance. Must inherit from the
            BaseConnection class and implement the required methods.
        database_update : bool, optional
            Whether to the execution record in the database, by default True.
            Can be set to False for example when debugging locally.
        task_session : TaskSession, optional
            The task session object instance. Must inherit from the TaskSession
            class, by default None.
        """
        self._task_id = task_id
        self._progress = 0.0
        self.database_update = database_update
        self.database_connection = database_connection
        self.algorithm_assets = None
        self.stream = io.StringIO()
        self.logger = logger.bind(log_type="TASK", task_id=task_id)
        self.logger_sink_id = self.logger.add(
            self.stream,
            format="{time:YYYY-MM-DD HH:mm:ss} {level} {message}",
            level="INFO",
            filter=lambda record: record["extra"].get("task_id")
            == self.task_id,
        )

        self.file_fetching_stats = {
            "count": 0,
            "time": 0,
        }
        self.file_posting_stats = {
            "count": 0,
            "time": 0,
        }

        self.status = "STARTED"

        self.task_session = task_session
        if task_session is not None:
            self.session_token = task_session.session_token

    @property
    def task_id(self):
        """
        The identifier of the task. Typically a UUID.

        :getter: Returns the task id.
        :setter: Sets the task id.
        :type: str
        """
        return self._task_id

    @property
    def progress(self):
        """
        The progress of the task in the range [0., 1.].

        :getter: Returns the progress of the task.
        :setter: Sets the progress of the task.
        :type: float
        """
        return self._progress

    @progress.setter
    def progress(self, progress: float):
        """
        Update the progress of the task.

        Parameters
        ----------
        progress : float
            The progress of the task in the range [0., 1.].
        """
        if not (0.0 <= progress <= 1.0):
            raise ValueError(
                f"Progress must be between 0 and 1. Got: {progress}"
            )

        self._progress = progress
        if self.database_update:
            try:
                execution_record = json.loads(
                    self.database_connection.get_objects(
                        "execution-store",
                        [self._task_id],
                    )[0]
                )
                execution_record["progress"] = progress

                self.database_connection.put_objects(
                    "execution-store",
                    [self._task_id],
                    [json.dumps(execution_record)],
                )
            except Exception as e:
                self.mark_as_failed(e)
                raise e

    @property
    def status(self):
        """
        The status of the task. e.g. "RUNNING", "COMPLETED", "FAILED"

        :getter: Returns the status of the task.
        :setter: Sets the status of the task.
        :type: str
        """

        return self._status

    @status.setter
    def status(self, status: str):
        """
        Update the status of the task.

        Parameters
        ----------
        status : str
            The status of the task. e.g. "RUNNING", "COMPLETED", "FAILED"
        """
        if status not in [
            "RUNNING",
            "COMPLETED",
            "FAILED",
            "PENDING",
            "STARTED",
        ]:
            raise ValueError(f"Invalid status. Got: {status}")

        self._status = status
        if self.database_update:
            try:
                execution_record = json.loads(
                    self.database_connection.get_objects(
                        "execution-store",
                        [self._task_id],
                    )[0]
                )
                execution_record["status"] = status

                self.database_connection.put_objects(
                    "execution-store",
                    [self._task_id],
                    [json.dumps(execution_record)],
                )
            except Exception as e:
                self.mark_as_failed(e)
                raise e

    @property
    def output_dataset_ids(self):
        """
        The output dataset identifiers of the task.

        :getter: Returns the output dataset identifiers of the task.
        :setter: Sets the output dataset identifiers of the task.
        :type: list[str]
        """
        return self._output_dataset_ids

    @output_dataset_ids.setter
    def output_dataset_ids(self, output_dataset_ids: list[str]):
        """
        Update the output dataset identifiers of the task.

        Parameters
        ----------
        output_dataset_ids : list[str]
            The output dataset identifiers of the task.
        """
        self._output_dataset_ids = output_dataset_ids
        if self.database_update:
            try:
                execution_record = json.loads(
                    self.database_connection.get_objects(
                        "execution-store",
                        [self._task_id],
                    )[0]
                )
                execution_record["output_dataset_ids"] = output_dataset_ids

                self.database_connection.put_objects(
                    "execution-store",
                    [self._task_id],
                    [json.dumps(execution_record)],
                )
            except Exception as e:
                self.mark_as_failed(e)
                raise e

    @property
    def time_completed(self):
        """
        The time the task was completed.

        :getter: Returns the time the task was completed.
        :setter: Sets the time the task was completed.
        :type: str
        """
        return self._time_completed

    @time_completed.setter
    def time_completed(self, time_completed: str):
        """
        Update the time the task was completed.

        Parameters
        ----------
        time_completed : str
            The time the task was completed.
        """
        self._time_completed = time_completed
        if self.database_update:
            try:
                execution_record = json.loads(
                    self.database_connection.get_objects(
                        "execution-store",
                        [self._task_id],
                    )[0]
                )
                execution_record["time_completed"] = time_completed

                self.database_connection.put_objects(
                    "execution-store",
                    [self._task_id],
                    [json.dumps(execution_record)],
                )
            except Exception as e:
                self.mark_as_failed(e)
                raise e

    @property
    def session_token(self):
        """
        The identifier of the session. Typically a UUID.

        :getter: Returns the session id.
        :setter: Sets the session id.
        :type: str
        """
        return self._session_token

    @session_token.setter
    def session_token(self, session_token: str):
        """
        Update the session token of the task.

        Parameters
        ----------
        session_token : str
            The session token of the task.
        """
        self._session_token = session_token
        if self.database_update:
            try:
                execution_record = json.loads(
                    self.database_connection.get_objects(
                        "execution-store",
                        [self._task_id],
                    )[0]
                )
                execution_record["session_token"] = session_token

                self.database_connection.put_objects(
                    "execution-store",
                    [self._task_id],
                    [json.dumps(execution_record)],
                )
            except Exception as e:
                self.mark_as_failed(e)
                raise e

    def set_as_current_task_handler(self) -> None:
        """
        Set this task handler as the current task handler in the
        current_task_handler context variable. This is used to access the
        current task handler from anywhere in the code.

        Returns
        -------
        None
        """
        from t3d_server.tasks.context_task_handler import current_task_handler

        current_task_handler.set(self)

    def mark_as_completed(self, output_dataset_ids: list[str]) -> None:
        """
        Mark the task as completed and update its record in the database. This
        will set the progress to 1.0, the status to "COMPLETED" and the time
        completed to the current time.

        Parameters
        ----------
        output_dataset_ids : list[str]
            The output dataset identifiers of the task.

        Returns
        ------
        None
        """
        self.progress = 1.0
        self.output_dataset_ids = output_dataset_ids
        self.time_completed = str(datetime.now())

        # log the posting and fetching stats
        self._log_file_stats()
        self.update_log()
        self.status = "COMPLETED"

        logger.remove(self.logger_sink_id)

    def _log_file_stats(self) -> None:
        """
        Log the file fetching and posting stats.
        """
        self.logger.info(
            f"File fetching stats: {self.file_fetching_stats['count']} files "
            f"fetched in {self.file_fetching_stats['time']:.4f} seconds."
        )
        self.logger.info(
            f"File posting stats: {self.file_posting_stats['count']} files "
            f"posted in {self.file_posting_stats['time']:.4f} seconds."
        )

    def mark_as_failed(self, e: Exception = None) -> None:
        """
        Mark the task as failed and update its record in the database. This
        will set the progress to 1.0, the status to "FAILED" and the time
        completed to the current time. The exception that caused the task to
        fail will be logged in the task log.

        Parameters
        ----------
        e : Exception, optional
            The exception that caused the task to fail, by default None. It will
            be logged in the task log.
        Returns
        ------
        None
        """
        if e is not None:
            self.logger.error(e)
            self.logger.error(traceback.format_exc())
        self.progress = 1.0
        self.time_completed = str(datetime.now())
        self.output_dataset_ids = []
        self._log_file_stats()
        self.update_log()
        self.status = "FAILED"
        logger.remove(self.logger_sink_id)

    def update_log(self):
        """
        Update the log of the task in the database. This method is called
        automatically when the task is completed or failed. It can also be
        called manually to update the log during the execution of the task.

        Parameters
        ----------
        log : str
            The log of the task.
        """
        self.log = str(self.stream.getvalue())
        if self.database_update:
            try:
                execution_record = json.loads(
                    self.database_connection.get_objects(
                        "execution-store",
                        [self._task_id],
                    )[0]
                )
                execution_record["log"] = self.log

                self.database_connection.put_objects(
                    "execution-store",
                    [self._task_id],
                    [json.dumps(execution_record)],
                )
            except Exception as e:
                self.mark_as_failed(e)
                raise e

    def fetch_algorithm(
        self, algorithm_id: str, execution_device_override=None
    ) -> list:
        """
        Fetches the algorithm from the database and imports its corresponding
        Python module and runner class.

        Parameters
        ----------

        algorithm_id : str
            The id of the algorithm.

        execution_device_override : str, optional
            The computing device override, by default None. If provided, the
            device will be set to the computing device override (if the device
            is supported and available).

        Returns
        ----------

        algorithm : object
            The algorithm Runner object.

        """

        # get the algorithm json file from algorithm-store bucket

        try:
            self.logger.info(
                f"Fetching algorithm {algorithm_id} from the database."
            )
            self.logger.info("Loading the algorithm.")
            start = time.time()
            runner, algorithm_assets, algorithm_json = (
                self.__cached_fetch_algorithm(
                    algorithm_id, execution_device_override
                )
            )
            # call the runners initialize method to reset the state of the runner
            runner.initialize()
            self.algorithm_assets = algorithm_assets

            self.logger.info(
                "Algorithm runner successfully loaded in {} seconds.".format(
                    round(time.time() - start, 8)
                )
            )
            self.logger = logger.bind(
                algorithm=f"{algorithm_json['algorithm_name']} {algorithm_json['algorithm_major_version']}.{algorithm_json['algorithm_minor_version']}",
                log_type="TASK",
                task_id=self.task_id,
            )
            return runner
        except Exception as e:
            self.mark_as_failed(e)
            raise ValueError(f"Failed to fetch algorithm: {e}")

    @algorithm_cache(maxsize=1)
    def __cached_fetch_algorithm(
        self, algorithm_id: str, execution_device_override: str = None
    ) -> object:
        """
        Fetches the algorithm from the database and imports its corresponding
        Python module and runner class. This method is cached to avoid
        unnecessary fetches from the database when repeated calls are made
        to the same algorithm.

        Parameters
        ----------

        algorithm_id : str
            The id of the algorithm.

        execution_device_override : str, optional
            The computing device override, by default None. If provided, the
            device will be set to the computing device override (if the device
            is supported and available).

        Returns
        ----------

        algorithm : object
            The algorithm Runner object.
        algorithm_assets : dict
            The assets of the algorithm, such as model weights, configuration files, etc.
        algorithm_json : dict
            The algorithm json file as a dictionary. The algorithm json file
            contains the metadata of the algorithm (e.g. algorithm type, tags).

        """

        # get the algorithm json file from algorithm-store bucket

        try:
            found_algorithm_key, _, _, _, _ = find_algorithm_by_id(
                algorithm_id,
                self.database_connection.list_objects("algorithm-store"),
            )
            if found_algorithm_key is None:
                raise ValueError(f"Algorithm with id {algorithm_id} not found.")

            # get algorithm object
            algorithm_json = json.loads(
                self.database_connection.get_objects(
                    "algorithm-store",
                    [found_algorithm_key],
                )[0]
            )

        except Exception as e:
            self.mark_as_failed(e)
            raise ValueError(f"Failed to fetch algorithm: {e}")

        # get the algorithm module from the module-store bucket

        module_id = algorithm_json["module_id"]
        algorithm_assets = algorithm_json["assets"]
        self.algorithm_assets = algorithm_assets
        device = self.__get_device(algorithm_json, execution_device_override)

        try:
            module_archive_bytes = io.BytesIO(
                self.database_connection.get_objects(
                    "module-store",
                    [module_id],
                )[0]
            )
            with ZipImporter(module_archive_bytes.getvalue(), "Runner") as m:
                runner = m.Runner.__new__(m.Runner)
                runner.initialize(device=device)
                runner._load_assets()
        except Exception as e:
            self.mark_as_failed(e)
            raise ValueError(f"Failed to fetch algorithm: {e}")
        return runner, algorithm_assets, algorithm_json

    def __get_device(self, algorithm_json, execution_device_override=None):
        """
        Get the device to run the model and inference on. The device is set based
        on the default device specified in the algorithms pyproject.toml file
        and the availability of CUDA.

        Parameters
        ----------
        algorithm_json : dict
            The algorithm json file as a dictionary. The algorithm json file
            contains the metadata of the algorithm (e.g. algorithm type, tags).

        execution_device_override : str, optional
            The computing device override, by default None. If provided, the
            device will be set to the computing device override (if the device
            is supported and available).

        Returns
        -------
        device : str
            The device to run the model and inference on.
        """
        assert algorithm_json["default_device"].lower() in [
            d.lower() for d in algorithm_json["supported_devices"]
        ], (
            f"Default device {algorithm_json['default_device']} is not supported. "
            f"Supported devices are {algorithm_json['supported_devices']}. Check the "
            "algorithm pyproject.toml file."
        )

        # set the device to run the model and inference on
        gpu_available, _ = check_system_gpu_availability()
        if not execution_device_override:
            if algorithm_json["default_device"].lower() == "cpu":
                self.logger.info(
                    "Algorithm is set to run on CPU. Running on CPU."
                )
                device = "cpu"
            elif (
                algorithm_json["default_device"].lower() == "gpu"
                and gpu_available
            ):
                self.logger.info(
                    "Algorithm is set to run on GPU. Running on GPU."
                )
                device = "cuda"
            elif (
                algorithm_json["default_device"].lower() == "gpu"
                and not gpu_available
            ):
                self.logger.warning(
                    "Algorithm is set to run on GPU but CUDA is not available. Running on CPU."
                )
                device = "cpu"
            elif (
                (algorithm_json["default_device"].lower() == "")
                and ("gpu" in algorithm_json["supported_devices"])
                and (gpu_available)
            ):
                self.logger.info(
                    "No default device specified. CUDA is available and GPU is supported. Running on GPU."
                )
                device = "cuda"
            elif (
                (algorithm_json["default_device"].lower() == "")
                and ("gpu" in algorithm_json["supported_devices"])
                and (not gpu_available)
            ):
                self.logger.warning(
                    "No default device specified. GPU is supported but CUDA is not available. Running on CPU."
                )
                device = "cpu"
            elif algorithm_json["default_device"].lower() == "mps":
                mps_available = check_mps_availability()
                if not mps_available:
                    self.logger.warning(
                        "Algorithm is set to run on MPS, but MPS is not available. Running on CPU."
                    )
                    device = "cpu"
                else:
                    self.logger.info(
                        "Algorithm is set to run on MPS. Running on MPS."
                    )
                    device = "mps"
            else:
                raise ValueError(
                    f"Default device {algorithm_json['default_device']} is not supported."
                )
        else:
            if (
                execution_device_override.lower()
                in algorithm_json["supported_devices"]
                and execution_device_override.lower() == "cpu"
            ):
                self.logger.info(
                    f"Computing device override set to {execution_device_override}. Running on CPU."
                )
                device = "cpu"
            elif (
                execution_device_override.lower()
                in algorithm_json["supported_devices"]
                and execution_device_override.lower() == "gpu"
                and gpu_available
            ):
                self.logger.info(
                    f"Computing device override set to {execution_device_override}. Running on GPU."
                )
                device = "cuda"
            elif (
                execution_device_override.lower()
                in algorithm_json["supported_devices"]
                and execution_device_override.lower() == "gpu"
                and not gpu_available
            ):
                self.logger.warning(
                    f"Computing device override set to {execution_device_override}, however CUDA is not available. Running on CPU."
                )
                device = "cpu"
            else:
                self.logger.warning(
                    f"Computing device override {execution_device_override} is not supported, falling back to the default device: {algorithm_json['default_device']}."
                )
                device = self.__get_device(algorithm_json)

        return device

    def fetch_asset(self, asset_path: str) -> io.BytesIO:
        """
        Fetches an asset as bytes from the database by its path relative to the
        algorithm Runner class.

        Parameters
        ----------

        asset_path : str
            The path to the asset relative to the algorithm Runner class. e.g.
            "files/weights.pth"

        Returns
        ----------

        asset : io.BytesIO
            The asset as bytes.
        """

        asset_id = self.algorithm_assets[asset_path]
        self.logger.info(f"Fetching asset {asset_id} from the database.")
        try:
            start = time.time()
            asset = io.BytesIO(
                self.database_connection.get_objects(
                    "asset-store",
                    [asset_id],
                )[0]
            )
            end = time.time()
            # log the fetching time with 4 decimal places
            self.logger.info(
                f"Asset {asset_id} fetched in {round(end - start, 4)} seconds."
            )
            return asset
        except Exception as e:
            self.mark_as_failed(e)
            raise ValueError(f"Failed to fetch asset: {e}")

    def fetch_data(
        self,
        file_ids: list[str],
        pydantic_data_schema,
        *keys: str,
        parallel: bool = False,
    ) -> list[dict]:
        """
        Fetches the data from the database. A pydantic schema must be provided
        to validate the data. The data is fetches as a list of dictionaries, where
        each dictionary represents a dataset. Specific keys can be provided to
        fetch from the HDF5 file, if not provided, all keys will be fetched.

        Parameters
        ----------
        file_ids : list[str]
            The identifiers of the data files in the database.
        pydantic_data_schema : object
            The pydantic schema of the data. Must inherit from the DataSchema class.
        keys : str
            Optional keys to fetch from the HDF5 file, if not provided, all keys
            will be fetched.
        parallel : bool, optional
            If True, the data will be fetched in parallel. Default is False.
        Returns
        -------
        data : list[dict]
            List of the datasets fetched from the database as dictionaries.
        """

        # self.logger.info("Fetching data from the database.")
        # get data object
        datasets = []

        def fetch_file(file_id):
            # convert to file-like object
            file_like_obj = io.BytesIO(
                self.database_connection.get_objects(
                    "data-store",
                    [file_id],
                )[0]
            )
            # read from file-like object
            data_dict = {}
            if len(keys) == 0:
                with h5py.File(file_like_obj, "r") as f:
                    for key in f.keys():
                        data_dict[key] = f[key][()]
            else:
                with h5py.File(file_like_obj, "r") as f:
                    for key in keys:
                        try:
                            data_dict[key] = f[key][()]
                        except KeyError:
                            data_dict[key] = None
            # validate and dump
            data_dict = pydantic_data_schema.model_validate(data_dict)
            data_dict = data_dict.model_dump()
            return data_dict

        try:
            start = time.time()

            if parallel:
                with ThreadPoolExecutor() as executor:
                    datasets = list(executor.map(fetch_file, file_ids))
            else:
                datasets = [fetch_file(file_id) for file_id in file_ids]
            end = time.time()
            self.file_fetching_stats["count"] += len(file_ids)
            self.file_fetching_stats["time"] += end - start
            return datasets

        except Exception as e:
            self.mark_as_failed(e)
            raise e

    def post_data(
        self,
        result: list[dict],
        pydantic_data_schema: Type[DataSchema],
        parallel: bool = False,
    ) -> list[str]:
        """
        Uploads a list of datasets to the database. The dataset is a dictionary
        where the keys are the names of the datasets and the values are the
        datasets themselves (e.g. numpy arrays). A pydantic schema must be provided
        to validate the data before uploading. The data is uploaded as HDF5 files.

        Parameters
        ----------
        result : dict
            The result to upload to the database.
        pydantic_data_schema : object
            The pydantic schema of the data. Must inherit from the DataSchema class.
        parallel : bool, optional
            If True, the data will be uploaded in parallel. Default is False.

        Returns
        -------
        output_dataset_ids : list[str]
            The dataset identifiers of the uploaded datasets.
        """
        # TODO: this is not working for all algorithms currently, must be fixed
        self.logger.info(
            f"Uploading {str(len(result))} results to the database."
        )

        def post_file(r):
            r = pydantic_data_schema.model_validate(r)
            r = r.model_dump()
            bio = io.BytesIO()
            with h5py.File(bio, "w") as f:
                for key in r.keys():
                    if r[key] is not None:
                        f.create_dataset(
                            key,
                            data=r[key],
                        )
            # upload response to minio
            output_dataset_id = generate_uuid()
            self.database_connection.put_objects(
                "data-store",
                [output_dataset_id],
                [bio.getvalue()],
            )
            return output_dataset_id

        try:
            start = time.time()
            if parallel:
                with ThreadPoolExecutor() as executor:
                    output_dataset_ids = list(executor.map(post_file, result))
            else:
                output_dataset_ids = [post_file(file_id) for file_id in result]
            end = time.time()
            self.file_posting_stats["count"] += len(result)
            self.file_posting_stats["time"] += end - start

        except Exception as e:
            self.mark_as_failed(e)
            raise e
        return output_dataset_ids

    def save_item_to_session(self, obj: any, key: str):
        """
        Save an object to the task session.

        Parameters
        ----------
        obj : any
            The object to save.
        key : str
            The key to save the object under.
        """

        try:
            self.task_session.add_item(obj, key)
            self.logger.info(
                f"Saved object with key {key} to the task session."
            )
        except Exception as e:
            self.mark_as_failed(e)
            raise e

    def load_item_from_session(self, key: str):
        """
        Load an object from the task session.

        Parameters
        ----------
        key : str
            The key of the object to load.

        Returns
        -------
        any
            The object loaded from the task session.
        """

        try:
            obj = self.task_session[key]
            self.logger.info(
                f"Loaded object with key {key} from the task session."
            )
            return obj
        except Exception as e:
            if self.task_session is None:
                self.logger.error(
                    "The algorithm is attempting to load an object from the task",
                    "session, but the task session is not initialized.",
                    "Please make sure you are providing the session token in the",
                    "execution request.",
                )
            self.mark_as_failed(e)
            raise e

    def remove_item_from_session(self, key: str):
        """
        Remove an object from the task session.

        Parameters
        ----------
        key : str
            The key of the object to remove.
        """

        try:
            self.task_session.remove_item(key)
            self.logger.info(
                f"Removed object with key {key} from the task session."
            )
        except Exception as e:
            self.mark_as_failed(e)
            raise e
