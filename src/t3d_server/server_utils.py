"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import uuid
import hashlib
import functools
import weakref
import os
import tempfile
import zipimport
import sys
import subprocess
import importlib
import re
from collections import deque
from functools import partial


def check_system_gpu_availability():
    """
    Check if system has GPU support.

    Returns
    -------
    bool
        True if CUDA is available, False otherwise.
    int
        The number of available GPUs.
    """
    try:
        process_fn = get_subprocess_fn()
        process = process_fn(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            encoding="utf-8",
            stdout=subprocess.PIPE,
        )
        result, error = process.communicate()
        if process.returncode:
            raise RuntimeError(f'Calling nvidia-smi failed with error: {error}!')
        devices = []
        for line in result.strip().split("\n"):
            index, name, memory = re.split(r",\s*", line)
            devices.append(
                {
                    "index": int(index),
                    "name": name,
                    "memory_total": int(memory),  # Memory in MB
                }
            )

        cuda_available = True
        cuda_capable_devices_count = len(devices)
    except Exception as _:
        cuda_available = None
        cuda_capable_devices_count = None

    return cuda_available, cuda_capable_devices_count


def check_torch_with_cuda_available():
    """
    Check if PyTorch has CUDA support.

    Returns
    -------
    bool
        True if PyTorch has CUDA support, False otherwise.
    """
    if importlib.util.find_spec("torch") is None:
        return False
    else:
        import torch

        return torch.cuda.is_available() and hasattr(torch, "cuda")


def check_mps_availability():
    """
    Check if MacOS MPS (Metal Performance Shaders) is available.

    Returns
    -------
    bool
        True if MPS is available, False otherwise.
    """
    if importlib.util.find_spec("torch") is None:
        return False
    else:
        import torch

        backends = torch.backends
        mps_available = (
            hasattr(backends, "mps") and torch.backends.mps.is_available()
        )

    return mps_available


def generate_uuid(version=1) -> str:
    """
    Generate a uuid.

    Parameters
    ----------
    version : int, optional
        The version of the uuid. The default is 1.

    Returns
    -------
    str
        The uuid.

    """
    if version == 1:
        return str(uuid.uuid1())
    elif version == 4:
        return str(uuid.uuid4())
    else:
        raise ValueError("uuid version must be 1 or 4")


def calculate_s3_etag(bytes_obj):
    """
    Calculate the etag hash of a file, the etag should be the same as the etag
    calculate internally by the boto3/minio client

    Parameters
    ----------
    bytes_obj : io.BytesIO
        The file bytes to calculate the etag hash of.

    Returns
    -------
    str
        The etag hash.

    """
    md5s = hashlib.md5(bytes_obj.getvalue())
    return '"{}"'.format(md5s.hexdigest())


def find_algorithm_by_id(
    algorithm_id: str,
    bucket_contents: dict,
    separator="~",
) -> tuple:
    """
    Find an algorithm by its id.

    Parameters
    ----------
    algorithm_id : str
        The id of the algorithm.
    bucket_contents : list[str]
        The bucket contents.
    separator : str, optional
        The separator between the fields in the key. The default is "~".
    Returns
    -------
    tuple
        The algorithm key, id, name, major version, minor version.
    """
    found_model_key = None
    found_model_id = None
    found_model_name = None
    found_model_major_version = None
    found_model_minor_version = -1
    for key in bucket_contents:
        (
            bucket_model_id,
            bucket_model_name,
            bucket_model_major_version,
            bucket_model_minor_version,
        ) = key["Key"].split(separator)
        if bucket_model_id == algorithm_id:
            found_model_key = key["Key"]
            found_model_id = bucket_model_id
            found_model_name = bucket_model_name
            found_model_major_version = int(bucket_model_major_version)
            found_model_minor_version = int(bucket_model_minor_version)
            return (
                found_model_key,
                found_model_id,
                found_model_name,
                found_model_major_version,
                found_model_minor_version,
            )
    return (
        None,
        None,
        None,
        None,
        None,
    )


def weak_lru(maxsize=128, typed=False):
    'LRU Cache decorator that keeps a weak reference to "self"'

    def wrapper(func):
        @functools.lru_cache(maxsize, typed)
        def _func(_self, *args, **kwargs):
            return func(_self(), *args, **kwargs)

        @functools.wraps(func)
        def inner(self, *args, **kwargs):
            return _func(weakref.ref(self), *args, **kwargs)

        return inner

    return wrapper


