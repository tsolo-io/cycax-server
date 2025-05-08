import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from cycax_server.dependencies import get_job_manager, get_settings
from cycax_server.internal.background import run_background_tasks
from cycax_server.routers import jobs


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """
    This is the lifespan of the api.

    Args:
        app: application the lifespan needs to be applied to.
    """
    settings = get_settings()
    manager = get_job_manager()
    manager.update_from_disk()
    running = True
    bg_task = asyncio.create_task(run_background_tasks(running=running, manager=manager, settings=settings))
    yield
    running = False
    bg_task.cancel()
    await bg_task


app = FastAPI(lifespan=lifespan)

Instrumentator(app).instrument(app).expose(app, include_in_schema=False, should_gzip=True)

instrumentator = Instrumentator().instrument(app)

app.include_router(router=jobs.router)
