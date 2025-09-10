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
)


# Test 1: Basic Positive Test
def test_basic_positive_algorithm_execution(server_url):
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
    assert is_valid_uuid(response.json()["execution_id"])


# Test 2: Test invalid algorithm_id
def test_invalid_algorithm_id(server_url):
    base_url = f"{server_url}/api/v0/execute-algorithm"
    file_url = f"{server_url}/api/v0/files"
    payload = prepare_random_payload(10, 256, 256)
    responses = post_files(file_url, payload)
    file_ids = []
    for response in responses:
        print(response.json())
        assert response.status_code == 200
        file_ids.append(response.json()["file_id"])

    algorithm_id = "invalid"

    response = execute_algorithm(base_url, file_ids, algorithm_id)
    print(response.json())
    assert response.status_code == 404
    assert "detail" in response.json()


# Test 3: Test invalid file_id
def test_invalid_file_id(server_url):
    base_url = f"{server_url}/api/v0/execute-algorithm"
    algorithm_url = f"{server_url}/api/v0/algorithm"
    file_ids = ["invalid", "invalid"]

    response = get_algorithm_id(algorithm_url, "foo", "1")
    print(response.json())
    assert response.status_code == 200
    algorithm_id = response.json()["algorithm_id"]

    response = execute_algorithm(base_url, file_ids, algorithm_id)
    print(response.json())
    assert response.status_code == 404
    assert "detail" in response.json()


# Test 4: Test missing algorithm_id
def test_missing_algorithm_id(server_url):
    base_url = f"{server_url}/api/v0/execute-algorithm"
    file_url = f"{server_url}/api/v0/files"
    payload = prepare_random_payload(10, 256, 256)
    responses = post_files(file_url, payload)
    file_ids = []
    for response in responses:
        print(response.json())
        assert response.status_code == 200
        file_ids.append(response.json()["file_id"])

    response = execute_algorithm(base_url, file_ids)
    print(response.json())
    assert response.status_code == 422
    assert "detail" in response.json()


# Test 5: Test missing file_id
def test_missing_file_id(server_url):
    base_url = f"{server_url}/api/v0/execute-algorithm"
    algorithm_url = f"{server_url}/api/v0/algorithm"
    response = get_algorithm_id(algorithm_url, "foo", "1")
    print(response.json())
    assert response.status_code == 200
    algorithm_id = response.json()["algorithm_id"]

    response = execute_algorithm(base_url, algorithm_id)
    print(response.json())
    assert response.status_code == 422
    assert "detail" in response.json()


# Test 6: Test multiple consecutive executions
def test_multiple_consecutive_execution_starts(server_url):
    base_url = f"{server_url}/api/v0/execute-algorithm"
    file_url = f"{server_url}/api/v0/files"
    algorithm_url = f"{server_url}/api/v0/algorithm"
    n = 10
    for i in range(n):
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
        assert is_valid_uuid(response.json()["execution_id"])
