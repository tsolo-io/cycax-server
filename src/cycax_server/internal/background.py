# SPDX-FileCopyrightText: 2025 Tsolo.io
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import logging
import time

from cycax_server.internal.job_manager import JobManager
from cycax_server.internal.settings import Settings


async def prune_old_jobs(manager: JobManager, settings: Settings):
    logging.info("Checking if there are any old jobs that need to be deleted.")
    for job in manager.list_jobs():
        if job.get_age_hours() > settings.keep_age_hours:
            manager.delete_job(job.job_id)
        await asyncio.sleep(0)


async def run_background_tasks(*, running: bool, manager: JobManager, settings: Settings):
    logging.warning("Starting background tasks")
    bg_task_spec_list = [{"last": time.time(), "every": 6000, "func": prune_old_jobs}]
    while running:
        await asyncio.sleep(30)
        for bg_task in bg_task_spec_list:
            if time.time() - bg_task["last"] > bg_task["every"]:
                await bg_task["func"](manager, settings)
                bg_task["last"] = time.time()
    await asyncio.sleep(1)
