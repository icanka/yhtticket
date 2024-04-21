import json
import time
import click
import trip_search
import api_constants
from stations import get_station_list
from pprint import pprint
from datetime import datetime, timedelta
import payment
import logging

logging.basicConfig(level=logging.INFO)
# set logging formatting
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

# TODO Reserve seat for a specific seat and vagon number


def reserve_seat(trip):
    """Reserve a seat for the given trip."""
    try:
        pprint("Reserving the seat")
        end_time, reserve_seat, seat_lock_response = trip_search.select_first_empty_seat(
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


@click.group(help='This script is used to automate the ticket purchase process from TCDD website.')
def cli():
    """This script is used to automate the ticket purchase process from TCDD website."""


@cli.command()
@click.argument('from_station')
@click.argument('to_station')
# departure date, default to now
@click.option('--from-date', '-f', default=None,
              help='The departure date.')
@click.option('--to-date', '-t', default=None, help='The arrival date.')
@click.option('--reserve', '-r', is_flag=True,
              help='Reserve a seat for the first available trip.')
@click.option('--seat-type',
              '-s',
              type=click.Choice(['eco',
                                 'buss']),
              default=None,
              help='Purchase an eco or buss type ticket. Default is None for both.')
def get_trips(from_station, to_station, from_date, to_date, list_trips):
    """Get the trips based on the given parameters."""
    trips = []
    logging.info("get_trips: Searching for trips...")
    trips = trip_search.search_trips(
        from_station, to_station, from_date, to_date)
    # return none if no trips are found
    if len(trips) == 0:
        logging.info("get_trips: No trips found.")
        return None
    # pprint(len(trips))
    if list_trips:
        for trip in trips:
            dep_date_object = datetime.strptime(
                trip['binisTarih'], "%b %d, %Y %I:%M:%S %p")
            dep_formatted_date = dep_date_object.strftime("%b %d, %Y %H:%M")
            arr_date_object = datetime.strptime(
                trip['inisTarih'], "%b %d, %Y %I:%M:%S %p")
            arr_formatted_date = arr_date_object.strftime("%b %d, %Y %H:%M")
            trip_details = (f"Departure: {dep_formatted_date}\n"
                            f"Arrival  : {arr_formatted_date}\n"
                            f"Economy  : {trip['eco_empty_seat_count']}\n"
                            f"Business : {trip['buss_empty_seat_count']}\n")
            logging.info("get_trips: trip_details: %s", trip_details)
            logging.info("--------------------------------------------------")
    logging.info("get_trips: Total of %s trips found", len(trips))
    return trips


def find_trip(from_date, to_date, from_station, to_station, seat_type=None):
    """Find a trip based on the given parameters.
    This function will keep searching for trips until it finds a trip with empty seats."""

    trips_with_empty_seats = []
    logging.info("Searching for trips with empty seat...")
    while len(trips_with_empty_seats) == 0:
        time.sleep(1)
        if datetime.now().second % 60 == 0:
            logging.info("No trips found, still searching...")
        trips = get_trips(from_station, to_station, from_date, to_date, False)
        logging.info("Total of %s trips found", len(trips))
        for trip in trips:
            trip = trip_search.get_empty_seats_trip(
                trip, from_station, to_station, seat_type)
            if trip['empty_seat_count'] > 0:
                trips_with_empty_seats.append(trip)
                pprint(f"empty seats: {trip['empty_seat_count']}")
    return trips_with_empty_seats


@cli.command()
def list_stations():
    """List all the stations that support high-speed train."""
    stations = get_station_list()
    for station in stations:
        print(station['station_name'])


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
