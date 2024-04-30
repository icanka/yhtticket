""" This module contains the functions for searching for trips and selecting empty seats."""

import json
import logging
from pprint import pprint
from datetime import datetime
import requests
import dateparser
import api_constants
from _utils import find_value


class SeatLockedException(Exception):
    """Exception raised when a seat is already locked."""

    def __init__(self, seat):
        self.seat = seat
        self.message = f"Seat: {seat} is already locked"
        super().__init__(self.message)


class TripSearchApi:
    """Class for searching for trips and selecting empty seats."""

    def __init__(self) -> None:
        # set up class logger
        self.logger = logging.getLogger(__name__)
        self.time_format = "%b %d, %Y %I:%M:%S %p"

    def get_empty_vagon_seats(self, vagon_json):
        """
        Returns a generator that yields empty seats from the given vagon_json.

        Args:
            vagon_json (dict): The JSON data containing vagon information.

        Yields:
            dict: A dictionary representing an empty seat.

        """

        # business and economy class seat ids
        vagon_yerlesim = vagon_json["vagonHaritasiIcerikDVO"]["vagonYerlesim"]
        koltuk_durumlari = vagon_json["vagonHaritasiIcerikDVO"]["koltukDurumlari"]
        # efficient way to merge two lists of dictionaries based on a common key
        index_dict = {d["koltukNo"]
            : d for d in koltuk_durumlari if "koltukNo" in d}
        # pprint(index_dict)
        merged_list = []
        for seat in vagon_yerlesim:
            seat_no = seat.get("koltukNo")
            if seat_no:
                merged_dict = {**seat, **index_dict.get(seat_no, {})}
                merged_list.append(merged_dict)

        # write merged list to file
        # Take only the seats which has the key for nesneTanimId in empty_seat_ids
        merged_list = [
            d
            for d in merged_list
            if d.get("nesneTanimId") not in api_constants.DISABLED_SEAT_IDS
        ]
        empty_seats = [d for d in merged_list if d.get("durum") == 0]
        # pprint(empty_seats)
        # yield items from empty_seats
        for empty_seat in empty_seats:
            yield empty_seat

    # return a list of dictionaries

    def get_active_vagons(self, json_data):
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
            for vagon in item["vagonListesi"]:
                if vagon["aktif"]:
                    v = {
                        "vagonBaslikId": vagon["vagonBaslikId"],
                        "vagonSiraNo": vagon["vagonSiraNo"],
                        "vagonTipId": item["vagonTipId"],
                    }
                    active_vagons.append(v)
        return active_vagons

    def select_first_empty_seat(self, trip, empty_seat=None):
        """
        Selects the first empty seat for a given trip.

        Args:
            trip (dict): The trip information. trip_json

        Returns:
            dict: The response JSON containing the selected seat information
            if the response code is 200.
        """
        # Select the first empty seat
        seat_select_req = api_constants.koltuk_sec_req_body.copy()
        s_check = api_constants.seat_check.copy()
        if trip["empty_seats"]:
            empty_seat = trip["empty_seats"][0] if empty_seat is None else empty_seat
            self.logger.info("Selecting the first empty seat: %s", empty_seat)

            seat_select_req["seferId"] = trip["seferId"]
            seat_select_req["vagonSiraNo"] = empty_seat["vagonSiraNo"]
            seat_select_req["koltukNo"] = empty_seat["koltukNo"]
            seat_select_req["binisIst"] = trip["binisIstasyonId"]
            seat_select_req["inisIst"] = trip["inisIstasyonId"]
            s_check["seferId"] = trip["seferId"]
            s_check["seciliVagonSiraNo"] = empty_seat["vagonSiraNo"]
            s_check["koltukNo"] = empty_seat["koltukNo"]

            try:
                s_response = requests.post(
                    api_constants.SEAT_CHECK_ENDPOINT,
                    headers=api_constants.REQUEST_HEADER,
                    data=json.dumps(s_check),
                    timeout=10,
                )
                s_response_json = json.loads(s_response.text)
                self.logger.debug(s_response_json)
            except requests.exceptions.RequestException as e:
                self.logger.error(
                    "Error occurred while fetching the seat check: %s", e)
                raise e

            if s_response_json["cevapBilgileri"]["cevapKodu"] != "000":
                self.logger.error("response_json: %s", s_response_json)
                raise Exception(
                    "Non zero response code: response_json: %s", s_response_json
                )

            if not s_response_json["koltukLocked"]:
                # Send the request to the endpoint

                try:
                    response = requests.post(
                        api_constants.SELECT_EMPTY_SEAT_ENDPOINT,
                        headers=api_constants.REQUEST_HEADER,
                        data=json.dumps(seat_select_req),
                        timeout=10,
                    )
                except requests.exceptions.RequestException as e:
                    self.logger.error(
                        "Error occurred while fetching the seat lock: %s", e
                    )
                    raise e

                response_json = json.loads(response.text)
                self.logger.debug(response_json)
                if response_json["cevapBilgileri"]["cevapKodu"] != "000":
                    self.logger.error(
                        "Non zero response code: response_json: %s", response_json
                    )
                    raise Exception(
                        "Non zero response code: response_json: %s", response_json
                    )
                end_time = response_json["koltuklarimListesi"][0]["bitisZamani"]
            else:
                raise SeatLockedException(empty_seat)
            return end_time, empty_seat, response_json

    def get_detailed_vagon_info_empty_seats(self, vagon_map_req, vagons):
        """
        Retrieves the empty seats for a given vagon.

        Args:
            vagon_map_req (dict): The request body for getting the seat map of a vagon.

        Returns:
            list: The list of dictionaries containing the empty seat information.
        """
        self.logger.debug(vagon_map_req)
        self.logger.debug(vagons)
        empty_seats = list()
        response = requests.post(
            api_constants.VAGON_HARITA_ENDPOINT,
            headers=api_constants.REQUEST_HEADER,
            data=json.dumps(vagon_map_req),
            timeout=10,
        )
        response_json = json.loads(response.text)
        self.logger.debug(response_json)

        for empty_seat in self.get_empty_vagon_seats(response_json):
            empty_seat["vagonTipId"] = next(
                vagon["vagonTipId"]
                for vagon in vagons
                if vagon["vagonSiraNo"] == vagon_map_req["vagonSiraNo"]
            )
            empty_seats.append(empty_seat)

        self.logger.debug(empty_seats)
        return empty_seats

    def get_empty_seats_trip(self, trip, from_station, to_station, seat_type=None):
        """
        Retrieves the empty seats for a given trip.

        Args:
            trip (dict): The trip object containing information about the trip.

        Returns:
            dict: The trip object with an additional 'empty_seats' field
            containing the list of empty seats or an empty list if no empty seats are found.
        """
        # clone trip object
        trip_with_seats = trip.copy()
        vagon_req = api_constants.vagon_req_body.copy()
        vagon_map_req = api_constants.vagon_harita_req_body.copy()

        vagon_req["seferBaslikId"] = trip_with_seats["seferId"]
        vagon_req["binisIstId"] = trip_with_seats["binisIstasyonId"]
        vagon_req["inisIstId"] = trip_with_seats["inisIstasyonId"]

        # get the vagons' seat status for the trip
        self.logger.debug(vagon_req)
        response = requests.post(
            api_constants.VAGON_SEARCH_ENDPOINT,
            headers=api_constants.REQUEST_HEADER,
            data=json.dumps(vagon_req),
            timeout=10,
        )
        response_json = json.loads(response.text)
        self.logger.debug(response_json)
        trip_with_seats["empty_seats"] = list()
        for vagon in response_json["vagonBosYerList"]:
            vagon_map_req["vagonSiraNo"] = vagon["vagonSiraNo"]
            vagon_map_req["seferBaslikId"] = vagon_req["seferBaslikId"]
            vagon_map_req["binisIst"] = from_station
            vagon_map_req["InisIst"] = to_station
            if seat_type is not None:
                vagon_type = next(
                    vagon_["vagonTipId"]
                    for vagon_ in trip["vagons"]
                    if vagon_["vagonSiraNo"] == vagon["vagonSiraNo"]
                )
                if seat_type != vagon_type:
                    continue
            empty_seats = self.get_detailed_vagon_info_empty_seats(
                vagon_map_req, trip["vagons"]
            )
            self.logger.debug(empty_seats)
            trip_with_seats["empty_seats"].extend(empty_seats)
        self.logger.info(
            "Length of empty seats: %s", len(trip_with_seats["empty_seats"])
        )
        return trip_with_seats

    def check_stations(self, stations, from_station, to_station):
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
        if from_station not in [station["station_name"] for station in stations]:
            self.logger.error("%s is not a valid station", from_station)
            raise ValueError(f"{from_station} is not a valid station")

        if to_station not in [station["station_name"] for station in stations]:
            self.logger.error("%s is not a valid station", to_station)
            raise ValueError(f"{to_station} is not a valid station")

    def search_trips(
        self,
        from_station,
        to_station,
        from_date=None,
        to_date=None,
        check_satis_durum=True,
    ):
        """
        Search for trips based on the given parameters.

        Args:
            from_station (str): The name of the departure station.
            to_station (str): The name of the destination station.
            from_date (str, optional): The departure date in an human readable format.
            to_date (str, optional): The maximum arrival date in an human readable format. Defaults to None.
            check_satis_durum (bool, optional): Whether to check the sales status of the trip. Defaults to True.
                if the trip has no available seats at all, it will be filtered out. For example, if the trip has
                only disabled seats, it will be filtered out.

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
        # log the method parameters
        self.logger.info(
            "Searching for trips.\nfrom_station: %s to_station: %s from_date: %s to_date: %s",
            from_station,
            to_station,
            from_date,
            to_date,
        )

        if not from_date:
            from_date = datetime.now().strftime(self.time_format)

        vagon_req_body = api_constants.vagon_req_body.copy()
        trip_req = api_constants.trip_search_req_body.copy()
        trips = list()
        from_date = dateparser.parse(from_date)

        stations = self.get_station_list()

        try:
            self.check_stations(stations, from_station, to_station)
        except ValueError as e:
            self.logger.error(e)
            raise e

        # Find the station that matches from_station
        for station in stations:
            if station["station_name"] == from_station:
                binis_istasyon_id = station["station_id"]
                vagon_req_body["binisIstId"] = binis_istasyon_id
                trip_req["seferSorgulamaKriterWSDVO"]["binisIstasyonu"] = from_station
                trip_req["seferSorgulamaKriterWSDVO"][
                    "binisIstasyonId"
                ] = binis_istasyon_id
            if station["station_name"] == to_station:
                inis_istasyon_id = station["station_id"]
                vagon_req_body["inisIstId"] = inis_istasyon_id
                trip_req["seferSorgulamaKriterWSDVO"][
                    "inisIstasyonId"
                ] = inis_istasyon_id
                trip_req["seferSorgulamaKriterWSDVO"]["inisIstasyonu"] = to_station
        # Set the date
        trip_req["seferSorgulamaKriterWSDVO"]["gidisTarih"] = datetime.strftime(
            from_date, self.time_format
        )

        response = requests.post(
            api_constants.TRIP_SEARCH_ENDPOINT,
            headers=api_constants.REQUEST_HEADER,
            data=json.dumps(trip_req),
            timeout=30,
        )

        response_json = json.loads(response.text)

        sorted_trips = sorted(
            response_json["seferSorgulamaSonucList"],
            key=lambda trip: datetime.strptime(
                trip["binisTarih"], self.time_format),
        )

        # filter trips based on to_date
        if to_date:
            to_date = dateparser.parse(to_date)
            sorted_trips = [
                trip
                for trip in sorted_trips
                if datetime.strptime(trip["binisTarih"], self.time_format) < to_date
            ]
        for trip in sorted_trips:
            if trip["vagonHaritasindanKoltukSecimi"] == 1 and (
                trip["satisDurum"] == 1 or not check_satis_durum
            ):  # and trip['satisDurum'] == 1
                try:
                    t = {}
                    t["vagons"] = self.get_active_vagons(
                        trip["vagonTipleriBosYerUcret"]
                    )

                    # kalansayi seems to be updated a little bit later on server side
                    # so empty_seat_count can be negative.

                    t["eco_empty_seat_count"] = (
                        trip["vagonTipleriBosYerUcret"][0]["kalanSayi"]
                        - trip["vagonTipleriBosYerUcret"][0]["kalanEngelliKoltukSayisi"]
                    )

                    t["buss_empty_seat_count"] = (
                        trip["vagonTipleriBosYerUcret"][1]["kalanSayi"]
                        - trip["vagonTipleriBosYerUcret"][1]["kalanEngelliKoltukSayisi"]
                    )

                    t["empty_seat_count"] = (
                        t["eco_empty_seat_count"] + t["buss_empty_seat_count"]
                    )
                    # sanitize the empty seat count
                    t["empty_seat_count"] = 0 if t["empty_seat_count"] < 0 else t["empty_seat_count"]

                    t["binisTarih"] = trip["binisTarih"]
                    t["inisTarih"] = trip["inisTarih"]
                    t["trenAdi"] = trip["trenAdi"]
                    t["seferAdi"] = trip["seferAdi"]
                    t["seferId"] = trip["seferId"]
                    t["trenTuruTktId"] = trip["trenTuruTktId"]
                    t["seyahatTuru"] = trip["seyahatTuru"]
                    t["binisIstasyonId"] = trip_req["seferSorgulamaKriterWSDVO"][
                        "binisIstasyonId"
                    ]
                    t["inisIstasyonId"] = trip_req["seferSorgulamaKriterWSDVO"][
                        "inisIstasyonId"
                    ]
                    trips.append(t)
                except IndexError as e:  # no business class, just ignore
                    self.logger.error("IndexError: %s", e)
                    self.logger.error("No business class for trip: %s", trip)
        return trips

    def get_station_list(self):
        """
        Retrieves the list of stations from the API endpoint and filters out the
        high-speed train stations.

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
                timeout=10,
            )

            response.raise_for_status()  # Raise an exception if the request fails

            # Parse the JSON response
            data = json.loads(response.text)

            for item in data["istasyonBilgileriList"]:
                if "YHT" in item["stationTrainTypes"]:
                    station = {}
                    station["station_name"] = find_value(item, "istasyonAdi")
                    station["station_code"] = find_value(item, "istasyonKodu")
                    station["station_id"] = find_value(item, "istasyonId")
                    station["station_view_name"] = find_value(
                        item, "stationViewName")
                    station["is_available"] = find_value(
                        item, "istasyonDurumu")
                    station["is_purchasable"] = find_value(
                        item, "satisSorgudaGelsin")

                    # Filter out the stations that are not available or not
                    # purchasable
                    if (
                        station["is_available"] is True
                        and station["is_purchasable"] is True
                    ):
                        hst_stations.append(station)

            return hst_stations

        except requests.exceptions.RequestException as e:
            self.logger.error(
                "Error occurred while fetching the station list: %s", e)
            raise e
