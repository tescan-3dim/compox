"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import os
import socket
import argparse
import json
from fastapi import FastAPI

from compox.config.server_settings import Settings

from compox.internal import downloader
from compox.config.server_settings import get_server_settings
from compox.components.api_builder import build_api
from compox.components.server_builder import build_server
from compox.algorithm_utils.deployment_utils import (
    deploy_algorithm_from_folder,
)


def parse_args() -> object:
    """
    Argument parser for the deployer.

    Returns
    -------
    object
        The parsed arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        help="Path to configuration yaml file. If None, use defaults specified in server_config.py.",
        default=None,
        required=False,
    )
    parser.add_argument(
        "-n",
        "--name",
        action="append",
        dest="algorithm_names",
        help="Deploy only the specified algorithm folder names. Repeat the option for multiple names.",
        default=None,
        required=False,
    )
    parser.add_argument(
        "--path",
        default=None,
        required=False,
        help="Override the root folder containing deployable algorithms.",
    )
    parser.add_argument(
        "--delete-existing",
        action="store_true",
        help="Delete an existing algorithm with the same name and major version before deployment.",
    )
    args, _ = parser.parse_known_args()
    return args


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def resolve_algorithm_paths(
    algorithms_path: str,
    algorithm_names: list[str] | None = None,
) -> list[str]:
    """
    Resolve deployable algorithm directories under the given root path.

    Parameters
    ----------
    algorithms_path : str
        Path to the root folder containing algorithm subdirectories.
    algorithm_names : list | None, optional
        List of specific algorithm names to deploy.

    Returns
    -------
    list[str]
        Absolute paths to deployable algorithm directories.
    """
    algorithms_path = os.path.abspath(algorithms_path)
    if not os.path.isdir(algorithms_path):
        raise FileNotFoundError(
            f"Algorithms directory not found: {algorithms_path}"
        )

    if algorithm_names:
        resolved_paths = []
        missing_algorithms = []
        for algorithm_name in algorithm_names:
            algo_path = os.path.join(algorithms_path, algorithm_name)
            if not os.path.isdir(algo_path):
                missing_algorithms.append(algorithm_name)
                continue
            resolved_paths.append(algo_path)
        if missing_algorithms:
            missing = ", ".join(sorted(missing_algorithms))
            raise FileNotFoundError(
                f"Algorithm folders not found in {algorithms_path}: {missing}"
            )
        return resolved_paths

    return [
        os.path.join(algorithms_path, folder_name)
        for folder_name in sorted(os.listdir(algorithms_path))
        if folder_name != "algorithm_template"
        and os.path.isdir(os.path.join(algorithms_path, folder_name))
    ]


def deploy_algorithms(
    algorithms_path: str,
    api: FastAPI,
    algorithm_names: list[str] | None = None,
    delete_existing: bool = False,
) -> None:
    """
    Deploy selected or all algorithms from the given root path.
    """
    algorithm_paths = resolve_algorithm_paths(
        algorithms_path=algorithms_path,
        algorithm_names=algorithm_names,
    )
    for algo_path in algorithm_paths:
        deploy_algorithm_from_folder(
            algo_path,
            api.state.database_connection,
            delete_existing=delete_existing,
        )


def run_deployment(
    settings: Settings | None = None,
    config_path: str | None = None,
    algorithm_names: list[str] | None = None,
    algorithms_path: str | None = None,
    delete_existing: bool = False,
    verbose: bool = True,
) -> None:
    """
    Run the deployment pipeline using the provided settings or config path.
    """
    if settings is None:
        settings = get_server_settings(config_path, verbose=verbose)
    elif verbose:
        print(json.dumps(json.loads(settings.model_dump_json()), indent=4))

    api = build_api(settings, with_lifespan=True)
    algorithms_path = os.path.abspath(
        algorithms_path or settings.deploy_algorithms_from
    )

    if not is_port_in_use(settings.port):
        print(f"Port {settings.port} is free. Starting deployment server.")

        # prepare storage
        if (
            settings.storage.backend_settings.provider == "minio"
            and settings.storage.backend_settings.start_instance
        ):

            os.makedirs(
                settings.storage.backend_settings.storage_path, exist_ok=True
            )
            downloader.get_minio(settings)

        server = build_server(api, settings)
        with server.run_in_thread():
            deploy_algorithms(
                algorithms_path,
                api=api,
                algorithm_names=algorithm_names,
                delete_existing=delete_existing,
            )
        server.should_exit = True
        print("Stopping deployment server")

    else:
        print(
            f"Port {settings.port} is already in use. Assuming server already running."
        )
        deploy_algorithms(
            algorithms_path,
            api=api,
            algorithm_names=algorithm_names,
            delete_existing=delete_existing,
        )


if __name__ == "__main__":
    args = parse_args()
    run_deployment(
        config_path=args.config,
        algorithm_names=args.algorithm_names,
        algorithms_path=args.path,
        delete_existing=args.delete_existing,
    )
