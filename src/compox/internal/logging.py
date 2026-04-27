"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import logging
import sys
import os
import inspect
import re
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
        self.logger = logger.bind(log_type=self.prefix or "DEFAULT")

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
        bound_logger = self.logger.bind(source_logger=record.name)
        if self.debug:
            bound_logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )
        else:
            if level != "DEBUG":
                bound_logger.opt(depth=depth, exception=record.exc_info).log(
                    level, record.getMessage()
                )


def ensure_stdout_stderr():
    if getattr(sys, "frozen", False):  # PyInstaller sets sys.frozen = True
        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w")
        if sys.stderr is None:
            sys.stderr = open(os.devnull, "w")


# setup filters and handlers for the logger
_POLLING_ACCESS_PATTERNS = (
    re.compile(r"GET /api/v\d+/executions/[^ ]+"),
    re.compile(r"GET /api/v\d+/training/[^ ]+"),
    re.compile(r"GET /api/v\d+/deploy/[^ ]+"),
    re.compile(r"POST /api/v\d+/files/?"),
    re.compile(r"DELETE /api/v\d+/files/[^ ]+"),
    re.compile(r"GET /api/v\d+/files/[^ ]+"),
)
_DEBUG_CONSOLE_LEVELS = {"TRACE", "DEBUG"}


def _is_polling_access_log(message: str) -> bool:
    """
    Return True when a uvicorn access log line represents a high-frequency
    polling request that should not be shown on the interactive console.
    """
    return any(pattern.search(message) for pattern in _POLLING_ACCESS_PATTERNS)


def _should_emit_console_record(
    record: dict, console_level: str = "INFO"
) -> bool:
    """
    Decide whether a log record should be shown on the interactive console.

    Detailed request logs remain available in the file sink, but high-frequency
    polling requests are suppressed on the console to keep task lifecycle logs
    readable.
    """
    if console_level.upper() in _DEBUG_CONSOLE_LEVELS:
        return True

    extra = record["extra"]
    if extra.get("log_type") == "MINIO" and record["level"].name != "ERROR":
        return False
    if extra.get("source_logger") == "uvicorn.access":
        return not _is_polling_access_log(record["message"])
    return True


def configure_logging(
    log_path: str,
    rotation_mb: int = 8,
    retention_days: int = 10,
    debug: bool = False,
    console_level: str = "INFO",
    file_level: str = "INFO",
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
    console_level : str, optional
        The minimum log level emitted to the console sink. The default is "INFO".
    file_level : str, optional
        The minimum log level emitted to the file sink. The default is "INFO".


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
    console_log_format = (
        "<green>{time:YYYY-MM-DD at HH:mm:ss}</green> | "
        "<bold><white>{extra[log_type]:<8}</white></bold> | "
        "<level>{level: <7}</level> | "
        "<bold><magenta>{extra[algorithm]}</magenta></bold> "
        "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "{message}"
    )
    file_log_format = (
        "{time:YYYY-MM-DD at HH:mm:ss} | "
        "{extra[log_type]:<8} | "
        "{level: <7} | "
        "{extra[algorithm]} {module}:{function}:{line} - "
        "{message}"
    )

    # remove default handlers
    logger.remove()

    # add standard output handler (the default is to log to stderr, this can be changed)
    # but not if the application is frozen (e.g. PyInstaller)
    if not getattr(sys, "frozen", False):  # PyInstaller sets sys.frozen = True
        logger.add(
            sys.__stderr__,
            level=console_level,
            format=console_log_format,
            colorize=True,
            filter=lambda record: _should_emit_console_record(
                record, console_level
            ),
        )

    # this configures the log file handler as a secondary sink for log messages
    logger.add(
        log_path,
        rotation=f"{rotation_mb} MB",
        retention=f"{retention_days} days",
        level=file_level,
        format=file_log_format,
    )

    # this configures the extra field default value for the log messages
    # this should be modified in the event we want to add more fields to the log messages
    logger.configure(
        extra={"log_type": "DEFAULT", "algorithm": "", "source_logger": ""}
    )

    # this configures the default log level for the logger
    logger_object = logger.bind(log_type="DEFAULT")
    logger_object.info("Logger successfully configured.")

    return logger_object
