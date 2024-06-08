"""This script is used to automate the ticket purchase process from TCDD website."""

import asyncio
from datetime import datetime
import logging
import requests
from tasks.trip_search import TripSearchApi
from tasks.trip_search import SeatLockedException
from passenger import Passenger, Seat

logger = logging.getLogger(__name__)


class Trip:
    """Trip class to store trip details."""

    def __init__(
        self,
        from_station,
        to_station,
        from_date,
        passenger=None,
        to_date=None,
    ):
        self.passenger: Passenger = passenger
        self.from_station = from_station
        self.to_station = to_station
        self.from_date = from_date
        self.to_date = to_date
        self.trip_json = None
        self.time_format = "%b %d, %Y %I:%M:%S %p"
        self.output_time_format = "%b %d, %H:%M"
        self.empty_seat_json = None
        self.seat_lock_response = None
        self.koltuk_lock_id_list = []
        self.lock_end_time = None
        self.semaphore_count = 5

    def is_reservation_expired(self):
        """Check if the seat reservation is expired."""
        if self.lock_end_time is None:
            return True
        elif self.lock_end_time:
            time_diff = self.lock_end_time - datetime.now()
            if time_diff.total_seconds() < 60:
                # lock time is passed, seat reserveation is expired
                return True
        return False

    def reset_reservation_data(self):
        """Reset the reservation status."""
        self.trip_json = None
        self.empty_seat_json = None
        self.seat_lock_response = None
        self.lock_end_time = None
        self.koltuk_lock_id_list = []

    def set_seat_lock_id(self):
        """Get the lock id of the seat."""
        self.koltuk_lock_id_list.clear()
        seats = self.seat_lock_response["koltuklarimListesi"]
        for seat in seats:
            self.koltuk_lock_id_list.append(seat["koltukLockId"])
        logger.info("koltuk_lock_id_list: %s", self.koltuk_lock_id_list)

    def reserve_seat(self):
        """Reserve a seat for the given trip."""

        try:
            # first reserving of the seat
            if not self.lock_end_time:
                logger.info("Seat is not reserved, reserving the seat.")

                # check if we have already reserved the seat before
                if self.empty_seat_json:
                    lock_end_time, _, self.seat_lock_response = (
                        TripSearchApi.select_first_empty_seat(
                            self.trip_json, self.empty_seat_json
                        )
                    )

                # First time reserving the seat
                else:
                    lock_end_time, self.empty_seat_json, self.seat_lock_response = (
                        TripSearchApi.select_first_empty_seat(self.trip_json)
                    )

                self.lock_end_time = datetime.strptime(lock_end_time, self.time_format)
                self.set_seat_lock_id()
                logger.info("lock_end_time: %s", self.lock_end_time)

            # we have already reserved the seat check lock_end_time and
            # if it is passed then reserve the seat again
            elif self.lock_end_time:
                if datetime.now().second % 30 == 0:
                    logger.info("Seat is already reserved.")
                time_diff = self.lock_end_time - datetime.now()
                # server doesnt seem to release the lock at least 15-20 seconds
                # after the lock_end_time so we are starting to reserve
                #  the seat again 10 seconds after the lock_end_time
                if time_diff.total_seconds() < -10:
                    self.lock_end_time = None

            logger.info("lock_end_time: %s", self.lock_end_time)

        except SeatLockedException as e:
            logging.error("Error while reserving the seat: %s", e)

    def get_trips(self, **kwargs):
        """Get the trips based on the given parameters."""
        trips = []
        trips = TripSearchApi.search_trips(
            self.from_station, self.to_station, self.from_date, self.to_date, **kwargs
        )
        # return none if no trips are found
        if len(trips) == 0:
            logger.info("No trips found. Returning None.")
            return None
        logger.info("Total of %s trips found", len(trips))
        logger.info("returning trips")
        return trips

    async def find_trips(self):
        """Find a trip based on the given parameters.
        This function will keep searching for trips until it finds a trip with empty seats.
        """
        trips_with_empty_seats = []
        event = asyncio.Event()
        # lock for shared resource trips_with_empty_seats
        sem = asyncio.Semaphore(self.semaphore_count)
        lock = asyncio.Lock()
        logger.info("Searching for trips with empty seat.")

        # if trips_with_empty_seats is empty keep searching for trips
        while len(trips_with_empty_seats) == 0:
            trips = self.get_trips()
            tasks = [
                self.check_trip_for_empty_seats(
                    trip, trips_with_empty_seats, lock, sem, event
                )
                for trip in trips
            ]
            await asyncio.gather(*tasks)
            logger.info("Trips with empty seats len: %s", len(trips_with_empty_seats))

        return trips_with_empty_seats

    async def check_trip_for_empty_seats(
        self, trip, trips_with_empty_seats, lock, sem, event
    ):
        """Check if the given trip has empty seats."""
        # await asyncio.sleep(100)
        # logger.info("Checking trip for empty seats: %s", trip.get("binisTarih"))

        # lock for running only a certain amount of tasks concurrently
        async with sem:
            logger.info("Aquired semaphore")
            while not event.is_set():
                trip = await TripSearchApi.get_empty_seats_trip(
                    trip,
                    self.from_station,
                    self.to_station,
                    self.passenger.seat_type,
                )
                empty_seat_count = await self.get_trip_empty_seat_count(trip)
                if empty_seat_count > 0:
                    # onyl one  task should access the shared resources below at a time
                    async with lock:
                        while not event.is_set():
                            event.set()
                            trips_with_empty_seats.append(trip)

    async def get_trip_empty_seat_count(self, trip):
        """Get the empty seat count for the given trip."""
        empty_seat_count = 0
        if self.passenger.seat_type:
            if self.passenger.seat_type == Seat.BUSS:
                empty_seat_count = trip["buss_empty_seat_count"]
            elif self.passenger.seat_type == Seat.ECO:
                empty_seat_count = trip["eco_empty_seat_count"]
        else:
            empty_seat_count = trip["empty_seat_count"]
        return empty_seat_count


def list_stations():
    """List all the stations that support high-speed train."""
    logger.info("Listing stations")
    try:
        stations_json = TripSearchApi.get_station_list()
        stations = []
        for station in stations_json:
            stations.append(station["station_name"])
        return stations
    except requests.exceptions.HTTPError as e:
        logger.error("Error while listing stations: %s", e)
        raise


if __name__ == "__main__":
    stations_ = list_stations()
