""" This module contains the listeners for the scheduler events. """

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s"
)
handlers = [logging.FileHandler("../bot_data/logs/scheduler_listeners.log")]
for handler in handlers:
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def submit_listener(event):
    """Log the job ID of the submitted job."""
    logger.info("Job SUBMITTED: ID: %s", event.job_id)


def mis_listener(event):
    """Log the job ID of the missed job."""
    logger.info("Job MISSED: ID: %s", event.job_id)


def max_instances_listener(event):
    """Log the job ID of the job that reached the maximum number of instances."""
    logger.info("Job MAX INSTANCES: ID: %s", event.job_id)


def job_executed_listener(event):
    """Log the job ID of the executed job."""
    if event.exception:
        logger.error(
            "Job EXECUTED: ID: %s, Exception: %s", event.job_id, event.exception
        )
    else:
        logger.info(
            "Job EXECUTED: ID: %s, Return Value: %s", event.job_id, event.retval
        )


def job_added_listener(event):
    """Log the job ID of the added job."""
    logger.info("Job ADDED: ID: %s", event.job_id)
