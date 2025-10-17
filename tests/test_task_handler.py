"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import pytest
import json
import io
from unittest.mock import patch, MagicMock
from pydantic import BaseModel, ConfigDict, ValidationError
import numpy as np
import h5py
from datetime import datetime

from compox.tasks.TaskHandler import TaskHandler
from compox.tasks.context_task_handler import current_task_handler


class DummySchema(BaseModel):
    """
    Simple Pydantic model used for testing HDF5 data fetching.

    Attributes
    ----------
    array1 : np.ndarray
        Required NumPy array field.
    array2 : np.ndarray | None
        Optional NumPy array field, defaults to None.
    """

    array1: np.ndarray
    array2: np.ndarray | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class DummySession:
    """
    In-memory session storage for testing session CRUD operations.
    """

    def __init__(self):
        self.store = {}

    def add_item(self, obj, key):
        """
        Store an object under `key`.
        """
        self.store[key] = obj

    def __getitem__(self, key):
        """
        Return the object stored under `key` (raises KeyError if missing).
        """
        return self.store[key]

    def remove_item(self, key):
        """
        Remove the object stored under `key` (raises KeyError if missing).
        """
        del self.store[key]


def verify_storage_and_get_saved_json(mock_connection):
    """
    Retrieve the last JSON payload passed to `put_objects` and returns the resulting dict.

    Parameters
    ----------
    mock_connection : MagicMock
        An S3-style mock that has been called with `put_objects()`.

    Returns
    -------
    dict
        The Python object obtained by `json.loads` of the saved payload.
    """
    args, _ = mock_connection.put_objects.call_args
    payload_json = args[2][0]
    payload = json.loads(payload_json)
    return payload


@pytest.fixture
def handler_with_session(task_handler):
    """
    Attach a DummySession instance to a TaskHandler and return both.
    """
    session = DummySession()
    task_handler.task_session = session
    return task_handler, session


# test 1 - progress, status, dataset_ids, session_token
def test_updates_db(task_handler, mock_connection):
    """
    Verify that task_handler correctly store:
        - progress
        - status
        - output_dataset_ids
        - time_completed
        - session_token
    """
    task_handler.progress = 0.75
    task_handler.status = "RUNNING"
    task_handler.output_dataset_ids = [
        "dataset-id1",
        "dataset-id2",
        "dataset-id3",
    ]
    task_handler.time_completed = "1.23"
    task_handler.session_token = "uuid1"
    payload = verify_storage_and_get_saved_json(mock_connection)

    assert (
        payload["progress"] == 0.75
    ), f"Expected 'progress' to be '0.75', got {payload['progress']!r}"
    assert (
        payload["status"] == "RUNNING"
    ), f"Expected 'status' to be 'RUNNING', got {payload['status']!r}"
    assert payload["output_dataset_ids"] == [
        "dataset-id1",
        "dataset-id2",
        "dataset-id3",
    ], (
        f"Expected 'output_dataset_ids' to be '['dataset-id1', 'dataset-id2', 'dataset-id3']', "
        f"got {payload['output_dataset_ids']!r}"
    )
    assert (
        payload["time_completed"] == "1.23"
    ), f"Expected 'time_completed' to be '1.23', got {payload['time_completed']!r}"
    assert (
        payload["session_token"] == "uuid1"
    ), f"Expected 'session_token' to be 'uuid1', got {payload['session_token']!r}"


# Test 2 - Mark as Completed
def test_mark_as_completed(task_handler, mock_connection):
    """
    Veify that 'mark_as_completed':
        - set 'progress' to 1.0
        - set 'status to' 'COMPLETED'
        - keep 'output_dataset_ids' same
    """
    task_handler.output_dataset_ids = ["test"]
    task_handler.mark_as_completed(task_handler.output_dataset_ids)
    assert (
        task_handler._progress == 1.0
    ), f"Expected 'progress' to be '1.0', got {task_handler._progress!r}"
    assert (
        task_handler._status == "COMPLETED"
    ), f"Expected 'status' to be 'COMPLETED', got {task_handler._status!r}"
    assert task_handler._output_dataset_ids == [
        "test"
    ], f"Expected 'output_dataset_ids' to be '['test']', got {task_handler._output_dataset_ids!r}"
    payload = verify_storage_and_get_saved_json(mock_connection)
    assert (
        payload["progress"] == 1.0
    ), f"Expected 'progress' to be '1.0', got {payload['progress']!r}"
    assert (
        payload["status"] == "COMPLETED"
    ), f"Expected 'status' to be 'COMPLETED', got {payload['status']!r}"
    assert payload["output_dataset_ids"] == [
        "test"
    ], f"Expected 'output_dataset_ids' to be '['test']', got {payload['output_dataset_ids']!r}"
    try:
        datetime.fromisoformat(payload["time_completed"])
    except:
        pytest.fail(f"'time_completed' is not valid ISO-formatted date/time")


