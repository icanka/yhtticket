"""This script is used to automate the ticket purchase process from TCDD website."""

import time
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
        self.is_seat_reserved = False

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
            if not self.is_seat_reserved:
                logger.info("Seat is not reserved, reserving the seat.")
                lock_end_time, self.empty_seat_json, self.seat_lock_response = (
                    TripSearchApi.select_first_empty_seat(self.trip_json)
                )
                self.lock_end_time = datetime.strptime(lock_end_time, self.time_format)
                self.set_seat_lock_id()
                self.is_seat_reserved = True
                logger.info("lock_end_time: %s", self.lock_end_time)

            # we have already reserved the seat check lock_end_time and if it is passed then reserve the seat again
            elif self.is_seat_reserved:
                # if datetime.now().second % 10 == 0:
                logger.info("logger name: %s", logger.name)
                logger.info("Seat is already reserved.")
                time_diff = self.lock_end_time - datetime.now()
                if time_diff.total_seconds() < 0:
                    logger.info(time_diff.total_seconds())
                    logger.info(
                        "Lock time ending is approaching. Starting to reserve the seat again"
                    )
                    lock_end_time, _, self.seat_lock_response = (
                        TripSearchApi.select_first_empty_seat(
                            self.trip_json, self.empty_seat_json
                        )
                    )
                    self.lock_end_time = datetime.strptime(
                        lock_end_time, self.time_format
                    )
                    self.set_seat_lock_id()
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

    def find_trip(self):
        """Find a trip based on the given parameters.
        This function will keep searching for trips until it finds a trip with empty seats.
        """
        trips_with_empty_seats = []

        logger.info("Searching for trips with empty seat.")

        while len(trips_with_empty_seats) == 0:
            time.sleep(1)
            if datetime.now().second % 60 == 0:
                # log method parameters
                logger.info(
                    "from_station: %s, to_station: %s, from_date: %s, to_date: %s",
                    self.from_station,
                    self.to_station,
                    self.from_date,
                    self.to_date,
                )
            trips = self.get_trips()
            try:
                for trip in trips:

                    logging.info(
                        "Checking trip for empty seats: %s", trip.get("binisTarih")
                    )
                    trip = TripSearchApi.get_empty_seats_trip(
                        trip,
                        self.from_station,
                        self.to_station,
                        self.passenger.seat_type,
                    )

                    if self.passenger.seat_type:
                        if self.passenger.seat_type == Seat.BUSS:
                            empty_seat_count = trip["buss_empty_seat_count"]
                        elif self.passenger.seat_type == Seat.ECO:
                            empty_seat_count = trip["eco_empty_seat_count"]
                    else:
                        empty_seat_count = trip["empty_seat_count"]

                    if empty_seat_count > 0:
                        logging.info(
                            "Found trip with empty seats. trip: %s",
                            trip.get("binisTarih"),
                        )
                        trips_with_empty_seats.append(trip)
                        # return the trip as soon as we find a trip with empty seats
                        return trips_with_empty_seats

                    logging.info("empty_seat_count: %s", empty_seat_count)

            except TypeError as e:
                logger.error("Error while finding trip: %s", e)

        return trips_with_empty_seats


def list_stations():
    """List all the stations that support high-speed train."""
    try:
        stations_json = TripSearchApi.get_station_list()
        stations = []
        for station in stations_json:
            stations.append(station["station_name"])
        return stations
    except requests.exceptions.HTTPError as e:
        logger = logging.getLogger(__name__)
        logger.error("Error while listing stations: %s", e)
        raise


if __name__ == "__main__":
    stations_ = list_stations()
