""" Main module to run the script. """

import pickle
import asyncio
import time
from pprint import pprint

from passenger import Passenger, Seat, Tariff
from tasks.celery_tasks import find_trip_and_reserve
from tasks.trip import Trip
import logging


logging.basicConfig(level=logging.INFO)

"""Main function to run the script."""
tckn = "18700774442"
name = "izzet can"
surname = "karakuş"
# birthday = "Jul 14, 1994 03:00:00 AM"
birthday = "14/07/1994"
email = "izzetcankarakus@gmail.com"
phone = "05340771521"
sex = "E"
credit_card_no = "4506347008156065"
# credit_card_no = "6501700150491393"
credit_card_ccv = "035"
# credit_card_ccv = "777"
credit_card_exp = "2406"
# credit_card_exp = "3004"
passenger = Passenger(
    tckn,
    name,
    surname,
    birthday,
    email,
    phone,
    sex,
    credit_card_no,
    credit_card_ccv,
    credit_card_exp,
    Tariff.TSK,
    Seat.ANY,
)
from_station = "İstanbul(Pendik)"
to_station = "Ankara Gar"
from_date = "12 June 12:00"
to_date = None  # '27 April 17:00'
# seat_type = "buss"
# query(from_station, to_station, from_date)
my_trip = Trip(from_station, to_station, from_date, passenger, to_date)

semap = asyncio.Semaphore(5)

asyncio.run(my_trip.find_trips_test())




# my_trip_ = pickle.dumps(my_trip)
# task = find_trip_and_reserve.delay(my_trip_)
# print(task.id)
# while not task.ready():
#     time.sleep(1)
#     print("Waiting for task to complete")
# trip = pickle.loads(task.result)
# pprint(trip)
# pprint(trip.empty_seat_json)
# pprint(trip.seat_lock_response)
# check if trip is json

# p = Payment()
# p.trip = trip
# p.set_price()
# p.set_payment_url()
# pprint(p.current_payment_url)
# for i in range(10):
#     time.sleep(5)
#     p.is_payment_success()


# trip_str = my_trip.trip_json["binisTarih"]
# seat_str = my_trip.empty_seat_json["koltukNo"]
# vagon_str = my_trip.empty_seat_json["vagonSiraNo"]
# end_time = my_trip.lock_end_time
# pprint(f"Lock will end at {end_time}")
# pprint(f"Seat {seat_str} in vagon {vagon_str} is reserved for trip {trip_str}")
