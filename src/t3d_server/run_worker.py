"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import argparse
from t3d_server.server_utils import get_subprocess_fn
from t3d_server.config.server_settings import get_server_settings
from t3d_server.internal.logging import configure_logging
from t3d_server.components.celery_builder import build_celery
from t3d_server.tasks.celery_task import execution_task_celery  # noqa F401


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
        default=None,
        required=False,
    )
    args, _ = parser.parse_known_args()
    return args


def main():
    """
    Main function to run the Celery worker.
    """
    args = parse_args()
    settings = get_server_settings(args.config)
    _ = configure_logging(log_path=settings.log_path)

    if settings.inference.backend_settings.executor == "celery":
        celery_app = build_celery(settings)

        if settings.inference.backend_settings.run_flower:
            subprocess_fn = get_subprocess_fn()
            _ = subprocess_fn(
                [
                    "celery",
                    f"--broker={settings.inference.backend_settings.broker_url}",
                    "flower",
                    f"--port={settings.inference.backend_settings.flower_port}",
                ]
            )
        celery_app.worker_main(
            [
                "worker",
                "--loglevel=info",
                "--pool=solo",
                f"-n {settings.inference.backend_settings.worker_name}",
            ]
        )
    else:
        print(
            f"Unsupported executor: {settings.inference.backend_settings.executor}"
        )


if __name__ == "__main__":
    main()