def algorithm_cache(maxsize=None):
    """
        A cache decorator for algorithms. The cache is based on the algorithm_id and device.
        The cache is implemented as a dictionary with a maximum size. When the algorithm is requested
        the cache is checked and if the algorithm with the same algorithm_id and device is found
        the algorithm's Runner object is returned from the cache. If the algorithm is not found in the
        cache the algorithm is executed and the result is stored in the cache. If the cache size limit
        is reached the oldest cache entry is invalidated.

        Parameters
        ----------
        maxsize : int, optional
            The maximum size of the cache. The default is None.
    ;
    """
    cache = {}
    access_order = deque()

    def wrapper(func):
        def inner_wrapper(self, *args):
            # Generate a unique key based on the method name and arguments

            key = "".join([str(arg) for arg in args])

            if key in cache:
                # Update access order
                access_order.remove(key)
                access_order.append(key)
                return cache[key]
            else:
                result = func(self, *args)
                cache[key] = result
                access_order.append(key)

                # Check if cache size limit is reached
                if maxsize is not None and len(cache) > maxsize:
                    # Invalidate the oldest cache entry
                    oldest_key = access_order.popleft()
                    del cache[oldest_key]

                return result

        return inner_wrapper

    return wrapper


def data_cache(maxsize=None):
    """
        A cache decorator for data. The cache is based on the unique file key.
        The cache is implemented as a dictionary with a maximum size. When the file is requested
        the cache is checked and if the file with the same key is found
        the file is returned from the cache. If the file is not found in the
        cache the file is read and the result is stored in the cache. If the cache size limit
        is reached the oldest cache entry is invalidated.

        Parameters
        ----------
        maxsize : int, optional
            The maximum size of the cache. The default is None.
    ;
    """
    cache = {}
    access_order = deque()

    def wrapper(func):
        def inner_wrapper(self, *args):
            # Generate a unique key based on the method name and arguments

            key = "".join([str(arg) for arg in args])

            if key in cache:
                # Update access order
                access_order.remove(key)
                access_order.append(key)
                return cache[key]
            else:
                result = func(self, *args)
                cache[key] = result
                access_order.append(key)

                # Check if cache size limit is reached
                if maxsize is not None and len(cache) > maxsize:
                    # Invalidate the oldest cache entry
                    oldest_key = access_order.popleft()
                    del cache[oldest_key]

                return result

        return inner_wrapper

    return wrapper


class ZipImporter:
    def __init__(self, zip_bytes: bytes, module_name: str):
        self.temp_dir = tempfile.gettempdir()
        self.temp_file = os.path.join(self.temp_dir, str(uuid.uuid4()))
        sys.path.insert(0, self.temp_file)
        with open(self.temp_file, "wb") as f:
            f.write(zip_bytes)
        importer = zipimport.zipimporter(self.temp_file)
        spec = importlib.util.spec_from_loader(f"{module_name}", importer)
        module = importlib.util.module_from_spec(spec)
        importer.exec_module(module)
        self.module = module

    def __enter__(self):
        return self.module

    def __exit__(self, exc_type, exc_value, exc_traceback):
        # BUG: for some reason, the tempfile sometimes cannot be removed on windows
        # due to [PermissionError: [WinError 32] The process cannot access the file because it is being used by another process]
        try:
            os.remove(self.temp_file)
        except PermissionError as _:
            pass
        sys.path.remove(self.temp_file)


def check_and_create_database_collections(
    collection_names: list[str],
    database_connection: object,
) -> list[str]:
    """
    Checks if the collections exist in the database and creates them if they do not exist.

    Parameters
    ----------
    collection_names : list[str]
        The collection names.

    database_connection : object
        The database connection object.

    Returns
    -------
    list[str]
        The list of newly created collections.
    """
    collections_exist = database_connection.check_collections_exists(
        collection_names
    )
    not_existing_collections = [
        collection_names[i]
        for i in range(len(collection_names))
        if not collections_exist[i]
    ]
    if len(not_existing_collections) > 0:
        database_connection.create_collections(not_existing_collections)

    return not_existing_collections


def get_subprocess_fn():
    if os.name == "posix":
        subprocess_fn = subprocess.Popen
    elif os.name == "nt":
        from t3d_server.internal import JobPOpen

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess_fn = partial(JobPOpen.JobPOpen, startupinfo=startupinfo)
    else:
        raise ValueError(f"Unsupported OS: {os.name}")

    return subprocess_fn
