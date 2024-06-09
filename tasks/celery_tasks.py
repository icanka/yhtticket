from datetime import datetime
import asyncio
import json
import time
import logging
import pickle
import redis
from celery import Celery
from celery.utils.log import get_task_logger
from tasks.trip import Trip

logger = get_task_logger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.FileHandler("bot_data/logs/celery_tasks.log"))
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s"
)
for handler in logger.handlers:
    handler.setFormatter(formatter)

celery_app = Celery(
    "celery_tasks",
    backend="redis://localhost:6379/0",
    broker="redis://localhost:6379/0",
    include=["tasks.celery_tasks"],
)

redis_client = redis.Redis(host="localhost", port=6379, db=0)


@celery_app.task(bind=True, max_retries=None)
def find_trip_and_reserve(self, my_trip: Trip):
    """Search for trips with empty seats."""
    count = 0
    my_trip = pickle.loads(my_trip)
    try:
        trips = asyncio.run(my_trip.find_trips())
        logger.info("Trips found: %s", len(trips))
        my_trip.trip_json = trips[0]
        logger.info("Reserving: %s", trips[0].get("binisTarih"))
        my_trip.reserve_seat()
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error while reserving seat: %s", e)
        count += 1
        logger.info("Retrying... %s", count)
        self.retry(countdown=60)

    logger.info("Seat is reserved: %s", my_trip.empty_seat_json.get("koltukNo"))
    if my_trip.lock_end_time:
        logger.info("Seat is reserved")
        return pickle.dumps(my_trip)


@celery_app.task(bind=True, max_retries=None)
def keep_reserving_seat(self, my_trip: Trip, chat_id: int):
    """Reserve a seat for a trip."""
    my_trip = pickle.loads(my_trip)
    text = f"Reserving seat for trip: {my_trip.trip_json.get('binisTarih')}, {
        my_trip.empty_seat_json.get('koltukNo')}"
    logger.info(text)

    while True:
        if should_stop(self):
            return pickle.dumps(my_trip)

        if datetime.now().second % 60 == 0:
            logger.info("lock_end_time: %s", my_trip.lock_end_time)

        try:
            if my_trip.reserve_seat():
                logger.info("Seat reserve operation is successful.")
                time_ = datetime.strftime(my_trip.lock_end_time, my_trip.time_format)
                chat_id_data = {"lock_end_time": time_}
                logger.info("chat_id_data: %s", chat_id_data)
                logger.info("Setting redis keys...")
                redis_client.set(chat_id, json.dumps(chat_id_data), ex=600)

        except Exception as e:  # pylint: disable=broad-except
            logger.error("Error while reserving seat: %s", e)
            # retry indefinitely
            self.retry(countdown=0)

        time.sleep(1)


@celery_app.task(bind=True)
def test_task_(self, chat_id: int):
    """Test task."""
    # byte request id
    time_ = datetime.now()
    chat_id_data = json.dumps({"lock_end_time": time_.strftime("%H:%M:%S")})

    logger.info("Task is running Setting redis keys...")
    redis_client.set(chat_id, chat_id_data, ex=60)

    # while True:
    #     logger.info("Task is running")
    #     if should_stop(self):
    #         break
    #     logger.info("redis keys: %s", redis_client.keys())
    #     time.sleep(30)


def should_stop(task_instance):
    """Check if the task should be stopped."""
    request_id = str(task_instance.request.id).encode()
    if request_id in redis_client.keys():
        return True
    return False
