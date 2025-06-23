# SPDX-FileCopyrightText: 2025 Tsolo.io
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import logging
import time

from cycax_server.internal.job_manager import JobManager, JobState
from cycax_server.internal.settings import Settings


async def prune_old_jobs(manager: JobManager, settings: Settings):
    logging.info("Checking if there are any old jobs that need to be deleted.")
    for job in manager.list_jobs():
        if job.get_age_hours() > settings.keep_age_hours:
            manager.delete_job(job.job_id)
        await asyncio.sleep(0)


async def prune_stuck_jobs(manager: JobManager, *_args):
    logging.info("Checking if there are any stuck jobs that need to be set to CREATED.")
    # Reset Jobs marked as completed but that has no artifacts.
    for job in manager.list_jobs(states_in=[JobState.COMPLETED]):
        if len(job.list_artifacts()) == 0:
            job.reset()

    await asyncio.sleep(0)  # Service requests
    # Reset Jobs that have been in running for 5 minutes.
    for job in manager.list_jobs(states_in=[JobState.RUNNING]):
        logging.info("Running job %s", job.job_id)
        age = time.time() - job.state_changed_at
        if age > 300:  # noqa: PLR2004 - 300s is 5 minutes.
            job.reset()


async def run_background_tasks(*, running: bool, manager: JobManager, settings: Settings):
    logging.warning("Starting background tasks")
    bg_task_spec_list = [
        {"last": time.time(), "every": 600, "func": prune_old_jobs},
        {"last": time.time(), "every": 60, "func": prune_stuck_jobs},
    ]
    while running:
        await asyncio.sleep(30)
        for bg_task in bg_task_spec_list:
            if (time.time() - bg_task["last"]) > bg_task["every"]:
                try:
                    await bg_task["func"](manager, settings)
                except Exception as error:
                    logging.error("Error running background task %s: %s", bg_task["func"].__name__, error)
                bg_task["last"] = time.time()
    await asyncio.sleep(1)
