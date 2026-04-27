"""
Copyright 2025 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import time
import pytest

from tests.test_utils import (
    is_valid_uuid,
    prepare_random_payload,
    prepare_sample,
    post_files,
    post_samples,
    train_algorithm,
    get_algorithm_id,
    get_training_record,
    delete_file,
    delete_sample,
)


# Test 1: Basic Positive Test
def test_basic_positive(server_url):
    base_url = f"{server_url}/api/v0/training"
    train_url = f"{server_url}/api/v0/train-algorithm"
    sample_url = f"{server_url}/api/v0/sample"
    file_url = f"{server_url}/api/v0/files"
    algorithm_url = f"{server_url}/api/v0/algorithm"
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
    response = get_algorithm_id(algorithm_url, "test_training_algorithm", "1")
    print(response.json())
    assert response.status_code == 200
    algorithm_id = response.json()["algorithm_id"]
    # run training
    response = train_algorithm(train_url, algorithm_id, [sample_id])
    print(response.json())
    assert response.status_code == 200
    training_id = response.json()["training_id"]
    # test core
    response = get_training_record(base_url, training_id)
    print(response.json())
    assert response.status_code == 200
    # cleanup
    response = delete_sample(sample_url, sample_id)
    assert response.status_code == 200
    for file_id in file_ids:
        response = delete_file(file_url, file_id)
        assert response.status_code == 200


# Test 2: Test valid fields in output
def test_valid_response_fields(server_url):
    base_url = f"{server_url}/api/v0/training"
    train_url = f"{server_url}/api/v0/train-algorithm"
    sample_url = f"{server_url}/api/v0/sample"
    file_url = f"{server_url}/api/v0/files"
    algorithm_url = f"{server_url}/api/v0/algorithm"
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
    response = get_algorithm_id(algorithm_url, "test_training_algorithm", "1")
    print(response.json())
    assert response.status_code == 200
    algorithm_id = response.json()["algorithm_id"]
    # run training
    response = train_algorithm(train_url, algorithm_id, [sample_id])
    print(response.json())
    assert response.status_code == 200
    # test core
    training_id = response.json()["training_id"]
    response = get_training_record(base_url, training_id)
    print(response.json())
    assert response.status_code == 200
    assert "training_id" in response.json()
    assert "status" in response.json()
    assert "progress" in response.json()
    assert "time_started" in response.json()
    assert "time_completed" in response.json()
    assert "log" in response.json()
    assert "training_data" in response.json()
    assert "state" in response.json()
    assert "output_checkpoint_ids" in response.json()
    # cleanup
    response = delete_sample(sample_url, sample_id)
    assert response.status_code == 200
    for file_id in file_ids:
        response = delete_file(file_url, file_id)
        assert response.status_code == 200


# Test 3: Test invalid training_id
def test_invalid_training_id(server_url):
    base_url = f"{server_url}/api/v0/training"
    training_id = "invalid"
    response = get_training_record(base_url, training_id)
    print(response.json())
    assert response.status_code == 404
    assert "detail" in response.json()


# Test 4: Test single training
@pytest.mark.algorithms
def test_single_task_training(server_url):
    base_url = f"{server_url}/api/v0/training"
    train_url = f"{server_url}/api/v0/train-algorithm"
    sample_url = f"{server_url}/api/v0/sample"
    file_url = f"{server_url}/api/v0/files"
    algorithm_url = f"{server_url}/api/v0/algorithm"
    # preapre files
    payload = prepare_random_payload(10, 256, 256)
    responses = post_files(file_url, payload)
    file_ids = []
    for response in responses:
        print(response.json())
        assert response.status_code == 200
        file_ids.append(response.json()["file_id"])
    # preapre sample
    payload = prepare_sample(file_ids[:5], file_ids[5:])
    response = post_samples(sample_url, payload)[0]
    assert response.status_code == 200
    sample_id = response.json()["sample_id"]
    # prepare algorithm id
    response = get_algorithm_id(algorithm_url, "test_training_algorithm", "1")
    print(response.json())
    assert response.status_code == 200
    algorithm_id = response.json()["algorithm_id"]
    # run training
    response = train_algorithm(train_url, algorithm_id, [sample_id])
    print(response.json())
    assert response.status_code == 200
    # test core
    training_id = response.json()["training_id"]
    response = get_training_record(base_url, training_id)

    last_iter_progress = response.json()["progress"]
    while response.json()["status"] != "COMPLETED":

        if response.json()["status"] == "FAILED":
            assert False, "Task failed"
        response = get_training_record(base_url, training_id)
        print(response.json())
        assert response.status_code == 200
        progress = response.json()["progress"]
        assert progress >= 0.0 and progress <= 1.0
        assert progress >= last_iter_progress
        last_iter_progress = progress
        time.sleep(0.5)

    print(response.json())
    assert response.status_code == 200
    assert is_valid_uuid(response.json()["output_checkpoint_ids"][0])
    # cleanup
    response = delete_sample(sample_url, sample_id)
    assert response.status_code == 200
    for file_id in file_ids:
        response = delete_file(file_url, file_id)
        assert response.status_code == 200


# Test 5: Test multiple training
@pytest.mark.algorithms
def test_multiple_tasks(server_url):
    base_url = f"{server_url}/api/v0/training"
    train_url = f"{server_url}/api/v0/train-algorithm"
    sample_url = f"{server_url}/api/v0/sample"
    file_url = f"{server_url}/api/v0/files"
    algorithm_url = f"{server_url}/api/v0/algorithm"

    n = 10
    training_ids = []
    files_to_remove = []
    samples_to_remove = []
    for i in range(n):
        # prepare files
        payload = prepare_random_payload(10, 256, 256)
        responses = post_files(file_url, payload)
        file_ids = []
        for response in responses:
            print(response.json())
            assert response.status_code == 200
            file_ids.append(response.json()["file_id"])
            files_to_remove.append(response.json()["file_id"])
        # prepare sample
        payload = prepare_sample(file_ids[:5], file_ids[5:])
        response = post_samples(sample_url, payload)[0]
        assert response.status_code == 200
        sample_id = response.json()["sample_id"]
        samples_to_remove.append(sample_id)
        # prepare algorithm id
        response = get_algorithm_id(
            algorithm_url, "test_training_algorithm", "1"
        )
        print(response.json())
        assert response.status_code == 200
        algorithm_id = response.json()["algorithm_id"]
        # run training
        response = train_algorithm(train_url, algorithm_id, [sample_id])
        print(response.json())
        assert response.status_code == 200

        training_ids.append(response.json()["training_id"])

    # test core
    training_completed = [False] * n
    training_record = [None] * n

    while not all(training_completed):
        for i in range(n):
            if training_completed[i]:
                continue
            response = get_training_record(base_url, training_ids[i])
            new_record = response.json()
            if training_record[i] is None:
                training_record[i] = new_record
            elif training_record[i]["status"] == "FAILED":
                assert False, "Task failed"
            else:
                assert training_record[i]["progress"] <= new_record["progress"]
                assert (
                    training_record[i]["training_data"]
                    == new_record["training_data"]
                )
                assert (
                    training_record[i]["training_id"]
                    == new_record["training_id"]
                )
                training_record[i] = new_record
            print(response.json())
            assert response.status_code == 200

            if training_record[i]["status"] == "COMPLETED":
                training_completed[i] = True
            time.sleep(0.5)
        time.sleep(0.5)

    for i in range(n):
        assert is_valid_uuid(training_record[i]["output_checkpoint_ids"][0])

    # cleanup
    for sample_id in samples_to_remove:
        response = delete_sample(sample_url, sample_id)
        assert response.status_code == 200
    for file_id in files_to_remove:
        response = delete_file(file_url, file_id)
        assert response.status_code == 200
