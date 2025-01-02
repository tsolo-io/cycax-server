import hashlib
import json
import logging
from enum import Enum
from pathlib import Path
from typing import ClassVar

from cycax_server.internal.settings import Settings

PART_FN = "part.json"
STATE_FN = "state.json"


class JobState(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"


class TaskState(str, Enum):
    CREATED = "CREATED"
    TAKEN = "TAKEN"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"


class Job:
    """A job."""

    def __init__(self, jobs_path: Path, name: str):
        self._jobs_path = jobs_path
        self.name = name
        self._job_path = jobs_path / name
        self.artifacts = {}
        self._tasks = {}

    def __str__(self) -> str:
        return self.name

    def dump(self, *, short=False) -> dict:
        info = {}
        info["id"] = self.name
        info["type"] = "job"
        info["attributes"] = {}
        info["attributes"]["state"] = self.get_state()
        if not short:
            info["attributes"]["name"] = self.name
            info["attributes"]["path"] = self._job_path
        return info

    def get_spec(self) -> dict:
        spec_file = self._job_path / PART_FN
        return json.loads(spec_file.read_text())

    def get_state(self) -> dict:
        # Very Wrong. Only load on startup.
        state_path = self._job_path / STATE_FN
        if state_path.exists():
            state_map = json.loads(state_path.read_text())
        else:
            state_map = {"job": JobState.CREATED}
        if "tasks" not in state_map:
            state_map["tasks"] = self._tasks
        return state_map

    def set_state(self, state: JobState | None = None):
        """Directly update the Job state."""
        states = self.get_state()
        if state is None:
            task_state_set = set(self._tasks.values())
            if len(task_state_set) == 0:
                state = JobState.CREATE
            elif len(task_state_set) == 1:
                # All tasks have the same state.
                if task_state_set.intersection((TaskState.COMPLETED,)):
                    state = JobState.COMPLETED
                elif task_state_set.intersection((TaskState.CREATED,)):
                    state = JobState.CREATED
                else:
                    state = JobState.RUNNING
            else:
                # When tasks are in different states the Job is running.
                state = JobState.RUNNING
        else:
            states["job"] = state.name
        states["tasks"] = self._tasks
        state_path = self._job_path / STATE_FN
        state_path.write_text(json.dumps(states))

    def get_tasks(self) -> dict:
        return self._tasks

    def set_task_state(self, name: str, state: TaskState | None = None):
        if state is None:
            state = TaskState.CREATED
        self._tasks[name.lower()] = state
        self.set_state()

    def save_spec(self, spec: dict):
        """Save the Part Spec this Job is for."""
        self._job_path.mkdir(exist_ok=True, parents=True)
        spec_file = self._job_path / PART_FN
        spec_file.write_text(json.dumps(spec))
        self.set_state(JobState.CREATED)
        self.set_task_state("freecad")

    def delete(self):
        """Delete the Job, remove all files and then remove the directory."""
        if self._job_path.exists():
            for filepath in self._job_path.iterdir():
                filepath.unlink()
            self._job_path.rmdir()

    def artifact_filepath(self, name: str) -> Path:
        # TODO: Check the artifact path.
        filepath = self._job_path / name
        self.artifacts[name] = filepath
        return filepath

    def list_artifacts(self) -> list[str]:
        return self.artifacts.keys()

    def get_artifact_path(self, name: str) -> Path:
        return self.artifacts[name]


class JobManager:

    _jobs: ClassVar[dict] = {}
    _parts: ClassVar[dict] = {}

    def __init__(self, settings: Settings):
        self._settings = settings
        self._spool_path = self._settings.var_dir / "freecad_spool"
        self._parts_path = self._settings.var_dir / "parts"
        self._jobs_path = self._settings.var_dir / "jobs"

    def update_from_disk(self):
        var_dir = self._settings.var_dir
        logging.warning("Update from disk: %s.", var_dir)
        # Create directories.
        if not var_dir.exists():
            logging.warning("VarDir %s does not exist, creating.....", var_dir)
            var_dir.mkdir(parents=True)
        if not self._jobs_path.exists():
            logging.warning("JobsDir %s does not exist, creating.....", self._jobs_path)
            self._jobs_path.mkdir()
        if not self._parts_path.exists():
            logging.warning("PartsDir %s does not exist, creating.....", self._parts_path)
            self._parts_path.mkdir()

        for job_path in self._jobs_path.iterdir():
            job = Job(jobs_path=self._jobs_path, name=job_path.name)
            logging.warning("Add job %s", job)
            self._jobs[job.name] = job
        for part in self._parts_path.iterdir():
            logging.warning("Add part %s", part.name)
            self._parts[part.name] = {"path": part}

    def list_jobs(self) -> list[Job]:
        return self._jobs.values()

    def get_job(self, name: str) -> Job:
        return self._jobs.get(name)

    def delete_job(self, name: str):
        """Delete a Job.

        Will delete a job even if it is not in the registry.
        Does not error if a job delete is requested for a job that does not exist.

        Args:
            name: The name/id of the Job.
        """
        if name in self._jobs:
            job = self.get_job(name)
            job.delete()
            del self._jobs[name]
        else:
            job = Job(name=name, jobs_path=self._jobs_path)
            job.delete()

    def job_from_spec(self, spec: dict) -> Job:
        """Create a new Job from a Part Specification."""
        # We only use the features to determine the JOB ID.
        spec_str = json.dumps(spec.get("features", []))
        sha1hash = hashlib.sha1()  # noqa: S324
        sha1hash.update(spec_str.encode())
        name = sha1hash.hexdigest()
        job = Job(name=name, jobs_path=self._jobs_path)
        job.save_spec(spec)
        self._jobs[name] = job
        return job
