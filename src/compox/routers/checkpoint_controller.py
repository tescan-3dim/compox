"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from typing import List, Optional

from compox.training.AlgorithmCheckpoint import AlgorithmCheckpoint
from compox.pydantic_models import (
    ResponseMessage,
    AlgorithmCheckpointRecord,
)

router = APIRouter(prefix="/api", tags=["checkpoint-controller"])


@router.get(
    "/v0/checkpoint/all",
    summary="Returns all samples filtered by tag query parameters",
    response_model=List[AlgorithmCheckpointRecord],
    responses={
        500: {"model": ResponseMessage},
        404: {"model": ResponseMessage},
    },
)
async def list_checkpoints(
    request: Request,
    positive_tags: Optional[List[str]] = Query([]),
    negative_tags: Optional[List[str]] = Query([]),
) -> List[AlgorithmCheckpointRecord]:
    """
    Returns all checkpoints fulfilling criteria.

    Parameters
    ----------
    request : Request
        The request.
    positive_tags : List[str] | None
        A list of tags the sample must have.
    negative_tags : List[str] | None
        A list of tags the sample must not have.

    Returns
    -------
    List[AlgorithmCheckpointRecord]
        The list of checkpoints.
    """
    database_connection = request.app.state.database_connection

    try:
        # get all samples
        all_samples = database_connection.list_objects(
            "algorithm-checkpoint-store"
        )

        if len(all_samples) == 0:
            return JSONResponse(
                status_code=404,
                content={"detail": "No samples found in the sample store"},
            )

        checkpoints = []
        for key in all_samples:
            algorithm_checkpoint = AlgorithmCheckpoint(
                database_connection, checkpoint_id=key["Key"]
            )
            if algorithm_checkpoint.check_tags(
                query_positive_tags=positive_tags,
                query_negative_tags=negative_tags,
            ):
                checkpoint_json = (
                    algorithm_checkpoint.checkpoint_manifest.model_dump()
                )
                try:
                    checkpoints.append(
                        AlgorithmCheckpointRecord(**checkpoint_json)
                    )
                except ValidationError as _:
                    continue
        return checkpoints
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Failed to list checkpoints due to an internal server error: {e}"
            },
        )


@router.get(
    "/v0/checkpoint/{checkpoint_id}",
    summary="Returns a checkpoint from the database",
    response_model=AlgorithmCheckpointRecord,
    responses={
        500: {"model": ResponseMessage},
        404: {"model": ResponseMessage},
    },
)
async def get_checkpoint(checkpoint_id: str, request: Request):
    """
    Returns a checkpoint from database.

    Parameters
    ----------
    checkpoint_id : str
        The id of the checkpoint.

    Returns
    -------
    AlgorithmCheckpointRecord
        The checkpoint response.
    """
    database_connection = request.app.state.database_connection
    try:
        try:
            algorithm_checkpoint = AlgorithmCheckpoint(
                database_connection, checkpoint_id=checkpoint_id
            )
        except Exception as _:
            return JSONResponse(
                status_code=404,
                content={"detail": "Checkpoint not found"},
            )

        return AlgorithmCheckpointRecord(
            **algorithm_checkpoint.checkpoint_manifest.model_dump()
        )
    except Exception as _:
        return JSONResponse(
            status_code=500,
            content={"detail": "Failed to get sample"},
        )


@router.delete(
    "/v0/checkpoint/{checkpoint_id}",
    summary="Deletes a checkpoint from the database",
    response_model=ResponseMessage,
    responses={
        500: {"model": ResponseMessage},
        404: {"model": ResponseMessage},
    },
)
async def delete_checkpoint(
    checkpoint_id: str, request: Request
) -> ResponseMessage:
    """
    Deletes a checkpoint from the database.

    Parameters
    ----------
    checkpoint_id : str
        The id of the checkpoint.

    Returns
    -------
    ResponseMessage
    """

    database_connection = request.app.state.database_connection

    try:
        objects_exist = database_connection.check_objects_exist(
            "algorithm-checkpoint-store", [checkpoint_id]
        )

        if not objects_exist[0]:
            return JSONResponse(
                status_code=404,
                content={"detail": "Checkpoint not found"},
            )

        algorithm_checkpoint = AlgorithmCheckpoint(
            database_connection, checkpoint_id=checkpoint_id
        )

        algorithm_checkpoint.delete_checkpoint()

        return JSONResponse(
            status_code=200,
            content={"detail": "Checkpoint deleted successfully"},
        )
    except Exception as _:
        return JSONResponse(
            status_code=500,
            content={"detail": "Failed to delete checkpoint"},
        )
