"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from compox.tasks.TaskHandler import TaskHandler
from compox.database_connection.InMemoryConnection import InMemoryConnection
import sys
import os
import io


class DebuggingTaskHandler(TaskHandler):
    """
    TaskHandler for debugging algorithm runners locally, without the need to have
    a running server. Works in local filesystem instead of database server.

    Parameters
    ----------
    task_id : str
        The task id.
    """

    def __init__(self, task_id: str):
        database_connection = InMemoryConnection()
        database_connection.create_collections(
            ["data-store", "execution-store"]
        )

        super().__init__(task_id, database_connection, database_update=False)

    def fetch_algorithm(
        self, path_to_algorithm: str, device: str = "cpu"
    ) -> object:
        """
        Fetches the algorithm from the local filesystem.

        Parameters
        ----------
        path_to_algorithm : str
            The path to the algorithm.
        device : str
            The device to run the algorithm on.

        Returns
        -------
        object
            The algorithm runner instance.

        Raises
        ------
        ImportError
            If algorithm runner could not be imported.
        """
        # add the path to the algorithm to sys.path
        sys.path.insert(0, path_to_algorithm)
        self.path_to_algorithm = path_to_algorithm
        # import the algorithm runner

        try:
            algorithm_module = __import__("Runner")
        except ImportError:
            raise ImportError(
                f"Could not import the algorithm runner from {path_to_algorithm}"
            )
        sys.path.pop(0)

        runner = algorithm_module.Runner().__new__(algorithm_module.Runner)

        # Initialize the runner without calling __init__
        # This is done to ensure that the algorithm runner is immutable
        # and can be safely used in a multi-threaded environment.
        runner.initialize(device)
        runner._load_assets()

        return runner

    def fetch_asset(self, path_to_asset: str) -> io.BytesIO:
        """
        Fetches the asset from the local filesystem.

        Parameters
        ----------
        path_to_asset : str
            The path to the asset.

        Returns
        -------
        io.BytesIO
            The asset as a BytesIO object.
        """

        path_to_asset = os.path.join(self.path_to_algorithm, path_to_asset)

        with open(path_to_asset, "rb") as f:
            asset_bytes = f.read()

        bytes_io = io.BytesIO(asset_bytes)
        return bytes_io