# Test 3 - Mark as Failed
def test_mark_as_failed(task_handler, mock_connection):
    """
    Veify that 'mark_as_failed':
        - set 'progress' to 1.0
        - set 'status to' 'FAILED'
        - keep 'output_dataset_ids' same
    """
    task_handler.mark_as_failed()
    assert (
        task_handler._progress == 1.0
    ), f"Expected 'progress' to be '1.0', got {task_handler._progress!r}"
    assert (
        task_handler._status == "FAILED"
    ), f"Expected 'status' to be 'FAILED', got {task_handler._status!r}"
    assert (
        task_handler._output_dataset_ids == []
    ), f"Expected 'output_dataset_ids' to be '[]', got {task_handler._output_dataset_ids!r}"
    payload = verify_storage_and_get_saved_json(mock_connection)
    assert (
        payload["progress"] == 1.0
    ), f"Expected 'progress' to be '1.0', got {payload['progress']!r}"
    assert (
        payload["status"] == "FAILED"
    ), f"Expected 'status' to be 'FAILED', got {payload['status']!r}"
    assert (
        payload["output_dataset_ids"] == []
    ), f"Expected 'output_dataset_ids' to be '[]', got {payload['output_dataset_ids']!r}"
    try:
        datetime.fromisoformat(payload["time_completed"])
    except:
        pytest.fail(f"'time_completed' is not valid ISO-formatted date/time")


# Test 4 - Test Invalid Progress and Status
def test_invalid_progress_raises(task_handler):
    """
    Verify that invalid status or progress raises ValueError
    """
    with pytest.raises(ValueError):
        task_handler.progress = -0.1
    with pytest.raises(ValueError):
        task_handler.progress = 1.1
    with pytest.raises(ValueError):
        task_handler.status = " "


# Test 5 - Test Fetch Algorithm
def test_fetch_algorithm(task_handler):
    """
    Verify that fetch_algorithm calls the private cached method and registers the runner.
    """
    dummy_runner = MagicMock(name="RunnerInstance")
    dummy_assets = ["asset-1", "asset-2"]
    dummy_json = {
        "algorithm_name": "foo_alg",
        "algorithm_major_version": "1",
        "algorithm_minor_version": "0",
    }

    with patch.object(
        TaskHandler,
        "_TaskHandler__cached_fetch_algorithm",
        return_value=(dummy_runner, dummy_assets, dummy_json),
    ) as mock_cached:

        returned = task_handler.fetch_algorithm("any-id")

    assert (
        returned == dummy_runner
    ), f"Expected returned runner to be the same dummy_runner, got {returned!r}"
    assert task_handler.algorithm_assets == dummy_assets, (
        f"Expected algorithm_assets to be {dummy_assets!r}, "
        f"got {task_handler.algorithm_assets!r}"
    )
    task_handler.set_as_current_task_handler()

    context_task_handler = current_task_handler.get()
    assert (
        context_task_handler == task_handler
    ), f"Expected current_task_handler to be the same task_handler, got {context_task_handler!r}"


# Test 6 - Test __cached_fetch_algorithm
def test_cached_fetch_algorithm_uses_cache(task_handler, mock_connection):
    """
    Verify that the private cached fetch algorithm method caches after first call.
    """
    # Start with cleared Cache
    cache_func = TaskHandler._TaskHandler__cached_fetch_algorithm
    cache_dict = cache_func.__closure__[0].cell_contents
    access_order = cache_func.__closure__[1].cell_contents
    cache_dict.clear()
    access_order.clear()

    class DummyRunner:
        def __new__(cls):
            instance = super().__new__(cls)
            instance.initialize = MagicMock()
            instance._load_assets = MagicMock()
            return instance

    with patch("compox.tasks.TaskHandler.ZipImporter") as mock_import:
        dummy_mod = MagicMock()
        dummy_mod.Runner = DummyRunner
        mock_import.return_value.__enter__.return_value = dummy_mod
        runner1 = task_handler.fetch_algorithm("1")
        calls_first = (
            mock_connection.list_objects.call_count
            + mock_connection.get_objects.call_count
        )

        assert (
            calls_first > 0
        ), f"Expected storage calls on first fetch, got {calls_first}"

        runner2 = task_handler.fetch_algorithm("1")
        calls_second = (
            mock_connection.list_objects.call_count
            + mock_connection.get_objects.call_count
        )

    assert (
        runner1 == runner2
    ), f"Expected same runner instance from cache on second fetch"
    assert (
        calls_second == calls_first
    ), f"Expected no additional storage calls on second fetch, got {calls_second - calls_first} extra"


