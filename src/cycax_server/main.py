from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from cycax_server.dependencies import get_job_manager
from cycax_server.routers import jobs


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """
    This is the lifespan of the api.

    Args:
        app: application the lifespan needs to be applied to.
    """
    manager = get_job_manager()
    manager.update_from_disk()
    # asyncio.create_task(run_prometheus_updates())
    yield


app = FastAPI(lifespan=lifespan)

Instrumentator(app).instrument(app).expose(app, include_in_schema=False, should_gzip=True)

instrumentator = Instrumentator().instrument(app)

app.include_router(router=jobs.router)
