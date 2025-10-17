"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from contextvars import ContextVar
from t3d_server.tasks.TaskHandler import TaskHandler

current_task_handler: ContextVar[TaskHandler] = ContextVar(
    "current_task_handler"
)
