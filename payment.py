""" This module contains the Payment class for handling payment operations."""

import json
import logging
import time
from datetime import datetime

import requests
from requests.exceptions import RequestException

import api_constants
from tasks.trip_search import TripSearchApi

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handlers = [
    logging.FileHandler("bot_data/logs/payment.log"),
    logging.StreamHandler(),
]
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s"
)
for handler in handlers:
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class Payment:
    """
    A class for handling Selenium-based payment operations.

    Args:
        max_wait_time (int): Maximum wait time in seconds for page loading (default: 120).
        *args: Additional arguments to be passed to the Chrome options.
        **kwargs: Additional keyword arguments to be set as instance attributes.

    Attributes:
        options (Options): Chrome options for configuring the WebDriver.
        max_wait_time (int): Maximum wait time in seconds for page loading.

    Methods:
        open_html_with_selenium: Opens an HTML response using Selenium WebDriver.

    """

    def __init__(self, trip=None, **kwargs):
        """
        Initialize the Payment class.

        Args:
            *args: Variable length arguments.
            trip: Trip object.
            **kwargs: Variable keyword arguments.
        """

        self.price = None
        self.normal_price = None
        self.trip = trip
        self.base_payment_url = "https://ebilet.tcddtasimacilik.gov.tr/view/eybis/tnmGenel/tcdd3dsecure/3dsecure.html?url="
        self.current_payment_url = None
        # self.reserved_seat_data = reserved_seat_data

        self.vb_enroll_control_req = api_constants.vb_enroll_control_req_body.copy()
        self.ticket_reservation_req = api_constants.ticket_reservation_req_body.copy()
        self.ticket_reservation_info = None
        self.is_payment_successful = None
        self.vb_enroll_control_response = None
        self.html_response = None

        self.enroll_reference = None
        self.vpos_ref = None
        self.timeout = 10
        self.retry_delay = 30
        self.max_retries = 10
        self.odeme_sorgu = {
            "kanalKodu": "3",
            "dil": 0,
            "enrollReference": self.enroll_reference,
        }

        # add kwargs as instance attributes, you can override the default values
        for key, value in kwargs.items():
            setattr(self, key, value)

    def set_ticket_res_values(self):
        """_set_ticket_res_values"""
        self.ticket_reservation_req["biletRezYerBilgileri"][0]["biletWSDVO"].update(
            {
                "seferBaslikId": self.trip.trip_json["seferId"],
                "binisIstasyonId": self.trip.trip_json["binisIstasyonId"],
                "inisIstasyonId": self.trip.trip_json["inisIstasyonId"],
                "hareketTarihi": self.trip.trip_json["binisTarih"],
                "varisTarihi": self.trip.trip_json["varisTarih"],
                "tarifeId": self.trip.tariff,
                "vagonSiraNo": self.trip.empty_seat_json["vagonSiraNo"],
                "koltukNo": self.trip.empty_seat_json["koltukNo"],
                "ucret": self.price,
            }
        )
        logger.info(
            "Ticket reservation request values set: %s", self.ticket_reservation_req
        )

    def set_price(self):
        """
        Get the price of a trip for a given empty seat.

        Args:
            trip (dict): The trip information.
            empty_seat (dict): The information of the empty seat.

        Returns:
            float: The price of the trip for the empty seat.
        """

        vagon_tip_id = self.trip.empty_seat_json["vagonTipId"]
        # 17001 is the id for the economy class, 17002 is the id for the business class appere
        vagon_tip_id = 1 if vagon_tip_id == 17001 else 0

        req_body = api_constants.price_req_body.copy()
        req_body["yolcuList"][0]["tarifeId"] = self.trip.passenger.tariff
        seat_info = req_body["yolcuList"][0]["seferKoltuk"][0]
        seat_info.update(
            {
                "seferBaslikId": self.trip.trip_json["seferId"],
                "binisTarihi": self.trip.trip_json["binisTarih"],
                "vagonSiraNo": self.trip.empty_seat_json["vagonSiraNo"],
                "koltukNo": self.trip.empty_seat_json["koltukNo"],
                "binisIstasyonId": self.trip.trip_json["binisIstasyonId"],
                "inisIstasyonId": self.trip.trip_json["inisIstasyonId"],
                # This should  be'0' maybe, vuejs code sends '0' always for vagonTipId
                "vagonTipi": vagon_tip_id,
            }
        )
        logger.info("Price request: %s", json.dumps(req_body))
        # send request

        retries = 0
        while retries < self.max_retries:
            try:
                response = requests.post(
                    api_constants.PRICE_ENDPOINT,
                    headers=api_constants.REQUEST_HEADER,
                    data=json.dumps(req_body),
                    timeout=self.timeout,
                )
            except RequestException as e:
                retries += 1
                logger.error("Price request failed: %s, retry: %s", e, retries)
                time.sleep(self.retry_delay)
            break

        response_json = response.json()
        logger.info("Price response: %s", response_json["anahatFiyatHesSonucDVO"])
        self.normal_price = int(
            response_json["anahatFiyatHesSonucDVO"]["indirimsizToplamUcret"]
        )
        self.price = int(
            response_json["anahatFiyatHesSonucDVO"]["indirimliToplamUcret"]
        )

    def set_payment_url(self):
        """
        Process the payment for the trip.

        This method calculates the price, updates the payment information,
        sends a request to the payment API, and handles the payment authentication process.

        Returns:
            None
        """
        self.current_payment_url = None
        print(f"Price: {self.price}")

        self.vb_enroll_control_req["biletRezOdemeBilgileri"].update(
            {
                "krediKartNO": self.trip.passenger.credit_card_no,
                "krediKartSahibiAdSoyad": self.trip.passenger.name
                + " "
                + self.trip.passenger.surname,
                "ccv": self.trip.passenger.credit_card_ccv,
                "sonKullanmaTarihi": self.trip.passenger.credit_card_exp,
                "toplamBiletTutari": self.price,
                "krediKartiTutari": self.price,
            }
        )

        self.vb_enroll_control_req["koltukLockList"].clear()
        for seat in self.trip.seat_lock_response["koltuklarimListesi"]:
            self.vb_enroll_control_req["koltukLockList"].append(seat["koltukLockId"])

        retries = 0
        while retries < self.max_retries:
            try:
                response = requests.post(
                    api_constants.VB_ENROLL_CONTROL_ENDPOINT,
                    headers=api_constants.REQUEST_HEADER,
                    data=json.dumps(self.vb_enroll_control_req),
                    timeout=self.timeout,
                )
            except RequestException as e:
                retries += 1
                logger.error("Payment request failed: %s, retry: %s", e, retries)
                time.sleep(self.retry_delay)
            break

        response_json = response.json()
        if response_json["cevapBilgileri"]["cevapKodu"] != "000":
            logger.error("Payment failed: %s", response_json["cevapBilgileri"])
            raise ValueError(
                f"{response_json['cevapBilgileri']['cevapMsj']} {response_json['cevapBilgileri']['detay']}"
            )

        acs_url = response_json["paymentAuthRequest"]["acsUrl"]
        pareq = response_json["paymentAuthRequest"]["pareq"]
        md = response_json["paymentAuthRequest"]["md"]
        term_url = response_json["paymentAuthRequest"]["termUrl"]
        # used in vb_odeme_sorgu to validate payment
        self.enroll_reference = response_json["enrollReference"]
        # logger.info("response: %s", response_json)

        logger.info("Enroll reference: %s", self.enroll_reference)
        # logger.info("ACS URL: %s", acs_url)

        # form_data = {
        #     'PaReq': pareq,
        #     'MD': md,
        #     'TermUrl': term_url
        # }

        self.current_payment_url = (
            self.base_payment_url
            + acs_url
            + "&md="
            + md.replace("#", "%23")
            + "&pareq="
            + pareq
            + "&termurl="
            + term_url
        )

    def is_payment_success(self):
        """set_is_payment_success"""
        retries = 0
        logger.info("self.ode_sorgu: %s", self.odeme_sorgu)
        while retries < self.max_retries:
            try:
                odeme_sorgu_response = requests.post(
                    api_constants.VB_ODEME_SORGU,
                    headers=api_constants.REQUEST_HEADER,
                    data=json.dumps(self.odeme_sorgu),
                    timeout=self.timeout,
                )
                odeme_sorgu_response.raise_for_status()
            except RequestException as e:
                retries += 1
                logger.error("Odeme sorgu request failed: %s, retry: %s", e, retries)
                time.sleep(self.retry_delay)
            break

        odeme_sorgu_response_json = odeme_sorgu_response.json()

        if odeme_sorgu_response_json["cevapBilgileri"]["cevapKodu"] != "000":
            logger.error("Response: %s", odeme_sorgu_response.text)
            raise ValueError(
                f"{odeme_sorgu_response_json['cevapBilgileri']['cevapMsj']} {odeme_sorgu_response_json['cevapBilgileri']['detay']}"
            )
        else:
            logger.info("Response: %s", odeme_sorgu_response_json["vposReference"])
            self.vpos_ref = odeme_sorgu_response_json["vposReference"]
            return True

    def ticket_reservation(self, date_format="%d/%m/%Y"):
        """ticket_reservation"""
        req_body = api_constants.ticket_reservation_req_body.copy()
        req_body["biletRezYerBilgileri"][0]["biletWSDVO"].update(
            {
                "seferBaslikId": self.trip.trip_json["seferId"],
                "binisIstasyonId": self.trip.trip_json["binisIstasyonId"],
                "inisIstasyonId": self.trip.trip_json["inisIstasyonId"],
                "hareketTarihi": self.trip.trip_json["binisTarih"],
                "varisTarihi": self.trip.trip_json["inisTarih"],
                "trenTurTktId": self.trip.trip_json["trenTuruTktId"],
                "tckn": self.trip.passenger.tckn,
                "ad": self.trip.passenger.name,
                "soyad": self.trip.passenger.surname,
                "dogumTar": datetime.strptime(
                    self.trip.passenger.birthday, date_format
                ).strftime(TripSearchApi.time_format),
                "iletisimEposta": self.trip.passenger.email,
                "iletisimCepTel": self.trip.passenger.phone,
                "cinsiyet": self.trip.passenger.sex,
                "tarifeId": self.trip.passenger.tariff,
                "vagonSiraNo": self.trip.empty_seat_json["vagonSiraNo"],
                "koltukNo": self.trip.empty_seat_json["koltukNo"],
                "ucret": self.price,
                "koltukBazUcret": self.normal_price,
                "indirimsizUcret": self.normal_price,
            }
        )
        req_body["biletRezOdemeBilgileri"].update(
            {
                "vposReference": self.vpos_ref,
                "krediKartSahibiAdSoyad": self.trip.passenger.name
                + " "
                + self.trip.passenger.surname,
                "toplamBiletTutari": self.price,
                "krediKartiTutari": self.price,
                "krediKartNo": self.trip.passenger.credit_card_no,
            }
        )
        req_body["koltukLockIdList"] = self.trip.koltuk_lock_id_list

        logger.info("Ticket reservation request: %s", req_body)
        # send request

        retries = 0
        while retries < self.max_retries:
            try:
                response = requests.post(
                    api_constants.TICKET_RESERVATION_ENDPOINT,
                    headers=api_constants.REQUEST_HEADER,
                    data=json.dumps(req_body),
                    timeout=self.timeout,
                )
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                retries += 1
                logger.error(
                    "Ticket reservation request failed: %s, retry: %s", e, retries
                )
                time.sleep(self.retry_delay)
            break

        response_json = response.json()

        if response_json["cevapBilgileri"]["cevapKodu"] != "000":
            logger.error(
                "Ticket reservation failed: %s", response_json["cevapBilgileri"]
            )
            raise ValueError(
                f"{response_json['cevapBilgileri']['cevapMsj']} {response_json['cevapBilgileri']['detay']}"
            )
        else:
            logger.info("Ticket reservation successful.")
            self.ticket_reservation_info = response_json
            logger.debug("Ticket reservation response: %s", response_json)
            return True
