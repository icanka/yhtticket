import time
from datetime import datetime
import logging
import click
import trip_search
import api_constants
from stations import get_station_list


class Trip:
    """Trip class to store trip details."""
    
    def __init__(self, from_station, to_station, from_date, to_date, seat_type=None):
        self.from_station = from_station
        self.to_station = to_station
        self.from_date = from_date
        self.to_date = to_date
        self.seat_type = seat_type
        
        # new TripSearch object
        self.trip_search = trip_search.TripSearchApi()
        self.logger = logging.getLogger(__name__)

    def reserve_seat(self, trip):
        """Reserve a seat for the given trip."""
        try:
            self.logger.info("Reserving the seat.")
            end_time, reserve_seat, seat_lock_response = self.trip_search.select_first_empty_seat(
                trip)
            reserved_trip_data = {
                'seat_lock_response': seat_lock_response,
                'lock_end_time': datetime.strptime(
                    end_time, "%b %d, %Y %I:%M:%S %p"),
                'trip': trip,
                'reserved_seat': reserve_seat,
            }
            logging.info("empty seat: %s", reserve_seat)
            return reserved_trip_data
        except Exception as e:
            logging.error("Error while reserving the seat: %s", e)
            return None

    def get_trips(self, from_station, to_station, from_date, to_date, list_trips):
        """Get the trips based on the given parameters."""
        self.logger.info("Searching for trips.")
        trips = []
        trips = self.trip_search.search_trips(
            from_station, to_station, from_date, to_date)
        # return none if no trips are found
        if len(trips) == 0:
            self.logger.info("No trips found.")
            return None
        if list_trips:
            for trip in trips:
                dep_date_object = datetime.strptime(
                    trip['binisTarih'], "%b %d, %Y %I:%M:%S %p")
                dep_formatted_date = dep_date_object.strftime(
                    "%b %d, %Y %H:%M")
                arr_date_object = datetime.strptime(
                    trip['inisTarih'], "%b %d, %Y %I:%M:%S %p")
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

    def find_trip(self, from_date, to_date, from_station, to_station, seat_type=None):
        """Find a trip based on the given parameters.
        This function will keep searching for trips until it finds a trip with empty seats."""

        # get the seaty_type key from value given to this method
        seat_type_id = api_constants.VAGON_TYPES[seat_type.upper()]
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
                                 from_station, to_station, from_date, to_date, seat_type_id)
            trips = self.get_trips(
                from_station, to_station, from_date, to_date, False)
            self.logger.info("Total of %s trips found", len(trips))
            for trip in trips:
                trip = self.trip_search.get_empty_seats_trip(
                    trip, from_station, to_station, seat_type_id)
                if seat_type:
                    empty_seat_count = trip[f"{seat_type.lower()}_empty_seat_count"]
                else:
                    empty_seat_count = trip['empty_seat_count']
                if empty_seat_count > 0:
                    trips_with_empty_seats.append(trip)
        return trips_with_empty_seats

    def list_stations(self):
        """List all the stations that support high-speed train."""
        stations = get_station_list()
        for station in stations:
            print(station['station_name'])


@click.group(help='This script is used to automate the ticket purchase process from TCDD website.')
def cli():
    """This script is used to automate the ticket purchase process from TCDD website."""


# stations = get_station_list()
# # get the station view name for the given station name
# #

# to_station_view_name = next(
#     (station['station_view_name'] for station in stations if station['station_name'] == to_station), None)
# from_station_view_name = next(
#     (station['station_view_name'] for station in stations if station['station_name'] == from_station), None)


# selenium_payment = payment.SeleniumPayment()
# for _ in range(100):
#     selenium_payment.open_site()
#     selenium_payment.fill_in_departure_arrival_input(
#         "Ankara Gar", "İstanbul(Pendik)")

# exit(0)


# ready selenium
# selenium_payment = payment.SeleniumPayment()


# if __name__ == '__main__':
#     cli()
