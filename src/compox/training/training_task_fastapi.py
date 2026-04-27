"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import json
from datetime import datetime
from loguru import logger
from typing import Any

from compox.tasks.TaskHandler import TaskStoppedException
from compox.training.TrainingHandler import TrainingHandler
from compox.training.TempStore import TempStore
from compox.internal.CUDAMemoryManager import CUDAMemoryManager
from compox.pydantic_models import TrainingRecord
from compox.database_connection.S3Connection import S3Connection


@logger.catch
def training_task_fastapi(
    database_connection: S3Connection,
    training_record: type[TrainingRecord],
) -> Any:
    """
    Fastapi background task for the execution of an algorithm. This task is
    executed by a fastapi background tasks.

    Parameters
    ----------
    database_connection : S3Connection
        The database connection object instance. Must inherit from the
        BaseConnection class and implement the required methods.
    training_record : type[TrainingRecord]
        The training record.

    Returns
    -------
    Any
        Current training record from database.
    """

    with CUDAMemoryManager(), TempStore() as temp_store:
        training_handler = TrainingHandler(
            training_record.training_id,
            database_connection=database_connection,
            database_update=True,
            temp_store=temp_store,
        )
        training_handler.set_as_current_handler()
        training_handler.logger.info("Fetching algorithm...")
        start = datetime.now()
        runner = training_handler.fetch_algorithm(
            training_record.algorithm_id,
            checkpoint_id=training_record.checkpoint_id,
            algorithm_minor_version=training_record.algorithm_minor_version,
        )
        training_handler.logger.info(
            "Algorithm fetched in {} seconds.".format(
                (datetime.now() - start).total_seconds()
            )
        )
        try:
            runner.run_training(
                training_record.training_data,
                args=training_record.additional_parameters,
            )
        except TaskStoppedException:
            logger.info("Training task was interrupted by stop request.")

    # get current training record from database
    training_record = json.loads(
        database_connection.get_objects(
            "training-store", [training_record.training_id]
        )[0]
    )

    return training_record
