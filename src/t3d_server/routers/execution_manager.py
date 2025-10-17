"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from t3d_server.pydantic_models import ExecutionRecord, ResponseMessage
from typing import List
import json

router = APIRouter(
    prefix="/api", tags=["execution-manager"], include_in_schema=False
)


@router.get(
    "/v0/execute-algorithm/all",
    summary="Get all execution records",
    response_model=List[ExecutionRecord],
    responses={500: {"model": ResponseMessage}},
)
async def get_all_execution_records(request: Request) -> List[ExecutionRecord]:
    """
    Get all execution records.

    Returns
    -------
    List[ExecutionRecord]
    """

    database_connection = request.app.state.database_connection
    try:
        execution_records_ids = database_connection.list_objects(
            "execution-store"
        )
        execution_records = database_connection.get_objects(
            "execution-store", execution_records_ids
        )
        return [ExecutionRecord(**json.loads(obj)) for obj in execution_records]
    except:
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to get execution records"},
        )


@router.delete(
    "/v0/execute-algorithm/all",
    summary="Delete all execution records",
    response_model=ResponseMessage,
    responses={500: {"model": ResponseMessage}},
)
async def delete_all_execution_records(request: Request) -> ResponseMessage:
    """
    Delete all execution records.

    Returns
    -------
    ResponseMessage
    """
    database_connection = request.app.state.database_connection
    try:
        execution_records_ids = database_connection.list_objects(
            "execution-store"
        )
        database_connection.delete_objects(
            "execution-store", execution_records_ids
        )
        return ResponseMessage(message="Deleted all execution records")
    except:
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to delete execution records"},
        )


@router.delete(
    "/v0/execute-algorithm/{execution_id}",
    summary="Delete execution record by id",
    response_model=ResponseMessage,
    responses={500: {"model": ResponseMessage}},
)
async def delete_execution_record(
    execution_id: str, request: Request
) -> ResponseMessage:
    """
    Delete execution record by id.

    Parameters
    ----------
    execution_id : str
        The id of the execution record.

    Returns
    -------
    ResponseMessage
    """
    database_connection = request.app.state.database_connection
    try:
        database_connection.delete_objects("execution-store", [execution_id])
        return ResponseMessage(message="Deleted execution record")
    except:
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to delete execution record"},
        )
