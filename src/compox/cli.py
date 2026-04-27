"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import typer
import yaml
import sys
import subprocess
import os
import time
from typing import Optional
import requests
from compox.config.server_settings import Settings
from compox.algorithm_debug import app as debug_app

app = typer.Typer(
    help="This CLI tool contains commands for running the Compox.",
    no_args_is_help=True,
)

app.add_typer(debug_app, name="debug")


def _normalize_server_url(server_url: str) -> str:
    """
    Normalize server URL by ensuring scheme and removing trailing slash.

    Parameters
    ----------
    server_url : str
        The server URL input.

    Returns
    -------
    str
        Normalized server URL.
    """
    if not server_url.startswith("http"):
        server_url = "http://" + server_url
    if server_url.endswith("/"):
        server_url = server_url[:-1]
    return server_url


def _merge_nested_dicts(base: dict, updates: dict) -> dict:
    """
    Recursively merge nested dictionaries in-place.
    """
    for key, value in updates.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            _merge_nested_dicts(base[key], value)
        else:
            base[key] = value
    return base


def _load_settings_with_cli_overrides(
    config: str | None, cli_overrides: list[str]
) -> Settings:
    """
    Load server settings from config and apply dotted CLI overrides.
    """
    config_values = {}
    if config is not None:
        with open(config, "r") as file:
            config_values = yaml.safe_load(file) or {}

    override_values = parse_flat_args(cli_overrides)
    merged_values = dict(config_values)
    _merge_nested_dicts(merged_values, override_values)
    return Settings(**merged_values)


@app.command(name="deploy-local")
def deploy_local(
    path: str,
    server_url: str = "http://127.0.0.1:5471",
    algorithm_name: str = typer.Option(
        None, "--algorithm-name", help="Override algorithm name."
    ),
    algorithm_major_version: str = typer.Option(
        None,
        "--algorithm-major-version",
        help="Override algorithm major version.",
    ),
    removable: Optional[str] = typer.Option(
        None,
        "--removable",
        help="Override whether the algorithm is removable (true/false).",
    ),
    exportable: Optional[str] = typer.Option(
        None,
        "--exportable",
        help="Override whether the algorithm is exportable (true/false).",
    ),
    async_deploy: bool = typer.Option(
        False, "--async", help="Use async deploy endpoint."
    ),
    poll: bool = typer.Option(
        True, help="Poll deploy status until completion (async only)."
    ),
    timeout_s: int = typer.Option(
        60, help="Timeout in seconds when polling deploy status."
    ),
    poll_interval_s: float = typer.Option(
        0.5, help="Polling interval in seconds."
    ),
):
    """
    Deploy an algorithm from a local folder or zip file using the HTTP API.

    Parameters
    ----------
    path : str
        Local path to an algorithm folder or .zip file.
    server_url : str
        Base URL of the Compox server.
    algorithm_name : Optional[str]
        Optional override for algorithm name.
    algorithm_major_version : Optional[str]
        Optional override for algorithm major version.
    removable : Optional[str]
        Optional override for whether the algorithm is removable.
    exportable : Optional[str]
        Optional override for whether the algorithm is exportable.
    async_deploy : bool
        If True, uses the async deploy endpoint.
    poll : bool
        If True, polls deploy status until completion (async only).
    timeout_s : int
        Timeout in seconds for polling.
    poll_interval_s : float
        Polling interval in seconds.
    """
    server_url = _normalize_server_url(server_url)
    path = os.path.abspath(path)
    params = {"path": path}
    if algorithm_name is not None:
        params["algorithm_name"] = algorithm_name
    if algorithm_major_version is not None:
        params["algorithm_major_version"] = algorithm_major_version
    if removable is not None:
        removable_lc = removable.strip().lower()
        true_vals = {"true", "1", "yes", "y"}
        false_vals = {"false", "0", "no", "n"}
        if removable_lc in true_vals:
            params["removable"] = True
        elif removable_lc in false_vals:
            params["removable"] = False
        else:
            typer.echo("Invalid value for --removable. Use true/false.")
            raise typer.Exit(code=1)
    if exportable is not None:
        exportable_lc = exportable.strip().lower()
        true_vals = {"true", "1", "yes", "y"}
        false_vals = {"false", "0", "no", "n"}
        if exportable_lc in true_vals:
            params["exportable"] = True
        elif exportable_lc in false_vals:
            params["exportable"] = False
        else:
            typer.echo("Invalid value for --exportable. Use true/false.")
            raise typer.Exit(code=1)
    endpoint = (
        "/api/v0/deploy/local-async" if async_deploy else "/api/v0/deploy/local"
    )
    response = requests.post(f"{server_url}{endpoint}", params=params)
    typer.echo(response.text)
    if not async_deploy or response.status_code != 200 or not poll:
        return
    try:
        deploy_id = response.json().get("deploy_id")
    except Exception:
        return
    if not deploy_id:
        return
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status_response = requests.get(
            f"{server_url}/api/v0/deploy/{deploy_id}"
        )
        typer.echo(status_response.text)
        if status_response.status_code == 200:
            payload = status_response.json()
            if payload.get("status") in {"COMPLETED", "FAILED"}:
                return
        time.sleep(poll_interval_s)
    typer.echo("Timed out waiting for deploy to complete.")


