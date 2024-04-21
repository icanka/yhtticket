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
def search(
        from_station,
        to_station,
        from_date,
        to_date,
        reserve,
        seat_type):
    """
    Search for trips based on the given parameters.

    Args:
        from_station (str): The departure station.
        to_station (str): The arrival station.
        from_date (str): The departure date.
        to_date (str): The arrival date.
        list_trips (bool): Whether to list the trips or not.
        seat_type (str): The type of seat to search for.

    Returns:
        str: The trip details if list_trips is True, otherwise None.
    """
    # print all args and options
    # pprint(locals())

    if seat_type:
        seat_type = seat_type.upper()
        seat_type = api_constants.VAGON_TYPES[seat_type]

    # create an empty list of trips
    while reserve:
        time.sleep(1)
        trips = []
        if len(trips) == 0:
            print("NO TRIPS FOUND, RETRYING...")
        while len(trips) == 0:
            time.sleep(1)
            trips = trip_search.search_trips(
                from_station, to_station, from_date, to_date)
            if datetime.now().second % 60 == 0:
                print("NO TRIPS FOUND, RETRYING...")

        for trip in trips:
            trip = trip_search.get_empty_seats_trip(
                trip, from_station, to_station, seat_type)

            # print trip if empty seats are available
            if trip['empty_seat_count'] > 0:
                pprint(f"empty seats: {trip['empty_seat_count']}")
                if reserve:
                    combined_data = reserve_seat(trip)
                    # reserve_seat rezerves only for 10 minutes, so until the user exits the script check the seat indefinitely and keep it reserved
                    # wait for 8 minutes after first reservation

                    if combined_data['seat_lock_json_result']:
                        while True:
                            trip_str = combined_data['trip']['binisTarih']
                            seat_str = combined_data['empty_seat']['koltukNo']
                            vagon_str = combined_data['empty_seat']['vagonSiraNo']
                            pprint(
                                f"Seat {seat_str} in vagon {vagon_str} is reserved for trip {trip_str}")
                            end_time = combined_data['seat_lock_json_result']['koltuklarimListesi'][0]['bitisZamani']
                            # end_time = now + 10 sec

                            # end_time = datetime.now() + timedelta(seconds=10)
                            # stringfy the end_time to format "Apr 5, 2024 01:41:30 AM"
                            # end_time = end_time.strftime("%b %d, %Y %I:%M:%S %p")

                            pprint(f"Lock will end at {end_time}")
                            # parse the bitisZamani to datetime and wait until that time -5 seconds to renew the reservation
                            end_time = datetime.strptime(
                                end_time, "%b %d, %Y %I:%M:%S %p")
                            pprint(
                                f"Waiting  until {end_time - timedelta(seconds=5)}")
                            while datetime.now() - timedelta(seconds=3) < end_time:
                                time.sleep(1)
                            pprint("Renewing the reservation")
                            while True:
                                time.sleep(1)
                                pprint("S1")
                            # start reserving the seat
                                combined_data = reserve_seat(trip)
                            # We reserved the seat
                                if combined_data and combined_data['seat_lock_json_result']:
                                    break
                            trip_str = combined_data['trip']['binisTarih']
                            seat_str = combined_data['empty_seat']['koltukNo']
                            vagon_str = combined_data['empty_seat']['vagonSiraNo']
                            pprint(
                                f"Reservation renewed, Vagon:{vagon_str} Seat:{seat_str} Trip:{trip_str}")

                break
            else:
                print('No empty seats available for this trip.')


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
