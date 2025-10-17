"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import pytest
import numpy as np
import types
from concurrent.futures import ThreadPoolExecutor

from compox.algorithm_utils.Image2ImageRunner import Image2ImageRunner
from compox.tasks.DebuggingTaskHandler import DebuggingTaskHandler


class AttributeSafetyRunner(Image2ImageRunner):
    """
    The runner class for the denoiser algorithm.
    """

    def __init__(self):
        self.my_attribute = [0]
        self.foo = "foo"
        self.bar = "bar"
        self.baz = "baz"

    def load_assets(self):
        """
        Here you can load the assets needed for the algorithm. This can be
        the model, the weights, etc. The assets are loaded upon the first
        call of the algorithm and are cached with the algorithm instance.
        """
        self.my_asset = [0]

    def preprocess(self, input_data: dict, args: dict = {}) -> np.ndarray:
        """
        Preprocess the request data before feeding into model for inference.

        Parameters
        ----------
        input_data : dict
            The input data.

        Returns
        -------
        np.ndarray
            The preprocessed images.
        """
        pass

    def set_inference_fn(self, fn):
        """
        Dynamically override the inference method for testing purposes.

        Parameters
        ----------
        fn : Callable
            A function that takes (self, data, args) and returns np.ndarray.
        """
        self._inference_override = types.MethodType(fn, self)

    def inference(self, data: np.ndarray, args: dict = {}) -> np.ndarray:
        """
        Run the inference.

        Parameters
        ----------
        input_data : dict
            The input data.

        Returns
        -------
        np.ndarray
            The denoised images.
        """
        if hasattr(self, "_inference_override"):
            return self._inference_override(data, args)
        raise NotImplementedError("No inference logic provided.")

    def postprocess(self, data: list, args: dict = {}) -> dict:
        return self.my_attribute


def run_inference(runner, inference_fn):
    """
    Run inference with the given runner and data.
    """
    runner.initialize()
    runner.set_inference_fn(inference_fn)
    task_handler = DebuggingTaskHandler("test_task_id")
    task_handler.set_as_current_task_handler()
    return runner.run(
        {
            "input_dataset_ids": ["test_image_id"],
        },
        args={},
    )


def test_runner_attribute_update():
    """
    Test that attribute reassignment in a runner does not modify the original attribute.

    A custom `inference` function is injected which reassigns `self.my_attribute` to a new
    list `[self.my_attribute[0] + 1]`. Because the runner is frozen, this reassignment should
    be captured in the context and not modify the original shared list.

    After executing 8 threads, each performing a reassignment, the original attribute should
    remain unchanged at `[0]`.
    """

    def test_inference(self, data, args):
        self.my_attribute = [self.my_attribute[0] + 1]

    runner = AttributeSafetyRunner.__new__(AttributeSafetyRunner)
    runner.initialize(device="cpu")
    runner.load_assets()

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(run_inference, runner, test_inference)
            for _ in range(8)
        ]
        _ = [future.result() for future in futures]

    # Check if the runner attribute was updated correctly
    assert (
        runner.my_attribute[0] == 0
    ), "The runner attribute should remain unchanged in frozen state."


def test_runner_asset_loading():
    """
    Test that that tests, that an AttributeError is raised when trying reassigning
    a Runner asset after the runner was initialized.
    """

    runner = AttributeSafetyRunner.__new__(AttributeSafetyRunner)
    runner.initialize(device="cpu")
    runner._load_assets()

    # test that AttributeError is raised when trying to reassign an asset
    with pytest.raises(AttributeError):
        runner.my_asset = "Trying to reassign an asset after initialization"


def test_runner_asset_access():
    """
    Test that the assets are accessible after the runner is initialized.
    """

    runner = AttributeSafetyRunner.__new__(AttributeSafetyRunner)
    runner.initialize(device="cpu")
    runner._load_assets()

    # Check if the asset is accessible
    assert hasattr(
        runner, "my_asset"
    ), "The asset should be accessible after initialization."
    assert isinstance(runner.my_asset, list), "The asset should be a list."
    assert len(runner.my_asset) == 1, "The asset should have one element."
    assert runner.my_asset[0] == 0, "The asset should be initialized to 0."


def test_device_access():
    """
    Test that the device is accessible after the runner is initialized.
    """

    runner = AttributeSafetyRunner.__new__(AttributeSafetyRunner)
    runner.initialize(device="cpu")

    # Check if the device is accessible
    assert hasattr(
        runner, "device"
    ), "The device should be accessible after initialization."
    assert runner.device == "cpu", "The device should be set to 'cpu'."

    # it should not be possible to change the device after initialization
    with pytest.raises(AttributeError):
        runner.device = "cuda:0"


def test_runner_context():
    """
    Test that the runner context is set correctly after initialization.
    """

    runner = AttributeSafetyRunner.__new__(AttributeSafetyRunner)
    runner.initialize(device="cpu")

    # Check if the runner context is set
    assert hasattr(
        runner, "runner_context"
    ), "The runner context should be set after initialization."
    assert isinstance(
        runner.runner_context, dict
    ), "The runner context should be a dict."
    # runnr context should contain only the attributes set in __init__
    assert set(runner.runner_context.keys()) == {
        "my_attribute",
        "foo",
        "bar",
        "baz",
    }, "The runner context should contain only the attributes set in __init__."


def test_runner_locked_attributes():
    """
    Test that the runner locked attributes are set correctly.
    """

    runner = AttributeSafetyRunner.__new__(AttributeSafetyRunner)
    runner.initialize(device="cpu")

    assert not hasattr(
        runner, "_locked_attributes"
    ), "The locked attributes should not be set before loading assets."
    runner._load_assets()

    # Check if the locked attributes are set
    assert hasattr(
        runner, "_locked_attributes"
    ), "The locked attributes should ve set after loading assets."
    assert isinstance(
        runner._locked_attributes, set
    ), "The locked attributes should be a set."
    assert runner._locked_attributes == {
        "my_asset"
    }, "The locked attributes should contain only 'my_asset'."


def test_inplace_operation_on_runner_attribute():
    """
    Test that inplace operations on runner attributes do not raise an error.
    """

    runner = AttributeSafetyRunner.__new__(AttributeSafetyRunner)
    runner.initialize(device="cpu")
    runner.load_assets()

    # Perform an inplace operation on the runner attribute
    runner.my_attribute.append(1)
    # Check if the inplace operation was successful
    assert (
        runner.my_attribute[0] == 0 and runner.my_attribute[1] == 1
    ), "The inplace operation should update the attribute."