@app.command(name="delete-algorithm")
def delete_algorithm(
    algorithm_name: str,
    algorithm_major_version: str,
    server_url: str = "http://127.0.0.1:5471",
    algorithm_minor_version: Optional[str] = None,
):
    """
    Delete a removable algorithm (or a specific minor version) using the HTTP API.

    Parameters
    ----------
    algorithm_name : str
        Algorithm name.
    algorithm_major_version : str
        Algorithm major version.
    server_url : str
        Base URL of the Compox server.
    algorithm_minor_version : Optional[str]
        If provided, delete only this minor version.
    """
    server_url = _normalize_server_url(server_url)
    lookup = requests.get(
        f"{server_url}/api/v0/algorithm/{algorithm_name}/{algorithm_major_version}"
    )
    if lookup.status_code != 200:
        typer.echo(lookup.text)
        raise typer.Exit(code=1)
    algorithm_id = lookup.json().get("algorithm_id")
    if not algorithm_id:
        typer.echo("Algorithm id not found in response.")
        raise typer.Exit(code=1)
    params = {}
    if algorithm_minor_version is not None:
        params["algorithm_minor_version"] = algorithm_minor_version
    response = requests.delete(
        f"{server_url}/api/v0/deploy/algorithm/{algorithm_id}",
        params=params or None,
    )
    typer.echo(response.text)


@app.command(name="export-algorithm")
def export_algorithm(
    algorithm_name: str,
    algorithm_major_version: str,
    server_url: str = "http://127.0.0.1:5471",
    algorithm_minor_version: Optional[str] = None,
    checkpoint_id: Optional[str] = None,
    output_dir: Optional[str] = None,
):
    """
    Export an algorithm package (zip) using the HTTP API.

    Parameters
    ----------
    algorithm_name : str
        Algorithm name.
    algorithm_major_version : str
        Algorithm major version.
    server_url : str
        Base URL of the Compox server.
    algorithm_minor_version : Optional[str]
        Optional minor version to export.
    checkpoint_id : Optional[str]
        Optional checkpoint id to override assets.
    output_dir : Optional[str]
        Output directory for the exported zip.
    """
    server_url = _normalize_server_url(server_url)
    params = {}
    if algorithm_minor_version is not None:
        params["algorithm_minor_version"] = algorithm_minor_version
    if checkpoint_id is not None:
        params["checkpoint_id"] = checkpoint_id
    url = (
        f"{server_url}/api/v0/algorithm/"
        f"{algorithm_name}/{algorithm_major_version}/export"
    )
    response = requests.get(url, params=params, stream=True)
    if response.status_code != 200:
        typer.echo(response.text)
        raise typer.Exit(code=1)
    filename = f"{algorithm_name}_{algorithm_major_version}.zip"
    output_dir = os.path.abspath(output_dir) if output_dir is not None else None
    output_path = (
        os.path.join(output_dir, filename)
        if output_dir is not None
        else filename
    )
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
    typer.echo(f"Saved: {output_path}")


