""" This module contains the SeleniumPayment class for handling Selenium-based payment operations."""

from datetime import datetime
import tempfile
import time
import requests
import json
from pprint import pprint
from selenium import webdriver
import selenium
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import api_constants
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import logging

from trip_search import TripSearchApi


# create a class which will be inherited from the SeleniumPayment class
class MainSeleniumPayment:
    def __init__(self, *args) -> None:
        self.logger = logging.getLogger(__name__)
        self.options = Options()
        self.options.add_argument("--disable-notifications")
        self.options.add_argument("--disable-geolocation")
        # self.options.add_argument("--disable-application-cache")
        # self.options.add_argument("--disable-cache")
        self.options.add_argument("--headless")
        self.options.add_argument("--disable-infobars")
        self.options.add_argument("--mute-audio")
        # self.options.add_argument("--disable-gpu")
        # self.options.add_argument("--no-sandbox")
        # self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--disable-extensions")
        # self.options.add_argument("--disable-software-rasterizer")
        # self.options.add_argument("--disable-setuid-sandbox")
        # self.options.add_argument("--disable-sandbox")
        # self.options.add_argument("--single-process")
        # self.options.add_argument("--ignore-certificate-errors")
        # self.options.add_argument("--ignore-ssl-errors")
        self.options.add_argument("--disable-logging")
        self.options.page_load_strategy = "eager"
        # add args values to options
        for arg in args:
            self.options.add_argument(arg)
        self.driver = webdriver.Chrome(options=self.options)
        self.driver.implicitly_wait(10)


#
class SeleniumPayment(MainSeleniumPayment):
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

    def __init__(self, *args, trip=None, **kwargs):
        """
        Initialize the Payment class.

        Args:
            *args: Variable length arguments.
            trip: Trip object.
            **kwargs: Variable keyword arguments.
        """
        super().__init__(*args)  # Call the __init__ method of the base class
        self.logger = logging.getLogger(__name__)

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
        self.logger.info(
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
        self.logger.info("Price request: %s", json.dumps(req_body))
        # send request
        response = requests.post(
            api_constants.PRICE_ENDPOINT,
            headers=api_constants.REQUEST_HEADER,
            data=json.dumps(req_body),
            timeout=10,
        )
        response_json = json.loads(response.text)
        self.logger.info("Price response: %s", response_json["anahatFiyatHesSonucDVO"])
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

        try:
            response = requests.post(
                api_constants.VB_ENROLL_CONTROL_ENDPOINT,
                headers=api_constants.REQUEST_HEADER,
                data=json.dumps(self.vb_enroll_control_req),
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            self.logger.error("Payment request failed: %s", e)
            raise e

        response_json = json.loads(response.text)
        if response_json["cevapBilgileri"]["cevapKodu"] != "000":
            self.logger.error("Payment failed: %s", response_json["cevapBilgileri"])
            raise ValueError(
                f"{response_json['cevapBilgileri']['cevapMsj']} {response_json['cevapBilgileri']['detay']}"
            )

        # with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
        #     temp_file.write(response.text.encode('utf-8'))
        #     temp_file_path = temp_file.name
        #     self.vb_enroll_control_response = temp_file_path
        #  Payment request
        # session = requests.Session()

        acs_url = response_json["paymentAuthRequest"]["acsUrl"]
        pareq = response_json["paymentAuthRequest"]["pareq"]
        md = response_json["paymentAuthRequest"]["md"]
        term_url = response_json["paymentAuthRequest"]["termUrl"]
        # used in vb_odeme_sorgu to validate payment
        self.enroll_reference = response_json["enrollReference"]
        # self.logger.info("response: %s", response_json)

        self.logger.info("Enroll reference: %s", self.enroll_reference)
        # self.logger.info("ACS URL: %s", acs_url)

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
        odeme_sorgu = {
            "kanalKodu": "3",
            "dil": 0,
            "enrollReference": self.enroll_reference,
        }
        self.logger.info("Sending odeme sorgu request: %s", odeme_sorgu)

        odeme_sorgu_response = requests.post(
            api_constants.VB_ODEME_SORGU,
            headers=api_constants.REQUEST_HEADER,
            data=json.dumps(odeme_sorgu),
            timeout=10,
        )

        odeme_sorgu_response.raise_for_status()
        odeme_sorgu_response_json = json.loads(odeme_sorgu_response.text)

        if odeme_sorgu_response_json["cevapBilgileri"]["cevapKodu"] != "000":
            self.logger.error("Response: %s", odeme_sorgu_response.text)
            raise ValueError(
                f"{odeme_sorgu_response_json['cevapBilgileri']['cevapMsj']} {odeme_sorgu_response_json['cevapBilgileri']['detay']}"
            )
        else:
            self.logger.info("Response: %s", odeme_sorgu_response_json["vposReference"])
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

        self.logger.info("Ticket reservation request: %s", req_body)
        # send request

        try:
            response = requests.post(
                api_constants.TICKET_RESERVATION_ENDPOINT,
                headers=api_constants.REQUEST_HEADER,
                data=json.dumps(req_body),
                timeout=30,
            )
        except Exception as e:
            self.logger.error("Ticket reservation request failed: %s", e)
            # print detailed error message
            self.logger.error("Ticket reservation request failed: %s", e.args)
            raise e

        response_json = json.loads(response.text)

        if response_json["cevapBilgileri"]["cevapKodu"] != "000":
            self.logger.error(
                "Ticket reservation failed: %s", response_json["cevapBilgileri"]
            )
            raise ValueError(
                f"{response_json['cevapBilgileri']['cevapMsj']} {response_json['cevapBilgileri']['detay']}"
            )
        else:
            self.logger.info("Ticket reservation successful.")
            self.ticket_reservation_info = response_json
            self.logger.debug("Ticket reservation response: %s", response_json)
            return True
