"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import json
from datetime import datetime

from compox.database_connection.BaseConnection import BaseConnection


class StopRequest:
    """
    Class representing a stop request for an ongoing execution or training run.

    Parameters
    ----------
    task_id : str
        The ID of the execution or training task to be stopped.
    database_connection : BaseConnection
        The database connection instance.
    exist_check_buffer_seconds : int
        Minimum time in seconds between existence checks of the stop
        request. Default is 0.
    """

    def __init__(
        self,
        task_id: str,
        database_connection: BaseConnection,
        exist_check_buffer_seconds: int = 0,
    ):
        self.task_id = task_id
        self.database_connection = database_connection
        self.exist_check_buffer_seconds = exist_check_buffer_seconds
        self.acknowledged = False
        self._last_exist_check_time = None
        self._exists_cache = None

    def submit(self):
        """
        Submits a stop request for the execution or training task.
        """

        obj = json.dumps(
            {
                "task_id": self.task_id,
                "timestamp": str(datetime.now()),
            }
        )

        self.database_connection.put_objects(
            "stop-requests",
            [self.task_id],
            [obj],
        )

    def delete(self):
        """
        Deletes a stop request for the execution or training task.
        """
        self.database_connection.delete_objects(
            "stop-requests",
            [self.task_id],
        )

    def acknowledge(self):
        """
        Acknowledges the stop request for the execution.
        """
        self.acknowledged = True

    def is_acknowledged(self) -> bool:
        """
        Checks if the stop request has been acknowledged.

        Returns
        -------
        bool
            True if the stop request has been acknowledged, otherwise False.
        """
        return self.acknowledged

    def exists(self) -> bool:
        """
        Checks if a stop request exists for the execution. Uses buffering to
        limit the frequency of existence checks.

        Returns
        -------
        bool
            True if the stop request exists, otherwise False.
        """
        if self.exist_check_buffer_seconds > 0:
            if self._last_exist_check_time is not None:
                elapsed_time = (
                    datetime.now() - self._last_exist_check_time
                ).total_seconds()
                if elapsed_time < self.exist_check_buffer_seconds:
                    return self._exists_cache
            self._last_exist_check_time = datetime.now()
        exists = self.database_connection.check_objects_exist(
            "stop-requests",
            [self.task_id],
        )[0]

        self._exists_cache = exists
        return exists


if __name__ == "__main__":
    from compox.database_connection.InMemoryConnection import InMemoryConnection

    db_conn = InMemoryConnection()
    stop_request = StopRequest("test_execution", db_conn)
    print("Exists:", stop_request.exists())
    stop_request.submit()
    print("Stop request posted.")
    print("Exists:", stop_request.exists())
    stop_request.delete()
    print("Stop request deleted.")
    print("Exists:", stop_request.exists())

    # check buffering
    stop_request = StopRequest(
        "test_execution", db_conn, exist_check_buffer_seconds=5
    )
    print("Exists (buffered):", stop_request.exists())
    stop_request.submit()
    print("Stop request posted.")
    print("Exists (buffered):", stop_request.exists())
    stop_request.delete()
    print("Stop request deleted.")
    print("Exists (buffered):", stop_request.exists())
    print("Waiting 6 seconds to test buffering...")
    import time

    time.sleep(6)
    print("Exists (buffered):", stop_request.exists())
    stop_request.delete()
    print("Stop request deleted.")
    print("Exists (buffered):", stop_request.exists())
