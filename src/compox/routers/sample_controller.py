"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from typing import List, Optional
from datetime import datetime

from compox.training.TrainingSample import TrainingSample
from compox.server_utils import generate_uuid
from compox.pydantic_models import (
    IncomingSampleRequest,
    SampleRecord,
    SampleResponse,
    ResponseMessage,
)

router = APIRouter(prefix="/api", tags=["sample-controller"])


@router.post(
    "/v0/sample",
    summary="Adds a sample to the database",
    response_model=SampleResponse,
    responses={
        500: {"model": ResponseMessage},
        422: {"model": ResponseMessage},
        404: {"model": ResponseMessage},
    },
)
async def add_sample(
    request: Request,
    incoming_sample_request: IncomingSampleRequest,
) -> SampleResponse:
    """
    Adds a sample configuration to the database.

    Parameters
    ----------
    request : Request
        Request to add a sample.

    incoming_sample_request : IncomingSampleRequest
        The incoming sample request.

    Returns
    -------
    SampleResponse
        The sample add response.
    """

    sample_id = generate_uuid()
    database_connection = request.app.state.database_connection

    files = [
        f for d in incoming_sample_request.files for k in d.values() for f in k
    ]
    files_exist = database_connection.check_objects_exist("data-store", files)

    if False in files_exist:
        not_found_files = [
            files[i] for i in range(len(files_exist)) if not files_exist[i]
        ]
        return JSONResponse(
            status_code=404,
            content={
                "detail": "Input files with the following identifiers not found: {}".format(
                    "\n".join(not_found_files)
                )
            },
        )

    sample_manifest = SampleRecord(
        sample_id=sample_id,
        files=incoming_sample_request.files,
        tags=incoming_sample_request.tags,
        time_created=str(datetime.now()),
    )

    training_sample = TrainingSample(
        database_connection, sample_manifest=sample_manifest.model_dump()
    )

    try:
        training_sample.save_sample_manifest()
        return SampleResponse(
            sample_id=sample_id,
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Failed to add sample: {e}"},
        )


@router.get(
    "/v0/sample/all",
    summary="Returns all samples filtered by tag query parameters",
    response_model=List[SampleRecord],
    responses={
        500: {"model": ResponseMessage},
        404: {"model": ResponseMessage},
    },
)
async def list_samples(
    request: Request,
    positive_tags: Optional[List[str]] = Query([]),
    negative_tags: Optional[List[str]] = Query([]),
) -> List[SampleRecord]:
    """
    Returns all samples fulfilling criteria.

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
    List[SampleRecord]
        The list of samples.
    """
    database_connection = request.app.state.database_connection

    try:
        # get all samples
        all_samples = database_connection.list_objects("sample-store")

        if len(all_samples) == 0:
            return JSONResponse(
                status_code=404,
                content={"detail": "No samples found in the sample store"},
            )

        samples = []
        for key in all_samples:
            training_sample = TrainingSample(
                database_connection, sample_id=key["Key"]
            )
            if training_sample.check_tags(
                query_positive_tags=positive_tags,
                query_negative_tags=negative_tags,
            ):
                sample_json = training_sample.sample_manifest.model_dump()
                try:
                    samples.append(SampleRecord(**sample_json))
                except ValidationError as _:
                    continue
        return samples
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Failed to list samples due to an internal server error: {e}"
            },
        )


@router.get(
    "/v0/sample/{sample_id}",
    summary="Returns a sample from the database",
    response_model=SampleRecord,
    responses={
        500: {"model": ResponseMessage},
        404: {"model": ResponseMessage},
    },
)
async def get_sample(sample_id: str, request: Request):
    """
    Returns a sample from database.

    Parameters
    ----------
    sample_id : str
        The id of the sample.

    Returns
    -------
    SampleRecord
        The sample response.
    """
    database_connection = request.app.state.database_connection
    try:
        try:
            training_sample = TrainingSample(
                database_connection, sample_id=sample_id
            )
        except Exception as e:
            return JSONResponse(
                status_code=404,
                content={"detail": "Sample not found: " + str(e)},
            )

        return SampleRecord(**training_sample.sample_manifest.model_dump())
    except Exception as _:
        return JSONResponse(
            status_code=500,
            content={"detail": "Failed to get sample"},
        )


@router.delete(
    "/v0/sample/{sample_id}",
    summary="Deletes a sample from the database",
    response_model=ResponseMessage,
    responses={
        500: {"model": ResponseMessage},
        404: {"model": ResponseMessage},
    },
)
async def delete_sample(sample_id: str, request: Request) -> ResponseMessage:
    """
    Deletes a sample from the database.

    Parameters
    ----------
    sample_id : str
        The id of the sample.

    Returns
    -------
    ResponseMessage
    """

    database_connection = request.app.state.database_connection

    try:
        objects_exist = database_connection.check_objects_exist(
            "sample-store", [sample_id]
        )

        if not objects_exist[0]:
            return JSONResponse(
                status_code=404,
                content={"detail": "Sample not found"},
            )

        training_sample = TrainingSample(
            database_connection, sample_id=sample_id
        )

        training_sample.delete_sample_manifest()

        return JSONResponse(
            status_code=200,
            content={"detail": "Sample deleted successfully"},
        )
    except Exception as _:
        return JSONResponse(
            status_code=500,
            content={"detail": "Failed to delete sample"},
        )
