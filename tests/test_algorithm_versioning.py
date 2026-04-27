"""
Copyright 2026 TESCAN GROUP, a.s.
All rights reserved
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
import toml

from compox.algorithm_utils.AlgorithmDeployer import AlgorithmDeployer
from compox.database_connection.InMemoryConnection import InMemoryConnection


def _make_algorithm_dir(tmp_path: Path, name: str, version: str) -> Path:
    """
    Create a minimal algorithm directory with pyproject.toml and Runner.py.
    """
    unique = uuid.uuid4().hex[:8]
    directory = tmp_path / f"{name}_{version.replace('.', '_')}_{unique}"
    directory.mkdir()
    content = {
        "project": {"name": name, "version": version},
        "tool": {
            "compox": {
                "check_importable": False,
                "obfuscate": False,
                "algorithm_type": "Generic",
                "tags": ["versioning"],
                "description": "versioning tests",
                "supported_devices": ["cpu"],
                "default_device": "cpu",
                "additional_parameters": [],
            }
        },
    }
    (directory / "pyproject.toml").write_text(toml.dumps(content))
    (directory / "Runner.py").write_text("class Runner: pass\n")
    return directory


@pytest.fixture
def db():
    """
    In-memory DB with list_objects shaped like S3 (list of dicts with Key).
    """
    db = InMemoryConnection()
    db.list_objects = lambda collection_name: [
        {"Key": key} for key in db.store.get(collection_name, {}).keys()
    ]
    return db


def _get_algorithm_record(
    db: InMemoryConnection, algorithm_id: str, name: str, major: str
) -> dict:
    """
    Load algorithm JSON from algorithm-store for assertions.
    """
    key = f"{algorithm_id}~{name}~{major}"
    raw = db.get_objects("algorithm-store", [key])[0]
    return json.loads(raw)


def test_initial_deploy_sets_minor_from_pyproject(db, tmp_path):
    """
    Initial deployment should store pyproject minor version as latest.
    """
    alg_dir = _make_algorithm_dir(tmp_path, "versioned_algo", "1.2")
    deployer = AlgorithmDeployer(str(alg_dir))
    algorithm_id = deployer.store_algorithm(database_connection=db)

    record = _get_algorithm_record(db, algorithm_id, "versioned_algo", "1")
    assert (
        record["latest_algorithm_minor_version"] == "2"
    ), "Expected latest minor to match pyproject minor on first deploy."
    assert (
        "2" in record["algorithm_minor_version"]
    ), "Expected algorithm_minor_version to contain the pyproject minor key."


def test_redeploy_of_identical_algo_keeps_minor_and_id(db, tmp_path):
    """
    Redeployment should keep algorithm_id and preserve latest minor if unchanged.
    """
    alg_dir = _make_algorithm_dir(tmp_path, "versioned_algo", "1.2")
    deployer = AlgorithmDeployer(str(alg_dir))
    algorithm_id_first = deployer.store_algorithm(database_connection=db)
    algorithm_id_second = deployer.store_algorithm(database_connection=db)

    assert (
        algorithm_id_first == algorithm_id_second
    ), "Expected algorithm_id to remain stable across redeployments."

    record = _get_algorithm_record(
        db, algorithm_id_first, "versioned_algo", "1"
    )
    assert (
        record["latest_algorithm_minor_version"] == "2"
    ), "Expected latest minor to preserve on redeploy (2)."
    assert (
        "2" in record["algorithm_minor_version"]
    ), "Expected algorithm_minor_version to still contain the minor key."


def test_redeploy_ignores_pyproject_minor_on_existing_algorithm(db, tmp_path):
    """
    Redeploy uses stored latest minor + 1, not pyproject minor.
    """
    alg_dir_v1 = _make_algorithm_dir(tmp_path, "versioned_algo", "1.2")
    deployer_v1 = AlgorithmDeployer(str(alg_dir_v1))
    algorithm_id = deployer_v1.store_algorithm(database_connection=db)

    alg_dir_v2 = _make_algorithm_dir(tmp_path, "versioned_algo", "1.99")
    deployer_v2 = AlgorithmDeployer(str(alg_dir_v2))
    deployer_v2.store_algorithm(database_connection=db)

    record = _get_algorithm_record(db, algorithm_id, "versioned_algo", "1")
    assert (
        record["latest_algorithm_minor_version"] == "3"
    ), "Expected minor to increment from stored latest (2 -> 3), not jump to 99."


def test_legacy_record_without_latest_minor_starts_at_zero(db, tmp_path):
    """
    Missing latest_algorithm_minor_version should start at 0 on redeploy.
    """
    algorithm_id = "alg-legacy"
    name = "legacy_algo"
    major = "1"
    legacy_record = {
        "algorithm_id": algorithm_id,
        "algorithm_name": name,
        "algorithm_major_version": major,
        "algorithm_minor_version": {},
    }
    db.put_objects(
        "algorithm-store",
        [f"{algorithm_id}~{name}~{major}"],
        [json.dumps(legacy_record)],
    )

    alg_dir = _make_algorithm_dir(tmp_path, name, "1.2")
    deployer = AlgorithmDeployer(str(alg_dir))
    returned_id = deployer.store_algorithm(database_connection=db)

    assert (
        returned_id == algorithm_id
    ), "Expected existing algorithm_id to be reused for legacy record."
    record = _get_algorithm_record(db, algorithm_id, name, major)
    assert (
        record["latest_algorithm_minor_version"] == "0"
    ), "Expected latest minor to start at 0 for legacy records."
    assert (
        "0" in record["algorithm_minor_version"]
    ), "Expected algorithm_minor_version to include newly created 0 key."


def _make_algorithm_sources(
    tmp_path: Path, name: str, version: str, runner_body: str
) -> Path:
    """
    Create a minimal algorithm directory with customizable Runner.py content.
    """
    directory = _make_algorithm_dir(tmp_path, name, version)
    (directory / "Runner.py").write_text(runner_body)
    return directory


def test_module_id_same_for_identical_sources(tmp_path):
    """
    Identical module sources should produce identical module ids.
    """
    alg_dir_1 = _make_algorithm_sources(
        tmp_path, "mod_algo", "1.0", "class Runner: pass\n"
    )
    alg_dir_2 = _make_algorithm_sources(
        tmp_path, "mod_algo", "1.0", "class Runner: pass\n"
    )

    deployer_1 = AlgorithmDeployer(str(alg_dir_1))
    deployer_2 = AlgorithmDeployer(str(alg_dir_2))

    module_id_1, _ = deployer_1._create_algorithm_module(str(alg_dir_1))
    module_id_2, _ = deployer_2._create_algorithm_module(str(alg_dir_2))

    assert (
        module_id_1 == module_id_2
    ), "Expected identical module sources to produce identical module ids."


def test_module_id_differs_for_different_sources(tmp_path):
    """
    Different module sources should produce different module ids.
    """
    alg_dir_1 = _make_algorithm_sources(
        tmp_path, "mod_algo", "1.0", "class Runner: pass\n"
    )
    alg_dir_2 = _make_algorithm_sources(
        tmp_path,
        "mod_algo",
        "1.0",
        "class Runner:\n    def x(self):\n        return 1\n",
    )

    deployer_1 = AlgorithmDeployer(str(alg_dir_1))
    deployer_2 = AlgorithmDeployer(str(alg_dir_2))

    module_id_1, _ = deployer_1._create_algorithm_module(str(alg_dir_1))
    module_id_2, _ = deployer_2._create_algorithm_module(str(alg_dir_2))

    assert (
        module_id_1 != module_id_2
    ), "Expected different module sources to produce different module ids."


def _write_asset(directory: Path, relpath: str, content: bytes) -> None:
    """
    Write a non-.py asset file under the algorithm directory.
    """
    asset_path = directory / relpath
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(content)


def test_assets_hashes_same_for_identical_assets(db, tmp_path):
    """
    Identical asset bytes should produce identical asset hashes.
    """
    alg_dir_1 = _make_algorithm_dir(tmp_path, "asset_algo", "1.0")
    alg_dir_2 = _make_algorithm_dir(tmp_path, "asset_algo", "1.0")

    _write_asset(alg_dir_1, "files/weights.bin", b"same")
    _write_asset(alg_dir_2, "files/weights.bin", b"same")

    deployer_1 = AlgorithmDeployer(str(alg_dir_1))
    deployer_2 = AlgorithmDeployer(str(alg_dir_2))

    assets_1 = deployer_1._store_algorithm_assets(
        str(alg_dir_1), database_connection=db
    )
    assets_2 = deployer_2._store_algorithm_assets(
        str(alg_dir_2), database_connection=db
    )

    assert (
        assets_1 == assets_2
    ), "Expected identical assets to produce identical asset hashes."


def test_assets_hashes_differ_for_different_assets(db, tmp_path):
    """
    Different asset bytes should produce different asset hashes.
    """
    alg_dir_1 = _make_algorithm_dir(tmp_path, "asset_algo", "1.0")
    alg_dir_2 = _make_algorithm_dir(tmp_path, "asset_algo", "1.0")

    _write_asset(alg_dir_1, "files/weights.bin", b"one")
    _write_asset(alg_dir_2, "files/weights.bin", b"two")

    deployer_1 = AlgorithmDeployer(str(alg_dir_1))
    deployer_2 = AlgorithmDeployer(str(alg_dir_2))

    assets_1 = deployer_1._store_algorithm_assets(
        str(alg_dir_1), database_connection=db
    )
    assets_2 = deployer_2._store_algorithm_assets(
        str(alg_dir_2), database_connection=db
    )

    assert (
        assets_1 != assets_2
    ), "Expected different assets to produce different asset hashes."
