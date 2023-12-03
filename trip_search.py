import json
import requests
import api_constants
import dateparser
from datetime import datetime
from pprint import pprint
from payment import SeleniumPayment


to_station = "İstanbul(Pendik)"
from_station = "Ankara Gar"
from_date = "10 december 14:00"
to_date = "10 december 16:00"


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
    index_dict = {d['koltukNo']: d for d in koltuk_durumlari if 'koltukNo' in d}
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
        yield empty_seat

# return a list of dictionaries


def get_active_vagons(json_data):
    """
    Retrieves the list of active wagons from the given JSON data.

    Args:
        json_data (list): A list of dictionaries representing the JSON data.

    Returns:
        list: A list of dictionaries containing the active wagon details, including 'vagonBaslikId' and 'vagonSiraNo'.
    """
    active_vagons = list()
    for item in json_data:
        for vagon in item['vagonListesi']:
            if vagon['aktif'] == True:
                v = {'vagonBaslikId': vagon['vagonBaslikId'],
                     'vagonSiraNo': vagon['vagonSiraNo']}
                active_vagons.append(v)
    return active_vagons


def select_first_empty_seat(trip):
    """
    Selects the first empty seat for a given trip.

    Args:
        trip (dict): The trip information.

    Returns:
        dict: The response JSON containing the selected seat information if the response code is 200.
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
        s_response = requests.post(api_constants.SEAT_CHECK_ENDPOINT,
                                   headers=api_constants.REQUEST_HEADER, data=json.dumps(s_check), timeout=10)
        s_response_json = json.loads(s_response.text)
        if s_response_json['koltukLocked'] == False:
            # Send the request to the endpoint
            response = requests.post(api_constants.SELECT_EMPTY_SEAT_ENDPOINT,
                                     headers=api_constants.REQUEST_HEADER, data=json.dumps(seat_select_req), timeout=10)
            response_json = json.loads(response.text)
            # return trip with selected seat if the response code is 200
            return response_json
        else:
            pprint("Seat is locked")
            return None


def get_empty_seats_trip(trip):
    """
    Retrieves the empty seats for a given trip.

    Args:
        trip (dict): The trip object containing information about the trip.

    Returns:
        dict: The trip object with an additional 'empty_seats' field containing the list of empty seats.
    """
    # clone trip object
    trip_with_seats = trip.copy()
    vagon_req = api_constants.vagon_req_body.copy()
    vagon_map_req = api_constants.vagon_harita_req_body.copy()
    empty_seats = list()
    vagon_req['seferBaslikId'] = trip['seferId']
    vagon_req['binisIstId'] = trip['binisIstasyonId']
    vagon_req['inisIstId'] = trip['inisIstasyonId']
    # Send the request to the endpoint
    response = requests.post(api_constants.VAGON_SEARCH_ENDPOINT,
                             headers=api_constants.REQUEST_HEADER, data=json.dumps(vagon_req), timeout=10)
    response_json = json.loads(response.text)
    for vagon in response_json['vagonBosYerList']:
        vagon_map_req['vagonSiraNo'] = vagon['vagonSiraNo']
        vagon_map_req['seferBaslikId'] = vagon_req['seferBaslikId']
        vagon_map_req['binisIst'] = from_station
        vagon_map_req['InisIst'] = to_station
        # Send the request to the endpoint
        response = requests.post(api_constants.VAGON_HARITA_ENDPOINT,
                                 headers=api_constants.REQUEST_HEADER, data=json.dumps(vagon_map_req), timeout=10)
        response_json = json.loads(response.text)
        for empty_set in get_empty_vagon_seats(response_json):
            empty_seats.append(empty_set)
    trip_with_seats['empty_seats'] = empty_seats
    return trip_with_seats


def get_trips(from_station, to_station, from_date, to_date):
    """
    Retrieves a list of trips based on the specified parameters.

    Args:
        from_station (str): The name of the departure station.
        to_station (str): The name of the destination station.
        from_date (str): The departure date in the format 'YYYY-MM-DD'.
        to_date (str): The maximum date for the trips in the format 'YYYY-MM-DD'.

    Returns:
        list: A list of dictionaries representing the trips. Each dictionary contains the following keys:
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

    vagon_req_body = api_constants.vagon_req_body.copy()
    trip_req = api_constants.trip_search_req_body.copy()
    trips = list()
    from_date = dateparser.parse(from_date)
    to_date = dateparser.parse(to_date)

    with open('station_list.json') as f:
        station_list = json.load(f)
    # Find the station that matches from_station
        for station in station_list:
            if station['station_name'] == from_station:
                binisIstasyonId = station['station_id']
                vagon_req_body['binisIstId'] = binisIstasyonId
                trip_req['seferSorgulamaKriterWSDVO']['binisIstasyonu'] = from_station
                trip_req['seferSorgulamaKriterWSDVO']['binisIstasyonId'] = binisIstasyonId
            if station['station_name'] == to_station:
                inisIstasyonId = station['station_id']
                vagon_req_body['inisIstId'] = inisIstasyonId
                trip_req['seferSorgulamaKriterWSDVO']['inisIstasyonId'] = inisIstasyonId
                trip_req['seferSorgulamaKriterWSDVO']['inisIstasyonu'] = to_station
    # Set the date
    trip_req['seferSorgulamaKriterWSDVO']['gidisTarih'] = datetime.strftime(
        from_date, "%b %d, %Y %I:%M:%S %p")
    # pprint(trip_req)

    response = requests.post(api_constants.TRIP_SEARCH_ENDPOINT,
                             headers=api_constants.REQUEST_HEADER, data=json.dumps(trip_req), timeout=10)

    response_json = json.loads(response.text)
    # pprint(response_json)

    sorted_trips = sorted(response_json['seferSorgulamaSonucList'], key=lambda trip: datetime.strptime(
        trip['binisTarih'], "%b %d, %Y %I:%M:%S %p"))

    # pprint(len(sorted_trips))
    # ony get trips whose date is less than to_date
    sorted_trips = [trip for trip in sorted_trips if datetime.strptime(
        trip['binisTarih'], "%b %d, %Y %I:%M:%S %p") < to_date]
    # pprint(len(sorted_trips))

    for trip in sorted_trips:
        if trip['satisDurum'] == 1 and trip['vagonHaritasindanKoltukSecimi'] == 1:
            # 0 is economy class and 1 is business class
            try:
                t = {}
                t['vagons'] = get_active_vagons(
                    trip['vagonTipleriBosYerUcret'])
                t['eco_empty_seat_count'] = trip['vagonTipleriBosYerUcret'][0]['kalanSayi'] - \
                    trip['vagonTipleriBosYerUcret'][0]['kalanEngelliKoltukSayisi']
                t['buss_empty_seat_count'] = trip['vagonTipleriBosYerUcret'][1]['kalanSayi'] - \
                    trip['vagonTipleriBosYerUcret'][1]['kalanEngelliKoltukSayisi']
                t['empty_seat_count'] = t['eco_empty_seat_count'] + \
                    t['buss_empty_seat_count']
                t['binisTarih'] = trip['binisTarih']
                t['inisTarih'] = trip['inisTarih']
                t['trenAdi'] = trip['trenAdi']
                t['seferAdi'] = trip['seferAdi']
                t['seferId'] = trip['seferId']
                t['binisIstasyonId'] = trip_req['seferSorgulamaKriterWSDVO']['binisIstasyonId']
                t['inisIstasyonId'] = trip_req['seferSorgulamaKriterWSDVO']['inisIstasyonId']
                trips.append(t)
                date_object = datetime.strptime(
                    trip['binisTarih'], "%b %d, %Y %I:%M:%S %p")
                # print(
                #    f"Engelli  : {trip['vagonTipleriBosYerUcret'][0]['kalanEngelliKoltukSayisi']}  Total Kalan Bos: {trip['vagonTipleriBosYerUcret'][0]['kalanSayi']}")
                print(
                    f"Eco empty: {t['eco_empty_seat_count']}  Buss empty:{t['buss_empty_seat_count']}         -- {date_object.strftime('%H:%M')}")
            except IndexError:  # no business class, just ignore
                pprint("No business class")
    return trips


