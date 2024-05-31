from apscheduler.schedulers.background import BackgroundScheduler
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s"
)
handlers = [logging.FileHandler("bot_data/logs/scheduler_listeners.log")]
for handler in handlers:
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def submit_listener(event):
    logger.info("Job SUBMITTED: ID: %s", event.job_id)


def mis_listener(event):
    logger.info("Job MISSED: ID: %s", event.job_id)


def max_instances_listener(event):
    logger.info("Job MAX INSTANCES: ID: %s", event.job_id)
