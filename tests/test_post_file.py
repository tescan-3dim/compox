"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import pytest
from tests.test_utils import (
    is_valid_uuid,
    prepare_random_payload,
    post_files,
    delete_file,
)
from copy import deepcopy


# Test 1: Basic Positive Test
def test_basic_positive_post_file(server_url):
    base_url = f"{server_url}/api/v0/files"
    payload = prepare_random_payload(1, 256, 256)
    response = post_files(base_url, payload)[0]
    print(response.json())
    assert response.status_code == 200
    assert "file_id" in response.json()
    assert is_valid_uuid(response.json()["file_id"])
    file_id = response.json()["file_id"]
    delete_file(base_url, file_id)


# Test 2: Test invalid payload
def test_invalid_payload(server_url):
    base_url = f"{server_url}/api/v0/files"
    payload = ["invalid"]
    response = post_files(base_url, payload)[0]
    print(response.json())
    assert response.status_code == 422
    assert "detail" in response.json()


# Test 3: Test big payload
def test_big_payload(server_url):
    base_url = f"{server_url}/api/v0/files"
    payload = prepare_random_payload(1, 16000, 16000)
    response = post_files(base_url, payload)[0]
    print(response.json())
    assert response.status_code == 200
    assert "file_id" in response.json()
    assert is_valid_uuid(response.json()["file_id"])
    file_id = response.json()["file_id"]
    delete_file(base_url, file_id)


# Test 4: Test multiple valid identical payloads
@pytest.mark.skip(
    reason="This feature is currently not supported in the server"
)
def test_multiple_valid_identical_payloads(server_url):
    base_url = f"{server_url}/api/v0/files"
    n = 100
    payload = prepare_random_payload(50, 256, 256)
    file_ids = []
    previous_response = None
    for i in range(n):
        current_payload = deepcopy(payload)
        response = post_files(base_url, current_payload)[0]
        print(response.json())
        assert response.status_code == 200
        assert "file_id" in response.json()
        assert is_valid_uuid(response.json()["file_id"])
        if i > 0:
            assert response.json() == previous_response.json()
        previous_response = response
        file_ids.append(response.json()["file_id"])
    for file_id in file_ids:
        delete_file(base_url, file_id)


# Test 5: Test multiple valid different payloads
def test_multiple_valid_different_payloads(server_url):
    base_url = f"{server_url}/api/v0/files"
    n = 50
    file_ids = []
    previous_response = None
    for i in range(n):
        payload = prepare_random_payload(1, 1024, 1024)
        response = post_files(base_url, payload)[0]
        print(response.json())
        assert response.status_code == 200
        assert "file_id" in response.json()
        assert is_valid_uuid(response.json()["file_id"])
        if i > 0:
            assert response.json() != previous_response.json()
        previous_response = response
        file_ids.append(response.json()["file_id"])
    for file_id in file_ids:
        delete_file(base_url, file_id)
