"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

from tests.test_utils import get_all_algorithms


# Test 1: Basic Positive Test
def test_basic_positive_get_all_algorithms(server_url):
    base_url = f"{server_url}/api/v0/algorithm/all"
    response = get_all_algorithms(base_url)
    print(response.json())
    assert response.status_code == 200
    assert len(response.json()) > 0


# Test 2: Test all algorithms have the required fields
def test_all_fields(server_url):
    base_url = f"{server_url}/api/v0/algorithm/all"
    response = get_all_algorithms(base_url)
    print(response.json())
    assert response.status_code == 200
    for algorithm in response.json():
        assert "algorithm_id" in algorithm
        assert "algorithm_name" in algorithm
        assert "algorithm_version" in algorithm
        assert "algorithm_minor_version" in algorithm
        assert "algorithm_input_queue" in algorithm


# Test 3: Test multiple requests
def test_multiple_requests(server_url):
    base_url = f"{server_url}/api/v0/algorithm/all"
    n = 10
    previous_response = None
    for i in range(n):
        response = get_all_algorithms(base_url)
        print(response.json())
        assert response.status_code == 200
        assert len(response.json()) > 0
        for algorithm in response.json():
            assert "algorithm_id" in algorithm
            assert "algorithm_name" in algorithm
            assert "algorithm_version" in algorithm
            assert "algorithm_minor_version" in algorithm
            assert "algorithm_input_queue" in algorithm
        if i > 0:
            assert response.json() == previous_response.json()
        previous_response = response
