"""
Copyright 2026 TESCAN GROUP, a.s.
All rights reserved
"""

from __future__ import annotations

import time
import uuid
import shutil
from pathlib import Path

import requests
import toml


def _create_algorithm_dir(
    tmp_path: Path,
    name: str,
    version: str,
    runner_body: str | None = None,
) -> Path:
    """
    Create a minimal algorithm directory with a valid pyproject.toml and Runner.py.
    """
    alg_dir = tmp_path / name
    alg_dir.mkdir(exist_ok=True)
    pyproject = {
        "project": {"name": name, "version": version},
        "tool": {
            "compox": {
                "check_importable": False,
                "obfuscate": False,
                "algorithm_type": "Generic",
                "tags": ["test"],
                "description": "test algorithm",
                "supported_devices": ["cpu"],
                "default_device": "cpu",
                "additional_parameters": [],
                "training_parameters": [],
                "removable": True,
            }
        },
    }
    (alg_dir / "pyproject.toml").write_text(toml.dumps(pyproject))
    runner_code = runner_body or "class Runner: pass"
    (alg_dir / "Runner.py").write_text(runner_code)
    return alg_dir


def _zip_algorithm_dir(tmp_path: Path, alg_dir: Path) -> Path:
    """
    Zip a single algorithm directory and return the created zip path.
    """
    archive_base = tmp_path / f"{alg_dir.name}_pkg"
    zip_path = shutil.make_archive(
        str(archive_base),
        "zip",
        root_dir=str(alg_dir.parent),
        base_dir=alg_dir.name,
    )
    return Path(zip_path)


def _poll_deploy_status(server_url: str, deploy_id: str, timeout_s: int = 10):
    """
    Poll deploy status until completion or timeout.
    """
    deadline = time.time() + timeout_s
    last_payload = None
    while time.time() < deadline:
        response = requests.get(f"{server_url}/api/v0/deploy/{deploy_id}")
        if response.status_code == 200:
            payload = response.json()
            last_payload = payload
            if payload.get("status") in {"COMPLETED", "FAILED"}:
                return response, payload
        time.sleep(0.5)
    return response, last_payload


def _cleanup_algorithm(server_url: str, algorithm_id: str | None) -> None:
    """
    Cleanup deployed algorithm via delete endpoint.
    """
    if not algorithm_id:
        return
    try:
        requests.delete(f"{server_url}/api/v0/deploy/algorithm/{algorithm_id}")
    except Exception:
        pass


def test_deploy_local_folder_success(server_url, tmp_path):
    """
    Deploy from a folder should return algorithm metadata.
    """
    name = f"deploy_folder_{uuid.uuid4().hex[:8]}"
    version = "1.0"
    alg_dir = _create_algorithm_dir(tmp_path, name, version)

    algorithm_id = None
    try:
        response = requests.post(
            f"{server_url}/api/v0/deploy/local",
            params={"path": str(alg_dir)},
        )
        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code} with body {response.text!r}"
        payload = response.json()
        algorithm_id = payload.get("algorithm_id")
        assert payload["algorithm_name"] == name
        assert payload["algorithm_major_version"] == "1"
        assert algorithm_id
    finally:
        _cleanup_algorithm(server_url, algorithm_id)


def test_deploy_local_zip_success(server_url, tmp_path):
    """
    Deploy from a zip should return algorithm metadata.
    """
    name = f"deploy_zip_{uuid.uuid4().hex[:8]}"
    version = "2.0"
    alg_dir = _create_algorithm_dir(tmp_path, name, version)
    zip_path = _zip_algorithm_dir(tmp_path, alg_dir)

    algorithm_id = None
    try:
        response = requests.post(
            f"{server_url}/api/v0/deploy/local",
            params={"path": str(zip_path)},
        )
        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code} with body {response.text!r}"
        payload = response.json()
        algorithm_id = payload.get("algorithm_id")
        assert payload["algorithm_name"] == name
        assert payload["algorithm_major_version"] == "2"
        assert algorithm_id
    finally:
        _cleanup_algorithm(server_url, algorithm_id)


def test_deploy_local_invalid_path(server_url):
    """
    Deploy should fail for a non-existent path.
    """
    response = requests.post(
        f"{server_url}/api/v0/deploy/local",
        params={"path": "C:/this/path/does/not/exist"},
    )
    assert (
        response.status_code == 400
    ), f"Expected 400, got {response.status_code} with body {response.text!r}"


def test_deploy_local_async_and_status(server_url, tmp_path):
    """
    Async deploy should complete and be observable via status polling.
    """
    name = f"deploy_async_{uuid.uuid4().hex[:8]}"
    version = "3.0"
    alg_dir = _create_algorithm_dir(tmp_path, name, version)
    zip_path = _zip_algorithm_dir(tmp_path, alg_dir)

    algorithm_id = None
    try:
        response = requests.post(
            f"{server_url}/api/v0/deploy/local-async",
            params={"path": str(zip_path)},
        )
        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code} with body {response.text!r}"
        deploy_id = response.json()["deploy_id"]

        status_response, payload = _poll_deploy_status(
            server_url, deploy_id, timeout_s=15
        )
        assert (
            status_response.status_code == 200
        ), f"Expected 200 from deploy status, got {status_response.status_code} with body {status_response.text!r}"
        assert payload is not None, "Expected deploy status payload."
        assert (
            payload.get("status") == "COMPLETED"
        ), f"Expected COMPLETED, got {payload!r}"
        algorithm_id = payload.get("algorithm_id")
        assert algorithm_id, "Expected algorithm_id in deploy record."
    finally:
        _cleanup_algorithm(server_url, algorithm_id)


