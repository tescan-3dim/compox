"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import os
import subprocess
import threading

from loguru import logger

from compox.config.server_settings import Settings


class MinIOWrapper:

    def __init__(self, settings: Settings):
        self.user = settings.storage.access_key_id
        self.password = settings.storage.secret_access_key
        self.executable_path = settings.storage.backend_settings.executable_path
        self.storage_path = settings.storage.backend_settings.storage_path
        self.address = settings.storage.backend_settings.port
        self.console_address = settings.storage.backend_settings.console_port
        self.process = None

    @staticmethod
    def _stream_logger(stream, default_level="INFO", prefix="MINIO"):
        """
        Stream logger for minio subprocess. It reads the stream line by line and
        logs it with the appropriate level.
        """
        minio_logger = logger.bind(log_type=prefix)
        for line in iter(stream.readline, ""):
            if line:
                text = line.rstrip()
                level = (
                    "ERROR"
                    if any(
                        word in text.lower()
                        for word in ["error", "fatal", "panic"]
                    )
                    else default_level
                )
                minio_logger.log(level, text)
        stream.close()

    def start(self, process_factory=subprocess.Popen) -> subprocess.Popen:
        env = os.environ.copy()
        env["MINIO_ROOT_USER"] = self.user
        env["MINIO_ROOT_PASSWORD"] = self.password

        process = process_factory(
            [
                self.executable_path,
                "server",
                self.storage_path,
                "--console-address",
                f":{str(self.console_address)}",
                "--address",
                f":{str(self.address)}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,  # <-- critical
            bufsize=1,  # line buffered (works only with text mode)
            env=env,
        )

        threading.Thread(
            target=self._stream_logger,
            args=(process.stderr, "INFO"),
            daemon=True,
        ).start()

        return process
