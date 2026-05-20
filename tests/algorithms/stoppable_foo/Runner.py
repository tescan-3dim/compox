"""
Copyright 2026 TESCAN GROUP, a.s.
All rights reserved
"""

import time

from compox.algorithm_utils.BaseRunner import BaseRunner
from compox.algorithm_utils.io_schemas import ImageSchema


class Runner(BaseRunner):
    """
    Slow test runner that periodically reports progress so stop requests can be
    observed during execution.
    """

    def preprocess(
        self, input_data: ImageSchema, args: dict | None = None
    ) -> tuple:
        self.log_message("Preprocessing the stoppable foo input data.")
        return input_data, args

    def inference(
        self,
        model,
        preprocessed_data: tuple,
        args: dict | None = None,
    ) -> str:
        self.log_message("Running the stoppable foo inference.")
        total_steps = 30
        for i in range(total_steps):
            self.set_progress(float((i + 1) / (total_steps + 1)))
            time.sleep(0.1)
        return "stoppable foo"

    def postprocess(
        self, inference_output: str, args: dict | None = None
    ) -> list[str]:
        self.log_message("Postprocessing the stoppable foo inference output.")
        return [inference_output]
