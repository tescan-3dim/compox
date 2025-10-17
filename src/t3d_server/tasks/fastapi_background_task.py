"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import json
from datetime import datetime
from loguru import logger

# from algorithms.aligner.Runner import Runner
from t3d_server.tasks.TaskHandler import TaskHandler
from t3d_server.internal.CUDAMemoryManager import CUDAMemoryManager
from t3d_server.session.TaskSession import TaskSession
from t3d_server.pydantic_models import ExecutionRecord
from t3d_server.database_connection.S3Connection import S3Connection


@logger.catch
def execution_task_fastapi(
    database_connection: S3Connection,
    algorithm_id: str,
    input_dataset_ids: str,
    execution_record: type[ExecutionRecord],
    args: dict = {},
):
    """
    Fastapi background task for the execution of an algorithm. This task is
    executed by a fastapi background tasks.

    Parameters
    ----------
    algorithm_id : str
        The id of the algorithm.
    input_dataset_id : str
        The id of the input dataset.
    execution_record : ExecutionRecord
        The execution record.
    args : dict
        The arguments of the algorithm.
    """

    with CUDAMemoryManager(), TaskSession(
        session_token=execution_record.session_token
    ) as task_session:
        task_handler = TaskHandler(
            execution_record.execution_id,
            database_connection=database_connection,
            database_update=True,
            task_session=task_session,
        )
        task_handler.set_as_current_task_handler()
        task_handler.logger.info("Fetching algorithm...")
        start = datetime.now()
        runner = task_handler.fetch_algorithm(
            algorithm_id,
            execution_device_override=execution_record.execution_device_override,
        )
        task_handler.logger.info(
            "Algorithm fetched in {} seconds.".format(
                (datetime.now() - start).total_seconds()
            )
        )

        runner.run(
            {
                "input_dataset_ids": input_dataset_ids,
            },
            args=args,
        )

    # get current execution record from database
    execution_record = json.loads(
        database_connection.get_objects(
            "execution-store", [execution_record.execution_id]
        )[0]
    )

    return execution_record
