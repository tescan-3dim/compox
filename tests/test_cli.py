"""
Copyright 2026 Tescan group, a.s.
All rights reserved
"""

from pathlib import Path
import sys
import types

import yaml
from typer.testing import CliRunner

from compox.cli import app


def test_root_cli_shows_help_when_no_command_provided():
    runner = CliRunner()

    result = runner.invoke(app, [])

    assert "Usage:" in result.output
    assert "Commands" in result.output
    assert "Missing command" not in result.output


def test_deploy_algorithms_cli_passes_typed_options_and_overrides(
    monkeypatch, tmp_path: Path
):
    """
    The CLI should resolve config + dotted overrides and pass typed options
    directly into the deployment entrypoint.
    """
    runner = CliRunner()
    config_path = tmp_path / "config.yaml"
    algorithm_root = tmp_path / "algorithms_override"
    algorithm_root.mkdir()

    config_path.write_text(
        yaml.safe_dump(
            {
                "port": 5471,
                "deploy_algorithms_from": str(
                    tmp_path / "algorithms_from_config"
                ),
                "storage": {
                    "backend_settings": {
                        "provider": "minio",
                        "start_instance": False,
                        "port": 9101,
                        "console_port": 9100,
                        "storage_path": str(tmp_path / "storage"),
                        "executable_path": "minio/minio.exe",
                    }
                },
            }
        )
    )

    captured = {}

    def _fake_run_deployment(**kwargs):
        captured.update(kwargs)

    monkeypatch.setitem(
        sys.modules,
        "compox.deploy_algorithms",
        types.SimpleNamespace(run_deployment=_fake_run_deployment),
    )

    result = runner.invoke(
        app,
        [
            "deploy-algorithms",
            "--config",
            str(config_path),
            "--path",
            str(algorithm_root),
            "--name",
            "foo",
            "--name",
            "bar",
            "--delete-existing",
            "--no-verbose",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["algorithms_path"] == str(algorithm_root.resolve())
    assert captured["algorithm_names"] == ["foo", "bar"]
    assert captured["delete_existing"] is True
    assert captured["verbose"] is False


def test_resolve_algorithm_paths_requires_requested_algorithm_folders(
    tmp_path: Path,
):
    """
    Explicitly requested algorithm folders should fail fast if any are missing.
    """
    from compox.deploy_algorithms import resolve_algorithm_paths

    (tmp_path / "foo").mkdir()

    try:
        resolve_algorithm_paths(str(tmp_path), algorithm_names=["foo", "bar"])
    except FileNotFoundError as exc:
        assert "bar" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError for missing algorithm")
