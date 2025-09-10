"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from tests.test_utils import (
    is_valid_uuid,
    prepare_random_payload,
    post_files,
    execute_algorithm,
    get_algorithm_id,
    get_execution_record,
    delete_file,
)
import time
import pytest


# Test 1: Test algorithm is succesfully finished
def test_algorithm_execution_finishes(server_url):
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
    assert "execution_id" in response.json()
    assert is_valid_uuid(response.json()["execution_id"])

    execution_id = response.json()["execution_id"]
    response = get_execution_record(base_url, execution_id)
    elapsed_time = 0
    while response.json()["status"] != "COMPLETED":
        print(response.json()["log"])
        assert response.json()["status"] != "FAILED"
        response = get_execution_record(base_url, execution_id)
        time.sleep(0.5)
        elapsed_time += 0.5
        assert elapsed_time < 3


# Test 2: Test single task with big file
@pytest.mark.algorithms
def test_single_task_big_file(server_url):
    base_url = f"{server_url}/api/v0/executions"
    execute_url = f"{server_url}/api/v0/execute-algorithm"
    file_url = f"{server_url}/api/v0/files"
    algorithm_url = f"{server_url}/api/v0/algorithm"
    payload = prepare_random_payload(2, 16000, 16000)
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
            assert False
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
    for file_id in file_ids:
        response = delete_file(file_url, file_id)
        assert response.status_code == 200
    response = get_execution_record(base_url, execution_id)
    assert response.status_code == 200
    for output_dataset_id in response.json()["output_dataset_ids"]:
        response = delete_file(file_url, output_dataset_id)
        assert response.status_code == 200


# Test 3: Test many tasks
@pytest.mark.algorithms
def test_many_medium_files(server_url):
    base_url = f"{server_url}/api/v0/executions"
    execute_url = f"{server_url}/api/v0/execute-algorithm"
    file_url = f"{server_url}/api/v0/files"
    algorithm_url = f"{server_url}/api/v0/algorithm"
    n = 3
    task_ids = []
    for i in range(n):
        payload = prepare_random_payload(2, 8000, 8000)
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
            response = get_execution_record(base_url, task_ids[i])
            new_record = response.json()
            if task_record[i] is None:
                task_record[i] = new_record
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
            elif task_record[i]["status"] == "FAILED":
                assert False
            time.sleep(0.5)
        time.sleep(0.5)

    for i in range(n):
        for output_dataset_id in task_record[i]["output_dataset_ids"]:
            assert is_valid_uuid(output_dataset_id)
            response = delete_file(file_url, output_dataset_id)
            assert response.status_code == 200

    # delete the input files
    for i in range(n):
        for input_dataset_id in task_record[i]["input_dataset_ids"]:
            response = delete_file(file_url, input_dataset_id)
            assert response.status_code == 200


# Test 4: Test 24 hours
@pytest.mark.skip(
    reason="This test is too slow to be run in the standard test suite"
)
def test_24_hours(server_url):
    start_time = time.time()
    while time.time() - start_time < 24 * 60 * 60:
        test_many_medium_files(server_url)
