"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import logging
import sys
import os
import inspect
from loguru import logger


class InterceptHandler(logging.Handler):
    def __init__(self, debug: bool = False, prefix: str = ""):
        """
        InterceptHandler constructor. This handler intercepts log messages from the
        standard logging module and redirects them to the loguru logger.

        It is used to capture log messages from the standard library and third-party
        libraries that use the standard logging module.

        Parameters

        ----------
        debug : bool, optional
            If True, set the log level to DEBUG. The default is False.
        prefix : str, optional
            The prefix to add to the log message. The default is "".
        """
        super().__init__()
        self.debug = debug
        self.prefix = prefix
        self.logger = logger.bind(log_type=self.prefix)

    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where the log originated
        frame, depth = inspect.currentframe(), 0
        while frame:
            filename = frame.f_code.co_filename
            is_logging = filename == logging.__file__
            is_frozen = "importlib" in filename and "_bootstrap" in filename
            if depth > 0 and not (is_logging or is_frozen):
                break
            frame = frame.f_back
            depth += 1

        # Log with Loguru, include exception info if any
        if self.debug:
            self.logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )
        else:
            if level != "DEBUG":
                self.logger.opt(depth=depth, exception=record.exc_info).log(
                    level, record.getMessage()
                )


def ensure_stdout_stderr():
    if getattr(sys, "frozen", False):  # PyInstaller sets sys.frozen = True
        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w")
        if sys.stderr is None:
            sys.stderr = open(os.devnull, "w")


def configure_logging(
    log_path: str,
    rotation_mb: int = 8,
    retention_days: int = 10,
    debug: bool = False,
):
    """
    Configure the loguru logger.

    Parameters
    ----------
    log_path : str
        The path to the log file.
    rotation_mb : int, optional
        The size of the log file in MB before it is rotated. The default is 8.
    debug : bool, optional
            If True, set the log level to DEBUG. The default is False.


    Returns
    -------
    object
        The logger object.
    """
    # intercept all standard logging calls and redirect them to loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # intercept uvicorn logs and redirect them to loguru
    logging.getLogger("uvicorn").handlers = [InterceptHandler(prefix="UVICORN")]
    logging.getLogger("uvicorn.access").handlers = [
        InterceptHandler(prefix="UVICORN")
    ]
    logging.getLogger("uvicorn.error").handlers = [
        InterceptHandler(prefix="UVICORN")
    ]

    logging.getLogger("uvicorn").propagate = False
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("uvicorn.error").propagate = False

    # intercept celery loggers and redirect them to loguru
    celery_loggers = [
        "celery.worker.job",
        "celery.worker.strategy",
        "celery.worker.consumer",
        "celery.worker",
        "celery.app.trace",
        "celery.app.trace",
    ]
    for logger_name in celery_loggers:
        logging.getLogger(logger_name).handlers = [
            InterceptHandler(prefix="CELERY")
        ]
        logging.getLogger(logger_name).propagate = False

    # format log messages
    log_format = (
        "<green>{time:YYYY-MM-DD at HH:mm:ss}</green> | "
        "<bold><white>{extra[log_type]:<8}</white></bold> | "
        "<level>{level: <7}</level> | "
        "<bold><magenta>{extra[algorithm]}</magenta></bold> <cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "{message}"
    )

    # remove default handlers
    logger.remove()

    # add standard output handler (the default is to log to stderr, this can be changed)
    # but not if the application is frozen (e.g. PyInstaller)
    if not getattr(sys, "frozen", False):  # PyInstaller sets sys.frozen = True
        logger.add(
            sys.__stderr__, level="INFO", format=log_format, colorize=True
        )

    # this configures the log file handler as a secondary sink for log messages
    logger.add(
        log_path,
        rotation=f"{rotation_mb} MB",
        retention=f"{retention_days} days",
        level="INFO",
        format=log_format,
    )

    # this configures the extra field default value for the log messages
    # this should be modified in the event we want to add more fields to the log messages
    logger.configure(extra={"log_type": "DEFAULT", "algorithm": ""})

    # this configures the default log level for the logger
    logger_object = logger.bind(log_type="DEFAULT")
    logger_object.info("Logger successfully configured.")

    return logger_object
