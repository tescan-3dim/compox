from compox.internal.logging import (
    _is_polling_access_log,
    _should_emit_console_record,
)
from compox.config.server_settings import Settings


def test_polling_access_log_detection():
    assert _is_polling_access_log(
        '127.0.0.1:12345 - "GET /api/v0/executions/test-id HTTP/1.1" 200'
    )
    assert _is_polling_access_log(
        '127.0.0.1:12345 - "GET /api/v0/training/test-id HTTP/1.1" 200'
    )
    assert _is_polling_access_log(
        '127.0.0.1:12345 - "GET /api/v0/deploy/test-id HTTP/1.1" 200'
    )
    assert _is_polling_access_log(
        '127.0.0.1:12345 - "POST /api/v0/files HTTP/1.1" 200'
    )
    assert _is_polling_access_log(
        '127.0.0.1:12345 - "GET /api/v0/files/test-id HTTP/1.1" 200'
    )
    assert _is_polling_access_log(
        '127.0.0.1:12345 - "DELETE /api/v0/files/test-id HTTP/1.1" 200'
    )
    assert not _is_polling_access_log(
        '127.0.0.1:12345 - "POST /api/v0/execute-algorithm HTTP/1.1" 200'
    )


def test_console_filter_suppresses_polling_access_logs():
    record = {
        "message": (
            '127.0.0.1:12345 - '
            '"GET /api/v0/executions/test-id HTTP/1.1" 200'
        ),
        "extra": {"source_logger": "uvicorn.access"},
    }

    assert not _should_emit_console_record(record)


def test_console_filter_keeps_non_polling_access_logs():
    record = {
        "message": (
            '127.0.0.1:12345 - '
            '"POST /api/v0/execute-algorithm HTTP/1.1" 200'
        ),
        "extra": {"source_logger": "uvicorn.access"},
    }

    assert _should_emit_console_record(record)


def test_console_filter_suppresses_file_upload_access_logs():
    record = {
        "message": (
            '127.0.0.1:12345 - "POST /api/v0/files HTTP/1.1" 200'
        ),
        "extra": {"source_logger": "uvicorn.access"},
        "level": type("Level", (), {"name": "INFO"})(),
    }

    assert not _should_emit_console_record(record)


def test_console_filter_keeps_task_logs():
    record = {
        "message": "Algorithm fetched in 0.05 seconds.",
        "extra": {"source_logger": "", "log_type": "TASK"},
        "level": type("Level", (), {"name": "INFO"})(),
    }

    assert _should_emit_console_record(record)


def test_console_filter_suppresses_minio_info_logs():
    record = {
        "message": "API: http://127.0.0.1:5483",
        "extra": {"source_logger": "", "log_type": "MINIO"},
        "level": type("Level", (), {"name": "INFO"})(),
    }

    assert not _should_emit_console_record(record)


def test_console_filter_keeps_minio_error_logs():
    record = {
        "message": "FATAL Unable to start MinIO.",
        "extra": {"source_logger": "", "log_type": "MINIO"},
        "level": type("Level", (), {"name": "ERROR"})(),
    }

    assert _should_emit_console_record(record)


def test_console_filter_keeps_polling_logs_in_debug_mode():
    record = {
        "message": (
            '127.0.0.1:12345 - '
            '"GET /api/v0/executions/test-id HTTP/1.1" 200'
        ),
        "extra": {"source_logger": "uvicorn.access"},
        "level": type("Level", (), {"name": "INFO"})(),
    }

    assert _should_emit_console_record(record, console_level="DEBUG")


def test_console_filter_keeps_minio_info_logs_in_debug_mode():
    record = {
        "message": "API: http://127.0.0.1:5483",
        "extra": {"source_logger": "", "log_type": "MINIO"},
        "level": type("Level", (), {"name": "INFO"})(),
    }

    assert _should_emit_console_record(record, console_level="DEBUG")


def test_settings_accept_logging_levels():
    settings = Settings(
        logging={
            "console_level": "DEBUG",
            "file_level": "INFO",
        }
    )

    assert settings.logging.console_level == "DEBUG"
    assert settings.logging.file_level == "INFO"
