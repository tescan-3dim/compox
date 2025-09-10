"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import typer
import yaml
import pytest
import sys
import subprocess
import os
from typing import Optional
from t3d_server.config.server_settings import Settings

app = typer.Typer(
    help="This CLI tool contains commands for running the T3D server."
)


@app.command(
    "run",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def run_server(
    ctx: typer.Context,
    config: str = None,
):
    """
    Run the T3D server with the specified configuration file. This command allows
    additional arguments to be passed to the server for its pydantic configuration.

    Parameters
    ----------
    config : str
        Path to the server configuration YAML file. If not provided, default server
        configuration will be used.
    ctx : typer.Context
        The context object that allows passing additional arguments to the server.
        These arguments will be passed to the server's pydantic configuration.
    """
    import subprocess
    import sys

    if config is None:
        command = [
            sys.executable,
            "-m",
            "t3d_server.run_server",
        ]
    else:
        command = [
            sys.executable,
            "-m",
            "t3d_server.run_server",
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
    Spawn a Celery worker for the T3D server. Additional arguments can be passed
    to the worker for its pydantic configuration.

    Parameters
    ----------
    config : str
        Path to the server configuration YAML file. If not provided, default server
        configuration will be used.
    ctx : typer.Context
        The context object that allows passing additional arguments to the worker.
        These arguments will be passed to the worker's pydantic configuration.
    """
    import subprocess
    import sys

    if config is None:
        command = [
            sys.executable,
            "-m",
            "t3d_server.run_worker",
        ]
    else:
        command = [
            sys.executable,
            "-m",
            "t3d_server.run_worker",
            "--config",
            config,
        ]

    command.extend(ctx.args)
    subprocess.run(command)


@app.command(name="test")
def test(
    config: str = "test_server.yaml",
    test_path: str = "../t3d_server/tests",
    server_url: str = None,
    junit_xml: Optional[str] = typer.Option(
        None,
        "--junit-xml",
    ),
):
    """
    Run the T3D server tests with the specified configuration file.

    Parameters
    ----------
    config : str
        Path to the server configuration YAML file. Default is 'test_server.yaml'.
    test_path : str
        Path to the directory containing the tests. Default is '../t3d_server/tests'.
    server_url : str
        You can also test against a running server by providing its URL. In that case,
        the server will not be started by the tests, and the tests will connect to the
        specified server URL instead of starting a new one.
    junit_xml : Optional[str]
        If provided, the test results will be saved in JUnit XML format to the specified file.
        This is useful for CI/CD pipelines or other automated testing environments.
        If not provided, the results will be printed to the console.
    """

    if server_url is None:

        if junit_xml:
            _ = pytest.main(
                [
                    test_path,
                    "--t3d_server_config_path",
                    config,
                    "--junit-xml",
                    junit_xml,
                ]
            )
        else:
            _ = pytest.main([test_path, "--t3d_server_config_path", config])
    else:
        if junit_xml:
            _ = pytest.main(
                [
                    test_path,
                    "--t3d_server_url",
                    server_url,
                    "--junit-xml",
                    junit_xml,
                ]
            )
        else:
            _ = pytest.main(
                [
                    test_path,
                    "--t3d_server_url",
                    server_url,
                ]
            )


@app.command(
    name="deploy-algorithms",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def deploy_algorithms(
    ctx: typer.Context,
    config: str = None,
):
    """
    Deploy the T3D algorithms with the specified configuration file. Additional
    arguments can be passed to the deployment for its pydantic configuration.

    Parameters
    ----------
    config : str
        Path to the server configuration YAML file. If not provided, default server
        configuration will be used.
    ctx : typer.Context
        The context object that allows passing additional arguments to the deployment.
        These arguments will be passed to the deployment server's pydantic configuration.
    """
    import subprocess
    import sys

    if config is None:
        command = [
            sys.executable,
            "-m",
            "t3d_server.deploy_algorithms",
        ]
    else:
        command = [
            sys.executable,
            "-m",
            "t3d_server.deploy_algorithms",
            "--config",
            config,
        ]

    command.extend(ctx.args)
    subprocess.run(command)


@app.command(name="serve-docs")
def serve_docs(port: int = 8234, directory: str = "docs/_build/html"):
    """
    Serve the documentation files from the specified directory on the given port.
    Parameters
    ----------
    port : int
        The port on which to serve the documentation. Default is 8234.
    directory : str
        The directory containing the documentation files. Default is 'docs/_build/html'.
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
    path: str = "t3d_server_config.yaml",
    overwrite: Optional[bool] = typer.Option(
        None,
        help="Set to true/false to skip prompt; if not set, user will be prompted.",
    ),
):
    """
    Generate a yaml configuration file for the T3D server.

    Parameters
    ----------
    ctx : typer.Context
        The context object that allows passing additional arguments to the to override
        the default server settings. These arguments will be passed to the server's
        pydantic configuration.
    path : str
        The path where the configuration file will be saved. Default is 't3d_server_config.yaml'.
        If the file already exists, the user will be prompted to overwrite it.
    overwrite : Optional[bool]
        If set to True, the existing file will be overwritten without prompting.
        If set to False, the existing file will not be overwritten and the user will
        be informed. If not set, the user will be prompted to confirm overwriting.
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
        if overwrite.lower() == "y":
            typer.echo(f"Overwriting existing file '{os.path.abspath(path)}'")
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
