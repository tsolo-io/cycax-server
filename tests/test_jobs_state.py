"""Test the Job states and tasks."""

from fastapi.testclient import TestClient

from cycax_server.main import app

from . import utils

client = TestClient(app)


def get_job_tasks(client: TestClient, job_id: str):
    response = client.get(f"/jobs/{job_id}/tasks")
    assert response.status_code == 200
    tasks = response.json().get("data")
    assert isinstance(tasks, list)
    return tasks


def set_job_task(client: TestClient, job_id: str, taskname: str, state: str | None = None):
    if state is None:
        state = "created"
    response = client.post(f"/jobs/{job_id}/tasks", json={"state": "Created", "name": taskname})
    assert response.status_code == 200


def test_state_update():
    job_id = "ce5d2d744108a6221a7094d5fc2c6086f633afc1"
    utils.remove_job(client, job_id)
    # Create a new Post.
    feature = {
        "name": "cube",
        "type": "add",
        "side": None,
        "x": 0,
        "y": 0,
        "z": 0,
        "x_size": 9,
        "y_size": 9,
        "z_size": 9,
        "center": False,
    }
    data = {"name": "test-part1", "features": [feature]}
    response = client.post("/jobs", json=data)
    assert response.status_code == 200
    tasks = get_job_tasks(client, job_id)
    assert len(tasks) == 1, "There is already tasks"
    set_job_task(client, job_id, "sillycad")
    tasks = get_job_tasks(client, job_id)
    task_names = [v["id"] for v in tasks]
    assert "sillycad" in task_names
    # Cleanup
    utils.remove_job(client, job_id)
