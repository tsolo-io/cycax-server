from fastapi.testclient import TestClient

from cycax_server.dependencies import get_settings
from cycax_server.main import app

from . import utils

client = TestClient(app)


def test_settings():
    settings = get_settings()
    var_dir = settings.var_dir
    assert var_dir.exists()


def test_list_jobs():
    response = client.get("/jobs")
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data["data"], list)


def test_post_job():
    job_id = "cb891ab1ca8a68ce8610f0a1085e53fd2d4741f2"
    utils.remove_job(client, job_id)
    # Create a new Post.
    data = {"name": "test-part1", "features": []}
    response = client.post("/jobs", json=data)
    assert response.status_code == 200
    reply = response.json().get("data", {})
    assert reply["id"] == job_id
    assert reply["attributes"]["state"]["job"] == "CREATED"
    # Cleanup
    utils.remove_job(client, job_id)


def test_job_list():
    for number in range(1, 3):
        feature = {
            "name": "cube",
            "type": "add",
            "side": None,
            "x": 0,
            "y": 0,
            "z": 0,
            "x_size": number,
            "y_size": number,
            "z_size": number,
            "center": False,
        }
        data = {"name": f"test-part-{number}", "features": [feature]}
        response = client.post("/jobs", json=data)
        assert response.status_code == 200
    response = client.get("/jobs/")
    assert response.status_code == 200
    jobs = response.json().get("data")
    assert isinstance(jobs, list)
    assert len(jobs) > 1

    job_ids = [job["id"] for job in jobs]
    for check_id in ("ecbeb873a2d8611f300e2f8df877e8d77a9cd98c", "b2feb2b22c131b9d3e57ded026535b908e149495"):
        assert check_id in job_ids
        client.delete(f"/jobs/{check_id}")
