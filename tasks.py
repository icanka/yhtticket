import time
from celery import shared_task, Celery
from trip import Trip
from telegram import Bot
import pickle


app = Celery('celery_app', backend='redis://localhost:6379/0',
             broker='redis://localhost:6379/0',
             include=['tasks'])

@app.task
def tripp(my_trip: Trip):
    """Search for trips with empty seats."""
    trip = pickle.loads(my_trip)
    trips = trip.find_trip()
    trip_ = pickle.dumps(trips[0])
    return trip_



@app.task
def reserve_seat(my_trip: Trip):
    """Reserve a seat for a trip."""
    time.sleep(20)
    return "Im finished"
    