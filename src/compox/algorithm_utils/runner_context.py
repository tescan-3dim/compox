"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from contextvars import ContextVar

current_runner_context: ContextVar[dict] = ContextVar("current_runner_context")
