import json
import click
import trip_search
import api_constants
from stations import get_station_list
from pprint import pprint
from datetime import datetime
import payment


# to_station = "İstanbul(Pendik)"
# from_station = "Ankara Gar"
# from_date = "15 december 12:00"
# to_date = "15 december 16:00"
# tariff = 'TSK'


@click.group(help='This script is used to automate the ticket purchase process from TCDD website.')
def cli():
    pass


@cli.command()
@click.argument('from_station')
@click.argument('to_station')
# departure date, default to now
@click.option('--from-date', '-f', default=None,
              help='The departure date.')
@click.option('--to-date', '-t', default=None, help='The arrival date.')
@click.option('--list-trips', '-l', is_flag=True,
              help='List all the available trips.')
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
        list_trips,
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
    pprint(locals())
    
    if seat_type:
        seat_type = seat_type.upper()
        seat_type = api_constants.VAGON_TYPES[seat_type]

    trips = trip_search.search_trips(
        from_station, to_station, from_date, to_date)

    pprint(len(trips))

    # if seat_type == 'eco':
    #     trips = [trip for trip in trips if trip['eco_empty_seat_count'] > 0]
    # elif seat_type == 'buss':
    #     trips = [trip for trip in trips if trip['buss_empty_seat_count'] > 0]
    # elif seat_type == 'any':
    #     trips = [trip for trip in trips if trip['empty_seat_count'] > 0]

    for trip in trips:
        trip = trip_search.get_empty_seats_trip(
            trip, from_station, to_station, seat_type)
        
        # dump to json and write to file
        with open('trip.json', 'w') as f:
            f.write(json.dumps(trip))
            
            
        #pprint(trip)
        exit(0)

    if list_trips:
        pprint(len(trips))
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
            print(trip_details)
            print('-' * 40)


@cli.command()
def list_stations():
    """List all the stations that support high-speed train."""
    stations = get_station_list()
    for station in stations:
        print(station['station_name'])


if __name__ == '__main__':
    cli()
