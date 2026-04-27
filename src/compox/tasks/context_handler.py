"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from contextvars import ContextVar
from compox.tasks.TaskHandler import TaskHandler
from compox.training.TrainingHandler import TrainingHandler

current_handler: ContextVar[TaskHandler | TrainingHandler] = ContextVar(
    "current_handler"
)
