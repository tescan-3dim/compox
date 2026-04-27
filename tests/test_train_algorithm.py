"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from tests.test_utils import (
    is_valid_uuid,
    prepare_random_payload,
    prepare_sample,
    post_files,
    post_samples,
    get_algorithm_id,
    train_algorithm,
    delete_file,
    delete_sample,
)


# Test 1: Basic Positive Test
def test_basic_positive_algorithm_training(server_url):
    base_url = f"{server_url}/api/v0/train-algorithm"
    file_url = f"{server_url}/api/v0/files"
    sample_url = f"{server_url}/api/v0/sample"
    algorithm_url = f"{server_url}/api/v0/algorithm"
    # prepare files
    payload = prepare_random_payload(10, 256, 256)
    responses = post_files(file_url, payload)
    file_ids = []
    for response in responses:
        print(response.json())
        assert response.status_code == 200
        file_ids.append(response.json()["file_id"])
    # prepare dataset
    payload = prepare_sample(file_ids[:5], file_ids[5:])
    response = post_samples(sample_url, payload)[0]
    assert response.status_code == 200
    sample_id = response.json()["sample_id"]
    # prepare algorithm id
    response = get_algorithm_id(algorithm_url, "foo", "1")
    print(response.json())
    assert response.status_code == 200
    algorithm_id = response.json()["algorithm_id"]
    # test core
    response = train_algorithm(base_url, algorithm_id, [sample_id])
    print(response.json())
    assert response.status_code == 200
    assert "training_id" in response.json()
    assert is_valid_uuid(response.json()["training_id"])
    # cleanup
    response = delete_sample(sample_url, sample_id)
    assert response.status_code == 200
    for file_id in file_ids:
        response = delete_file(file_url, file_id)
        assert response.status_code == 200

# Test 2: Test invalid algorithm_id
def test_invalid_algorithm_id(server_url):
    base_url = f"{server_url}/api/v0/train-algorithm"
    file_url = f"{server_url}/api/v0/files"
    sample_url = f"{server_url}/api/v0/sample"
    # prepare files
    payload = prepare_random_payload(10, 256, 256)
    responses = post_files(file_url, payload)
    file_ids = []
    for response in responses:
        print(response.json())
        assert response.status_code == 200
        file_ids.append(response.json()["file_id"])
    # prepare sample
    payload = prepare_sample(file_ids[:5], file_ids[5:])
    response = post_samples(sample_url, payload)[0]
    assert response.status_code == 200
    sample_id = response.json()["sample_id"]
    # prepare algorithm id
    algorithm_id = "invalid"
    # test core
    response = train_algorithm(base_url, algorithm_id, [sample_id])
    print(response.json())
    assert response.status_code == 404
    assert "detail" in response.json()
    # cleanup
    response = delete_sample(sample_url, sample_id)
    assert response.status_code == 200
    for file_id in file_ids:
        response = delete_file(file_url, file_id)
        assert response.status_code == 200


# Test 3: Test invalid sample_id
def test_invalid_sample_id(server_url):
    base_url = f"{server_url}/api/v0/train-algorithm"
    algorithm_url = f"{server_url}/api/v0/algorithm"
    # prepare samples
    sample_ids = ["invalid", "invalid"]
    # prepare algorithm id
    response = get_algorithm_id(algorithm_url, "foo", "1")
    print(response.json())
    assert response.status_code == 200
    algorithm_id = response.json()["algorithm_id"]
    # test core
    response = train_algorithm(base_url, algorithm_id, sample_ids)
    print(response.json())
    assert response.status_code == 404
    assert "detail" in response.json()


# Test 4: Test missing algorithm_id
def test_missing_algorithm_id(server_url):
    base_url = f"{server_url}/api/v0/train-algorithm"
    file_url = f"{server_url}/api/v0/files"
    sample_url = f"{server_url}/api/v0/sample"
    # prepare files
    payload = prepare_random_payload(10, 256, 256)
    responses = post_files(file_url, payload)
    file_ids = []
    for response in responses:
        print(response.json())
        assert response.status_code == 200
        file_ids.append(response.json()["file_id"])
    # prepare sample
    payload = prepare_sample(file_ids[:5], file_ids[5:])
    response = post_samples(sample_url, payload)[0]
    assert response.status_code == 200
    sample_id = response.json()["sample_id"]
    # test core
    response = train_algorithm(base_url, [sample_id])
    print(response.json())
    assert response.status_code == 422
    assert "detail" in response.json()
    # cleanup
    response = delete_sample(sample_url, sample_id)
    assert response.status_code == 200
    for file_id in file_ids:
        response = delete_file(file_url, file_id)
        assert response.status_code == 200


# Test 5: Test missing sample_id
def test_missing_sample_id(server_url):
    base_url = f"{server_url}/api/v0/train-algorithm"
    algorithm_url = f"{server_url}/api/v0/algorithm"
    # prepare algorithm id
    response = get_algorithm_id(algorithm_url, "foo", "1")
    print(response.json())
    assert response.status_code == 200
    algorithm_id = response.json()["algorithm_id"]
    # test core
    response = train_algorithm(base_url, algorithm_id)
    print(response.json())
    assert response.status_code == 422
    assert "detail" in response.json()


# Test 6: Test multiple consecutive trainings
def test_multiple_consecutive_training_starts(server_url):
    base_url = f"{server_url}/api/v0/train-algorithm"
    file_url = f"{server_url}/api/v0/files"
    sample_url = f"{server_url}/api/v0/sample"
    algorithm_url = f"{server_url}/api/v0/algorithm"
    n = 10
    for i in range(n):
        # prepare files
        payload = prepare_random_payload(10, 256, 256)
        responses = post_files(file_url, payload)
        file_ids = []
        for response in responses:
            print(response.json())
            assert response.status_code == 200
            file_ids.append(response.json()["file_id"])
        # prepare sample
        payload = prepare_sample(file_ids[:5], file_ids[5:])
        response = post_samples(sample_url, payload)[0]
        assert response.status_code == 200
        sample_id = response.json()["sample_id"]
        # prepare algorithm id
        response = get_algorithm_id(algorithm_url, "foo", "1")
        print(response.json())
        assert response.status_code == 200
        algorithm_id = response.json()["algorithm_id"]
        # test core
        response = train_algorithm(base_url, algorithm_id, [sample_id])
        print(response.json())
        assert response.status_code == 200
        assert "training_id" in response.json()
        assert is_valid_uuid(response.json()["training_id"])
        # cleanup
        response = delete_sample(sample_url, sample_id)
        assert response.status_code == 200
        for file_id in file_ids:
            response = delete_file(file_url, file_id)
            assert response.status_code == 200
