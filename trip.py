"""This script is used to automate the ticket purchase process from TCDD website."""

from dataclasses import dataclass, field
import time
from datetime import datetime
import logging
from typing import Optional

import requests
import api_constants
from trip_search import TripSearchApi
from trip_search import SeatLockedException
from passenger import Passenger, Seat


class Trip:
    """Trip class to store trip details."""

    def __init__(
        self,
        from_station,
        to_station,
        from_date,
        passenger,
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
        self.logger = logging.getLogger(__name__)

    def set_seat_lock_id(self):
        """Get the lock id of the seat."""
        self.koltuk_lock_id_list.clear()
        seats = self.seat_lock_response["koltuklarimListesi"]
        for seat in seats:
            self.koltuk_lock_id_list.append(seat["koltukLockId"])
        self.logger.info("koltuk_lock_id_list: %s", self.koltuk_lock_id_list)

    def reserve_seat(self):
        """Reserve a seat for the given trip."""

        try:
            # first reserving of the seat
            if not self.is_seat_reserved:
                self.logger.info("Seat is not reserved, reserving the seat.")
                lock_end_time, self.empty_seat_json, self.seat_lock_response = (
                    TripSearchApi.select_first_empty_seat(self.trip_json)
                )
                self.lock_end_time = datetime.strptime(lock_end_time, self.time_format)
                self.set_seat_lock_id()
                self.is_seat_reserved = True
                self.logger.info("lock_end_time: %s", self.lock_end_time)

            # we have already reserved the seat check lock_end_time and if it is passed then reserve the seat again
            elif self.is_seat_reserved:
                self.logger.info("Seat is already reserved.")
                time_diff = self.lock_end_time - datetime.now()
                if time_diff.total_seconds() < 5:
                    self.logger.info(time_diff.total_seconds())
                    self.logger.info(
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
                    self.logger.info("lock_end_time: %s", self.lock_end_time)

        except SeatLockedException as e:
            logging.error("Error while reserving the seat: %s", e)

    def get_trips(self, list_trips=False, **kwargs):
        """Get the trips based on the given parameters."""
        trips = []
        self.logger.info(
            "get_trips"
            "Searching for trips.\n"
            "from_station: %s\n"
            "to_station: %s\n"
            "from_date: %s\n"
            "to_date: %s\n"
            "seat_type_id: %s",
            self.from_station,
            self.to_station,
            self.from_date,
            self.to_date,
            self.passenger.seat_type,
        )
        trips = TripSearchApi.search_trips(
            self.from_station, self.to_station, self.from_date, self.to_date, **kwargs
        )
        # return none if no trips are found
        if len(trips) == 0:
            self.logger.info("No trips found. Returning None.")
            return None
        # if list_trips:
        #     for trip in trips:
        #         dep_date_object = datetime.strptime(
        #             trip["binisTarih"], self.time_format
        #         )
        #         dep_formatted_date = dep_date_object.strftime("%b %d, %Y %H:%M")
        #         arr_date_object = datetime.strptime(trip["inisTarih"], self.time_format)
        #         arr_formatted_date = arr_date_object.strftime("%b %d, %Y %H:%M")
        #         trip_details = (
        #             f"Departure: {dep_formatted_date}\n"
        #             f"Arrival  : {arr_formatted_date}\n"
        #             f"Economy  : {trip['eco_empty_seat_count']}\n"
        #             f"Business : {trip['buss_empty_seat_count']}\n"
        #         )
        #         self.logger.info("trip_details: %s", trip_details)
        #         self.logger.info("--------------------------------------------------")
        self.logger.info("Total of %s trips found", len(trips))
        self.logger.info("returning trips")
        return trips

    def find_trip(self):
        """Find a trip based on the given parameters.
        This function will keep searching for trips until it finds a trip with empty seats.
        """
        trips_with_empty_seats = []

        self.logger.info("seat_type_id: %s", self.passenger.seat_type)
        self.logger.info("Searching for trips with empty seat.")

        while len(trips_with_empty_seats) == 0:

            time.sleep(1)
            if datetime.now().second % 60 == 0:
                # log method parameters
                self.logger.info(
                    "Still searching for trips with empty seat.\n"
                    "from_station: %s\n"
                    "to_station: %s\n"
                    "from_date: %s\n"
                    "to_date: %s\n"
                    "seat_type_id: %s",
                    self.from_station,
                    self.to_station,
                    self.from_date,
                    self.to_date,
                    self.passenger.seat_type,
                )

            self.logger.info(
                "Still searching for trips with empty seat.\n"
                "from_station: %s\n"
                "to_station: %s\n"
                "from_date: %s\n"
                "to_date: %s\n"
                "seat_type_id: %s",
                self.from_station,
                self.to_station,
                self.from_date,
                self.to_date,
                self.passenger.seat_type,
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
                self.logger.error("Error while finding trip: %s", e)

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
