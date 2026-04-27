"""
Copyright 2026 TESCAN GROUP, a.s.
All rights reserved
"""

from __future__ import annotations

import io
import time
import uuid
from pathlib import Path

import h5py
import numpy as np
import pytest
import requests
import toml

from tests.test_utils import get_execution_record


def _create_algorithm_dir(
    tmp_path: Path, name: str, version: str, inference_offset: int
) -> Path:
    """
    Create a minimal Image2Image algorithm directory.
    """
    alg_dir = tmp_path / name
    alg_dir.mkdir(exist_ok=True)

    pyproject = {
        "project": {"name": name, "version": version},
        "tool": {
            "compox": {
                "algorithm_type": "Image2Image",
                "tags": ["integration-test"],
                "description": "Redeploy runner update integration test.",
                "supported_devices": ["cpu"],
                "default_device": "cpu",
                "additional_parameters": [],
                "check_importable": False,
                "obfuscate": False,
                "removable": True,
            }
        },
    }
    (alg_dir / "pyproject.toml").write_text(toml.dumps(pyproject))

    runner_code = f"""
import numpy as np
from compox.algorithm_utils.Image2ImageRunner import Image2ImageRunner


class Runner(Image2ImageRunner):
    def load_assets(self):
        pass

    def inference(self, data: np.ndarray, args: dict = {{}}):
        return data + {inference_offset}
"""
    (alg_dir / "Runner.py").write_text(runner_code.strip() + "\n")
    return alg_dir


def _post_single_image(file_url: str, image: np.ndarray) -> str:
    """
    Upload one image as HDF5 to /files and return file_id.
    """
    bio = io.BytesIO()
    with h5py.File(bio, "w") as f:
        f["image"] = image
    bio.seek(0)
    response = requests.post(file_url, data=bio.getvalue())
    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code} with body {response.text!r}"
    return response.json()["file_id"]


def _deploy_local(server_url: str, path: Path) -> dict:
    """
    Deploy algorithm from local folder and return response json.
    """
    response = requests.post(
        f"{server_url}/api/v0/deploy/local",
        params={"path": str(path)},
    )
    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code} with body {response.text!r}"
    return response.json()


def _get_latest_minor_version(
    server_url: str, algorithm_name: str, algorithm_major_version: str
) -> str:
    """
    Read the currently latest minor version from algorithm metadata endpoint.
    """
    response = requests.get(
        f"{server_url}/api/v0/algorithm/{algorithm_name}/{algorithm_major_version}"
    )
    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code} with body {response.text!r}"
    payload = response.json()
    return str(payload["latest_algorithm_minor_version"])


def _wait_for_execution_completed(
    executions_url: str, execution_id: str, timeout_s: int = 20
) -> dict:
    """
    Poll execution record until COMPLETED or FAILED.
    """
    deadline = time.time() + timeout_s
    last_payload: dict | None = None
    while time.time() < deadline:
        response = get_execution_record(executions_url, execution_id)
        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code} with body {response.text!r}"
        payload = response.json()
        last_payload = payload
        if payload["status"] == "COMPLETED":
            return payload
        if payload["status"] == "FAILED":
            raise AssertionError(f"Execution failed: {payload!r}")
        time.sleep(0.5)
    raise AssertionError(f"Execution did not complete in time: {last_payload!r}")


def _execute_algorithm(
    execute_url: str,
    input_dataset_ids: list[str],
    algorithm_id: str,
    algorithm_minor_version: str | None,
) -> requests.Response:
    """
    Execute algorithm with an explicit optional minor version.
    """
    payload = {
        "input_dataset_ids": input_dataset_ids,
        "algorithm_id": algorithm_id,
        "algorithm_minor_version": algorithm_minor_version,
    }
    return requests.post(execute_url, json=payload)


def _load_image_from_file_response(response: requests.Response) -> np.ndarray:
    """
    Parse HDF5 bytes from /files/{id} and return the first dataset as ndarray.
    """
    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code} with body {response.text!r}"
    with h5py.File(io.BytesIO(response.content), "r") as f:
        first_key = next(iter(f.keys()))
        return np.array(f[first_key][()])


