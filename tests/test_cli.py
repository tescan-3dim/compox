"""
Copyright 2026 Tescan group, a.s.
All rights reserved
"""

from pathlib import Path
import sys
import types
import subprocess

import yaml
from typer.testing import CliRunner

from compox.cli import app, parse_flat_args


class DummyResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        text: str = "",
        json_data=None,
        chunks: list[bytes] | None = None,
    ):
        self.status_code = status_code
        self.text = text
        self._json_data = json_data
        self._chunks = chunks or []

    def json(self):
        if self._json_data is None:
            raise ValueError("No JSON payload")
        return self._json_data

    def iter_content(self, chunk_size: int = 1024 * 1024):
        yield from self._chunks


def test_root_cli_shows_help_when_no_command_provided():
    runner = CliRunner()

    result = runner.invoke(app, [])

    assert "Usage:" in result.output
    assert "Commands" in result.output
    assert "Missing command" not in result.output


def test_parse_flat_args_parses_nested_typed_values():
    """Flat CLI overrides should become a nested dict with sensible types."""
    parsed = parse_flat_args(
        [
            "--port",
            "1234",
            "--ssl.use_ssl",
            "false",
            "--info.product_name=Compox",
            "--tags",
            "a,b,c",
            "--checkpoint_id",
            "none",
        ]
    )

    assert parsed == {
        "port": 1234,
        "ssl": {"use_ssl": False},
        "info": {"product_name": "Compox"},
        "tags": ["a", "b", "c"],
        "checkpoint_id": None,
    }


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


def test_deploy_local_rejects_invalid_boolean_flag(monkeypatch):
    """Invalid boolean option values should fail before any HTTP request is sent."""
    runner = CliRunner()
    called = {"post": False}

    def _fail_if_called(*args, **kwargs):
        called["post"] = True
        raise AssertionError("requests.post should not be called")

    monkeypatch.setattr("compox.cli.requests.post", _fail_if_called)

    result = runner.invoke(
        app,
        [
            "deploy-local",
            ".",
            "--removable",
            "maybe",
        ],
    )

    assert result.exit_code == 1
    assert "Invalid value for --removable" in result.output
    assert called["post"] is False


def test_deploy_local_async_polls_until_terminal_status(
    monkeypatch, tmp_path: Path
):
    """Async deploy should poll deploy status until completion without touching the real network."""
    runner = CliRunner()
    algorithm_dir = tmp_path / "algo"
    algorithm_dir.mkdir()

    post_calls = []
    get_calls = []
    responses = iter(
        [
            DummyResponse(
                status_code=200,
                text='{"deploy_id":"dep-1"}',
                json_data={"deploy_id": "dep-1"},
            ),
            DummyResponse(
                status_code=200,
                text='{"status":"RUNNING"}',
                json_data={"status": "RUNNING"},
            ),
            DummyResponse(
                status_code=200,
                text='{"status":"COMPLETED"}',
                json_data={"status": "COMPLETED"},
            ),
        ]
    )

    def _fake_post(url, params=None):
        post_calls.append((url, params))
        return next(responses)

    def _fake_get(url):
        get_calls.append(url)
        return next(responses)

    monkeypatch.setattr("compox.cli.requests.post", _fake_post)
    monkeypatch.setattr("compox.cli.requests.get", _fake_get)
    monkeypatch.setattr("compox.cli.time.sleep", lambda *_args, **_kwargs: None)

    result = runner.invoke(
        app,
        [
            "deploy-local",
            str(algorithm_dir),
            "--async",
            "--poll",
            "--timeout-s",
            "1",
            "--poll-interval-s",
            "0.01",
        ],
    )

    assert result.exit_code == 0, result.output
    assert post_calls[0][0].endswith("/api/v0/deploy/local-async")
    assert len(get_calls) == 2
    assert "/api/v0/deploy/dep-1" in get_calls[0]


def test_delete_algorithm_looks_up_id_then_deletes(monkeypatch):
    """Delete command should resolve algorithm id first and then call the delete endpoint."""
    runner = CliRunner()
    calls = []

    def _fake_get(url):
        calls.append(("get", url))
        return DummyResponse(
            status_code=200,
            text='{"algorithm_id":"algo-1"}',
            json_data={"algorithm_id": "algo-1"},
        )

    def _fake_delete(url, params=None):
        calls.append(("delete", url, params))
        return DummyResponse(status_code=200, text='{"detail":"ok"}')

    monkeypatch.setattr("compox.cli.requests.get", _fake_get)
    monkeypatch.setattr("compox.cli.requests.delete", _fake_delete)

    result = runner.invoke(
        app,
        [
            "delete-algorithm",
            "foo",
            "1",
            "--algorithm-minor-version",
            "7",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls[0] == ("get", "http://127.0.0.1:5471/api/v0/algorithm/foo/1")
    assert calls[1] == (
        "delete",
        "http://127.0.0.1:5471/api/v0/deploy/algorithm/algo-1",
        {"algorithm_minor_version": "7"},
    )


def test_export_algorithm_writes_zip_to_output_dir(monkeypatch, tmp_path: Path):
    """Export command should stream the zip payload into the requested directory."""
    runner = CliRunner()
    output_dir = tmp_path / "exports"
    output_dir.mkdir()

    def _fake_get(url, params=None, stream=None):
        return DummyResponse(
            status_code=200,
            chunks=[b"abc", b"def"],
        )

    monkeypatch.setattr("compox.cli.requests.get", _fake_get)

    result = runner.invoke(
        app,
        [
            "export-algorithm",
            "foo",
            "1",
            "--output-dir",
            str(output_dir),
        ],
    )

    exported = output_dir / "foo_1.zip"
    assert result.exit_code == 0, result.output
    assert exported.read_bytes() == b"abcdef"


def test_run_command_builds_subprocess_with_extra_args(monkeypatch):
    """Run command should forward config and extra arguments to compox.run_server."""
    runner = CliRunner()
    captured = {}

    def _fake_run(command, *args, **kwargs):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("subprocess.run", _fake_run)

    result = runner.invoke(
        app,
        [
            "run",
            "--config",
            "server.yaml",
            "--port",
            "9999",
            "--ssl.use_ssl",
            "false",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["command"] == [
        sys.executable,
        "-m",
        "compox.run_server",
        "--config",
        "server.yaml",
        "--port",
        "9999",
        "--ssl.use_ssl",
        "false",
    ]


def test_generate_config_writes_yaml_with_cli_overrides(
    monkeypatch, tmp_path: Path
):
    """Config generation should stay inside the temp directory and apply dotted overrides."""
    runner = CliRunner()
    config_path = tmp_path / "generated.yaml"

    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "generate-config",
            "--path",
            str(config_path),
            "--overwrite",
            "true",
            "--port",
            "6001",
            "--ssl.use_ssl",
            "false",
        ],
    )

    assert result.exit_code == 0, result.output
    generated = yaml.safe_load(config_path.read_text())
    assert generated["port"] == 6001
    assert generated["ssl"]["use_ssl"] is False
