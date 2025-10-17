"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from pydantic import BaseModel, Field
from typing import List, Union, Optional

from compox.algorithm_utils.AlgorithmConfigSchema import (
    AdditionalParameterSchema,
)


class Algorithm(BaseModel):
    """
    Algorithm model.

    Attributes
    ----------
    algorithm_name : str
        The name of the algorithm.
    algorithm_major_version : str
        The major version of the algorithm.
    """

    algorithm_name: str
    algorithm_major_version: str


class FileUploadBody(BaseModel):
    """
    File upload body model.

    Attributes
    ----------
    file_body : List
        The file body.
    """

    file_body: List


class FileUploadResponse(BaseModel):
    """
    File upload response model.

    Attributes
    ----------
    file_id : str
        The id of the file.
    """

    file_id: str


class AlgorithmRegisteredResponse(BaseModel):
    """
    Algorithm registered response model.

    Attributes
    ----------
    algorithm_id : str
        The id of the algorithm.
    algorithm_name : str
        The name of the algorithm.
    algorithm_version : str
        The major version of the algorithm.
    algorithm_minor_version : str
        The minor version of the algorithm.
    algorithm_input_queue : str
        The input queue of the algorithm.
    algorithm_type : str
        The type of the algorithm.
    algorithm_tags : list[str]
        The tags of the algorithm.
    algorithm_description : str
        Description of the algorithm.
    supported_devices : list[str]
        The supported devices.
    default_device : str
        The default device.
    additional_parameters : list[AdditionalParameterSchema]
        The additional parameters.
    """

    algorithm_id: str
    algorithm_name: str
    algorithm_version: str
    algorithm_minor_version: str
    algorithm_input_queue: str
    algorithm_type: str
    algorithm_tags: list[str]
    algorithm_description: str
    supported_devices: list[str] = Field(default=[])
    default_device: str
    additional_parameters: list[AdditionalParameterSchema] = Field(default=[])


class FailedAlgorithmRegisteredResponse(BaseModel):
    """
    Failed algorithm response model.

    Attributes
    ----------
    algorithm_name : str
        The name of the algorithm.
    algorithm_version : str
        The version of the algorithm.
    message : str
        The message.
    """

    algorithm_name: str
    algorithm_version: str
    message: str


class IncomingExecutionRequest(BaseModel):
    """
    Incoming execution request model.

    Attributes
    ----------
    algorithm_id : str
        The id of the algorithm.
    input_dataset_ids : list[str]
        The id of the input dataset.
    execution_device_override : str
        The execution device override.
    additional_parameters : dict
        The additional parameters.
    session_token : Union[str, None]
        The string identifier of the session.
    """

    algorithm_id: str
    input_dataset_ids: list[str]
    execution_device_override: str = Field(default=None)
    additional_parameters: dict = Field(default={})
    session_token: Union[str, None] = Field(default=None)


class ExecutionRecord(BaseModel):
    """
    Execution record model.

    Attributes
    ----------
    execution_id : str
        The id of the execution.
    algorithm_id : str
        The id of the algorithm.
    input_dataset_ids : list[str]
        The ids of the input datasets.
    execution_device_override : Optional[str]
        The execution device override.
    additional_parameters : dict
        The additional parameters.
    session_token : Union[str, None]
        The string identifier of the session.
    output_dataset_ids : list[str]
        The ids of the output datasets.
    status : str
        The status of the execution.
    progress : float
        The progress of the execution.
    time_started : str
        The time the execution started.
    time_completed : str
        The time the execution completed.
    log : str
        The log of the execution.
    """

    execution_id: str
    algorithm_id: str
    input_dataset_ids: list[str]
    execution_device_override: Optional[str] = Field(default=None)
    additional_parameters: dict
    session_token: Union[str, None]
    output_dataset_ids: list[str]
    status: str
    progress: float
    time_started: str
    time_completed: str
    log: str


class ExecutionResponse(BaseModel):
    """
    Execution response model.

    Attributes
    ----------
    execution_id : str
        The id of the execution.
    """

    execution_id: str


class ExecutionLogRecord(BaseModel):
    """
    Execution log record model.

    Attributes
    ----------
    log : str
        The log.
    """

    log: str


class MinioServer(BaseModel):
    """
    Minio server model.

    Attributes
    ----------
    executable_path : str
        The path to the minio executable.
    storage_path : str
        The path to the minio storage.
    console_address : str
        The address of the minio console.
    address : str
        The address of the minio server.
    """

    executable_path: str
    storage_path: str
    console_address: str
    address: str


class MinioServerInfo(BaseModel):
    """
    Minio server info model.

    Attributes
    ----------
    storage_path : str
        The path to the minio storage.
    console_address : str
        The address of the minio console.
    address : str
        The address of the minio server.
    """

    storage_path: str
    console_address: str
    address: str


class S3Bucket(BaseModel):
    """
    S3 bucket model.

    Attributes
    ----------
    bucket_name : str
        The name of the bucket.
    """

    bucket_name: str


class S3ModelFile(BaseModel):
    """
    S3 model file model.

    Attributes
    ----------
    runner_path : str
        The path to the runner file.
    algorithm_path : str
        The path to the algorithm file.
    algorithm_name : str
        The name of the algorithm.
    algorithm_major_version : str
        The major version of the algorithm.
    algorithm_minor_version : str
    """

    runner_path: str
    algorithm_path: str
    algorithm_name: str
    algorithm_major_version: str
    algorithm_minor_version: str


class S3ModelFileRecord(BaseModel):
    """
    S3 model file record model.

    Attributes
    ----------
    algorithm_key : str
        The key of the algorithm.
    """

    algorithm_key: str


class ResponseMessage(BaseModel):
    """
    Response message model.

    Attributes
    ----------
    detail : str | None
        The message.
    """

    detail: str | None = None


class RootMessage(BaseModel):
    """
    Root message model.

    Attributes
    ----------
    name : str
        The name of the server.
    tags: list[str]
        The server tags.
    group : str
        The group.
    organization : str
        The organization.
    domain : str
        The domain.
    version : str
        The version.
    cuda_available : bool | None
        If cuda is available.
    cuda_capable_devices_count : int | None
        The number of cuda capable devices.
    """

    name: str
    tags: list[str]
    group: str
    organization: str
    domain: str
    version: str
    cuda_available: bool | None = None
    cuda_capable_devices_count: int | None = None


class UrlResponse(BaseModel):
    """
    Url response model.

    Attributes
    ----------
    url : str
        The url.
    """

    url: str
