# SPDX-FileCopyrightText: 2025 Tsolo.io
#
# SPDX-License-Identifier: Apache-2.0

"""Tests the upload, list and download of a Jobs artifacts."""

import tempfile

from fastapi.testclient import TestClient

from cycax_server.main import app

from . import utils

client = TestClient(app)


def file_download(client: TestClient, job_id: str, filename: str, contents: str):
    """Download a artifact and check the contents."""
    response = client.get(f"/jobs/{job_id}/artifacts/{filename}")
    assert response.status_code == 200
    assert response.content == contents.encode()


def file_upload(client: TestClient, job_id: str, filename: str, contents: str):
    """Upload a file and check that it is in the artifacts list."""
    data = {"filename": filename}
    with tempfile.NamedTemporaryFile() as fp:
        fp.write(contents.encode())
        fp.seek(0)
        response = client.post(f"/jobs/{job_id}/artifacts", files={"upload_file": fp}, data=data)
        assert response.status_code == 200

    response = client.get(f"/jobs/{job_id}/artifacts")
    artifact_list = response.json().get("data")
    artifact_ids = [v["id"] for v in artifact_list]
    assert filename in artifact_ids, "The uploaded file is not listed."


def test_post_job():
    # Remove an check
    job_id = "cb891ab1ca8a68ce8610f0a1085e53fd2d4741f2"
    utils.remove_job(client, job_id)
    # Create a new Post.
    data = {"name": "test-part1", "features": []}
    response = client.post("/jobs", json=data)
    assert response.status_code == 200
    filename = "image.dat"
    contents = "1234567890-1234567890"
    file_upload(client, job_id, filename, contents)
    file_download(client, job_id, filename, contents)
    # Cleanup
    utils.remove_job(client, job_id)