# Test 7 – Fetch Asset
def test_fetch_asset(task_handler, mock_connection):
    """
    Verify fetch_asset retrieves the correct bytes and calls the proper bucket.
    """
    with patch("importlib.import_module") as mock_import:
        # Create the instance that should have `.initialize`
        mock_runner_instance = MagicMock()
        mock_runner_instance.initialize = MagicMock()

        # Create the Runner class that returns the instance
        mock_runner_class = MagicMock(return_value=mock_runner_instance)

        # Create the dummy module with the Runner class
        dummy_module = MagicMock()
        dummy_module.Runner = mock_runner_class

        # Patch importlib to return the dummy module
        mock_import.return_value = dummy_module

        task_handler.fetch_algorithm("1")
        result = task_handler.fetch_asset(0)

        assert (
            result.read() == b"dummy binary content"
        ), f"Expected asset bytes to be 'b'dummy binary content'', got {result.read()!r}"
        mock_connection.get_objects.assert_any_call("asset-store", ["asset-1"])


# Test 8 – Fetch Data (All keys)
def test_fetch_data_all_keys(task_handler):
    """
    Verify fetch_data returns all arrays when no keys specified.
    """
    result = task_handler.fetch_data(["file-id-1"], DummySchema)

    assert isinstance(result, list), f"Expected list, got {type(result)!r}"
    assert len(result) == 1, f"Expected list of length 1, got {result!r}"

    data = result[0]
    try:
        np.testing.assert_array_equal(data["array1"], np.array([1, 2]))
    except:
        pytest.fail(f"'array1' should be array([1,2]), got {data['array1']!r}")

    try:
        np.testing.assert_array_equal(data["array2"], np.array([3, 4, 5]))
    except:
        pytest.fail(
            f"'array2' should be array([3,4,5]), got {data['array2']!r}"
        )


# Test 9 – Fetch Data (One key)
def test_fetch_data_specific_key(task_handler):
    """
    Verify fetch_data returns only the specified key and sets missing to None.
    """
    result = task_handler.fetch_data(["file-id-2"], DummySchema, "array1")

    assert isinstance(result, list), f"Expected list, got {type(result)!r}"
    assert len(result) == 1, f"Expected list of length 1, got {result!r}"

    data = result[0]
    try:
        np.testing.assert_array_equal(data["array1"], np.array([1, 2]))
    except:
        pytest.fail(f"'array1' should be array([1,2]), got {data['array1']!r}")

    assert (
        data["array2"] == None
    ), f"Expected missing key 'array2' to be None, got {data.get('array2')!r}"


# Test 10 – Fetch Data (invalid HDF 5)
def test_fetch_data_invalid_hdf5_raises(task_handler, mock_connection):
    """
    Verify fetch_data raises on invalid HDF5 bytes.
    """
    mock_connection.get_objects.side_effect = lambda bucket, keys: [
        b"not a valid hdf5"
    ]
    with pytest.raises(Exception):
        task_handler.fetch_data(["bad-file"], DummySchema)


# Test 11 – Fetch Data (parallel)
def test_fetch_data_parallel(task_handler):
    """
    Verify parallel fetch_data increments stats and returns correct list.
    """
    ids = ["id1", "id2", "id3"]
    result = task_handler.fetch_data(ids, DummySchema, parallel=True)

    assert isinstance(result, list), f"Expected list, got {type(result)!r}"
    assert (
        len(result) == 3
    ), f"Expected list of length 3, got list of length {len(result)!r}"
    assert (
        task_handler.file_fetching_stats["count"] == 3
    ), f"Expected fetch count 3, got {task_handler.file_fetching_stats['count']}"

    data = result[0]
    try:
        np.testing.assert_array_equal(data["array1"], np.array([1, 2]))
    except:
        pytest.fail(f"'array1' should be array([1,2]), got {data['array1']!r}")

    try:
        np.testing.assert_array_equal(data["array2"], np.array([3, 4, 5]))
    except:
        pytest.fail(
            f"'array2' should be array([3,4,5]), got {data['array2']!r}"
        )