@pytest.mark.algorithms
def test_redeploy_runner_change_is_reflected_in_execution(server_url, tmp_path):
    """
    Deploy algorithm, execute, mutate Runner, redeploy, execute again,
    and verify output changed according to new Runner logic.
    """
    name = f"redeploy_update_{uuid.uuid4().hex[:8]}"
    alg_dir = _create_algorithm_dir(tmp_path, name, "1.0.0", inference_offset=1)

    file_url = f"{server_url}/api/v0/files"
    execute_url = f"{server_url}/api/v0/execute-algorithm"
    executions_url = f"{server_url}/api/v0/executions"

    input_image = np.array([[1, 2], [3, 4]], dtype=np.uint8)
    input_file_id = _post_single_image(file_url, input_image)

    algorithm_id = None
    output_file_ids: list[str] = []
    try:
        deploy_payload_v1 = _deploy_local(server_url, alg_dir)
        algorithm_id = deploy_payload_v1["algorithm_id"]
        latest_minor_v1 = _get_latest_minor_version(
            server_url,
            deploy_payload_v1["algorithm_name"],
            deploy_payload_v1["algorithm_major_version"],
        )

        execute_response_v1 = _execute_algorithm(
            execute_url,
            [input_file_id],
            algorithm_id,
            latest_minor_v1,
        )
        assert (
            execute_response_v1.status_code == 200
        ), f"Expected 200, got {execute_response_v1.status_code} with body {execute_response_v1.text!r}"
        execution_id_v1 = execute_response_v1.json()["execution_id"]
        execution_record_v1 = _wait_for_execution_completed(
            executions_url, execution_id_v1
        )
        output_file_id_v1 = execution_record_v1["output_dataset_ids"][0]
        output_file_ids.append(output_file_id_v1)

        output_response_v1 = requests.get(f"{file_url}/{output_file_id_v1}")
        output_image_v1 = _load_image_from_file_response(output_response_v1)
        np.testing.assert_array_equal(output_image_v1, input_image + 1)

        # Mutate Runner logic and redeploy same algorithm name/major version.
        _create_algorithm_dir(
            tmp_path, name, "1.1.0", inference_offset=2
        )  # overwrite files in place
        deploy_payload_v2 = _deploy_local(server_url, alg_dir)
        assert (
            deploy_payload_v2["algorithm_id"] == algorithm_id
        ), "Expected redeploy to preserve algorithm_id for same name/major."
        latest_minor_v2 = _get_latest_minor_version(
            server_url,
            deploy_payload_v2["algorithm_name"],
            deploy_payload_v2["algorithm_major_version"],
        )

        execute_response_v2 = _execute_algorithm(
            execute_url,
            [input_file_id],
            algorithm_id,
            latest_minor_v2,
        )
        assert (
            execute_response_v2.status_code == 200
        ), f"Expected 200, got {execute_response_v2.status_code} with body {execute_response_v2.text!r}"
        execution_id_v2 = execute_response_v2.json()["execution_id"]
        execution_record_v2 = _wait_for_execution_completed(
            executions_url, execution_id_v2
        )
        output_file_id_v2 = execution_record_v2["output_dataset_ids"][0]
        output_file_ids.append(output_file_id_v2)

        output_response_v2 = requests.get(f"{file_url}/{output_file_id_v2}")
        output_image_v2 = _load_image_from_file_response(output_response_v2)
        np.testing.assert_array_equal(output_image_v2, input_image + 2)
        assert not np.array_equal(
            output_image_v1, output_image_v2
        ), "Expected output to change after runner update and redeploy."
    finally:
        for output_file_id in output_file_ids:
            requests.delete(f"{file_url}/{output_file_id}")
        requests.delete(f"{file_url}/{input_file_id}")
        if algorithm_id is not None:
            requests.delete(f"{server_url}/api/v0/deploy/algorithm/{algorithm_id}")
