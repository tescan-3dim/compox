"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import sys
import os

from t3d_server.tasks.DebuggingTaskHandler import DebuggingTaskHandler


if __name__ == "__main__":
    task_handler = DebuggingTaskHandler("task_id")
    algorithm_runner = task_handler.fetch_algorithm(os.path.dirname(__file__))
    out = algorithm_runner.run(
        {
            "input_dataset_ids": ["input_dataset_ids"],
        },
        args={},
    )
    print(out)
