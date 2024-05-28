import time
from celery import shared_task, Celery
import redis
import requests
from trip import Trip
from telegram import Bot
import pickle
import logging


celery_app = Celery(
    "celery_app",
    backend="redis://localhost:6379/0",
    broker="redis://localhost:6379/0",
    include=["tasks"],
)

redis_client = redis.Redis(host="localhost", port=6379, db=0)


@celery_app.task(bind=True)
def find_trip_and_reserve(self, my_trip: Trip):
    """Search for trips with empty seats."""
    my_trip = pickle.loads(my_trip)
    try:
        trips = my_trip.find_trip()
        my_trip.trip_json = trips[0]
        logging.info("Reserving: %s", trips[0].get("binisTarih"))
        my_trip.reserve_seat()
    except Exception as e:
        logging.error("Error while reserving seat: %s", e)
        self.retry(countdown=10, exc=e)

    logging.info("Seat is reserved: %s", my_trip.empty_seat_json.get("koltukNo"))
    if my_trip.is_seat_reserved:
        logging.info("Seat is reserved")
        return pickle.dumps(my_trip)


@celery_app.task(bind=True)
def keep_reserving_seat(self, my_trip: Trip):
    """Reserve a seat for a trip."""
    my_trip = pickle.loads(my_trip)
    text = f"Reserving seat for trip: {my_trip.trip_json.get('binisTarih')}, {
        my_trip.empty_seat_json.get('koltukNo')}"
    logging.info(text)
    while True:
        logging.info("Checking stop_reserve_seat_flag")
        if redis_client.get("stop_reserve_seat_flag"):
            logging.info(
                "Stop reserve seat flag is set %s. Stopping and returning trip",
                redis_client.get("stop_reserve_seat_flag"),
            )
            return pickle.dumps(my_trip)
        time.sleep(1)
        logging.info("Looping to reserve seat lock_end_time: %s", my_trip.lock_end_time)
        try:
            my_trip.reserve_seat()
        except requests.exceptions.ReadTimeout as e:
            logging.error("Error while reserving seat: %s", e)
            # retry indefinitely
            self.retry(countdown=0)


@celery_app.task(bind=True)
def test_task(self):
    """Test task."""
    logging.info("Test task is running")
    while True:
        time.sleep(10)
        logging.info("Test task is running")
        if redis_client.get("stop_task_id"):
            if redis_client.get("stop_task_id").decode() == self.request.id:
                logging.info(
                    "Stop task flag is set: %s, self.request.id: %s",
                    redis_client.get("stop_task_id"),
                    self.request.id,
                )
                return 0
