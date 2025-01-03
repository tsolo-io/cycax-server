import logging
import shutil
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from cycax_server.dependencies import JobManager, get_job_manager

router = APIRouter()


class PartSpec(BaseModel):
    name: str | None = Field(None, alias="id")
    features: list[dict]


class TaskState(BaseModel):
    name: str
    state: str  # TODO: Make this one of the Enum values.


@router.get("/jobs", tags=["Jobs"])
async def read_jobs(manager: Annotated[JobManager, Depends(get_job_manager)]):
    """ """
    reply = {"data": []}
    for job in manager.list_jobs():
        reply["data"].append(job.dump(short=True))
    return reply


@router.post("/jobs", tags=["Jobs"])
async def create_job(spec: PartSpec, manager: Annotated[JobManager, Depends(get_job_manager)]):
    """ """
    job = manager.job_from_spec(spec.model_dump())
    return {"data": job.dump(short=True)}


@router.get("/jobs/{job_id}", tags=["Jobs"])
async def read_job(job_id: str, manager: Annotated[JobManager, Depends(get_job_manager)]):
    """ """
    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"data": job.dump()}


@router.delete("/jobs/{job_id}", tags=["Jobs"])
async def delete_job(job_id: str, manager: Annotated[JobManager, Depends(get_job_manager)]):
    """ """
    manager.delete_job(job_id)
    data = {"id": job_id, "type": "job", "attributes": {"state": {"job": "DELETED"}}}
    return {"data": data}


@router.get("/jobs/{job_id}/tasks", tags=["Jobs"])
async def job_list_tasks(job_id: str, manager: Annotated[JobManager, Depends(get_job_manager)]):
    """ """
    job = manager.get_job(job_id)
    states = job.get_state()
    data = []
    for task_id, task_state in states["tasks"].items():
        data.append({"id": task_id, "type": "task", "attributes": {"state": task_state}})
    return {"data": data}


@router.get("/jobs/{job_id}/tasks/{task_id}", tags=["Jobs"])
async def job_get_task_state(job_id: str, task_id: str, manager: Annotated[JobManager, Depends(get_job_manager)]):
    """ """
    job = manager.get_job(job_id)
    states = job.get_state()
    state = states["tasks"][task_id]
    # TODO: RAISE 404 if not found.
    return {"data": {"id": task_id, "attributes": {"state": state}}}


@router.post("/jobs/{job_id}/tasks", tags=["Jobs"])
async def task_set_job_state(job_id: str, task: TaskState, manager: Annotated[JobManager, Depends(get_job_manager)]):
    """ """
    job = manager.get_job(job_id)
    job.set_task_state(task.name, task.state)
    return {}


@router.get("/jobs/{job_id}/spec", tags=["Jobs"])
async def task_spec(job_id: str, manager: Annotated[JobManager, Depends(get_job_manager)]):
    """ """
    job = manager.get_job(job_id)
    spec = job.get_spec()
    return {"data": spec}


@router.get("/jobs/{job_id}/artifacts", tags=["Jobs"])
async def task_list_artifacts(job_id: str, manager: Annotated[JobManager, Depends(get_job_manager)]):
    """ """
    job = manager.get_job(job_id)
    artifacts = []
    for artifact in job.list_artifacts():
        artifacts.append({"id": artifact, "type": "artifact"})
    return {"data": artifacts}


@router.post("/jobs/{job_id}/artifacts", tags=["Jobs"])
async def task_upload_artifacts(
    job_id: str,
    upload_file: UploadFile,
    filename: Annotated[str, Form()],
    manager: Annotated[JobManager, Depends(get_job_manager)],
):
    """ """
    job = manager.get_job(job_id)
    logging.error(upload_file)
    logging.error(filename)
    destination = job.artifact_filepath(filename)
    shutil.copyfileobj(upload_file.file, destination.open("wb"))
    logging.info("Saved to %s", destination)
    return {}


@router.get("/jobs/{job_id}/artifacts/{artifact_name}", tags=["Jobs"])
async def task_download_artifacts(
    job_id: str, artifact_name: str, manager: Annotated[JobManager, Depends(get_job_manager)]
):
    """ """
    job = manager.get_job(job_id)
    apath = job.get_artifact_path(artifact_name)
    return FileResponse(apath, filename=artifact_name)
