"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import json
from celery import shared_task, Task
from datetime import datetime
from loguru import logger
from typing import Any

from compox.tasks.TaskHandler import TaskHandler
from compox.internal.CUDAMemoryManager import CUDAMemoryManager
from compox.session.TaskSession import TaskSession
from compox.pydantic_models import ExecutionRecord


@logger.catch
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=0,
    name="task",
)
def execution_task_celery(
    self: Task,
    algorithm_id: str,
    input_dataset_ids: list[str],
    message: str,
    args: dict = {},
) -> Any:
    """
    Celery task for the execution of an algorithm. This task is executed by a
    celery worker.

    Parameters
    ----------
    self : Task
        The celery task object.
    algorithm_id : str
        The algorithm id.
    input_dataset_ids : list[str]
        The input dataset id.
    message : str
        The message.
    args : dict
        The arguments of the algorithm.

    Returns
    -------
    Any
        Current execution record from database.
    """

    execution_record = ExecutionRecord.model_validate_json(message)

    with CUDAMemoryManager(), TaskSession(
        session_token=execution_record.session_token, not_implemented=True
    ) as task_session:
        task_handler = TaskHandler(
            execution_record.execution_id,
            self.app.database_connection,
            database_update=True,
            task_session=task_session,
        )
        task_handler.set_as_current_task_handler()
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
        self.app.database_connection.get_objects(
            "execution-store", [execution_record.execution_id]
        )[0]
    )

    return execution_record
