# SPDX-FileCopyrightText: 2025 Tsolo.io
#
# SPDX-License-Identifier: Apache-2.0

import hashlib
import json
import logging
import time
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import ClassVar

from cycax_server.internal.settings import Settings

# Filenames
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

    def __init__(self, jobs_path: Path, job_id: str):
        self._jobs_path: Path = jobs_path
        self._last_updated: float | None = None
        self.job_id: str = job_id
        self.artifacts: dict = {}
        self.part_name: str | None = None
        self._job_path: Path = jobs_path / job_id
        self._tasks: dict = {}
        self.state: JobState = JobState.CREATED
        self.state_changed_at = time.time()
        self.feature_count: int = 0
        self.parts_count: int = 0

    def __str__(self) -> str:
        if self.part_name:
            return f"{self.job_id} ({self.part_name})"
        else:
            return self.job_id

    def dump(self, *, short=False) -> dict:
        """Dump the job information to a dictionary."""
        info = {}
        info["id"] = self.job_id
        info["type"] = "job"
        info["attributes"] = {}
        if self._last_updated is None:
            last = datetime.now(tz=UTC).isoformat()
        else:
            last = datetime.fromtimestamp(self._last_updated, tz=UTC).isoformat()
        info["attributes"]["last_updated"] = last
        info["attributes"]["state"] = self.get_state()
        info["attributes"]["part_name"] = self.part_name
        info["attributes"]["feature_count"] = self.feature_count
        info["attributes"]["part_count"] = self.parts_count
        if not short:
            info["attributes"]["path"] = self._job_path
        return info

    def get_age_hours(self) -> int:
        """Get the number of full hours that elapsed since the job was last updated.

        Returns:
            int: The number of full hours that elapsed since the job was last updated.
        """
        if self._last_updated is None:
            return 0
        delta = datetime.now(tz=UTC) - datetime.fromtimestamp(self._last_updated, tz=UTC)
        return int(delta.total_seconds() // 3600)

    def get_spec(self) -> dict:
        """Load the job specification from disk and return it."""
        spec_file = self._job_path / PART_FN
        if self._last_updated is None:
            self._last_updated = self._job_path.stat().st_mtime
        return json.loads(spec_file.read_text())

    def get_state(self) -> dict:
        state_map = {"job": self.state, "tasks": self._tasks}
        return state_map

    def load(self):
        """Load the job from disk and initialize the Job object."""
        spec = self.get_spec()
        self.part_name = spec.get("name")
        features = spec.get("feature_count")
        if features:
            self.feature_count = len(features)
        else:
            self.feature_count = 0
        parts = spec.get("part_count")
        if parts:
            self.part_count = len(parts)
        else:
            self.part_count = 0

        state_path = self._job_path / STATE_FN
        if state_path.exists():
            state_map = json.loads(state_path.read_text())
        else:
            state_map = {}

        self.state = state_map.get("job", JobState.CREATED)
        for task_name, task_state in state_map.get("tasks", {}).items():
            self.set_task_state(task_name, task_state, save=False)
        self.set_state()
        self.save_state()

    def save_state(self):
        """Save the Job state to disk."""
        states = {}
        states["job"] = self.state
        states["tasks"] = self._tasks
        state_path = self._job_path / STATE_FN
        state_path.write_text(json.dumps(states))

    def set_state(self, state: JobState | str | None = None, *, save: bool = True):
        """Directly update the Job state or look through task states and set accordingly.

        Args:
            state: The state to set the Job to.
            save: Whether to save the state to disk.
        """
        if state is None:
            task_state_set = set(self._tasks.values())
            if len(task_state_set) == 0:
                state = JobState.CREATED
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
        if self.state != state:
            self.state_changed_at = time.time()
            self.state = state
        if save:
            self.save_state()

    def reset(self):
        self.state = JobState.CREATED
        self.state_changed_at = time.time()
        for key in self._tasks.keys():
            self.set_task_state(key, TaskState.CREATED)

    def get_tasks(self) -> dict:
        """Get the tasks associated with this Job."""
        return self._tasks

    def set_task_state(self, name: str, state: TaskState | None = None, *, save: bool = True):
        """Set the state of a task.

        Args:
            name: The name of the task.
            state: The state to set the task to.
            save: Whether to save the state to disk.
        """
        if state is None:
            # Make sure it exists.
            state = self._tasks.get(name.lower(), TaskState.CREATED)
        self._tasks[name.lower()] = state
        if save:
            self.set_state()
            self.save_state()

    def save_spec(self, spec: dict):
        """Save the Part Spec this Job is for."""
        self.part_name = spec.get("name")
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
        return list(self.artifacts.keys())

    def get_artifact_path(self, name: str) -> Path:
        return self.artifacts[name]


class JobManager:
    """Keep track of all jobs."""

    _jobs: ClassVar[dict[str, Job]] = {}
    _parts: ClassVar[dict[str, dict[str, str]]] = {}

    def __init__(self, settings: Settings):
        self._settings = settings
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
                job = Job(jobs_path=self._jobs_path, job_id=job_path.name)
                job.load()
                logging.warning("Add job %s", str(job))
                self._jobs[job.job_id] = job

    def update_part_job_relation(self, job: Job):
        part_name = job.part_name
        if part_name:
            if part_name not in self._parts:
                self._parts[part_name] = {}
            self._parts[part_name][job.job_id] = {"job_id": job.job_id}
            self._parts[part_name]["."] = {"job_id": job.job_id}

    def list_parts(self) -> list[str]:
        return list(self._parts.keys())

    def get_part(self, part_name: str) -> dict[str, dict]:
        return self._parts.get(part_name, {})

    def list_jobs(
        self, states_in: list[JobState] | None = None, states_not_in: list[JobState] | None = None
    ) -> list[Job]:
        """List the jobs in the registry.

        The jobs returned can be filtered by state.

        Args:
            states_in: A list of states to filter the jobs by. Only return jobs with these states.
            states_not_in: A list of states to exclude from the jobs. Do not return jobs with these states.

        Returns:
            A list of jobs.
        """
        return_jobs = []
        states_not_in_set = set(states_not_in) if states_not_in else set()
        for job in self._jobs.values():
            # logging.warning("job %s, states_in %s, states_not_in %s", job, states_in, states_not_in)
            if job.state in states_not_in_set:
                continue
            if states_in is None or job.state in states_in:
                return_jobs.append(job)
        return return_jobs

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def delete_job(self, job_id: str):
        """Delete a Job.

        Will delete a job even if it is not in the registry.
        Does not error if a job delete is requested for a job that does not exist.

        Args:
            name: The name/id of the Job.
        """
        if job_id in self._jobs:
            job = self.get_job(job_id)
            if job:
                job.delete()
            del self._jobs[job_id]
        else:
            job = Job(job_id=job_id, jobs_path=self._jobs_path)
            job.delete()

    def job_from_spec(self, spec: dict) -> Job:
        """Create a new Job from a Part Specification."""
        # We only use the features to determine the JOB ID.
        sha1hash = hashlib.sha1()  # noqa: S324
        features_spec = spec.get("features", [])
        sha1hash.update(json.dumps(features_spec).encode())
        parts_spec = spec.get("parts", [])
        sha1hash.update(json.dumps(parts_spec).encode())
        job_id = sha1hash.hexdigest()

        if job_id in self._jobs:
            job = self._jobs[job_id]
        else:
            job = Job(job_id=job_id, jobs_path=self._jobs_path)
            job.save_spec(spec)
            if features_spec:
                # TODO: Replace hardcoded freecad with config driven.
                job.set_task_state("freecad", TaskState.CREATED)  # For now: Give every parts job a FreeCAD task.
                job.feature_count = len(features_spec)
            if parts_spec:
                # TODO: Replace hardcoded blender with config driven.
                job.set_task_state("blender", TaskState.CREATED)  # For now: Give every assembly job a Blender task.
                job.part_count = len(parts_spec)
            self._jobs[job_id] = job
            self.update_part_job_relation(job)
        return job
