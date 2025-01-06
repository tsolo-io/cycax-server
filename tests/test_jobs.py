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
    job_id = "97d170e1550eee4afc0af065b78cda302a97674c"
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
    for check_id in ("387ea31e1f26fdeeeb90d335fac48b5cd50beecf", "ed0d31456b5bf9b91e447b2d84af9c4569c33210"):
        assert check_id in job_ids
        client.delete(f"/jobs/{check_id}")
