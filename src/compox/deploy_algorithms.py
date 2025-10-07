"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from multiprocessing import Value
import os
import socket
import argparse
from fastapi import FastAPI
from argparse import Namespace

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
        "--names",
        help="Only deploy the following names of algorithms (space separated)",
        default=None,
        required=False,
    )
    args, _ = parser.parse_known_args()
    return args


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def deploy_algorithms(
    algorithms_path: str,
    api: FastAPI | None = None,
    algorithm_names: list | None = None,
    args: argparse.Namespace | None = None,
) -> None:
    """
    This function iterates over the specified algorithms or all subfolders
    in the given `algorithms_path`, and deploys each found algorithm using
    the database connection provided by the API object.

    Parameters
    ----------
    algorithms_path : str
        Path to the root folder containing algorithm subdirectories.
    api : object | None, optional
        FastAPI app.
    algorithm_names : list | None, optional
        List of specific algorithm names to deploy.
    args : argparse.Namespace | None

    Returns
    -------
    None
    """

    if algorithm_names is not None:
        if args is not None:
            algos = args.names.split(" ")
            for algo in algos:
                algo_path = os.path.join(algorithms_path, algo)
                if not os.path.isdir(algo_path):
                    print(f"Algorithm {algo} not found.")
                    continue
                if api is not None:
                    deploy_algorithm_from_folder(
                        algo_path, api.state.database_connection
            )
    else:
        for folder_name in os.listdir(algorithms_path):
            algo_path = os.path.join(algorithms_path, folder_name)
            if folder_name == "algorithm_template" or not os.path.isdir(
                algo_path
            ):
                continue
            if api is not None:
                deploy_algorithm_from_folder(
                    algo_path, api.state.database_connection
                )


def run_deployment():
    """
    Run the deployment pipeline.
    """
    args = parse_args()
    settings = get_server_settings(args.config)
    api = build_api(settings, with_lifespan=True)

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
                settings.deploy_algorithms_from,
                api=api,
                algorithm_names=args.names,
                args=args,
            )
        server.should_exit = True
        print("Stopping deployment server")

    else:
        print(
            f"Port {settings.port} is already in use. Assuming server already running."
        )
        deploy_algorithms(
            settings.deploy_algorithms_from,
            api=api,
            algorithm_names=args.names,
            args=args,
        )


if __name__ == "__main__":
    run_deployment()
