"""
Copyright 2026 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from datetime import datetime
import json
import os
from typing import Optional

from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse

from compox.algorithm_utils.AlgorithmDeployer import AlgorithmDeployer
from compox.algorithm_utils.AlgorithmManager import AlgorithmManager
from compox.pydantic_models import (
    AlgorithmDeployResponse,
    DeployRecord,
    DeployResponse,
    ResponseMessage,
)
from compox.server_utils import generate_uuid
from compox.tasks.deploy_task_fastapi import deploy_task_fastapi

router = APIRouter(prefix="/api", tags=["deploy-controller"])


def _set_algorithm_removable(
    database_connection, algorithm_id: str, removable: bool = True
) -> None:
    algorithm_collection = "algorithm-store"
    for item in database_connection.list_objects(algorithm_collection):
        key = item["Key"]
        if key.startswith(f"{algorithm_id}~"):
            algorithm_json = json.loads(
                database_connection.get_objects(
                    algorithm_collection, [key]
                )[0]
            )
            algorithm_json["removable"] = removable
            database_connection.put_objects(
                algorithm_collection, [key], [json.dumps(algorithm_json)]
            )
            return


def _set_algorithm_exportable(
    database_connection, algorithm_id: str, exportable: bool = True
) -> None:
    algorithm_collection = "algorithm-store"
    for item in database_connection.list_objects(algorithm_collection):
        key = item["Key"]
        if key.startswith(f"{algorithm_id}~"):
            algorithm_json = json.loads(
                database_connection.get_objects(
                    algorithm_collection, [key]
                )[0]
            )
            algorithm_json["exportable"] = exportable
            database_connection.put_objects(
                algorithm_collection, [key], [json.dumps(algorithm_json)]
            )
            return


@router.post(
    "/v0/deploy/local",
    summary="Deploy an algorithm from a local folder or zip file",
    response_model=AlgorithmDeployResponse,
    responses={
        400: {"model": ResponseMessage},
        500: {"model": ResponseMessage},
    },
)
def deploy_algorithm_local(
    request: Request,
    path: str = Query(
        ...,
        description="Local path to algorithm folder or .zip file.",
    ),
    algorithm_name: Optional[str] = Query(
        None, description="Optional override for algorithm name."
    ),
    algorithm_major_version: Optional[str] = Query(
        None, description="Optional override for algorithm major version."
    ),
    removable: Optional[bool] = Query(
        None,
        description="Optional override for whether the algorithm is removable.",
    ),
    exportable: Optional[bool] = Query(
        None,
        description="Optional override for whether the algorithm is exportable.",
    ),
) -> AlgorithmDeployResponse | JSONResponse:
    """
    Deploy an algorithm from a local folder or zip file.
    """
    database_connection = request.app.state.database_connection

    if not os.path.exists(path):
        return JSONResponse(
            status_code=400,
            content={"detail": f"Path not found: {path}"},
        )

    def build_deploy_response(algorithm_id: str) -> AlgorithmDeployResponse:
        algorithm_collection = "algorithm-store"
        for item in database_connection.list_objects(algorithm_collection):
            key = item["Key"]
            if key.startswith(f"{algorithm_id}~"):
                algorithm_json = json.loads(
                    database_connection.get_objects(
                        algorithm_collection, [key]
                    )[0]
                )
                return AlgorithmDeployResponse(
                    algorithm_id=algorithm_id,
                    algorithm_name=algorithm_json["algorithm_name"],
                    algorithm_major_version=algorithm_json[
                        "algorithm_major_version"
                    ],
                    algorithm_minor_version=algorithm_json[
                        "latest_algorithm_minor_version"
                    ],
                )
        return AlgorithmDeployResponse(
            algorithm_id=algorithm_id,
            algorithm_name=algorithm_name or "",
            algorithm_major_version=algorithm_major_version or "",
            algorithm_minor_version="",
        )

    def deploy_from_directory(algorithm_root: str) -> AlgorithmDeployResponse:
        deployer = AlgorithmDeployer(algorithm_root)
        algorithm_id = deployer.store_algorithm(
            database_connection=database_connection,
            algorithm_name_override=algorithm_name,
            algorithm_major_version_override=algorithm_major_version,
        )
        _set_algorithm_removable(
            database_connection,
            algorithm_id,
            deployer.removable if removable is None else removable,
        )
        _set_algorithm_exportable(
            database_connection,
            algorithm_id,
            deployer.exportable if exportable is None else exportable,
        )
        return AlgorithmDeployResponse(
            algorithm_id=algorithm_id,
            algorithm_name=deployer.algorithm_name,
            algorithm_major_version=deployer.algorithm_major_version,
            algorithm_minor_version=deployer.algorithm_minor_version,
        )

    try:
        if os.path.isdir(path):
            return deploy_from_directory(path)
        if os.path.isfile(path) and path.lower().endswith(".zip"):
            algorithm_id = AlgorithmDeployer.deploy_from_zip(
                path,
                database_connection=database_connection,
                algorithm_name_override=algorithm_name,
                algorithm_major_version_override=algorithm_major_version,
            )
            algorithm_record = None
            for item in database_connection.list_objects("algorithm-store"):
                key = item["Key"]
                if key.startswith(f"{algorithm_id}~"):
                    algorithm_record = json.loads(
                        database_connection.get_objects(
                            "algorithm-store", [key]
                        )[0]
                    )
                    break
            _set_algorithm_removable(
                database_connection,
                algorithm_id,
                (
                    bool(algorithm_record and algorithm_record.get("removable"))
                    if removable is None
                    else removable
                ),
            )
            _set_algorithm_exportable(
                database_connection,
                algorithm_id,
                (
                    bool(algorithm_record and algorithm_record.get("exportable", True))
                    if exportable is None
                    else exportable
                ),
            )
            return build_deploy_response(algorithm_id)
        return JSONResponse(
            status_code=400,
            content={"detail": "Path must be a directory or a .zip file."},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Failed to deploy algorithm: {e}"},
        )


@router.post(
    "/v0/deploy/local-async",
    summary="Deploy an algorithm from a local folder or zip file asynchronously",
    response_model=DeployResponse,
    responses={
        400: {"model": ResponseMessage},
        500: {"model": ResponseMessage},
    },
)
def deploy_algorithm_local_async(
    request: Request,
    path: str = Query(
        ...,
        description="Local path to algorithm folder or .zip file.",
    ),
    algorithm_name: Optional[str] = Query(
        None, description="Optional override for algorithm name."
    ),
    algorithm_major_version: Optional[str] = Query(
        None, description="Optional override for algorithm major version."
    ),
    removable: Optional[bool] = Query(
        None,
        description="Optional override for whether the algorithm is removable.",
    ),
    exportable: Optional[bool] = Query(
        None,
        description="Optional override for whether the algorithm is exportable.",
    ),
) -> DeployResponse | JSONResponse:
    """
    Deploy an algorithm from a local folder or zip file asynchronously.
    """
    settings = request.app.state.settings
    if settings.inference.backend_settings.executor != "fastapi_background_tasks":
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Async deploy requires fastapi_background_tasks executor."
            },
        )

    if not os.path.exists(path):
        return JSONResponse(
            status_code=400,
            content={"detail": f"Path not found: {path}"},
        )

    database_connection = request.app.state.database_connection
    deploy_id = generate_uuid()
    record = DeployRecord(
        deploy_id=deploy_id,
        status="PENDING",
        path=path,
        time_started=str(datetime.now()),
        time_completed=None,
        log=None,
    )
    try:
        database_connection.put_objects(
            "deploy-store",
            [deploy_id],
            [json.dumps(record.model_dump())],
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Failed to save deploy record: {e}"},
        )

    try:
        request.app.state.executor.submit(
            deploy_task_fastapi,
            database_connection=database_connection,
            deploy_id=deploy_id,
            path=path,
            algorithm_name_override=algorithm_name,
            algorithm_major_version_override=algorithm_major_version,
            removable_override=removable,
            exportable_override=exportable,
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Failed to start deploy task: {e}"},
        )

    return DeployResponse(deploy_id=deploy_id)


@router.get(
    "/v0/deploy/{deploy_id}",
    summary="Get deploy record by id",
    response_model=DeployRecord,
    responses={500: {"model": ResponseMessage}},
)
async def get_deploy_record(
    deploy_id: str, request: Request
) -> DeployRecord | JSONResponse:
    """
    Get deploy record by id.
    """
    database_connection = request.app.state.database_connection
    try:
        object_exists = database_connection.check_objects_exist(
            "deploy-store", [deploy_id]
        )[0]
        if not object_exists:
            return JSONResponse(
                status_code=404,
                content={"detail": "Deploy record not found"},
            )
        return DeployRecord(
            **json.loads(
                database_connection.get_objects(
                    "deploy-store", [deploy_id]
                )[0]
            )
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Failed to get deploy record: {e}"},
        )


@router.delete(
    "/v0/deploy/algorithm/{algorithm_id}",
    summary="Remove a removable algorithm by id",
    response_model=ResponseMessage,
    responses={500: {"model": ResponseMessage}},
)
async def delete_removable_algorithm(
    algorithm_id: str,
    request: Request,
    algorithm_minor_version: Optional[str] = Query(
        None,
        description="Optional minor version to delete instead of the entire algorithm.",
    ),
) -> ResponseMessage | JSONResponse:
    """
    Delete an algorithm only if it is marked as removable.
    """
    database_connection = request.app.state.database_connection
    algorithm_collection = "algorithm-store"

    try:
        algorithm_record = None
        for item in database_connection.list_objects(algorithm_collection):
            key = item["Key"]
            if key.startswith(f"{algorithm_id}~"):
                algorithm_record = json.loads(
                    database_connection.get_objects(
                        algorithm_collection, [key]
                    )[0]
                )
                break
        if algorithm_record is None:
            return JSONResponse(
                status_code=404,
                content={"detail": "Algorithm not found"},
            )

        if not algorithm_record.get("removable", False):
            return JSONResponse(
                status_code=400,
                content={"detail": "Algorithm is not removable"},
            )

        algorithm_manager = AlgorithmManager(database_connection)
        if algorithm_minor_version is None:
            algorithm_manager.delete_algorithm(
                name=algorithm_record["algorithm_name"],
                major_version=algorithm_record["algorithm_major_version"],
            )
            return ResponseMessage(detail="Algorithm removed")

        algorithm_manager.delete_algorithm_minor_version(
            name=algorithm_record["algorithm_name"],
            major_version=algorithm_record["algorithm_major_version"],
            minor_version=algorithm_minor_version,
        )
        return ResponseMessage(
            detail=f"Algorithm minor version {algorithm_minor_version} removed"
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Failed to remove algorithm: {e}"},
        )
