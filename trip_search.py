""" This module contains the functions for searching for trips and selecting empty seats."""
import json
from pprint import pprint
from datetime import datetime
import requests
import dateparser
import api_constants
from stations import get_station_list


def get_empty_vagon_seats(vagon_json):
    """
    Returns a generator that yields empty seats from the given vagon_json.

    Args:
        vagon_json (dict): The JSON data containing vagon information.

    Yields:
        dict: A dictionary representing an empty seat.

    """
    # business and economy class seat ids
    vagon_yerlesim = vagon_json['vagonHaritasiIcerikDVO']['vagonYerlesim']
    koltuk_durumlari = vagon_json['vagonHaritasiIcerikDVO']['koltukDurumlari']
    # efficient way to merge two lists of dictionaries based on a common key
    index_dict = {d['koltukNo']: d for d in koltuk_durumlari
                  if 'koltukNo' in d}
    merged_list = []
    for seat in vagon_yerlesim:
        seat_no = seat.get('koltukNo')
        if seat_no:
            merged_dict = {**seat, **index_dict.get(seat_no, {})}
            merged_list.append(merged_dict)

    # Take only the seats which has the key for nesneTanimId in empty_seat_ids
    merged_list = [d for d in merged_list if d.get(
        'nesneTanimId') in api_constants.SEATS_IDS]
    empty_seats = [d for d in merged_list if d.get('durum') == 0]
    # yield items from empty_seats
    for empty_seat in empty_seats:
        # pprint(empty_seat)
        yield empty_seat

# return a list of dictionaries


def get_active_vagons(json_data):
    """
    Retrieves the list of active wagons from the given JSON data.

    Args:
        json_data (list): A list of dictionaries representing the JSON data.

    Returns:
        list: A list of dictionaries containing the active wagon details,
        including 'vagonBaslikId' and 'vagonSiraNo'.
    """
    active_vagons = list()
    for item in json_data:
        for vagon in item['vagonListesi']:
            if vagon['aktif']:
                v = {'vagonBaslikId': vagon['vagonBaslikId'],
                     'vagonSiraNo': vagon['vagonSiraNo'],
                     'vagonTipId': item['vagonTipId']}
                active_vagons.append(v)
    return active_vagons


def select_first_empty_seat(trip):
    """
    Selects the first empty seat for a given trip.

    Args:
        trip (dict): The trip information.

    Returns:
        dict: The response JSON containing the selected seat information
        if the response code is 200.
    """

    # Select the first empty seat
    seat_select_req = api_constants.koltuk_sec_req_body.copy()
    s_check = api_constants.seat_check.copy()
    if trip['empty_seats']:
        empty_seat = trip['empty_seats'][0]
        seat_select_req['seferId'] = trip['seferId']
        seat_select_req['vagonSiraNo'] = empty_seat['vagonSiraNo']
        seat_select_req['koltukNo'] = empty_seat['koltukNo']
        seat_select_req['binisIst'] = trip['binisIstasyonId']
        seat_select_req['inisIst'] = trip['inisIstasyonId']
        s_check['seferId'] = trip['seferId']
        s_check['seciliVagonSiraNo'] = empty_seat['vagonSiraNo']
        s_check['koltukNo'] = empty_seat['koltukNo']
        s_response = requests.post(
            api_constants.SEAT_CHECK_ENDPOINT,
            headers=api_constants.REQUEST_HEADER,
            data=json.dumps(s_check),
            timeout=10)
        s_response_json = json.loads(s_response.text)
        if not s_response_json['koltukLocked']:
            # Send the request to the endpoint
            response = requests.post(
                api_constants.SELECT_EMPTY_SEAT_ENDPOINT,
                headers=api_constants.REQUEST_HEADER,
                data=json.dumps(seat_select_req),
                timeout=10)
            response_json = json.loads(response.text)
            # return trip with selected seat if the response code is 200
            return response_json, empty_seat
        else:
            pprint("Seat is already locked locked")
            return None


