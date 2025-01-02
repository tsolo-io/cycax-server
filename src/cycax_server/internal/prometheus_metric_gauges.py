import asyncio
import logging

from prometheus_client import Gauge
from pydantic_settings import BaseSettings
from s3probe.internal.probe import GET, PUT, check_all_to_output, get_clusters
from s3probe.internal.resultstore import ResultStore

s3probe_retries = Gauge(
    "s3probe_retries",
    "Number of retries the probe took to achieve success or timeout.",
    ["storage_id", "bucket", "action", "object"],
)
s3probe_duration = Gauge(
    "s3probe_duration",
    "The amount of time the probe took to achieve its action.",
    ["storage_id", "bucket", "action", "object"],
)
s3probe_size = Gauge(
    "s3probe_size",
    "The size in bytes of the s3probe actions.",
    ["storage_id", "bucket", "action", "object"],
)
s3probe_success = Gauge(
    "s3probe_success",
    "If the request was successful or failed.",
    ["storage_id", "bucket", "action", "object"],
)
s3probe_campaign_duration = Gauge(
    "s3probe_campaign_duration",
    "The amount of time the probe took to achieve its action.",
    ["storage_id", "bucket"],
)


async def update_prometheus(probe_settings: BaseSettings, resultstore: ResultStore):
    """
    Update the prometheus /metric endpoint with the current s3probe successes.
    """

    config = get_clusters(probe_settings.s3p_config_dir)
    resultstore.set_config(config)
    async for metric in check_all_to_output(config, resultstore=resultstore):
        storage_id = metric.get("name", metric["url"])
        if metric["action"] == "bucket":
            s3probe_campaign_duration.labels(storage_id, metric["bucket"]).set(metric["duration"])
        else:
            if "success" in metric:
                success = 1
                size = metric["success"]["size"]
            else:
                success = 0
                size = 0
            s3probe_retries.labels(storage_id, metric["bucket"], metric["action"], metric["object"]).set(
                metric["retries"]
            )
            s3probe_duration.labels(storage_id, metric["bucket"], metric["action"], metric["object"]).set(
                metric["duration"]
            )
            s3probe_success.labels(storage_id, metric["bucket"], metric["action"], metric["object"]).set(success)
            if metric["action"] in (PUT, GET):
                s3probe_size.labels(storage_id, metric["bucket"], metric["action"], metric["object"]).set(size)


async def run_prometheus_updates(probe_settings: BaseSettings, resultstore: ResultStore):
    """
    Run task that will update the prometheus /metric endpoint periodically.
    """
    while True:
        try:
            await update_prometheus(probe_settings=probe_settings, resultstore=resultstore)
        except Exception:
            logging.exception("While probing:")
        await asyncio.sleep(probe_settings.s3p_interval)
