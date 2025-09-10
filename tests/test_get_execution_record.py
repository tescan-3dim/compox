"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import time
import pytest

from tests.test_utils import (
    is_valid_uuid,
    prepare_random_payload,
    post_files,
    execute_algorithm,
    get_algorithm_id,
    get_execution_record,
)


# Test 1: Basic Positive Test
def test_basic_positive(server_url):
    base_url = f"{server_url}/api/v0/executions"
    execute_url = f"{server_url}/api/v0/execute-algorithm"
    file_url = f"{server_url}/api/v0/files"
    algorithm_url = f"{server_url}/api/v0/algorithm"
    payload = prepare_random_payload(10, 256, 256)
    responses = post_files(file_url, payload)

    file_ids = []
    for response in responses:
        print(response.json())
        assert response.status_code == 200
        file_ids.append(response.json()["file_id"])

    response = get_algorithm_id(algorithm_url, "foo", "1")
    print(response.json())
    assert response.status_code == 200
    algorithm_id = response.json()["algorithm_id"]

    response = execute_algorithm(execute_url, file_ids, algorithm_id)
    print(response.json())
    assert response.status_code == 200
    execution_id = response.json()["execution_id"]

    response = get_execution_record(base_url, execution_id)
    print(response.json())
    assert response.status_code == 200


# Test 2: Test valid fields in output
def test_valid_response_fields(server_url):
    base_url = f"{server_url}/api/v0/executions"
    execute_url = f"{server_url}/api/v0/execute-algorithm"
    file_url = f"{server_url}/api/v0/files"
    algorithm_url = f"{server_url}/api/v0/algorithm"
    payload = prepare_random_payload(10, 256, 256)
    responses = post_files(file_url, payload)

    file_ids = []
    for response in responses:
        print(response.json())
        assert response.status_code == 200
        file_ids.append(response.json()["file_id"])

    response = get_algorithm_id(algorithm_url, "foo", "1")
    print(response.json())
    assert response.status_code == 200
    algorithm_id = response.json()["algorithm_id"]

    response = execute_algorithm(execute_url, file_ids, algorithm_id)
    print(response.json())
    assert response.status_code == 200

    execution_id = response.json()["execution_id"]
    response = get_execution_record(base_url, execution_id)
    print(response.json())
    assert response.status_code == 200

    assert "execution_id" in response.json()
    assert "algorithm_id" in response.json()
    assert "input_dataset_ids" in response.json()
    assert "output_dataset_ids" in response.json()
    assert "status" in response.json()
    assert "progress" in response.json()
    assert "time_started" in response.json()
    assert "time_completed" in response.json()
    assert "log" in response.json()


# Test 3: Test invalid execution_id
def test_invalid_execution_id(server_url):
    base_url = f"{server_url}/api/v0/executions"
    execution_id = "invalid"
    response = get_execution_record(base_url, execution_id)
    print(response.json())
    assert response.status_code == 404
    assert "detail" in response.json()


# Test 4: Test single task
@pytest.mark.algorithms
def test_single_task_execution(server_url):
    base_url = f"{server_url}/api/v0/executions"
    execute_url = f"{server_url}/api/v0/execute-algorithm"
    file_url = f"{server_url}/api/v0/files"
    algorithm_url = f"{server_url}/api/v0/algorithm"
    payload = prepare_random_payload(10, 256, 256)
    responses = post_files(file_url, payload)
    file_ids = []
    for response in responses:
        print(response.json())
        assert response.status_code == 200
        file_ids.append(response.json()["file_id"])

    response = get_algorithm_id(algorithm_url, "dummy_algorithm", "1")
    print(response.json())
    assert response.status_code == 200
    algorithm_id = response.json()["algorithm_id"]

    response = execute_algorithm(execute_url, file_ids, algorithm_id)
    print(response.json())
    assert response.status_code == 200

    execution_id = response.json()["execution_id"]
    response = get_execution_record(base_url, execution_id)

    last_iter_progress = response.json()["progress"]
    while response.json()["status"] != "COMPLETED":

        if response.json()["status"] == "FAILED":
            assert False, "Task failed"
        response = get_execution_record(base_url, execution_id)
        print(response.json())
        assert response.status_code == 200
        progress = response.json()["progress"]
        assert progress >= 0.0 and progress <= 1.0
        assert progress >= last_iter_progress
        last_iter_progress = progress
        time.sleep(0.5)

    print(response.json())
    assert response.status_code == 200
    for output_dataset_id in response.json()["output_dataset_ids"]:
        assert is_valid_uuid(output_dataset_id)


# Test 5: Test multiple tasks
@pytest.mark.algorithms
def test_multiple_tasks(server_url):
    base_url = f"{server_url}/api/v0/executions"
    execute_url = f"{server_url}/api/v0/execute-algorithm"
    file_url = f"{server_url}/api/v0/files"
    algorithm_url = f"{server_url}/api/v0/algorithm"
    n = 10
    task_ids = []
    for i in range(n):
        payload = prepare_random_payload(10, 256, 256)
        responses = post_files(file_url, payload)
        file_ids = []
        for response in responses:
            print(response.json())
            assert response.status_code == 200
            file_ids.append(response.json()["file_id"])

        response = get_algorithm_id(algorithm_url, "dummy_algorithm", "1")
        print(response.json())
        assert response.status_code == 200
        algorithm_id = response.json()["algorithm_id"]

        response = execute_algorithm(execute_url, file_ids, algorithm_id)
        print(response.json())
        assert response.status_code == 200

        task_ids.append(response.json()["execution_id"])

    task_completed = [False] * n
    task_record = [None] * n

    while not all(task_completed):
        for i in range(n):
            if task_completed[i]:
                continue
            response = get_execution_record(base_url, task_ids[i])
            new_record = response.json()
            if task_record[i] is None:
                task_record[i] = new_record
            elif task_record[i]["status"] == "FAILED":
                assert False, "Task failed"
            else:
                assert task_record[i]["progress"] <= new_record["progress"]
                assert (
                    task_record[i]["input_dataset_ids"]
                    == new_record["input_dataset_ids"]
                )
                assert (
                    task_record[i]["algorithm_id"] == new_record["algorithm_id"]
                )
                assert (
                    task_record[i]["execution_id"] == new_record["execution_id"]
                )
                task_record[i] = new_record
            print(response.json())
            assert response.status_code == 200

            if task_record[i]["status"] == "COMPLETED":
                task_completed[i] = True
            time.sleep(0.5)
        time.sleep(0.5)

    for i in range(n):
        for output_dataset_id in task_record[i]["output_dataset_ids"]:
            assert is_valid_uuid(output_dataset_id)
