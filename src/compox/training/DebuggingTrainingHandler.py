"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import sys
import os
import io

from compox.training.TrainingHandler import TrainingHandler
from compox.training.TempStore import TempStore
from compox.database_connection.InMemoryConnection import InMemoryConnection
from compox.algorithm_utils.BaseRunner import BaseRunner
from compox.training.AlgorithmCheckpoint import AlgorithmCheckpoint


class DebuggingTrainingHandler(TrainingHandler):
    """
    TrainingHandler for debugging algorithm runners locally, without the need to have
    a running server. Works in local filesystem instead of database server.

    Parameters
    ----------
    training_id : str
        The training ID.
    temp_store : TempStore
        The temporary store for training data.
    """

    def __init__(
        self,
        database_connection: InMemoryConnection,
        training_id: str,
        temp_store: TempStore,
    ):

        database_connection.create_collections(
            [
                "data-store",
                "execution-store",
                "training-store",
                "sample-store",
                "training-checkpoint-store",
            ]
        )

        super().__init__(
            training_id,
            database_connection,
            temp_store=temp_store,
        )

    def fetch_algorithm(
        self,
        path_to_algorithm: str,
        device: str = "cpu",
        checkpoint_id: str | None = None,
    ) -> BaseRunner:
        """
        Fetches the algorithm from the local filesystem.

        Parameters
        ----------
        path_to_algorithm : str
            The path to the algorithm.
        device : str
            The device to run the algorithm on.
        checkpoint_id : str | None
            The checkpoint id to load the algorithm from.

        Returns
        -------
        BaseRunner
            The algorithm runner instance.

        Raises
        ------
        ImportError
            If algorithm runner could not be imported.
        """
        self.checkpoint_id = checkpoint_id
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

        runner = object.__new__(algorithm_module.Runner)

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

        if self.checkpoint_id is not None:
            algorithm_checkpoint = AlgorithmCheckpoint(
                self.database_connection, self.checkpoint_id
            )

            asset_dict = algorithm_checkpoint.checkpoint_manifest.assets
            if path_to_asset in asset_dict.keys():
                bytes_io = self.database_connection.get_objects(
                    "asset-store",
                    [asset_dict[path_to_asset]],
                )[0]
        else:
            path_to_asset = os.path.join(self.path_to_algorithm, path_to_asset)

            with open(path_to_asset, "rb") as f:
                asset_bytes = f.read()

            bytes_io = io.BytesIO(asset_bytes)
        return bytes_io
