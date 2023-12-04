""" This module contains the function to retrieve the list of stations
from the API endpoint and filters out the high-speed train stations. """
import json
from pprint import pprint
import requests
from _utils import find_value
import api_constants


def get_station_list():
    """
    Retrieves the list of stations from the API endpoint and filters out the high-speed train stations.

    Returns:
        str: JSON string representation of the filtered station list.
        int: HTTP status code if the request fails.
    """

    hst_stations = list()

    try:
        # Send the request to the endpoint
        response = requests.post(
            api_constants.STATION_LIST_ENDPOINT,
            headers=api_constants.REQUEST_HEADER,
            data=api_constants.STATION_LIST_REQUEST_BODY,
            timeout=10)

        response.raise_for_status()  # Raise an exception if the request fails

        # Parse the JSON response
        data = json.loads(response.text)

        for item in data['istasyonBilgileriList']:
            if "YHT" in item['stationTrainTypes']:
                station = {}
                station['station_name'] = find_value(item, 'istasyonAdi')
                station['station_code'] = find_value(item, 'istasyonKodu')
                station['station_id'] = find_value(item, 'istasyonId')
                station['is_available'] = find_value(item, 'istasyonDurumu')
                station['is_purchasable'] = find_value(
                    item, 'satisSorgudaGelsin')

                # Filter out the stations that are not available or not
                # purchasable
                if station['is_available'] is True and station['is_purchasable'] is True:
                    hst_stations.append(station)

        return hst_stations

    except requests.exceptions.RequestException as e:
        print("Failed to get station list:", str(e))
        return None
