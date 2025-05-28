# SPDX-FileCopyrightText: 2025 Tsolo.io
#
# SPDX-License-Identifier: Apache-2.0

"""Basic test utilities."""


def remove_job(client, job_id: str):
    # Remove an check
    response = client.delete(f"/jobs/{job_id}")
    assert response.status_code == 200
    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 404
