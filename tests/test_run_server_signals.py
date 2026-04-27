"""
Copyright 2026 Tescan group, a.s.
All rights reserved
"""

import signal

from compox.run_server import _systray_signal_shutdown


class _DummyLogger:
    """Minimal logger stub required by the shutdown helper."""

    def info(self, _message):
        return None


class _DummyServer:
    """Small stand-in for the Uvicorn server object used in production."""

    def __init__(self):
        self.should_exit = False
        self.logger = _DummyLogger()


class _DummySystray:
    """Records whether the shutdown path attempted to stop the systray."""

    def __init__(self):
        self.stop_calls = 0

    def stop(self):
        self.stop_calls += 1


def test_systray_signal_shutdown_requests_exit_and_restores_handlers():
    """SIGINT should request shutdown once and leave global signal state clean."""

    server = _DummyServer()
    systray = _DummySystray()

    original_sigint = signal.getsignal(signal.SIGINT)

    with _systray_signal_shutdown(server, systray):
        handler = signal.getsignal(signal.SIGINT)
        assert callable(handler)
        handler(signal.SIGINT, None)
        assert server.should_exit is True
        assert systray.stop_calls == 1

    restored_sigint = signal.getsignal(signal.SIGINT)
    assert restored_sigint == original_sigint


def test_systray_signal_shutdown_sets_optional_shutdown_event():
    """The helper should also set an external shutdown event when provided."""

    import threading

    server = _DummyServer()
    systray = _DummySystray()
    shutdown_event = threading.Event()

    with _systray_signal_shutdown(
        server, systray, shutdown_event=shutdown_event
    ):
        handler = signal.getsignal(signal.SIGINT)
        assert callable(handler)
        handler(signal.SIGINT, None)

    assert shutdown_event.is_set() is True
