from cycax_server.internal.job_manager import JobManager
from cycax_server.internal.settings import Settings

settings = Settings()


def get_settings() -> Settings:
    return settings


manager = JobManager(settings)


def get_job_manager() -> JobManager:
    return manager
