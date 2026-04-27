"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from tests.test_utils import (
    prepare_random_payload,
    post_files,
    post_samples,
    delete_file,
    delete_sample,
    prepare_sample,
)


# Test 1: Basic Positive Test
def test_basic_positive_delete(server_url):
    base_url = f"{server_url}/api/v0/sample"
    file_url = f"{server_url}/api/v0/files"
    payload = prepare_random_payload(10, 256, 256)
    responses = post_files(file_url, payload)
    file_ids = []
    for response in responses:
        print(response.json())
        assert response.status_code == 200
        file_ids.append(response.json()["file_id"])
    payload = prepare_sample(file_ids[:5], file_ids[5:])
    response = post_samples(base_url, payload)[0]
    assert response.status_code == 200
    # test core
    print(response.json()["sample_id"])
    response = delete_sample(base_url, response.json()["sample_id"])
    assert response.status_code == 200
    # cleanup
    for file_id in file_ids:
        response = delete_file(file_url, file_id)
        assert response.status_code == 200


# Test 2: Test invalid sample_id
def test_invalid_sample_id(server_url):
    base_url = f"{server_url}/api/v0/sample"
    sample_id = "invalid"
    # test core
    response = delete_sample(base_url, sample_id)
    assert response.status_code == 404
    assert "detail" in response.json()


# Test 3: Multiple delete on same sample_id
def test_delete_already_deleted_sample(server_url):
    base_url = f"{server_url}/api/v0/sample"
    file_url = f"{server_url}/api/v0/files"
    payload = prepare_random_payload(2, 256, 256)
    responses = post_files(file_url, payload)
    file_ids = []
    for response in responses:
        print(response.json())
        assert response.status_code == 200
        file_ids.append(response.json()["file_id"])
    payload = prepare_sample(file_ids[:1], file_ids[1:])
    response = post_samples(base_url, payload)[0]
    assert response.status_code == 200
    sample_id = response.json()["sample_id"]
    # test core
    response = delete_sample(base_url, sample_id)
    assert response.status_code == 200
    response = delete_sample(base_url, sample_id)
    assert response.status_code == 404
    assert "detail" in response.json()
    # cleanup
    for file_id in file_ids:
        response = delete_file(file_url, file_id)
        assert response.status_code == 200


