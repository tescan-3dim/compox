"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from tests.test_utils import (
    prepare_random_payload,
    post_files,
    delete_file,
)


# Test 1: Basic Positive Test
def test_basic_positive_post_delete(server_url):
    request_url = f"{server_url}/api/v0/files"
    payload = prepare_random_payload(10, 256, 256)
    responses = post_files(request_url, payload)
    file_ids = []
    for response in responses:
        print(response.json())
        assert response.status_code == 200
        file_ids.append(response.json()["file_id"])

    for file_id in file_ids:
        response = delete_file(request_url, file_id)
        assert response.status_code == 200


# Test 2: Test invalid file_id
def test_invalid_file_id(server_url):
    request_url = f"{server_url}/api/v0/files"
    file_id = "invalid"
    response = delete_file(request_url, file_id)
    assert response.status_code == 404
    assert "detail" in response.json()


# Test 3: Multiple delete on same file_id
def test_delete_already_deleted_file(server_url):
    request_url = f"{server_url}/api/v0/files"
    payload = prepare_random_payload(1, 256, 256)
    response = post_files(request_url, payload)[0]
    assert response.status_code == 200
    file_id = response.json()["file_id"]
    response = delete_file(request_url, file_id)
    assert response.status_code == 200
    response = delete_file(request_url, file_id)
    assert response.status_code == 404
    assert "detail" in response.json()