def test_delete_removable_algorithm(server_url, tmp_path):
    """
    Removable algorithms should be deletable via the deploy delete endpoint.
    """
    name = f"deploy_remove_{uuid.uuid4().hex[:8]}"
    version = "4.0"
    alg_dir = _create_algorithm_dir(tmp_path, name, version)

    deploy_response = requests.post(
        f"{server_url}/api/v0/deploy/local",
        params={"path": str(alg_dir)},
    )
    assert (
        deploy_response.status_code == 200
    ), f"Expected 200, got {deploy_response.status_code} with body {deploy_response.text!r}"
    algorithm_id = deploy_response.json()["algorithm_id"]

    delete_response = requests.delete(
        f"{server_url}/api/v0/deploy/algorithm/{algorithm_id}"
    )
    assert (
        delete_response.status_code == 200
    ), f"Expected 200, got {delete_response.status_code} with body {delete_response.text!r}"

    get_response = requests.get(f"{server_url}/api/v0/algorithm/{name}/4")
    assert (
        get_response.status_code == 404
    ), f"Expected 404 after delete, got {get_response.status_code} with body {get_response.text!r}"


def test_delete_removable_algorithm_minor_version(server_url, tmp_path):
    """
    Deleting a minor version should keep the algorithm if other minors exist.
    """
    name = f"deploy_minor_{uuid.uuid4().hex[:8]}"
    version_a = "1.0"
    version_b = "1.1"
    alg_dir_a = _create_algorithm_dir(
        tmp_path,
        name,
        version_a,
        runner_body="class Runner:\n    value = 1\n",
    )
    alg_dir_b = _create_algorithm_dir(
        tmp_path,
        name,
        version_b,
        runner_body="class Runner:\n    value = 2\n",
    )

    algorithm_id = None
    try:
        deploy_response_a = requests.post(
            f"{server_url}/api/v0/deploy/local",
            params={"path": str(alg_dir_a)},
        )
        assert (
            deploy_response_a.status_code == 200
        ), f"Expected 200, got {deploy_response_a.status_code} with body {deploy_response_a.text!r}"
        algorithm_id = deploy_response_a.json()["algorithm_id"]

        deploy_response_b = requests.post(
            f"{server_url}/api/v0/deploy/local",
            params={"path": str(alg_dir_b)},
        )
        assert (
            deploy_response_b.status_code == 200
        ), f"Expected 200, got {deploy_response_b.status_code} with body {deploy_response_b.text!r}"

        delete_response = requests.delete(
            f"{server_url}/api/v0/deploy/algorithm/{algorithm_id}",
            params={"algorithm_minor_version": "0"},
        )
        assert (
            delete_response.status_code == 200
        ), f"Expected 200, got {delete_response.status_code} with body {delete_response.text!r}"

        get_response = requests.get(f"{server_url}/api/v0/algorithm/{name}/1")
        assert (
            get_response.status_code == 200
        ), f"Expected 200 after minor delete, got {get_response.status_code} with body {get_response.text!r}"
        payload = get_response.json()
        assert "0" not in payload["algorithm_minor_versions"]
    finally:
        _cleanup_algorithm(server_url, algorithm_id)


def test_delete_removable_algorithm_last_minor_removes_algorithm(
    server_url, tmp_path
):
    """
    Deleting the last minor version should remove the algorithm record.
    """
    name = f"deploy_minor_last_{uuid.uuid4().hex[:8]}"
    version = "2.0"
    alg_dir = _create_algorithm_dir(tmp_path, name, version)

    deploy_response = requests.post(
        f"{server_url}/api/v0/deploy/local",
        params={"path": str(alg_dir)},
    )
    assert (
        deploy_response.status_code == 200
    ), f"Expected 200, got {deploy_response.status_code} with body {deploy_response.text!r}"
    algorithm_id = deploy_response.json()["algorithm_id"]

    delete_response = requests.delete(
        f"{server_url}/api/v0/deploy/algorithm/{algorithm_id}",
        params={"algorithm_minor_version": "0"},
    )
    assert (
        delete_response.status_code == 200
    ), f"Expected 200, got {delete_response.status_code} with body {delete_response.text!r}"

    get_response = requests.get(f"{server_url}/api/v0/algorithm/{name}/2")
    assert (
        get_response.status_code == 404
    ), f"Expected 404 after last minor delete, got {get_response.status_code} with body {get_response.text!r}"


def test_delete_non_removable_algorithm_returns_400(server_url):
    """
    Non-removable algorithms should not be deletable via the deploy delete endpoint.
    """
    get_response = requests.get(
        f"{server_url}/api/v0/algorithm/dummy_algorithm/1"
    )
    assert (
        get_response.status_code == 200
    ), f"Expected 200, got {get_response.status_code} with body {get_response.text!r}"
    algorithm_id = get_response.json()["algorithm_id"]

    delete_response = requests.delete(
        f"{server_url}/api/v0/deploy/algorithm/{algorithm_id}"
    )
    assert (
        delete_response.status_code == 400
    ), f"Expected 400, got {delete_response.status_code} with body {delete_response.text!r}"
