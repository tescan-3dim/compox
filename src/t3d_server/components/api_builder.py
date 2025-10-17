"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import os
import atexit
from contextlib import asynccontextmanager
from concurrent.futures import _base, ThreadPoolExecutor

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.logger import logger as fastapi_logger
from celery import Celery

from t3d_server.config.server_settings import Settings
from t3d_server.components.minio_wrapper import MinIOWrapper
from t3d_server.components.celery_builder import build_celery
from t3d_server.components.db_connection_builder import build_database_connection

from t3d_server.server_utils import check_and_create_database_collections, get_subprocess_fn

from t3d_server.routers import (
    algorithms_controller,
    execution_controller,
    execution_manager,
    file_controller,
    file_controller_v1,
    root
)
      
      
class ApiBuilder:
    def __init__(self):
        self.lifespan = None
        self.settings = None
        self.database_connection = None
        self.celery = None
        self.executor = None
        self.middleware = None
        self.routes = []

    def with_lifespan(self, lifespan):
        self.lifespan = lifespan
        return self

    def with_settings(self, settings):
        self.settings = settings
        return self

    def with_database_connection(self, database_connection):
        self.database_connection = database_connection
        return self

    def with_executor(self, executor: _base.Executor | Celery | None = None):
        self.executor = executor
        return self

    def with_route(self, route: APIRouter):
        self.routes.append(route)
        return self
    
    def with_middleware(self, middleware, middleware_settings):
        self.middleware = middleware
        self.middleware_settings = middleware_settings
        return self

    def build(self):
        app = FastAPI(lifespan=self.lifespan)
        app.state.database_connection = self.database_connection
        app.state.executor = self.executor
        app.state.settings = self.settings

        for route in self.routes:
            app.include_router(route)
            
        if self.middleware is not None:
            app.add_middleware(
                CORSMiddleware,
                **self.middleware_settings.model_dump()
            )

        return app


# define app context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI app. 
    The subprocess for minio is started here and killed when the app is closed.
    """
    # setup subprocess mechanism that runs on both linux and win
    subprocess_fn = get_subprocess_fn()
    
    lifecycle_subprocesses = {}
    
    settings = app.state.settings
    
    # maybe run local minio subprocess
    if (settings.storage.backend_settings.provider == "minio" and 
        settings.storage.backend_settings.start_instance):
        
        if not os.path.exists(settings.storage.backend_settings.storage_path):
            raise ValueError("Minio storage path does not exist!")
        
        minio_wrapper = MinIOWrapper(settings)
        lifecycle_subprocesses["minio"] = minio_wrapper.start(subprocess_fn)

    new_collections = check_and_create_database_collections(
        [
            "data-store",
            "execution-store",
            "algorithm-store",
            "module-store",
            "asset-store",
        ],
        database_connection=app.state.database_connection,
    )
    if len(new_collections) > 0:
        fastapi_logger.info(f"Created new collections: {new_collections}")

    for lifecycle_subprocess in lifecycle_subprocesses.values():
        atexit.register(lifecycle_subprocess.kill)

    yield

    # if the app database connection has s3_client, close it
    if app.state.database_connection.s3_client:
        app.state.database_connection.s3_client.close()
        
    for lifecycle_subprocess in lifecycle_subprocesses.values():
        atexit.register(lifecycle_subprocess.kill)
        

def build_api(settings: Settings, with_lifespan: bool = True) -> FastAPI:
    """
    Build a FastAPI instance with the provided settings and lifecycle management.

    Parameters
    ----------
    settings : Settings
        The settings object containing the configuration for the API.
    with_lifespan : bool, optional
        Whether to include the lifespan context manager for the API. Default is True.

    Returns
    -------
    FastAPI
        The FastAPI instance.
    """
    
    # Build database connection
    database_connection = build_database_connection(settings)

    # Task execution
    match settings.inference.backend_settings.executor:
        case "fastapi_background_tasks":
            task_executor = ThreadPoolExecutor(
                max_workers=settings.inference.backend_settings.worker_number
                )
        case "celery":
            task_executor = build_celery(settings)
        case _:
            raise ValueError("Invalid server backend")

    # build api with lifecycle management
    api_builder = (ApiBuilder()
        .with_settings(settings)
        .with_database_connection(database_connection)
        .with_executor(task_executor)
        .with_route(root.router)
        .with_route(algorithms_controller.router)
        .with_route(execution_controller.router)
        .with_route(file_controller.router)
        .with_route(file_controller_v1.router)
        .with_route(execution_manager.router)
        .with_middleware(CORSMiddleware, settings.middleware)
    )
    if with_lifespan:
        api_builder.with_lifespan(lifespan)
        
    return api_builder.build()

    