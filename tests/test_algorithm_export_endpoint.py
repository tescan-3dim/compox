"""
Copyright 2026 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from __future__ import annotations

from io import BytesIO
import zipfile
import uuid
from pathlib import Path

import requests
import toml


def _export_algorithm(server_url: str, name: str, major: str) -> requests.Response:
    """
    Call the export endpoint for a given algorithm name and major version.
    """
    return requests.get(
        f"{server_url}/api/v0/algorithm/{name}/{major}/export"
    )


def _create_algorithm_dir(
    tmp_path: Path, name: str, version: str, exportable: bool = True
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
                "exportable": exportable,
            }
        },
    }
    (alg_dir / "pyproject.toml").write_text(toml.dumps(pyproject))
    (alg_dir / "Runner.py").write_text("class Runner: pass")
    return alg_dir


def _cleanup_algorithm(server_url: str, algorithm_id: str | None) -> None:
    """
    Best-effort cleanup for a deployed algorithm by id.
    """
    if not algorithm_id:
        return
    try:
        requests.delete(f"{server_url}/api/v0/deploy/algorithm/{algorithm_id}")
    except Exception:
        pass


def test_export_endpoint_returns_zip(server_url):
    """
    Export endpoint should return a ZIP archive for an existing algorithm.
    """
    response = _export_algorithm(server_url, "dummy_algorithm", "1")
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code} with body {response.text!r}"
    )
    assert response.headers.get("content-type") == "application/zip", (
        "Expected content-type application/zip for export response."
    )

    zip_bytes = BytesIO(response.content)
    with zipfile.ZipFile(zip_bytes) as zf:
        names = zf.namelist()
        assert names, "Expected exported ZIP to contain files."
        # Runner.py should be present somewhere in the package
        assert any(name.endswith("Runner.py") for name in names), (
            f"Expected Runner.py in exported ZIP, got {names!r}"
        )


def test_export_endpoint_with_minor_version(server_url):
    """
    Export endpoint should accept an explicit minor version.
    """
    response = requests.get(
        f"{server_url}/api/v0/algorithm/dummy_algorithm/1/export",
        params={"algorithm_minor_version": 0},
    )
    assert response.status_code == 200, (
        f"Expected 200 for minor version 0, got {response.status_code} with body {response.text!r}"
    )
    assert response.headers.get("content-type") == "application/zip", (
        "Expected content-type application/zip for export response."
    )


def test_export_endpoint_invalid_minor_version(server_url):
    """
    Export endpoint should return 404 for a missing minor version.
    """
    response = requests.get(
        f"{server_url}/api/v0/algorithm/dummy_algorithm/1/export",
        params={"algorithm_minor_version": 999},
    )
    assert response.status_code == 404, (
        f"Expected 404 for missing minor version, got {response.status_code} with body {response.text!r}"
    )


def test_export_endpoint_invalid_checkpoint(server_url):
    """
    Export endpoint should return 404 for a missing checkpoint id.
    """
    response = requests.get(
        f"{server_url}/api/v0/algorithm/dummy_algorithm/1/export",
        params={"checkpoint_id": "does-not-exist"},
    )
    assert response.status_code == 404, (
        f"Expected 404 for missing checkpoint, got {response.status_code} with body {response.text!r}"
    )


def test_export_endpoint_missing_algorithm(server_url):
    """
    Export endpoint should return 404 for a missing algorithm.
    """
    response = _export_algorithm(server_url, "does_not_exist", "1")
    assert response.status_code == 404, (
        f"Expected 404, got {response.status_code} with body {response.text!r}"
    )


def test_export_endpoint_non_exportable_returns_403(server_url, tmp_path):
    """
    Export endpoint should return 403 for non-exportable algorithms.
    """
    name = f"export_block_{uuid.uuid4().hex[:8]}"
    version = "1.0"
    alg_dir = _create_algorithm_dir(
        tmp_path, name, version, exportable=False
    )

    algorithm_id = None
    try:
        deploy_response = requests.post(
            f"{server_url}/api/v0/deploy/local",
            params={"path": str(alg_dir), "exportable": False},
        )
        assert (
            deploy_response.status_code == 200
        ), f"Expected 200, got {deploy_response.status_code} with body {deploy_response.text!r}"
        algorithm_id = deploy_response.json()["algorithm_id"]

        response = _export_algorithm(server_url, name, "1")
        assert response.status_code == 403, (
            f"Expected 403, got {response.status_code} with body {response.text!r}"
        )
    finally:
        _cleanup_algorithm(server_url, algorithm_id)
