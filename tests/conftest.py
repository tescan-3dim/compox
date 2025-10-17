"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import pytest
import os
import io
import contextlib
from functools import partial
import json
from unittest.mock import MagicMock
import zipfile
import textwrap
import h5py
import numpy as np

from compox.internal import downloader
from compox.algorithm_utils.deployment_utils import (
    deploy_algorithm_from_folder,
    remove_algorithm_from_folder,
)
from compox.config.server_settings import get_server_settings
from compox.components.api_builder import build_api
from compox.components.server_builder import build_server
from compox.tasks.TaskHandler import TaskHandler


def pytest_addoption(parser):
    parser.addoption(
        "--compox_config_path",
        action="store",
        default=None,
        help="path to server configuration yaml file",
    )
    parser.addoption(
        "--compox_url",
        action="store",
        default=None,
        help="url of the server to run tests on",
    )


@pytest.fixture(scope="session", autouse=False)
def server_url(request):
    from loguru import logger

    logger.remove()

    compox_url = request.config.getoption("--compox_url")
    compox_config = request.config.getoption("--compox_config_path")
    # check if only one of the two options is provided

    if compox_url is not None and compox_config is None:

        # normalize the url
        if not compox_url.startswith("http"):
            compox_url = "http://" + compox_url
        if not compox_url.endswith("/"):
            compox_url += "/"
        yield compox_url
    elif compox_url is None and compox_config is not None:
        settings = get_server_settings(compox_config)

        # prepare storage
        if settings.storage.backend_settings.start_instance:
            os.makedirs(
                settings.storage.backend_settings.storage_path, exist_ok=True
            )
            downloader.get_minio(settings)

        # build components
        api = build_api(settings, with_lifespan=True)
        server = build_server(api, settings, disable_logger=True)

        protocol = "https" if settings.ssl.use_ssl else "http"
        port = settings.port
        server_url = (
            f"{protocol}://0.0.0.0:{port}"
            if os.name == "posix"
            else f"{protocol}://127.0.0.1:{port}"
        )

        def stop_server():
            print("Stopping test server on port", port)

            server.should_exit = True

        def suppress_prints():
            return contextlib.redirect_stdout(io.StringIO())

        print("Test server running on port", port)
        with server.run_in_thread(disable_logger=True):

            logger.remove()

            # deploy the test algorithms
            algo_path_base = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "algorithms"
            )
            request.addfinalizer(stop_server)
            for folder_name in os.listdir(algo_path_base):
                algo_path = os.path.join(algo_path_base, folder_name)

                # this handles the OSError: [WinError 6] The handle is invalid
                # that occurs when pytest is trying to capture the print statements
                # from the deploy_algorithm_from_folder function
                with suppress_prints():
                    deploy_algorithm_from_folder(
                        algo_path, api.state.database_connection
                    )
                request.addfinalizer(
                    partial(
                        remove_algorithm_from_folder,
                        algo_path,
                        api.state.database_connection,
                    )
                )
                print(f"Deployed algorithm {folder_name}")
            yield server_url
    elif compox_url is None and compox_config is None:
        raise ValueError(
            "You must provide one of the two options: --compox_url or --compox_config_path."
            "Use --compox_url to run tests on an existing server or --compox_config_path to run tests a dynamically created server from a configuration file."
        )
    else:
        raise ValueError(
            f"Invalid configuration: --compox_url: {compox_url}, --compox_config_path: {compox_config}"
        )


@pytest.fixture
def task_handler(mock_connection):
    return TaskHandler(
        task_id="test-task-id",
        database_connection=mock_connection,
        database_update=True,
        task_session=None,
    )


@pytest.fixture
def mock_connection():
    mock = MagicMock()
    execution_record = {
        "progress": 0.0,
        "status": "STARTED",
        "output_dataset_ids": [],
        "time_completed": None,
    }

    def get_objects(bucket, keys):
        if bucket == "algorithm-store":
            return [
                json.dumps(
                    {
                        "module_id": "runner.zip",
                        "runner_file": "runner.zip",
                        "runner_class_name": "Runner",
                        "runner_module": "my_module",
                        "assets": ["asset-1"],
                        "default_device": "cpu",
                        "supported_devices": ["cpu"],
                        "algorithm_name": "test_algorithm",
                        "algorithm_major_version": "1",
                        "algorithm_minor_version": "0",
                    }
                )
            ]
        elif bucket == "module-store":
            return [create_dummy_runner_zip()]
        elif bucket == "asset-store":
            return [b"dummy binary content"]
        elif bucket == "data-store":
            return [create_hdf5_bytes()]
        elif bucket == "execution-store":
            mock.put_objects.side_effect = put_objects
            return [json.dumps(execution_record)]
        else:
            return [json.dumps({})]

    def put_objects(bucket, keys, values):
        if bucket == "execution-store":
            updated = json.loads(values[0])
            execution_record.update(updated)
        elif bucket == "data-store":
            # Simulate storing HDF5 data
            if isinstance(values[0], bytes):
                return True
            else:
                raise ValueError("Expected bytes for HDF5 data")

    mock.get_objects.side_effect = get_objects
    mock.list_objects.return_value = [
        {
            "Key": "1~name~1~0"
        }  # Simulated key in algorithm-store: <id>~<name>~<major_version>~<minor_version>
    ]
    return mock


def create_hdf5_bytes():
    buf = io.BytesIO()
    with h5py.File(buf, "w") as f:
        f.create_dataset("array1", data=np.array([1, 2]))
        f.create_dataset("array2", data=np.array([3, 4, 5]))
    buf.seek(0)
    return buf.getvalue()


def create_dummy_runner_zip():
    buffer = io.BytesIO()
    runner_code = textwrap.dedent(
        """
        class Runner:
            def __init__(self, task_handler, device):
                self.task_handler = task_handler
                self.device = device

            def register_task_handler(self, handler, algorithm_json):
                pass
        """
    )
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("Runner.py", runner_code)
    buffer.seek(0)
    return buffer.read()
