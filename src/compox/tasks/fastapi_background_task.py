"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import json
from datetime import datetime
from loguru import logger
from typing import Any

from compox.tasks.TaskHandler import TaskHandler
from compox.tasks.TaskHandler import TaskStoppedException
from compox.internal.CUDAMemoryManager import CUDAMemoryManager
from compox.session.TaskSession import TaskSession
from compox.pydantic_models import ExecutionRecord
from compox.database_connection.S3Connection import S3Connection


@logger.catch
def execution_task_fastapi(
    database_connection: S3Connection,
    execution_record: type[ExecutionRecord],
    emergency_record_store=None,
) -> Any:
    """
    Fastapi background task for the execution of an algorithm. This task is
    executed by a fastapi background tasks.

    Parameters
    ----------
    database_connection : S3Connection
        The database connection object instance. Must inherit from the
        BaseConnection class and implement the required methods.
    execution_record : type[ExecutionRecord]
        The execution record.

    Returns
    -------
    Any
        Current execution record from database.
    """

    with CUDAMemoryManager(), TaskSession(
        session_token=execution_record.session_token
    ) as task_session:
        task_handler = TaskHandler(
            execution_record.execution_id,
            database_connection=database_connection,
            database_update=True,
            task_session=task_session,
            emergency_record_store=emergency_record_store,
        )
        task_handler.set_as_current_handler()
        task_handler.logger.info("Fetching algorithm...")
        start = datetime.now()
        runner = task_handler.fetch_algorithm(
            execution_record.algorithm_id,
            execution_device_override=execution_record.execution_device_override,
            checkpoint_id=execution_record.checkpoint_id,
            algorithm_minor_version=execution_record.algorithm_minor_version,
        )
        task_handler.logger.info(
            "Algorithm fetched in {} seconds.".format(
                (datetime.now() - start).total_seconds()
            )
        )
        try:
            runner.run(
                {
                    "input_dataset_ids": execution_record.input_dataset_ids,
                },
                args=execution_record.additional_parameters,
            )
        except TaskStoppedException:
            logger.info("Execution was interrupted by stop request.")

    # get current execution record from database
    execution_record = json.loads(
        database_connection.get_objects(
            "execution-store", [execution_record.execution_id]
        )[0]
    )

    return execution_record
