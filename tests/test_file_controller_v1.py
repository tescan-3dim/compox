"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import requests
from tests.test_utils import prepare_random_payload, post_files


def test_get_upload_url_ok(server_url):
    endpoint_url = f"{server_url}/api/v1/files"
    file_name = "new_file_name"

    response = requests.get(f"{endpoint_url}/{file_name}/upload-url")

    assert response.status_code == 200
    assert response.json()["url"] is not None


def test_get_download_ok(server_url):
    endpoint_url = f"{server_url}/api/v1/files"
    file_name = "existing_file_name"

    base_url = f"{server_url}/api/v0/files"
    payload = prepare_random_payload(1, 256, 256)
    response = post_files(base_url, payload)[0]
    file_name = response.json()["file_id"]

    response = requests.get(f"{endpoint_url}/{file_name}/download-url")

    assert response.status_code == 200
    assert response.json()["url"] is not None


def test_get_download_url_404_when_file_does_not_exist(server_url):
    endpoint_url = f"{server_url}/api/v1/files"
    file_name = "invalid_file_name"
    response = requests.get(f"{endpoint_url}/{file_name}/download-url")

    assert response.status_code == 404


def test_delete_ok(server_url):
    endpoint_url = f"{server_url}/api/v1/files"
    file_name = "existing_file_name"

    base_url = f"{server_url}/api/v0/files"
    payload = prepare_random_payload(1, 256, 256)
    response = post_files(base_url, payload)[0]
    file_name = response.json()["file_id"]

    response = requests.delete(f"{endpoint_url}/{file_name}")

    assert response.status_code == 200


def test_delete_404_when_file_does_not_exist(server_url):
    endpoint_url = f"{server_url}/api/v1/files"
    file_name = "invalid_file_name"

    response = requests.delete(f"{endpoint_url}/{file_name}")

    assert response.status_code == 404