trips = get_trips(from_station, to_station, from_date, to_date)
pprint(len(trips))
for trip in trips:
    trip = get_empty_seats_trip(trip)
    # pprint(trip)
    if trip['empty_seat_count'] > 0:
        pprint("Found empty seats")
        result = select_first_empty_seat(trip)
        vb_enroll_control_req = api_constants.vb_enroll_control_req_body.copy()
        pprint(result)
        for seat in result['koltuklarimListesi']:
            vb_enroll_control_req['koltukLockList'].append(
                seat['koltukLockId'])
        response = requests.post(api_constants.VB_ENROLL_CONTROL_ENDPOINT,
                                 headers=api_constants.REQUEST_HEADER, data=json.dumps(vb_enroll_control_req), timeout=10)

        response_json = json.loads(response.text)
        pprint(vb_enroll_control_req)

        session = requests.Session()

        acs_url = response_json['paymentAuthRequest']['acsUrl']
        pareq = response_json['paymentAuthRequest']['pareq']
        md = response_json['paymentAuthRequest']['md']
        term_url = response_json['paymentAuthRequest']['termUrl']

        form_data = {
            'PaReq': pareq,
            'MD': md,
            'TermUrl': term_url
        }

        response = session.post(acs_url, data=form_data)
        # save the response to a file and then open it with selenium

        seleniumPayment = SeleniumPayment()
        seleniumPayment.open_html_with_selenium(response.text)
    else:
        pprint("No empty seats")
exit(0)
# dump trips to json and then write to file
trips_json = json.dumps(trips)
with open('trips.json', 'w', encoding='utf-8') as file:
    file.write(trips_json)


for trip in trips:
    result = get_empty_seats_trip(trip)
    seat = select_first_empty_seat(result)
    # dump to json and write result to the file named trip_seats.json
    result_json = json.dumps(seat)
    with open('trip_seats.json', 'w', encoding='utf-8') as file:
        file.write(result_json)
    exit(0)
exit(0)