def get_detailed_vagon_info_empty_seats(vagon_map_req, vagons):
    """
    Retrieves the empty seats for a given vagon.

    Args:
        vagon_map_req (dict): The request body for getting the seat map of a vagon.

    Returns:
        list: The list of dictionaries containing the empty seat information.
    """
    empty_seats = list()
    response = requests.post(
        api_constants.VAGON_HARITA_ENDPOINT,
        headers=api_constants.REQUEST_HEADER,
        data=json.dumps(vagon_map_req),
        timeout=10)
    response_json = json.loads(response.text)

    for empty_seat in get_empty_vagon_seats(response_json):
        empty_seat['vagonTipId'] = next(
            vagon['vagonTipId'] for vagon in vagons
            if vagon['vagonSiraNo'] == vagon_map_req['vagonSiraNo'])
        empty_seats.append(empty_seat)

    return empty_seats


def get_empty_seats_trip(trip, from_station, to_station, seat_type=None):
    """
    Retrieves the empty seats for a given trip.

    Args:
        trip (dict): The trip object containing information about the trip.

    Returns:
        dict: The trip object with an additional 'empty_seats' field
        containing the list of empty seats.
    """
    # clone trip object
    trip_with_seats = trip.copy()
    vagon_req = api_constants.vagon_req_body.copy()
    vagon_map_req = api_constants.vagon_harita_req_body.copy()

    vagon_req['seferBaslikId'] = trip_with_seats['seferId']
    vagon_req['binisIstId'] = trip_with_seats['binisIstasyonId']
    vagon_req['inisIstId'] = trip_with_seats['inisIstasyonId']

    # get the vagons' seat status for the trip
    response = requests.post(
        api_constants.VAGON_SEARCH_ENDPOINT,
        headers=api_constants.REQUEST_HEADER,
        data=json.dumps(vagon_req),
        timeout=10)
    response_json = json.loads(response.text)

    trip_with_seats['empty_seats'] = list()
    for vagon in response_json['vagonBosYerList']:

        vagon_map_req['vagonSiraNo'] = vagon['vagonSiraNo']
        vagon_map_req['seferBaslikId'] = vagon_req['seferBaslikId']
        vagon_map_req['binisIst'] = from_station
        vagon_map_req['InisIst'] = to_station

        if seat_type:
            vagon_type = next(
                vagon_['vagonTipId'] for vagon_ in trip['vagons']
                if vagon_['vagonSiraNo'] == vagon['vagonSiraNo'])
            if seat_type != vagon_type:
                continue
            empty_seats = get_detailed_vagon_info_empty_seats(
                vagon_map_req, trip['vagons'])
            trip_with_seats['empty_seats'].extend(empty_seats)
        else:
            empty_seats = get_detailed_vagon_info_empty_seats(
                vagon_map_req, trip['vagons'])
            trip_with_seats['empty_seats'].extend(empty_seats)

    return trip_with_seats


def check_stations(stations, from_station, to_station):
    """
    Check if the given from_station and to_station are valid stations.

    Parameters:
    stations (list): A list of dictionaries representing the available stations.
    from_station (str): The name of the departure station.
    to_station (str): The name of the destination station.

    Raises:
    ValueError: If either from_station or to_station is not a valid station.

    Returns:
    None
    """
    if from_station not in [station['station_name'] for station in stations]:
        raise ValueError(f"{from_station} is not a valid station")

    if to_station not in [station['station_name'] for station in stations]:
        raise ValueError(f"{to_station} is not a valid station")


