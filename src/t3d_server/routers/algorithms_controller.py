"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from t3d_server.pydantic_models import (
    AlgorithmRegisteredResponse,
    ResponseMessage,
    S3ModelFileRecord,
    FailedAlgorithmRegisteredResponse,
)
import json
from typing import List, Optional, Union

router = APIRouter(prefix="/api", tags=["algorithms-controller"])


@router.get(
    "/v0/algorithm/{algorithm_name}/{algorithm_major_version}",
    summary="Returns algorithm by its name and version.",
    response_model=Union[
        AlgorithmRegisteredResponse, FailedAlgorithmRegisteredResponse
    ],
    responses={
        500: {"model": ResponseMessage},
        404: {"model": ResponseMessage},
    },
)
def get_algorithm(
    algorithm_name: str, algorithm_major_version: str, request: Request
) -> Union[
    AlgorithmRegisteredResponse, FailedAlgorithmRegisteredResponse, JSONResponse
]:
    """
    Returns algorithm by its name and version.

    Parameters
    ----------
    algorithm : Algorithm
        The algorithm.

    Returns
    -------
    AlgorithmRegisteredResponse, FailedAlgorithmRegisteredResponse, JSONResponse
        The algorithm.
    """
    database_connection = request.app.state.database_connection
    # get the model key with the highest minor version by model_name and major_version
    try:
        # get all algoerithms
        all_algorithms = database_connection.list_objects("algorithm-store")

        if len(all_algorithms) == 0:
            return JSONResponse(
                status_code=404,
                content={
                    "detail": "No algorithms found in the algorithm store"
                },
            )

        # find the algorithm with the requested name and major version
        minor_version = -1  # the highest minor version
        for key in all_algorithms:
            algorithm_json = json.loads(
                database_connection.get_objects(
                    "algorithm-store",
                    [key["Key"]],
                )[0]
            )

            if (
                algorithm_json["algorithm_name"].lower()
                == algorithm_name.lower()
                and algorithm_json["algorithm_major_version"].lower()
                == algorithm_major_version.lower()
            ):
                if (
                    int(algorithm_json["algorithm_minor_version"])
                    > minor_version
                ):
                    minor_version = int(
                        algorithm_json["algorithm_minor_version"]
                    )
                    found_algorithm = algorithm_json

        if minor_version != -1:
            try:
                return AlgorithmRegisteredResponse(
                    algorithm_id=found_algorithm["algorithm_id"],
                    algorithm_input_queue="NOT IMPLEMENTED YET",
                    algorithm_minor_version=found_algorithm[
                        "algorithm_minor_version"
                    ],
                    algorithm_name=found_algorithm["algorithm_name"],
                    algorithm_version=found_algorithm[
                        "algorithm_major_version"
                    ],
                    algorithm_type=found_algorithm["algorithm_type"],
                    algorithm_tags=found_algorithm["algorithm_tags"],
                    algorithm_description=found_algorithm[
                        "algorithm_description"
                    ],
                    supported_devices=found_algorithm["supported_devices"],
                    default_device=found_algorithm["default_device"],
                    additional_parameters=found_algorithm[
                        "additional_parameters"
                    ],
                )
            except ValidationError as e:
                return FailedAlgorithmRegisteredResponse(
                    algorithm_name=found_algorithm["algorithm_name"],
                    algorithm_version=found_algorithm[
                        "algorithm_major_version"
                    ],
                    message=f"The algorithm has not been configured correctly.\n{e}",
                )
        else:
            return JSONResponse(
                status_code=404,
                content={
                    "detail": "Model with the requested name and major version not found in the model store"
                },
            )
    except Exception as _:
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Failed to get algorithm due to an internal server error."
            },
        )


@router.get(
    "/v0/algorithm/all",
    summary="Lists all available algorithms",
    response_model=List[
        Union[AlgorithmRegisteredResponse, FailedAlgorithmRegisteredResponse]
    ],
    responses={500: {"model": ResponseMessage}},
)
async def list_model_files(
    request: Request,
    positive_tag: Optional[List[str]] = Query([]),
    negative_tag: Optional[List[str]] = Query([]),
    algorithm_type: Optional[str] = Query(None),
    supported_devices: Optional[List[str]] = Query([]),
) -> List[S3ModelFileRecord]:
    """
    Lists all available algorithms.

    Parameters
    ----------
    request : Request
        The request.
    positive_tag : List[str] | None
        A list of tags the algorithm must have.
    negative_tag : List[str] | None
        A list of tags the algorithm must not have.
    algorithm_type : str | None
        The type of the algorithm.
    supported_devices : List[str] | None
        The devices the algorithm is compatible with.

    Returns
    -------
    List[AlgorithmRegisteredResponse]
        The list of algorithms.
    """
    positive_tags = positive_tag
    negative_tags = negative_tag

    database_connection = request.app.state.database_connection

    try:
        # get all algoerithms
        all_algorithms = database_connection.list_objects("algorithm-store")

        if len(all_algorithms) == 0:
            return JSONResponse(
                status_code=404,
                content={
                    "detail": "No algorithms found in the algorithm store"
                },
            )

        algorithms = []
        for key in all_algorithms:
            algorithm_json = json.loads(
                database_connection.get_objects(
                    "algorithm-store",
                    [key["Key"]],
                )[0]
            )

            # check if the algorithm has all the positive tags
            if positive_tags:
                if not all(
                    tag in algorithm_json["algorithm_tags"]
                    for tag in positive_tags
                ):
                    continue

            # check if the algorithm has any of the negative tags
            if negative_tags:
                if any(
                    tag in algorithm_json["algorithm_tags"]
                    for tag in negative_tags
                ):
                    continue

            # check if the algorithm has the requested type
            if algorithm_type is not None:
                if (
                    algorithm_json["algorithm_type"].lower()
                    != algorithm_type.lower()
                ):
                    continue

            # check if the algorithm has the requested device
            if supported_devices:
                if not any(
                    d.lower()
                    in [
                        algorithm_device.lower()
                        for algorithm_device in algorithm_json[
                            "supported_devices"
                        ]
                    ]
                    for d in supported_devices
                ):
                    continue
            try:
                algorithms.append(
                    AlgorithmRegisteredResponse(
                        algorithm_id=algorithm_json["algorithm_id"],
                        algorithm_input_queue="NOT IMPLEMENTED YET",
                        algorithm_minor_version=algorithm_json[
                            "algorithm_minor_version"
                        ],
                        algorithm_name=algorithm_json["algorithm_name"],
                        algorithm_version=algorithm_json[
                            "algorithm_major_version"
                        ],
                        algorithm_type=algorithm_json["algorithm_type"],
                        algorithm_tags=algorithm_json["algorithm_tags"],
                        algorithm_description=algorithm_json[
                            "algorithm_description"
                        ],
                        default_device=algorithm_json["default_device"],
                        supported_devices=algorithm_json["supported_devices"],
                        additional_parameters=algorithm_json[
                            "additional_parameters"
                        ],
                    )
                )
            except ValidationError as _:
                continue

        return algorithms
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Failed to list algorithms due to an internal server error: {e}"
            },
        )
