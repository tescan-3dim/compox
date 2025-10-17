"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from compox.pydantic_models import (
    ExecutionRecord,
    ExecutionResponse,
    IncomingExecutionRequest,
    ResponseMessage,
)
import json
from datetime import datetime
from compox.server_utils import generate_uuid, find_algorithm_by_id

router = APIRouter(prefix="/api", tags=["execution-controller"])


# post inference request to torchserve
@router.post(
    "/v0/execute-algorithm",
    summary="Executes an algorithm on a dataset",
    response_model=ExecutionResponse,
    responses={
        500: {"model": ResponseMessage},
        404: {"model": ResponseMessage},
    },
)
def execute_algorithm(
    request: Request,
    incoming_execution_request: IncomingExecutionRequest,
) -> ExecutionResponse:
    """
    Executes an algorithm on a dataset.

    Parameters
    ----------
    request : Request
        The request.
    incoming_execution_request : IncomingExecutionRequest
        The incoming execution request.

    Returns
    -------
    ExecutionResponse
        The execution response.

    Raises
    ------
    Exception
        If the server backend is not supported or saving the execution record fails.
    """
    execution_id = generate_uuid()
    database_connection = request.app.state.database_connection
    settings = request.app.state.settings
    # check if input datasets exist
    files_exist = database_connection.check_objects_exist(
        "data-store", incoming_execution_request.input_dataset_ids
    )
    if False in files_exist:
        not_found_files = [
            incoming_execution_request.input_dataset_ids[i]
            for i in range(len(files_exist))
            if not files_exist[i]
        ]
        return JSONResponse(
            status_code=404,
            content={
                "detail": "Input datasets with the following identifiers not found: {}".format(
                    "\n".join(not_found_files)
                )
            },
        )

    # check if algorithm exists
    _, algorithm_id, _, _, _ = find_algorithm_by_id(
        incoming_execution_request.algorithm_id,
        database_connection.list_objects("algorithm-store"),
    )
    if algorithm_id is None:
        return JSONResponse(
            status_code=404,
            content={"detail": "Algorithm not found"},
        )
    # save execution record to db
    execution_record = ExecutionRecord(
        execution_id=execution_id,
        algorithm_id=incoming_execution_request.algorithm_id,
        input_dataset_ids=incoming_execution_request.input_dataset_ids,
        execution_device_override=incoming_execution_request.execution_device_override,
        additional_parameters=incoming_execution_request.additional_parameters,
        session_token=incoming_execution_request.session_token,
        output_dataset_ids=[],
        status="PENDING",
        progress=0,
        time_started=str(datetime.now()),
        time_completed="",
        log="",
    )
    try:
        database_connection.put_objects(
            "execution-store",
            [execution_id],
            [json.dumps(execution_record.model_dump())],
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Failed to save execution record: {e}"},
        )

    args = incoming_execution_request.additional_parameters
    if settings.inference.backend_settings.executor == "celery":
        request.app.state.executor.send_task(
            "task",
            args=[
                algorithm_id,
                incoming_execution_request.input_dataset_ids,
                json.dumps(execution_record.model_dump()),
                args,
            ],
            task_id=execution_id,
            retries=2
        )
    elif (
        settings.inference.backend_settings.executor
        == "fastapi_background_tasks"
    ):
        from compox.tasks.fastapi_background_task import (
            execution_task_fastapi,
        )

        request.app.state.executor.submit(
            execution_task_fastapi,
            database_connection,
            algorithm_id,
            incoming_execution_request.input_dataset_ids,
            execution_record,
            args,
        )
    else:
        raise Exception(
            "Server backend {} not supported:".format(
                settings.inference.backend_settings.executor
            )
        )

    return ExecutionResponse(execution_id=execution_id)


@router.get(
    "/v0/executions/{id}",
    summary="Get execution record by id",
    response_model=ExecutionRecord,
    responses={500: {"model": ResponseMessage}},
)
async def get_execution_record(id: str, request: Request) -> ExecutionRecord:
    """
    Get execution record by id.

    Parameters
    ----------
    id : str
        The id of the execution record.

    request : Request
        The request.

    Returns
    -------
    ExecutionRecord
        The execution record.
    """
    database_connection = request.app.state.database_connection
    try:
        object_exists = database_connection.check_objects_exist(
            "execution-store", [id]
        )[0]
        if not object_exists:
            return JSONResponse(
                status_code=404,
                content={"detail": "Execution record not found"},
            )
        return ExecutionRecord(
            **json.loads(
                database_connection.get_objects("execution-store", [id])[0]
            )
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Failed to get execution record: {e}"},
        )
