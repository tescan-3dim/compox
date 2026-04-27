"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import multiprocessing
import os
import argparse
import sys
import threading

from compox.internal import downloader
from compox.config.server_settings import get_server_settings
from compox.components.api_builder import build_api
from compox.components.server_builder import build_server
from compox.internal.logging import ensure_stdout_stderr
from compox.server_utils import _systray_signal_shutdown

# this is needed for pyinstaller
ensure_stdout_stderr()


def parse_args() -> object:
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
            from compox.internal.ServerSystrayInterface import (
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
    server.logger.debug("Main server loop start")
    first_run = True
    while server.should_restart() or first_run:
        first_run = False
        if server.should_restart():
            server.logger.debug("Resetting server")
            server = build_server(api, settings)
        if systray_imported:
            systray_interface = None
            try:  # this starts server in a thread and runs systray icon with menu
                server.logger.debug("Starting server")
                with server.run_in_thread():
                    systray_interface = ServerSystrayInterface(
                        settings,
                        api,
                        server,
                        server.config,
                    )
                    if os.name == "nt":
                        shutdown_event = threading.Event()
                        systray_exception = []

                        def _run_systray():
                            try:
                                systray_interface.run()
                            except Exception as e:
                                systray_exception.append(e)
                                shutdown_event.set()

                        with _systray_signal_shutdown(
                            server,
                            systray_interface,
                            shutdown_event=shutdown_event,
                        ):
                            systray_thread = threading.Thread(
                                target=_run_systray,
                                daemon=True,
                            )
                            systray_thread.start()
                            while (
                                systray_thread.is_alive()
                                and not server.should_exit
                                and not server.should_restart()
                            ):
                                shutdown_event.wait(0.2)
                            if systray_thread.is_alive():
                                try:
                                    systray_interface.stop()
                                except Exception:
                                    pass
                                systray_thread.join(timeout=5)
                            if systray_exception:
                                raise systray_exception[0]
                    else:
                        with _systray_signal_shutdown(
                            server, systray_interface
                        ):
                            systray_interface.run()
            except KeyboardInterrupt:
                server.logger.info(
                    "Keyboard interrupt received; shutting down server."
                )
                server.should_exit = True
                if systray_interface is not None:
                    try:
                        systray_interface.stop()
                    except Exception:
                        pass
                break
            except Exception as e:
                # unless an exception occurs and server is run "as is"
                print(f"Could no run the server with systray GUI: {e}")
                server.run()
        else:
            server.run()


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        multiprocessing.freeze_support()
    main()