# Test 12 - Post Data
def test_post_data(task_handler, mock_connection):
    """
    Verify post_data uploads HDF5 with correct datasets and returns IDs.
    """
    # Create 2 test data dictionaries
    data1 = {"array1": np.array([1, 2, 3]), "array2": np.array([10, 20, 30])}

    data2 = {"array1": np.array([-1, -2]), "array2": None}

    # Patch generate_uuid
    with patch("compox.tasks.TaskHandler.generate_uuid") as mock_uuid:
        mock_uuid.side_effect = ["id1", "id2"]
        out_ids = task_handler.post_data([data1, data2], DummySchema)

        assert out_ids == [
            "id1",
            "id2",
        ], f"Expected output IDs '['id1','id2']', got {out_ids!r}"
        assert (
            mock_connection.put_objects.call_count == 3
        ), f"Expected 2 put_objects calls, got {mock_connection.put_objects.call_count}"

        call_args_list = mock_connection.put_objects.call_args_list
        uploaded_0 = call_args_list[0]
        uploaded_1 = call_args_list[1]
        uploaded_2 = call_args_list[2]
        bucket0, keys0, _ = uploaded_0[0]
        bucket1, keys1, vals1 = uploaded_1[0]
        bucket2, keys2, vals2 = uploaded_2[0]

        assert (
            bucket0 == "execution-store"
        ), f"Expected first put_object call to be 'execution-store', got {bucket0!r}"
        assert keys0 == [
            "test-task-id"
        ], f"Expected execution-store key to be test-task-id, got {keys0!r}"
        assert (
            bucket1 == "data-store"
        ), f"Expected first put_object call to be 'data-store', got {bucket1!r}"
        assert keys1 == [
            "id1"
        ], f"Expected data-store key to be '['id1']', got {keys1!r}"
        assert (
            bucket2 == "data-store"
        ), f"Expected second put_object call to be 'data-store', got {bucket2!r}"
        assert keys2 == [
            "id2"
        ], f"Expected data-store key to be '['id2']', got {keys2!r}"

        # Dictionary 1
        h5_bytes_1 = vals1[0]
        fh1 = io.BytesIO(h5_bytes_1)

        with h5py.File(fh1, "r") as f1:
            try:
                np.testing.assert_array_equal(
                    data1["array1"], np.array([1, 2, 3])
                )
            except:
                pytest.fail(
                    f"'array1' should be array([1,2,3]), got {data1['array1']!r}"
                )

            try:
                np.testing.assert_array_equal(
                    data1["array2"], np.array([10, 20, 30])
                )
            except:
                pytest.fail(
                    f"'array2' should be array([10,20,30]), got {data1['array2']!r}"
                )

        # Dictionary 2
        h5_bytes_2 = vals2[0]
        fh2 = io.BytesIO(h5_bytes_2)

        with h5py.File(fh2, "r") as f2:
            try:
                np.testing.assert_array_equal(
                    data2["array1"], np.array([-1, -2])
                )
            except:
                pytest.fail(
                    f"'array1' should be array([-1,-2]), got {data2['array1']!r}"
                )
            assert (
                "array2" not in f2.keys()
            ), f"Expected 'array2' missing, keys: {list(f2.keys())!r}"


# Test 13 - Post invalid data
def test_post_data_validation_error(task_handler):
    """
    Verify post_data raises ValidationError on schema mismatch.
    """
    data1 = {"array1": np.array([1, 2, 3]), "array2": "not an array"}

    # Patch generate_uuid
    with patch("compox.tasks.TaskHandler.generate_uuid") as mock_uuid:
        mock_uuid.side_effect = ["id1", "id2"]
        with pytest.raises(ValidationError):
            task_handler.post_data(data1, DummySchema)


# test 14 - Post data + Exception
def test_post_data_storage_exception(task_handler, mock_connection):
    """
    Verify post_data propagates storage exceptions.
    """
    mock_connection.put_objects.side_effect = RuntimeError("S3 down")
    with pytest.raises(RuntimeError):
        task_handler.post_data(
            [{"array1": np.array([0]), "array2": np.array([1])}], DummySchema
        )


