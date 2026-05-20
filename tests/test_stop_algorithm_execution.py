"""
Copyright 2026 TESCAN GROUP, a.s.
All rights reserved
"""

import time
from tests.test_utils import (
    is_valid_uuid,
    prepare_random_payload,
    post_files,
    execute_algorithm,
    get_algorithm_id,
    stop_algorithm_execution,
    get_execution_record,
)


# Test 1: Test stop execution
def test_stop_execution(server_url):
    base_url = f"{server_url}/api/v0/execute-algorithm"
    file_url = f"{server_url}/api/v0/files"
    algorithm_url = f"{server_url}/api/v0/algorithm"
    payload = prepare_random_payload(10, 256, 256)
    responses = post_files(file_url, payload)
    file_ids = []
    for response in responses:
        print(response.json())
        assert response.status_code == 200
        file_ids.append(response.json()["file_id"])

    response = get_algorithm_id(algorithm_url, "stoppable_foo", "1")
    print(response.json())
    assert response.status_code == 200
    algorithm_id = response.json()["algorithm_id"]

    response = execute_algorithm(base_url, file_ids, algorithm_id)
    print(response.json())
    assert response.status_code == 200
    assert "execution_id" in response.json()
    execution_id = response.json()["execution_id"]
    assert is_valid_uuid(execution_id)

    response = stop_algorithm_execution(
        f"{server_url}/api/v0/executions", execution_id
    )
    print(response.json())
    assert response.status_code == 200
    assert response.json()["detail"] == "Stop request posted successfully"

    while True:
        status = (
            get_execution_record(
                f"{server_url}/api/v0/executions", execution_id
            )
            .json()["status"]
            .upper()
        )
        if status in {"STOPPED", "FAILED", "COMPLETED"}:
            break
        time.sleep(1)

    # Verify execution status is 'STOPPED'
    response = get_execution_record(
        f"{server_url}/api/v0/executions", execution_id
    )
    print(response.json())
    assert response.status_code == 200
    assert response.json()["status"] == "STOPPED"


# Test 2: Test stop execution with invalid execution_id
def test_stop_execution_invalid_id(server_url):
    execution_id = "invalid"

    response = stop_algorithm_execution(
        f"{server_url}/api/v0/executions", execution_id
    )
    print(response.json())
    assert response.status_code == 404
    assert "detail" in response.json()


# Test 3: Test already finished execution stop
def test_stop_already_finished_execution(server_url):
    base_url = f"{server_url}/api/v0/execute-algorithm"
    file_url = f"{server_url}/api/v0/files"
    algorithm_url = f"{server_url}/api/v0/algorithm"
    payload = prepare_random_payload(10, 256, 256)
    responses = post_files(file_url, payload)
    file_ids = []
    for response in responses:
        print(response.json())
        assert response.status_code == 200
        file_ids.append(response.json()["file_id"])

    response = get_algorithm_id(algorithm_url, "stoppable_foo", "1")
    print(response.json())
    assert response.status_code == 200
    algorithm_id = response.json()["algorithm_id"]

    response = execute_algorithm(base_url, file_ids, algorithm_id)
    print(response.json())
    assert response.status_code == 200
    assert "execution_id" in response.json()
    execution_id = response.json()["execution_id"]
    assert is_valid_uuid(execution_id)

    # Wait for execution to complete
    while True:
        status = (
            get_execution_record(
                f"{server_url}/api/v0/executions", execution_id
            )
            .json()["status"]
            .upper()
        )
        if status in {"COMPLETED", "FAILED"}:
            break
        time.sleep(1)

    response = stop_algorithm_execution(
        f"{server_url}/api/v0/executions", execution_id
    )
    print(response.json())
    assert response.status_code == 400
    status = (
        get_execution_record(f"{server_url}/api/v0/executions", execution_id)
        .json()["status"]
        .upper()
    )
    assert (
        response.json()["detail"]
        == f"Execution in state {status} cannot be stopped"
    )


# Test 4: Test multiple stop requests
def test_multiple_stop_requests(server_url):
    base_url = f"{server_url}/api/v0/execute-algorithm"
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

    response = execute_algorithm(base_url, file_ids, algorithm_id)
    print(response.json())
    assert response.status_code == 200
    assert "execution_id" in response.json()
    execution_id = response.json()["execution_id"]
    assert is_valid_uuid(execution_id)

    # First stop request
    response = stop_algorithm_execution(
        f"{server_url}/api/v0/executions", execution_id
    )
    print(response.json())
    assert response.status_code == 200
    assert response.json()["detail"] == "Stop request posted successfully"

    while True:
        status = (
            get_execution_record(
                f"{server_url}/api/v0/executions", execution_id
            )
            .json()["status"]
            .upper()
        )
        if status in {"STOPPED", "FAILED", "COMPLETED"}:
            break
        time.sleep(1)

    # Second stop request
    response = stop_algorithm_execution(
        f"{server_url}/api/v0/executions", execution_id
    )
    print(response.json())
    assert response.status_code == 400
    status = (
        get_execution_record(f"{server_url}/api/v0/executions", execution_id)
        .json()["status"]
        .upper()
    )
    assert (
        response.json()["detail"]
        == f"Execution in state {status} cannot be stopped"
    )
