"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import os
import argparse
import sys

from t3d_server.internal import downloader
from t3d_server.config.server_settings import get_server_settings
from t3d_server.components.api_builder import build_api
from t3d_server.components.server_builder import build_server
from t3d_server.internal.logging import ensure_stdout_stderr

# this is needed for pyinstaller
ensure_stdout_stderr()


def parse_args():
    """
    Argument parser for the server.

    Returns
    -------
    object
        The parsed arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        help="Path to server configuration yaml file. If None, use defaults specified in server_config.py.",
        default=(
            os.path.join(sys._MEIPASS, "app_server.yaml")
            if hasattr(sys, "_MEIPASS")
            else None
        ),
        required=False,
    )
    args, _ = parser.parse_known_args()
    return args


def main():
    args = parse_args()
    settings = get_server_settings(args.config)

    if settings.gui.use_systray:
        try:
            from t3d_server.internal.ServerSystrayInterface import (
                ServerSystrayInterface,
            )

            systray_imported = True
        except ImportError as e:
            systray_imported = False
            print(f"Could not import systray: {e}")
    else:
        systray_imported = False

    # prepare storage
    if (
        settings.storage.backend_settings.provider == "minio"
        and settings.storage.backend_settings.start_instance
    ):

        os.makedirs(
            settings.storage.backend_settings.storage_path, exist_ok=True
        )
        downloader.get_minio(settings)

    # build components
    api = build_api(settings, with_lifespan=True)
    server = build_server(api, settings)

    # server start/restart
    server.logger.info("Main server loop start")
    first_run = True
    while server.should_restart() or first_run:
        first_run = False
        if server.should_restart():
            server.logger.info("Resetting server")
            server = build_server(api, settings)
        if systray_imported:
            try:  # this starts server in a thread and runs systray icon with menu
                server.logger.info("Starting server")
                with server.run_in_thread():
                    ServerSystrayInterface(
                        settings,
                        api,
                        server,
                        server.config,
                    ).run()
            except Exception as e:
                # unless an exception occurs and server is run "as is"
                print(f"Could no run the server with systray GUI: {e}")
                server.run()
        else:
            server.run()


if __name__ == "__main__":
    main()
