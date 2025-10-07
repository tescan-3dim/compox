"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import gc
from compox.server_utils import check_torch_with_cuda_available

TORCH_WITH_CUDA_AVAILABLE = check_torch_with_cuda_available()

if TORCH_WITH_CUDA_AVAILABLE:
    import torch


class CUDAMemoryManager:
    """
    A context manager to release CUDA memory after a block of code.
    """

    def __enter__(self):
        # Enter the context
        return self

    if TORCH_WITH_CUDA_AVAILABLE:

        def __exit__(self, exc_type, exc_value, traceback):
            # Exit the context, release CUDA memory
            gc.collect()

            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

    else:

        def __exit__(self, exc_type, exc_value, traceback):
            gc.collect()
