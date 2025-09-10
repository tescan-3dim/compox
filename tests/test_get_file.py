"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from tests.test_utils import (
    is_valid_uuid,
    prepare_random_payload,
    post_files,
    get_file,
)


# Test 1: Basic Positive Test
def test_basic_positive_get_file(server_url):
    base_url = f"{server_url}/api/v0/files"
    payload = prepare_random_payload(10, 256, 256)
    responses = post_files(base_url, payload)
    for response in responses:
        print(response.json())
        assert response.status_code == 200
        assert "file_id" in response.json()
        assert is_valid_uuid(response.json()["file_id"])
        file_id = response.json()["file_id"]
        response = get_file(base_url, file_id)
        assert response.status_code == 200


# Test 2: Test invalid file_id
def test_invalid_file_id(server_url):
    base_url = f"{server_url}/api/v0/files"
    file_id = "invalid"
    response = get_file(base_url, file_id)
    print(response.json())
    assert response.status_code == 404
    assert "detail" in response.json()
