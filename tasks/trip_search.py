""" This module contains the functions for searching for trips and selecting empty seats."""

import asyncio
import json
import random
import aiohttp
import logging
from datetime import datetime, timedelta
import time
import requests
import dateparser
from requests.exceptions import RequestException
import api_constants
from _utils import find_value
from passenger import Passenger

logger = logging.getLogger(__name__)


class SeatLockedException(Exception):
    """Exception raised when a seat is already locked."""

    def __init__(self, seat):
        self.seat = seat
        self.message = f"Seat: {seat} is already locked"
        super().__init__(self.message)


class TripSearchApi:
    """Class for searching for trips and selecting empty seats."""

    time_format = "%b %d, %Y %I:%M:%S %p"

    # def __init__(self) -> None:
    #     # set up class logger
    #     logger = logging.getLogger(__name__)
    #     self.time_format = "%b %d, %Y %I:%M:%S %p"

    @staticmethod
    def get_empty_vagon_seats(vagon_json):
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
        index_dict = {d["koltukNo"]: d for d in koltuk_durumlari if "koltukNo" in d}
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

    @staticmethod
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
            for vagon in item["vagonListesi"]:
                if vagon["aktif"]:
                    v = {
                        "vagonBaslikId": vagon["vagonBaslikId"],
                        "vagonSiraNo": vagon["vagonSiraNo"],
                        "vagonTipId": item["vagonTipId"],
                    }
                    active_vagons.append(v)
        return active_vagons

    @staticmethod
    def select_first_empty_seat(trip, empty_seat=None):
        """
        Selects the first empty seat for a given trip.

        Args:
            trip (dict): The trip information. trip_json

        Returns:
            dict: The response JSON containing the selected seat information
            if the response code is 200.
        """

        retries = 0
        max_retries = 3
        sleep = 3
        timeout = 10
        # Select the first empty seat
        seat_select_req = api_constants.koltuk_sec_req_body.copy()
        s_check = api_constants.seat_check.copy()
        if trip["empty_seats"]:
            empty_seat = trip["empty_seats"][0] if empty_seat is None else empty_seat
            logger.info("Selecting empty seat: koltukNo: %s", empty_seat["koltukNo"])

            seat_select_req["seferId"] = trip["seferId"]
            seat_select_req["vagonSiraNo"] = empty_seat["vagonSiraNo"]
            seat_select_req["koltukNo"] = empty_seat["koltukNo"]
            seat_select_req["binisIst"] = trip["binisIstasyonId"]
            seat_select_req["inisIst"] = trip["inisIstasyonId"]
            s_check["seferId"] = trip["seferId"]
            s_check["seciliVagonSiraNo"] = empty_seat["vagonSiraNo"]
            s_check["koltukNo"] = empty_seat["koltukNo"]

            # for test purposes throw connectiontimeout exception

            while retries < max_retries:
                try:
                    s_response = requests.post(
                        api_constants.SEAT_CHECK_ENDPOINT,
                        headers=api_constants.REQUEST_HEADER,
                        data=json.dumps(s_check),
                        timeout=timeout,
                    )
                    s_response.raise_for_status()
                    s_response_json = s_response.json()

                    if s_response_json["cevapBilgileri"]["cevapKodu"] != "000":
                        logger.error("response_json: %s", s_response_json)
                        raise ValueError(
                            f"Non zero response code: s_response_json: {s_response_json}"
                        )

                    if not s_response_json["koltukLocked"]:
                        response = requests.post(
                            api_constants.SELECT_EMPTY_SEAT_ENDPOINT,
                            headers=api_constants.REQUEST_HEADER,
                            data=json.dumps(seat_select_req),
                            timeout=timeout,
                        )

                        response.raise_for_status()
                        response_json = response.json()

                        if response_json["cevapBilgileri"]["cevapKodu"] != "000":
                            logger.error(
                                "Non zero response code: response_json: %s",
                                response_json,
                            )
                            raise ValueError(
                                f"Non zero response code: response_json: {response_json}"
                            )
                        end_time = response_json["koltuklarimListesi"][0]["bitisZamani"]
                        logger.info("Breaking, Response status code: %s", response.status_code)
                        break
                    else:
                        raise SeatLockedException(empty_seat)
                except RequestException as e:
                    logger.error("Request exception: %s", e)
                    retries += 1
                    logger.error("Retrying seat selection. Retry count: %s", retries)
                    time.sleep(sleep)

            return end_time, empty_seat, response_json

    @staticmethod
    async def get_detailed_vagon_info_empty_seats(vagon_map_req, vagons, event: asyncio.Event = None):
        """
        Retrieves the empty seats for a given vagon.

        Args:
            vagon_map_req (dict): The request body for getting the seat map of a vagon.

        Returns:
            list: The list of dictionaries containing the empty seat information.
        """
        retries = 0
        max_retries = 0
        sleep = 3
        timeout = 3

        empty_seats = list()
        response_json = None

        while retries < max_retries:
            if event and event.is_set():
                logger.info("Event is set. Exiting.")
                break
            sleep_ = random.randint(int(sleep/3), sleep)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        api_constants.VAGON_HARITA_ENDPOINT,
                        headers=api_constants.REQUEST_HEADER,
                        data=json.dumps(vagon_map_req),
                        timeout=timeout,
                    ) as resp:
                        #resp.raise_for_status()
                        response_json = await resp.json()
                        logger.info("Breaking, Response status code: %s", resp.status)
                    break
            # except timeout error
            except asyncio.TimeoutError as e:
                logger.error("Timeout error while getting vagon map: %s", e)
                retries += 1
                logger.error("Sleeping: %s before Retrying vagon map. Retry count: %s", sleep_, retries)
                await asyncio.sleep(sleep_)
            except aiohttp.ClientError as e:
                logger.error("Error while getting vagon map: %s", e)
                retries += 1
                # random number between 0 and 30
                logger.error("Sleeping: %s before Retrying vagon map. Retry count: %s", sleep_, retries)
                await asyncio.sleep(sleep_)

        if response_json:
            for empty_seat in TripSearchApi.get_empty_vagon_seats(response_json):
                empty_seat["vagonTipId"] = next(
                    vagon["vagonTipId"]
                    for vagon in vagons
                    if vagon["vagonSiraNo"] == vagon_map_req["vagonSiraNo"]
                )
                empty_seats.append(empty_seat)
        logger.info("sefer: %s, vagon: %s, empty seats: %s", vagon_map_req["seferBaslikId"], vagon_map_req["vagonSiraNo"], len(empty_seats))
        return empty_seats

    @staticmethod
    async def get_empty_seats_trip(trip, from_station, to_station, seat_type=None, event: asyncio.Event = None):
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
        vagon_map_req = api_constants.vagon_harita_req_body.copy()
        trip_with_seats["empty_seats"] = list()

        for vagon in trip["vagons"]:
            vagon_map_req["vagonSiraNo"] = vagon["vagonSiraNo"]
            vagon_map_req["seferBaslikId"] = trip_with_seats["seferId"]
            vagon_map_req["binisIst"] = from_station
            vagon_map_req["InisIst"] = to_station
            if seat_type is not None:
                vagon_type = vagon["vagonTipId"]
                if seat_type != vagon_type:
                    continue
            empty_seats = await TripSearchApi.get_detailed_vagon_info_empty_seats(
                vagon_map_req, trip["vagons"], event=event
            )
            trip_with_seats["empty_seats"].extend(empty_seats)
        # logger.info("Length of empty seats: %s", len(trip_with_seats["empty_seats"]))

        return trip_with_seats

    @staticmethod
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
        if from_station not in [station["station_name"] for station in stations]:
            logger.error("%s is not a valid station", from_station)
            raise ValueError(f"{from_station} is not a valid station")

        if to_station not in [station["station_name"] for station in stations]:
            logger.error("%s is not a valid station", to_station)
            raise ValueError(f"{to_station} is not a valid station")

    @staticmethod
    def search_trips(
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
        retries = 0
        max_retries = 10
        sleep = 30
        timeout = 10

        logger.info(
            "Searching for trips. from_station: %s to_station: %s from_date: %s to_date: %s",
            from_station,
            to_station,
            from_date,
            to_date,
        )

        if not from_date:
            logger.info("from_date is not provided. Using the current date.")
            from_date = datetime.now().strftime(TripSearchApi.time_format)

        vagon_req_body = api_constants.vagon_req_body.copy()
        trip_req = api_constants.trip_search_req_body.copy()
        trips = list()
        from_date = dateparser.parse(from_date)

        stations = TripSearchApi.get_station_list()
        try:
            TripSearchApi.check_stations(stations, from_station, to_station)
        except ValueError as e:
            logger.error(e)
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
            from_date, TripSearchApi.time_format
        )

        response = None
        while retries < max_retries:
            try:
                response = requests.post(
                    api_constants.TRIP_SEARCH_ENDPOINT,
                    headers=api_constants.REQUEST_HEADER,
                    data=json.dumps(trip_req),
                    timeout=timeout,
                )
                response.raise_for_status()
                logger.info("Breaking, Response status code: %s", response.status_code)
                break
            except RequestException as e:
                logger.error("Error while searching for trips: %s", e)
                retries += 1
                logger.error("Retrying trip search. Retry count: %s", retries)
                time.sleep(sleep)
            
        response_json = response.json()

        sorted_trips = sorted(
            response_json["seferSorgulamaSonucList"],
            key=lambda trip: datetime.strptime(
                trip["binisTarih"], TripSearchApi.time_format
            ),
        )

        # filter trips based on to_date
        logger.info("total trip count: %s", len(sorted_trips))
        if to_date:
            to_date = dateparser.parse(to_date)
            # add one minute to the to_date in case the trip is at the same time
            to_date += timedelta(minutes=1)
            sorted_trips = [
                trip
                for trip in sorted_trips
                if datetime.strptime(trip["binisTarih"], TripSearchApi.time_format)
                < to_date
            ]

        logger.info("trip count after sort: %s", len(sorted_trips))
        for trip in sorted_trips:
            if trip["vagonHaritasindanKoltukSecimi"] == 1 and (
                trip["satisDurum"] == 1 or not check_satis_durum
            ):  # and trip['satisDurum'] == 1
                try:
                    t = {}
                    t["eco_empty_seat_count"], t["buss_empty_seat_count"] = 0, 0

                    t["vagons"] = TripSearchApi.get_active_vagons(
                        trip["vagonTipleriBosYerUcret"]
                    )

                    # kalansayi seems to be updated a little bit later on server side
                    # so empty_seat_count can be negative after calculation.

                    # this does not kinda work with 'Anahat' trips because [0] is not economy class
                    # with open("trip1111.json", "w") as file:
                    #    file.write(str(trip))

                    for vagon_type in trip["vagonTipleriBosYerUcret"]:
                        # 17002 is the vagonTipId for economy class
                        if vagon_type["vagonTipId"] == 17002:
                            t["eco_empty_seat_count"] = (
                                vagon_type["kalanSayi"]
                                - vagon_type["kalanEngelliKoltukSayisi"]
                            )
                            t["eco_empty_seat_count"] = (
                                0
                                if t["eco_empty_seat_count"] < 0
                                else t["eco_empty_seat_count"]
                            )
                        # 17001 is the vagonTipId for business class
                        if vagon_type["vagonTipId"] == 17001:
                            t["buss_empty_seat_count"] = (
                                vagon_type["kalanSayi"]
                                - vagon_type["kalanEngelliKoltukSayisi"]
                            )

                        # 11750035651 is the vagonTipId for 'anahat' trips' bed seat
                        if vagon_type["vagonTipId"] == 11750035651:
                            pass

                    t["empty_seat_count"] = t.get("eco_empty_seat_count", 0) + t.get(
                        "buss_empty_seat_count", 0
                    )

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
                    logger.error("IndexError: %s", e)
                    logger.error("No business class for trip: %s", trip["seferId"])
        return trips

    @staticmethod
    def get_station_list():
        """
        Retrieves the list of stations from the API endpoint and filters out the
        high-speed train stations.

        Returns:
            str: JSON string representation of the filtered station list.
            int: HTTP status code if the request fails.
        """
        retries = 0
        max_retries = 10
        sleep = 5
        timeout = 10
        hst_stations = list()

        while retries < max_retries:
            try:
                # Send the request to the endpoint
                response = requests.post(
                    api_constants.STATION_LIST_ENDPOINT,
                    headers=api_constants.REQUEST_HEADER,
                    data=api_constants.STATION_LIST_REQUEST_BODY,
                    timeout=timeout,
                )

                response.raise_for_status()
                data = response.json()

                for item in data["istasyonBilgileriList"]:
                    if "YHT" in item["stationTrainTypes"]:
                        station = {}
                        station["station_name"] = find_value(item, "istasyonAdi")
                        station["station_code"] = find_value(item, "istasyonKodu")
                        station["station_id"] = find_value(item, "istasyonId")
                        station["station_view_name"] = find_value(
                            item, "stationViewName"
                        )
                        station["is_available"] = find_value(item, "istasyonDurumu")
                        station["is_purchasable"] = find_value(
                            item, "satisSorgudaGelsin"
                        )

                        # Filter out the stations that are not available or not
                        # purchasable
                        if (
                            station["is_available"] is True
                            and station["is_purchasable"] is True
                        ):
                            hst_stations.append(station)
                logger.info("Breaking, Response status code: %s", response.status_code)
                return hst_stations

            except RequestException as e:
                logger.error("Error while getting station list: %s", e)
                retries += 1
                logger.error("Retrying station list. Retry count: %s", retries)
                time.sleep(sleep)

    @staticmethod
    def is_mernis_correct(passenger: Passenger, date_format: str = "%d/%m/%Y") -> bool:
        """Mernis verification for the given passenger."""
        retries = 0
        max_retries = 10
        sleep = 5

        mernis_req_body = api_constants.mernis_dogrula_req_body.copy()
        date = datetime.strptime(passenger.birthday, date_format).strftime(
            TripSearchApi.time_format
        )

        mernis_req_body["ad"] = passenger.name
        mernis_req_body["soyad"] = passenger.surname
        mernis_req_body["tckn"] = passenger.tckn
        mernis_req_body["dogumTar"] = date

        while retries < max_retries:
            try:
                response = requests.post(
                    api_constants.MERNIS_DOGRULAMA_ENDPOINT,
                    headers=api_constants.REQUEST_HEADER,
                    data=json.dumps(mernis_req_body),
                    timeout=30,
                )
                response.raise_for_status()
                response_json = response.json()
                logger.debug(response_json)

                if response_json["cevapBilgileri"]["cevapKodu"] != "000":
                    logger.error(
                        "Mernis verification failed. response_json: %s", response_json
                    )
                    logger.error(
                        "Passenger: %s %s TCKN: %s Birthday: %s",
                        passenger.name,
                        passenger.surname,
                        passenger.tckn,
                        date,
                    )
                    raise ValueError(response_json["cevapBilgileri"]["cevapMsj"])
                logger.info("Breaking, Response status code: %s", response.status_code)
                break
            except (requests.RequestException, ValueError) as e:
                retries += 1
                logger.error("Error while verifying mernis: %s", e)
                logger.error("Retrying mernis verification. Retry count: %s", retries)
                time.sleep(sleep)
                
        logger.info("Mernis verification succeeded.")
        return True