def search_trips(from_station, to_station, from_date=None, to_date=None):
    """
    Search for trips based on the given parameters.

    Args:
        from_station (str): The name of the departure station.
        to_station (str): The name of the destination station.
        from_date (str): The departure date in an human readable format.
        to_date (str, optional): The maximum arrival date in an human readable format. Defaults to None.

    Returns:
        list: A list of dictionaries representing the found trips. Each dictionary contains the following keys:
            - 'vagons': A list of active vagon types.
            - 'eco_empty_seat_count': The number of empty seats in the economy class.
            - 'buss_empty_seat_count': The number of empty seats in the business class.
            - 'empty_seat_count': The total number of empty seats.
            - 'binisTarih': The departure date and time.
            - 'inisTarih': The arrival date and time.
            - 'trenAdi': The name of the train.
            - 'seferAdi': The name of the trip.
            - 'seferId': The ID of the trip.
            - 'binisIstasyonId': The ID of the departure station.
            - 'inisIstasyonId': The ID of the destination station.
    """
    if not from_date:
        from_date = datetime.now().strftime("%b %d, %Y %I:%M:%S %p")

    vagon_req_body = api_constants.vagon_req_body.copy()
    trip_req = api_constants.trip_search_req_body.copy()
    trips = list()
    from_date = dateparser.parse(from_date)

    stations = get_station_list()
    check_stations(stations, from_station, to_station)

    # Find the station that matches from_station
    for station in stations:
        if station['station_name'] == from_station:
            binis_istasyon_id = station['station_id']
            vagon_req_body['binisIstId'] = binis_istasyon_id
            trip_req['seferSorgulamaKriterWSDVO']['binisIstasyonu'] = from_station
            trip_req['seferSorgulamaKriterWSDVO']['binisIstasyonId'] = binis_istasyon_id
        if station['station_name'] == to_station:
            inis_istasyon_id = station['station_id']
            vagon_req_body['inisIstId'] = inis_istasyon_id
            trip_req['seferSorgulamaKriterWSDVO']['inisIstasyonId'] = inis_istasyon_id
            trip_req['seferSorgulamaKriterWSDVO']['inisIstasyonu'] = to_station
    # Set the date
    trip_req['seferSorgulamaKriterWSDVO']['gidisTarih'] = datetime.strftime(
        from_date, "%b %d, %Y %I:%M:%S %p")

    response = requests.post(
        api_constants.TRIP_SEARCH_ENDPOINT,
        headers=api_constants.REQUEST_HEADER,
        data=json.dumps(trip_req),
        timeout=10)

    response_json = json.loads(response.text)

    sorted_trips = sorted(
        response_json['seferSorgulamaSonucList'],
        key=lambda trip: datetime.strptime(
            trip['binisTarih'],
            "%b %d, %Y %I:%M:%S %p"))

    # filter trips based on to_date
    if to_date:
        to_date = dateparser.parse(to_date)
        sorted_trips = [trip for trip in sorted_trips if datetime.strptime(
            trip['binisTarih'], "%b %d, %Y %I:%M:%S %p") < to_date]
        print('*' * 40)
    for trip in sorted_trips:
        if trip['satisDurum'] == 1 and trip['vagonHaritasindanKoltukSecimi'] == 1:
            # 0 is economy class and 1 is business class
            try:
                t = {}
                t['vagons'] = get_active_vagons(
                    trip['vagonTipleriBosYerUcret'])
                t['eco_empty_seat_count'] = trip['vagonTipleriBosYerUcret'][0]['kalanSayi'] - \
                    trip['vagonTipleriBosYerUcret'][0]['kalanEngelliKoltukSayisi']
                t['buss_empty_seat_count'] = trip['vagonTipleriBosYerUcret'][
                    1]['kalanSayi'] - trip['vagonTipleriBosYerUcret'][1][
                    'kalanEngelliKoltukSayisi']
                t['empty_seat_count'] = t['eco_empty_seat_count'] + \
                    t['buss_empty_seat_count']
                t['binisTarih'] = trip['binisTarih']
                t['inisTarih'] = trip['inisTarih']
                t['trenAdi'] = trip['trenAdi']
                t['seferAdi'] = trip['seferAdi']
                t['seferId'] = trip['seferId']
                t['binisIstasyonId'] = trip_req['seferSorgulamaKriterWSDVO'][
                    'binisIstasyonId']
                t['inisIstasyonId'] = trip_req['seferSorgulamaKriterWSDVO'][
                    'inisIstasyonId']
                trips.append(t)
            except IndexError:  # no business class, just ignore
                pprint("No business class")
    return trips


# trips = search_trips(from_station, to_station, from_date, to_date)
# for trip in trips:
#     trip = get_empty_seats_trip(trip)
#     # pprint(trip)
#     if trip['empty_seat_count'] > 0:
#         pprint("Found empty seats")
#         seat_lock_json_result, empty_seat = select_first_empty_seat(trip)
#         p = SeleniumPayment(
#             trip=trip,
#             empty_seat=empty_seat,
#             seat_lck_json=seat_lock_json_result,
#             tariff=tariff)
#         p.process_payment()
#     else:
#         pprint("No empty seats")

#     exit(0)
# # dump trips to json and then write to file
# trips_json = json.dumps(trips)
# with open('trips.json', 'w', encoding='utf-8') as file:
#     file.write(trips_json)
