import logging
import os

WORKER_LOGS_ENABLED = os.environ.get("WORKER_LOGS", "false").lower() in ("true", "1")


def configure_worker_logging(**kwargs):
    level = logging.INFO if WORKER_LOGS_ENABLED else logging.WARNING
    logging.basicConfig(level=level, **kwargs)
    logging.getLogger().setLevel(level)