# Test 15 - Save Item to Session
def test_save_item_to_session(handler_with_session):
    """
    Verify save_item_to_session stores obj under given key.
    """
    handler, session = handler_with_session
    assert (
        "my_key" not in session.store
    ), f"Did not expect 'my_key' in 'session.store'"
    handler.save_item_to_session(obj={"foo": 123}, key="my_key")
    assert (
        "my_key" in session.store
    ), f"Expect 'my_key' to be in 'session.store'"
    assert session.store["my_key"] == {
        "foo": 123
    }, f"Expected session['my_key'] to be ('foo' : 123), got {session.store.get('my_key')!r}"


# Test 16 - Load Item from Session
def test_load_item_from_session(handler_with_session):
    """
    Verify load_item_from_session returns stored object.
    """
    handler, session = handler_with_session
    session.store["my_key2"] = [1, 2, 3]
    result = handler.load_item_from_session("my_key2")
    assert result == [1, 2, 3], f"Expected loaded '[1,2,3]', got {result!r}"
    assert (
        "my_key2" in session.store
    ), f"Expect 'my_key2' to be in 'session.store'"


# Test 17 - Remove Item from Session
def test_remove_item_from_session(handler_with_session):
    """
    Verify remove_item_from_session deletes the key.
    """
    handler, session = handler_with_session
    session.store["my_key3"] = "value"
    handler.remove_item_from_session("my_key3")
    assert (
        "my_key3" not in session.store
    ), f"Expected 'my_key3' removed from session.store"


# Test 18 - Load Nonexistent key
def test_load_nonexistent_key_raises(handler_with_session):
    """
    Verify loading missing key raises KeyError.
    """
    handler, session = handler_with_session
    session.store.clear()

    with pytest.raises(KeyError):
        handler.load_item_from_session("my_key4")


# Test 19 - Remove Nonexistent Key
def test_remove_nonexistent_key_raises(handler_with_session):
    """
    Verify removing missing key raises KeyError.
    """
    handler, session = handler_with_session
    session.store.clear()

    with pytest.raises(KeyError):
        handler.remove_item_from_session("my_key5")


# Test 20 - Load/Remove/Save Key=None
def test_use_none_key(handler_with_session):
    """
    Verify session operations raise when session is None.
    """
    handler, _ = handler_with_session
    handler.task_session = None

    with pytest.raises(Exception):
        handler.load_item_from_session("unknown_key")
    with pytest.raises(Exception):
        handler.save_item_to_session("unknown_key")
    with pytest.raises(Exception):
        handler.remove_item_from_session("unknown_key")


# Test 21 - Test log
def test_update_log_writes_to_db(task_handler, mock_connection):
    """
    Verify update_log stores stream contents in database.
    """
    task_handler.logger.info("some message")
    task_handler.update_log()
    payload = verify_storage_and_get_saved_json(mock_connection)
    assert (
        "some message" in payload["log"]
    ), f"Expected 'some message' in log, got {payload.get('log')!r}"


# Test 22 - Test get Device (no cuda --> get cpu)
def test_get_device_no_cuda(task_handler):
    """
    Verify _get_device returns 'cpu' when CUDA unavailable.
    """
    with patch(
        "compox.tasks.TaskHandler.check_system_gpu_availability",
        return_value=(False, None),
    ):
        algo = {"default_device": "gpu", "supported_devices": ["cpu", "gpu"]}

        dev = task_handler._TaskHandler__get_device(
            algo, execution_device_override=None
        )
        assert dev == "cpu", f" Expected device to be 'cpu', got {dev!r}"


# Test 23 - Test get Device (cuda available)
def test_get_device_cuda_available(task_handler):
    """
    Verify _get_device returns 'cpu' when CUDA available.
    """
    with patch(
        "compox.tasks.TaskHandler.check_system_gpu_availability",
        return_value=(True, None),
    ):
        algo = {"default_device": "gpu", "supported_devices": ["cpu", "gpu"]}

        dev = task_handler._TaskHandler__get_device(
            algo, execution_device_override=None
        )
        assert dev == "cuda", f" Expected device to be 'cuda', got {dev!r}"


# Test 24 - Test get Device (cuda available, but override --> get cpu)
def test_get_device_respects_override(task_handler):
    """
    Verify _get_device returns 'cpu' when CUDA available with override.
    """
    with patch(
        "compox.tasks.TaskHandler.check_system_gpu_availability",
        return_value=(True, None),
    ):
        algo = {"default_device": "gpu", "supported_devices": ["cpu", "gpu"]}

        dev = task_handler._TaskHandler__get_device(
            algo, execution_device_override="cpu"
        )
        assert dev == "cpu", f" Expected device to be 'cpu', got {dev!r}"
