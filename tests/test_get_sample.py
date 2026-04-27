"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from tests.test_utils import (
    is_valid_uuid,
    prepare_random_payload,
    post_files,
    post_samples,
    get_sample,
    prepare_sample,
    delete_file,
    delete_sample,
)


# Test 1: Basic Positive Test
def test_basic_positive_get_sample(server_url):
    base_url = f"{server_url}/api/v0/sample"
    file_url = f"{server_url}/api/v0/files"
    files_payload = prepare_random_payload(10, 256, 256)
    responses = post_files(file_url, files_payload)
    file_ids = []
    for response in responses:
        print(response.json())
        assert response.status_code == 200
        file_ids.append(response.json()["file_id"])
    sample_payload = prepare_sample(file_ids[:5], file_ids[5:])
    response = post_samples(base_url, sample_payload)[0]
    print(response.json())
    assert response.status_code == 200
    assert "sample_id" in response.json()
    assert is_valid_uuid(response.json()["sample_id"])
    sample_id = response.json()["sample_id"]
    # test core
    response = get_sample(base_url, sample_id)
    assert response.status_code == 200
    # cleanup
    delete_sample(base_url, sample_id)
    for file_id in file_ids:
        response = delete_file(file_url, file_id)
        assert response.status_code == 200


# Test 2: Test invalid sample_id
def test_invalid_sample_id(server_url):
    base_url = f"{server_url}/api/v0/sample"
    sample_id = "invalid"
    # test core
    response = get_sample(base_url, sample_id)
    print(response.json())
    assert response.status_code == 404
    assert "detail" in response.json()
