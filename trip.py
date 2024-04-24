"""This script is used to automate the ticket purchase process from TCDD website."""
import time
from datetime import datetime
import logging
import trip_search
import api_constants


class Passenger:
    """Passenger class to store passenger details."""

    def __init__(self, tckn, name, surname, birthday, email, phone, sex, credit_card_no=None, credit_card_ccv=None, credit_card_exp=None):
        self.tckn = tckn
        self.name = name
        self.surname = surname
        self.birthday = birthday
        self.email = email
        self.phone = phone
        self.sex = sex
        self.credit_card_no = credit_card_no
        self.credit_card_ccv = credit_card_ccv
        self.credit_card_exp = credit_card_exp
        self.logger = logging.getLogger(__name__)


class Trip:
    """Trip class to store trip details."""

    def __init__(self, from_station, to_station, from_date, to_date, passenger, tariff=None, seat_type=None):
        self.passenger = passenger
        self.from_station = from_station
        self.to_station = to_station
        self.from_date = from_date
        self.to_date = to_date
        self.seat_type = seat_type
        self.trip_json = None
        self.time_format = "%b %d, %Y %I:%M:%S %p"
        self.empty_seat_json = None
        self.seat_lock_response = None
        self.koltuk_lock_id_list = []
        self.lock_end_time = None
        self.is_seat_reserved = False
        self.tariff = api_constants.TARIFFS[tariff.upper(
        )] if tariff else api_constants.TARIFFS['TAM']

        self.api = trip_search.TripSearchApi()
        self.logger = logging.getLogger(__name__)

    def set_seat_lock_id(self):
        """Get the lock id of the seat."""
        seats = self.seat_lock_response['koltuklarimListesi']
        for seat in seats:
            self.koltuk_lock_id_list.append(seat['koltukLockId'])
        self.logger.info("koltuk_lock_id_list: %s", self.koltuk_lock_id_list)

    def reserve_seat(self):
        """Reserve a seat for the given trip."""

        try:
            # first reserving of the seat
            if not self.is_seat_reserved:
                self.logger.info("Reserving the seat.")
                lock_end_time, self.empty_seat_json, self.seat_lock_response = self.api.select_first_empty_seat(
                    self.trip_json)
                self.lock_end_time = datetime.strptime(
                    lock_end_time, self.time_format)
                self.set_seat_lock_id()
                self.is_seat_reserved = True
                self.logger.info("lock_end_time: %s", self.lock_end_time)

            # we have already reserved the seat check lock_end_time and if it is passed then reserve the seat again
            elif self.is_seat_reserved:
                time_diff = self.lock_end_time - datetime.now()
                if time_diff.total_seconds() < 10:
                    self.logger.info(time_diff.total_seconds())
                    self.logger.info(
                        "Lock time ending is approaching. Starting to reserve the seat again")
                    lock_end_time, _, self.seat_lock_response = self.api.select_first_empty_seat(
                        self.trip_json, self.empty_seat_json)
                    self.lock_end_time = datetime.strptime(
                        lock_end_time, self.time_format)
                    self.set_seat_lock_id()
                    self.logger.info("lock_end_time: %s", self.lock_end_time)

        except trip_search.SeatLockedException as e:
            logging.error("Error while reserving the seat: %s", e)

    def get_trips(self, list_trips=False):
        """Get the trips based on the given parameters."""
        self.logger.info("Searching for trips.")
        trips = []
        trips = self.api.search_trips(
            self.from_station, self.to_station, self.from_date, self.to_date)
        # return none if no trips are found
        if len(trips) == 0:
            self.logger.info("No trips found.")
            return None
        if list_trips:
            for trip in trips:
                dep_date_object = datetime.strptime(
                    trip['binisTarih'], self.time_format)
                dep_formatted_date = dep_date_object.strftime(
                    "%b %d, %Y %H:%M")
                arr_date_object = datetime.strptime(
                    trip['inisTarih'], self.time_format)
                arr_formatted_date = arr_date_object.strftime(
                    "%b %d, %Y %H:%M")
                trip_details = (f"Departure: {dep_formatted_date}\n"
                                f"Arrival  : {arr_formatted_date}\n"
                                f"Economy  : {trip['eco_empty_seat_count']}\n"
                                f"Business : {trip['buss_empty_seat_count']}\n")
                self.logger.info("trip_details: %s", trip_details)
                self.logger.info(
                    "--------------------------------------------------")
        self.logger.info("Total of %s trips found", len(trips))
        return trips

    def find_trip(self):
        """Find a trip based on the given parameters.
        This function will keep searching for trips until it finds a trip with empty seats."""

        # get the seaty_type key from value given to this method
        seat_type_id = api_constants.VAGON_TYPES[self.seat_type.upper()]
        self.logger.info("seat_type_id: %s", seat_type_id)
        trips_with_empty_seats = []
        self.logger.info("Searching for trips with empty seat.")
        while len(trips_with_empty_seats) == 0:
            time.sleep(1)
            if datetime.now().second % 60 == 0:
                # log method parameters
                self.logger.info("Still searching for trips with empty seat.\n"
                                 "from_station: %s\n"
                                 "to_station: %s\n"
                                 "from_date: %s\n"
                                 "to_date: %s\n"
                                 "seat_type_id: %s",
                                 self.from_station, self.to_station, self.from_date,
                                 self.to_date, seat_type_id)
            trips = self.get_trips()
            try:
                for trip in trips:
                    trip = self.api.get_empty_seats_trip(
                        trip, self.from_station, self.to_station, seat_type_id)
                    if self.seat_type:
                        empty_seat_count = trip[f"{self.seat_type.lower()}_empty_seat_count"]
                    else:
                        empty_seat_count = trip['empty_seat_count']
                    if empty_seat_count > 0:
                        trips_with_empty_seats.append(trip)
            except TypeError as e:
                self.logger.error("Error while finding trip: %s", e)
        return trips_with_empty_seats

    def list_stations(self):
        """List all the stations that support high-speed train."""
        stations = self.api.get_station_list()
        for station in stations:
            print(station['station_name'])
