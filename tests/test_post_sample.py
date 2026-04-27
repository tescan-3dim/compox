"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from tests.test_utils import (
    is_valid_uuid,
    prepare_random_payload,
    post_files,
    post_samples,
    delete_file,
    delete_sample,
    prepare_sample,
)
import numpy as np


# Test 1: Basic Positive Test
def test_basic_positive_post_sample(server_url):
    base_url = f"{server_url}/api/v0/sample"
    file_url = f"{server_url}/api/v0/files"
    files_payload = prepare_random_payload(2, 256, 256)
    responses = post_files(file_url, files_payload)

    file_ids = []
    for response in responses:
        print(response.json())
        assert response.status_code == 200
        file_ids.append(response.json()["file_id"])
    # test core
    sample_payload = prepare_sample([file_ids[0]], [file_ids[1]])
    response = post_samples(base_url, sample_payload)[0]
    print(response.json())
    assert response.status_code == 200
    assert "sample_id" in response.json()
    assert is_valid_uuid(response.json()["sample_id"])
    sample_id = response.json()["sample_id"]
    # cleanup
    response = delete_sample(base_url, sample_id)
    assert response.status_code == 200
    for file_id in file_ids:
        response = delete_file(file_url, file_id)
        assert response.status_code == 200


# Test 2: Basic Positive Test With Tags
def test_basic_positive_post_sample_with_tags(server_url):
    base_url = f"{server_url}/api/v0/sample"
    file_url = f"{server_url}/api/v0/files"
    files_payload = prepare_random_payload(6, 256, 256)
    responses = post_files(file_url, files_payload)
    file_ids = []
    for response in responses:
        print(response.json())
        assert response.status_code == 200
        file_ids.append(response.json()["file_id"])
    # test core
    sample_payload = prepare_sample(file_ids[:3], file_ids[3:], ["tag1", "tag2"])
    response = post_samples(base_url, sample_payload)[0]
    print(response.json())
    assert response.status_code == 200
    assert "sample_id" in response.json()
    assert is_valid_uuid(response.json()["sample_id"])
    sample_id = response.json()["sample_id"]
    # cleanup
    response = delete_sample(base_url, sample_id)
    assert response.status_code == 200
    for file_id in file_ids:
        response = delete_file(file_url, file_id)
        assert response.status_code == 200


# Test 3: Test invalid payload
def test_invalid_payload(server_url):
    base_url = f"{server_url}/api/v0/sample"
    payload = ["invalid"]
    # test core
    response = post_samples(base_url, payload)[0]
    print(response.json())
    assert response.status_code == 422
    assert "detail" in response.json()


# Test 4: Test multiple valid different payloads
def test_multiple_valid_different_payloads(server_url):
    base_url = f"{server_url}/api/v0/sample"
    file_url = f"{server_url}/api/v0/files"
    files_to_delete_ids = []
    sample_ids = []
    n = 10
    for i in range(n):
        num_files_half = np.random.randint(1, 10)
        files_payload = prepare_random_payload(num_files_half * 2, 256, 256)
        responses = post_files(file_url, files_payload)
        file_ids = []
        for response in responses:
            # print(response.json())  # commented - produces too many prints
            assert response.status_code == 200
            file_ids.append(response.json()["file_id"])
            files_to_delete_ids.append(response.json()["file_id"])
        # test core
        current_payload = prepare_sample(file_ids[:num_files_half], file_ids[num_files_half:], ["atag"])
        response = post_samples(base_url, current_payload)[0]
        print(response.json())
        assert response.status_code == 200
        assert "sample_id" in response.json()
        sample_id = response.json()["sample_id"]
        assert is_valid_uuid(sample_id)
        sample_ids.append(sample_id)
    # cleanup
    for sample_id in sample_ids:
        response = delete_sample(base_url, sample_id)
        assert response.status_code == 200
    for file_id in files_to_delete_ids:
        response = delete_file(file_url, file_id)
        assert response.status_code == 200
