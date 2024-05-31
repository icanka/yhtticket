from datetime import datetime
import time
import logging
import pickle
import redis
from tasks.trip import Trip
from celery import Celery

logger = logging.getLogger(__name__)
logger.addHandler(logging.FileHandler("bot_data/logs/celery.log"))

celery_app = Celery(
    "celery_app",
    backend="redis://localhost:6379/0",
    broker="redis://localhost:6379/0",
    include=["tasks"],
)

redis_client = redis.Redis(host="localhost", port=6379, db=0)


@celery_app.task(bind=True, max_retries=None)
def find_trip_and_reserve(self, my_trip: Trip):
    """Search for trips with empty seats."""
    count = 0
    my_trip = pickle.loads(my_trip)
    try:
        trips = my_trip.find_trip()
        my_trip.trip_json = trips[0]
        logger.info("Reserving: %s", trips[0].get("binisTarih"))
        my_trip.reserve_seat()
    except Exception as e:
        logger.error("Error while reserving seat: %s", e)
        count += 1
        logger.info("Retrying... %s", count)
        self.retry(countdown=10)

    logger.info("Seat is reserved: %s", my_trip.empty_seat_json.get("koltukNo"))
    if my_trip.is_seat_reserved:
        logger.info("Seat is reserved")
        return pickle.dumps(my_trip)


@celery_app.task(bind=True, max_retries=None)
def keep_reserving_seat(self, my_trip: Trip):
    """Reserve a seat for a trip."""
    my_trip = pickle.loads(my_trip)
    text = f"Reserving seat for trip: {my_trip.trip_json.get('binisTarih')}, {
        my_trip.empty_seat_json.get('koltukNo')}"
    logger.info(text)
    while True:
        logger.info("logger name: %s", logger.name)
        if should_stop(self):
            return pickle.dumps(my_trip)

        if datetime.now().second % 60 == 0:
            logger.info("lock_end_time: %s", my_trip.lock_end_time)

        try:
            my_trip.reserve_seat()
        except Exception as e:
            logger.error("Error while reserving seat: %s", e)
            # retry indefinitely
            self.retry(countdown=0)

        time.sleep(1)


@celery_app.task(bind=True)
def test_task_(self):
    """Test task."""
    logger.info("Test task is running")
    # byte request id
    while True:
        if should_stop(self):
            break
        logger.info("redis keys: %s", redis_client.keys())
        time.sleep(30)


def should_stop(task_instance):
    """Check if the task should be stopped."""
    request_id = str(task_instance.request.id).encode()
    if request_id in redis_client.keys():
        return True
    return False
