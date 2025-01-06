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
        self._jobs_path: Path = jobs_path
        self.name: str = name
        self.artifacts: dict = {}
        self._part_name: str = None
        self._job_path: Path = jobs_path / name
        self._tasks: dict = {}
        self._state: JobState = None

    def __str__(self) -> str:
        if self._part_name:
            return f"{self.name} ({self._part_name})"
        else:
            return self.name

    def dump(self, *, short=False) -> dict:
        info = {}
        info["id"] = self.name
        info["type"] = "job"
        info["attributes"] = {}
        info["attributes"]["state"] = self.get_state()
        info["attributes"]["part_name"] = self._part_name
        if not short:
            info["attributes"]["path"] = self._job_path
        return info

    def get_spec(self) -> dict:
        spec_file = self._job_path / PART_FN
        return json.loads(spec_file.read_text())

    def get_state(self) -> dict:
        state_map = {"job": self._state, "tasks": self._tasks}
        return state_map

    def load(self):
        spec = self.get_spec()
        self._part_name = spec.get("name")
        state_path = self._job_path / STATE_FN
        if state_path.exists():
            state_map = json.loads(state_path.read_text())
        else:
            state_map = {}

        self._state = state_map.get("job", JobState.CREATED)
        for task_name, task_state in state_map.get("tasks", {}).items():
            self.set_task_state(task_name, task_state, save=False)
        self.set_state()
        self.save_state()

    def save_state(self):
        states = {}
        states["job"] = self._state
        states["tasks"] = self._tasks
        state_path = self._job_path / STATE_FN
        state_path.write_text(json.dumps(states))

    def set_state(self, state: JobState | None = None, *, save: bool = True):
        """Directly update the Job state or look through task states and set accordingly."""
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
        self._state = state
        if save:
            self.save_state()

    def get_tasks(self) -> dict:
        return self._tasks

    def set_task_state(self, name: str, state: TaskState | None = None, *, save: bool = True):
        if state is None:
            state = TaskState.CREATED
        self._tasks[name.lower()] = state
        if save:
            self.set_state()
            self.save_state()

    def save_spec(self, spec: dict):
        """Save the Part Spec this Job is for."""
        self._part_name = spec.get("name")
        self._job_path.mkdir(exist_ok=True, parents=True)
        spec_file = self._job_path / PART_FN
        spec_file.write_text(json.dumps(spec))

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
            part_spec = job_path / PART_FN
            if part_spec.exists():
                job = Job(jobs_path=self._jobs_path, name=job_path.name)
                job.load()
                logging.warning("Add job %s", str(job))
                self._jobs[job.name] = job

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

        if name in self._jobs:
            job = self._jobs[name]
        else:
            job = Job(name=name, jobs_path=self._jobs_path)
            job.save_spec(spec)
            job.set_task_state("freecad")  # For now: Give every job a FreeCAD task.
            self._jobs[name] = job
        return job