@app.command(
    "run",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def run_server(
    ctx: typer.Context,
    config: str = None,
):
    """
    Run compox with the specified configuration file. This command allows
    additional arguments to be passed to the server for its pydantic configuration.

    Parameters
    ----------
    ctx : typer.Context
        The context object that allows passing additional arguments to the server.
        These arguments will be passed to the server's pydantic configuration.
    config : str | None
        Path to the server configuration YAML file. If not provided, default server
        configuration will be used.
    """
    import subprocess
    import sys

    if config is None:
        command = [
            sys.executable,
            "-m",
            "compox.run_server",
        ]
    else:
        command = [
            sys.executable,
            "-m",
            "compox.run_server",
            "--config",
            config,
        ]

    command.extend(ctx.args)

    subprocess.run(command)


@app.command(
    name="spawn-worker",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def spawn_worker(ctx: typer.Context, config: str = None):
    """
    Spawn a Celery worker for the Compox. Additional arguments can be passed
    to the worker for its pydantic configuration.

    Parameters
    ----------
    ctx : typer.Context
        The context object that allows passing additional arguments to the worker.
        These arguments will be passed to the worker's pydantic configuration.
    config : str | None
        Path to the server configuration YAML file. If not provided, default server
        configuration will be used.
    """
    import subprocess
    import sys

    if config is None:
        command = [
            sys.executable,
            "-m",
            "compox.run_worker",
        ]
    else:
        command = [
            sys.executable,
            "-m",
            "compox.run_worker",
            "--config",
            config,
        ]

    command.extend(ctx.args)
    subprocess.run(command)


@app.command(name="test")
def test(
    config: str = "test_server.yaml",
    test_path: str = "../compox/tests",
    server_url: str = None,
    junit_xml: Optional[str] = typer.Option(
        None,
        "--junit-xml",
    ),
):
    """
    Run compox tests with the specified configuration file.

    Parameters
    ----------
    config : str
        Path to the server configuration YAML file. Default is 'test_server.yaml'.
    test_path : str
        Path to the directory containing the tests. Default is '../compox/tests'.
    server_url : str | None
        You can also test against a running server by providing its URL. In that case,
        the server will not be started by the tests, and the tests will connect to the
        specified server URL instead of starting a new one.
    junit_xml : Optional[str]
        If provided, the test results will be saved in JUnit XML format to the specified file.
        This is useful for CI/CD pipelines or other automated testing environments.
        If not provided, the results will be printed to the console.
    """

    command = [sys.executable, "-m", "pytest", test_path]

    if server_url is None:
        command.extend(["--compox_config_path", config])
    else:
        command.extend(["--compox_url", server_url])

    if junit_xml:
        command.extend(["--junit-xml", junit_xml])

    result = subprocess.run(command)
    if result.returncode != 0:
        raise typer.Exit(code=result.returncode)


@app.command(
    name="deploy-algorithms",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def deploy_algorithms(
    ctx: typer.Context,
    config: str | None = typer.Option(
        None, "--config", help="Path to server configuration YAML file."
    ),
    path: str | None = typer.Option(
        None,
        "--path",
        help="Override the root folder containing deployable algorithms.",
    ),
    name: Optional[list[str]] = typer.Option(
        None,
        "--name",
        "-n",
        help="Only deploy the specified algorithm folder names. Repeat for multiple names.",
    ),
    delete_existing: bool = typer.Option(
        False,
        "--delete-existing",
        help="Delete an existing algorithm with the same name and major version before deploying.",
    ),
    verbose: bool = typer.Option(
        True,
        "--verbose/--no-verbose",
        help="Print resolved settings before deployment.",
    ),
):
    """
    Deploy algorithms from the configured or explicitly provided folder.

    Additional dotted arguments from the compox configuration can be passed to,
    such as --port 1234 or --gui.use_systray false, and they will be used to
    override the corresponding settings in the server configuration for the deployment process.

    Parameters
    ----------
    ctx : typer.Context
        The context object that allows passing additional dotted setting
        overrides to the deployment command.
    config : str | None
        Path to the server configuration YAML file.
    path : str | None
        Optional override of the algorithm root directory.
    name : Optional[list[str]]
        Optional list of specific algorithm folder names to deploy.
    delete_existing : bool
        If True, delete an existing algorithm with the same name and major
        version before deploying.
    verbose : bool
        If True, print the resolved settings before deployment.
    """
    try:
        from compox.deploy_algorithms import (
            run_deployment as run_algorithm_deployment,
        )

        settings = _load_settings_with_cli_overrides(config, ctx.args)
        algorithms_path = os.path.abspath(
            path or settings.deploy_algorithms_from
        )
        run_algorithm_deployment(
            settings=settings,
            algorithms_path=algorithms_path,
            algorithm_names=name,
            delete_existing=delete_existing,
            verbose=verbose,
        )
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


@app.command(name="serve-docs")
def serve_docs(port: int = 8234, directory: str = "docs/_build/html") -> None:
    """
    Serve the documentation files from the specified directory on the given port.

    Parameters
    ----------
    port : int
        The port on which to serve the documentation. Default is 8234.
    directory : str
        The directory containing the documentation files. Default is 'docs/_build/html'.

    Returns
    -------
    None
    """
    command = [
        "python",
        "-m",
        "http.server",
        str(port),
        "--directory",
        directory,
    ]
    typer.echo(f"Serving documentation on http://localhost:{port}/")
    subprocess.run(command)


def parse_flat_args(args: list[str]) -> dict:
    """
    Parses leftover CLI args like ['--foo.bar', '123', '--gui.use_systray', 'true']
    into a nested dict: {'foo': {'bar': 123}, 'gui': {'use_systray': True}}

    Parameters
    ----------
    args : list[str]
        Input CLI args.

    Returns
    -------
    dict
        Output nested dict.
    """
    updates = {}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--"):
            key = arg[2:]
            # Support --key=value form
            if "=" in key:
                key, value = key.split("=", 1)
            else:
                i += 1
                value = args[i] if i < len(args) else None

            # Try type conversion
            val = value

            # Handle booleans
            true_vals = {"true", "yes", "1"}
            false_vals = {"false", "no", "0"}

            if isinstance(val, str):
                val_lc = val.lower()
                if val_lc in {"null", "none"}:
                    val = None
                elif val_lc in true_vals:
                    val = True
                elif val_lc in false_vals:
                    val = False
                elif "," in val:
                    # Interpret comma-separated values as a list
                    val = [v.strip() for v in val.split(",")]
                elif val.isdigit():
                    val = int(val)
                else:
                    try:
                        val = float(val)
                    except ValueError:
                        pass  # leave as string

            # Assign to nested structure
            parts = key.split(".")
            target = updates
            for part in parts[:-1]:
                target = target.setdefault(part, {})
            target[parts[-1]] = val
        i += 1
    return updates


@app.command(
    name="generate-config",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def generate_config(
    ctx: typer.Context,
    path: str = "compox_config.yaml",
    overwrite: bool = typer.Option(
        None,
        help="Set to true/false to skip prompt; if not set, user will be prompted.",
    ),
) -> None:
    """
    Generate a yaml configuration file for the Compox.

    Parameters
    ----------
    ctx : typer.Context
        The context object that allows passing additional arguments to the to override
        the default server settings. These arguments will be passed to the server's
        pydantic configuration.
    path : str
        The path where the configuration file will be saved. Default is 'compox_config.yaml'.
        If the file already exists, the user will be prompted to overwrite it.
    overwrite : bool | str | None
        If set to True, the existing file will be overwritten without prompting.
        If set to False, the existing file will not be overwritten and the user will
        be informed. If not set, the user will be prompted to confirm overwriting.

    Returns
    -------
    None
    """
    typer.echo("Starting the configuration generator...\n")

    # check if the file already exists
    if path and os.path.exists(path):
        # if the file exists, prompt the user to overwrite it

        if overwrite is None:
            overwrite = typer.prompt(
                f"The file '{path}' already exists. Do you want to overwrite it? (y/n)",
                default="n",
            )
        else:
            overwrite = "y" if overwrite else "n"

        if isinstance(overwrite, str):
            if overwrite.lower() == "y":
                typer.echo(
                    f"Overwriting existing file '{os.path.abspath(path)}'"
                )
            else:
                typer.echo(
                    f"Keeping existing file '{os.path.abspath(path)}'. No changes made to the configuration."
                )
                return
    else:
        typer.echo(
            f"Generating configuration file at '{os.path.abspath(path)}'"
        )

    # update the server settings with the additional arguments passed to the command
    if ctx.args:
        typer.echo(
            "Updating server settings with additional arguments passed to the command."
        )
    typer.echo(sys.argv)

    # convert the flat args to a nested dict
    additional_args = parse_flat_args(ctx.args)

    server_settings = Settings(**additional_args)
    with open(path, "w") as f:
        yaml.dump(
            server_settings.model_dump(
                exclude_none=True
            ),  # TODO: this is a workaround
            # which can potentially break things if the default value is something other than None
            # and we want to set it to None, it will be dropped from the output
            # and upon loading the yaml file, the default value will be used instead
            # of None, which the developer might not expect.
            f,
            default_flow_style=False,
            sort_keys=False,
        )
