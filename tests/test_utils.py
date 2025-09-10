"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from uuid import UUID
import os
import io
import h5py
import numpy as np
from PIL import Image
from natsort import natsorted
import requests
import json
import socket


def is_valid_uuid(uuid_to_test: str, version: int = 1) -> bool:
    """
    Check if uuid_to_test is a valid UUID.
    Parameters
    ----------
    uuid_to_test : str
        The uuid to test.
    version : int, optional
        The uuid version. The default is 1.
    Returns
    -------
    bool
        Whether uuid_to_test is a valid UUID.
    """

    try:
        uuid_obj = UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test


def prepare_payload(image_stack_path: str) -> io.BytesIO:
    """
    Prepare payload for post request.
    Parameters
    ----------
    image_stack_path : str
        The path to the image stack.
    Returns
    -------
    io.BytesIO
        The payload.

    """
    image_paths = [
        os.path.join(image_stack_path, file)
        for file in os.listdir(image_stack_path)
        if file.endswith(".png")
    ]
    image_paths = natsorted(image_paths)
    images = [np.array(Image.open(image_path)) for image_path in image_paths]
    images = np.array(images)
    print(images.shape)
    bio = io.BytesIO()
    with h5py.File(bio, "w") as f:
        f["image_stack"] = images
    bio.seek(0)
    return bio


def prepare_random_payload(num_of_slices: int, width: int, height: int) -> io.BytesIO:
    """
    Prepare payload for post request.
    Parameters
    ----------
    num_of_slices : int
        The number of slices.
    width : int
        The width of the image.
    height : int
        The height of the image.
    Returns
    -------
    io.BytesIO
        The payload.

    """

    images = np.random.randint(0, 255, (num_of_slices, width, height), dtype=np.uint8)
    print(images.shape)
    files = []
    for i in range(images.shape[0]):
        bio = io.BytesIO()
        with h5py.File(bio, "w") as f:
            f["image"] = images[i]
        bio.seek(0)
        files.append(bio)
    return files


# Helper function to perform API call
def get_algorithm_id(
    endpoint_url: str,
    name: str,
    version: str,
    headers=None,
    use_name: bool = True,
    use_version: bool = True,
) -> requests.Response:
    """
    Get algorithm id.
    Parameters
    ----------
    endpoint_url : str
        The endpoint url.
    name : str
        The name of the algorithm.
    version : str
        The version of the algorithm.
    headers : dict, optional
        The headers. The default is None.
    use_name : bool, optional
        Whether to use the name. The default is True.
    use_version : bool, optional
        Whether to use the version. The default is True.
    Returns
    -------
    requests.Response
        The response.
    """

    if headers is not None:
        if use_name and use_version:
            response = requests.get(f"{endpoint_url}/{name}/{version}", headers=headers)
        elif use_name:
            response = requests.get(f"{endpoint_url}/{name}", headers=headers)
        elif use_version:
            response = requests.get(f"{endpoint_url}/{version}", headers=headers)
        elif not use_name and not use_version:
            response = requests.get(f"{endpoint_url}/", headers=headers)
    else:
        if use_name and use_version:
            response = requests.get(f"{endpoint_url}/{name}/{version}")
        elif use_name:
            response = requests.get(f"{endpoint_url}/{name}")
        elif use_version:
            response = requests.get(f"{endpoint_url}/{version}")
        elif not use_name and not use_version:
            response = requests.get(f"{endpoint_url}/")
    return response


def get_all_algorithms(endpoint_url: str, headers=None) -> requests.Response:
    """
    Get all algorithms.
    Parameters
    ----------
    endpoint_url : str
        The endpoint url.
    headers : dict, optional
        The headers. The default is None.
    Returns
    -------
    requests.Response
        The response.
    """

    if headers is not None:
        response = requests.get(f"{endpoint_url}", headers=headers)
    else:
        response = requests.get(f"{endpoint_url}")
    return response


def post_files(
    endpoint_url: str, payload: list[io.BytesIO], headers=None
) -> list[requests.Response]:
    """
    Post file.
    Parameters
    ----------
    endpoint_url : str
        The endpoint url.
    payload : list[io.BytesIO]
        The payload.
    headers : dict, optional
        The headers. The default is None.
    Returns
    -------
    requests.Response
        The response.
    """
    responses = []
    for file in payload:
        if headers is not None:
            response = requests.post(endpoint_url, headers=headers, data=file)
            responses.append(response)
        else:
            response = requests.post(endpoint_url, data=file)
            responses.append(response)
    return responses


def get_file(endpoint_url: str, file_id: str, headers=None) -> requests.Response:
    """
    Get file.
    Parameters
    ----------
    endpoint_url : str
        The endpoint url.
    file_id : str
        The file id.
    headers : dict, optional
        The headers. The default is None.
    Returns
    -------
    requests.Response
        The response.
    """

    if headers is not None:
        response = requests.get(f"{endpoint_url}/{file_id}", headers=headers)
    else:
        response = requests.get(f"{endpoint_url}/{file_id}")
    return response


def delete_file(endpoint_url: str, file_id: str, headers=None) -> requests.Response:
    """
    Delete file.
    Parameters
    ----------
    endpoint_url : str
        The endpoint url.
    file_id : str
        The file id.
    headers : dict, optional
        The headers. The default is None.
    Returns
    -------
    requests.Response
        The response.
    """
    if headers is not None:
        response = requests.delete(f"{endpoint_url}/{file_id}", headers=headers)
    else:
        response = requests.delete(f"{endpoint_url}/{file_id}")
    return response


def execute_algorithm(
    endpoint_url: str,
    input_dataset_ids: list[str] = None,
    algorithm_id: str = None,
    headers=None,
) -> requests.Response:
    """
    Execute algorithm.
    Parameters
    ----------
    endpoint_url : str
        The endpoint url.
    input_dataset_ids : list[str]
        The input dataset id.
    algorithm_id : str
        The algorithm id.
    headers : dict, optional
        The headers. The default is None.
    Returns
    -------
    requests.Response
        The response.
    """
    if input_dataset_ids is None:
        payload = {
            "algorithm_id": algorithm_id,
        }
    elif algorithm_id is None:
        payload = {
            "input_dataset_ids": input_dataset_ids,
        }
    else:
        payload = {
            "input_dataset_ids": input_dataset_ids,
            "algorithm_id": algorithm_id,
        }
    payload = json.dumps(payload)
    if headers is not None:
        response = requests.post(endpoint_url, headers=headers, data=payload)
    else:
        response = requests.post(endpoint_url, data=payload)
    return response


def get_execution_record(
    endpoint_url: str, execution_id: str, headers=None
) -> requests.Response:
    """
    Get execution record.
    Parameters
    ----------
    endpoint_url : str
        The endpoint url.
    execution_id : str
        The execution id.
    headers : dict, optional
        The headers. The default is None.
    Returns
    -------
    requests.Response
        The response.
    """
    if headers is not None:
        response = requests.get(f"{endpoint_url}/{execution_id}", headers=headers)
    else:
        response = requests.get(f"{endpoint_url}/{execution_id}")
    return response


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0
