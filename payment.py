""" This module contains the SeleniumPayment class for handling Selenium-based payment operations."""
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


# create a class which will be inherited from the SeleniumPayment class
class MainSeleniumPayment:
    def __init__(self, *args) -> None:
        self.logger = logging.getLogger(__name__)
        self.options = Options()
        self.options.add_argument("--disable-notifications")
        self.options.add_argument("--disable-geolocation")
        # self.options.add_argument("--disable-application-cache")
        # self.options.add_argument("--disable-cache")
        # self.options.add_argument("--headless")
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
        self.options.page_load_strategy = 'eager'
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

    def __init__(
            self,
            *args,
            trip=None,
            reserved_seat_data=None,
            tariff=None,
            **kwargs):
        """
        Initialize the Payment class.

        Args:
            *args: Variable length arguments.
            max_wait_time (int): Maximum wait time in seconds (default is 120).
            trip: Trip information.
            empty_seat: Empty seat information.
            seat_lck_json: Seat lock JSON.
            tariff: Tariff information.
            **kwargs: Variable keyword arguments.
        """
        super().__init__(*args)  # Call the __init__ method of the base class
        self.logger = logging.getLogger(__name__)

        self.price = None
        self.trip = trip
        self.reserved_seat_data = reserved_seat_data

        self.tariff = api_constants.TARIFFS[tariff.upper(
        )] if tariff else api_constants.TARIFFS['TAM']

        self.vb_enroll_control_req = api_constants.vb_enroll_control_req_body.copy()
        self.ticket_reservation_req = api_constants.ticket_reservation_req_body.copy()
        self.is_payment_successful = None
        self.vb_enroll_control_response = None
        self.html_response = None
        self.user_data = [{
            "ad": "izzet can",
            "soyad": "karakuş",
            "cinsiyet": 1,
            "tarifeId": 11750067704,
            "cep": "0(534) 077-1521",
            "eposta": "izzetcankarakus@gmail.com",
            "dogumTarihi": "1994-07-14",
            "kimlikNo": "18700774442",
            "tc_degil": False
        }]

        # add kwargs as instance attributes, you can override the default values
        for key, value in kwargs.items():
            setattr(self, key, value)

    def set_ticket_res_values(self):
        """_set_ticket_res_values"""
        self.ticket_reservation_req['biletRezYerBilgileri'][0]['biletWSDVO'].update({
            'seferBaslikId': self.trip['seferId'],
            'binisIstasyonId': self.trip['binisIstasyonId'],
            'inisIstasyonId': self.trip['inisIstasyonId'],
            'hareketTarihi': self.trip['binisTarih'],
            'varisTarihi': self.trip['varisTarih'],
            'tarifeId': self.tariff,
            'vagonSiraNo': self.reserved_seat_data['reserved_seat']['vagonSiraNo'],
            'koltukNo': self.reserved_seat_data['reserved_seat']['koltukNo'],
            'ucret': self.price,

        })
        self.logger.info("Ticket reservation request values set: %s",
                         self.ticket_reservation_req)

    def get_price(self):
        """
        Get the price of a trip for a given empty seat.

        Args:
            trip (dict): The trip information.
            empty_seat (dict): The information of the empty seat.

        Returns:
            float: The price of the trip for the empty seat.
        """

        req_body = api_constants.price_req_body.copy()
        req_body['yolcuList'][0]['tarifeId'] = self.tariff
        seat_info = req_body['yolcuList'][0]['seferKoltuk'][0]
        seat_info.update({
            'seferBaslikId': self.trip['seferId'],
            'binisTarihi': self.trip['binisTarih'],
            'vagonSiraNo': self.reserved_seat_data['reserved_seat']['vagonSiraNo'],
            'koltukNo': self.reserved_seat_data['reserved_seat']['koltukNo'],
            'binisIstasyonId': self.trip['binisIstasyonId'],
            'inisIstasyonId': self.trip['inisIstasyonId'],
            # This should '0' maybe, vuejs code sends '0' always
            'vagonTipi': self.reserved_seat_data['reserved_seat']['vagonTipId']
        })
        # send request
        response = requests.post(
            api_constants.PRICE_ENDPOINT,
            headers=api_constants.REQUEST_HEADER,
            data=json.dumps(req_body),
            timeout=10)
        response_json = json.loads(response.text)
        return int(
            response_json['anahatFiyatHesSonucDVO']['indirimliToplamUcret'])

    def process_payment(self):
        """
        Process the payment for the trip.

        This method calculates the price, updates the payment information,
        sends a request to the payment API, and handles the payment authentication process.

        Returns:
            None
        """
        self.price = self.get_price()
        print(f"Price: {self.price}")

        self.vb_enroll_control_req['biletRezOdemeBilgileri'].update({
            'toplamBiletTutari': self.price,
            'krediKartiTutari': self. price
        })

        for seat in self.reserved_seat_data['seat_lock_response']['koltuklarimListesi']:
            self.vb_enroll_control_req['koltukLockList'].append(
                seat['koltukLockId'])

        response = requests.post(
            api_constants.VB_ENROLL_CONTROL_ENDPOINT,
            headers=api_constants.REQUEST_HEADER,
            data=json.dumps(self.vb_enroll_control_req),
            timeout=10)

        if response.status_code != 200:
            self.logger.error("Payment failed.")
            self.logger.error("Response: %s", response.text)
            return

        response_json = json.loads(response.text)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
            temp_file.write(response.text.encode('utf-8'))
            temp_file_path = temp_file.name
            self.vb_enroll_control_response = temp_file_path
        #  Payment request
        session = requests.Session()

        acs_url = response_json['paymentAuthRequest']['acsUrl']
        pareq = response_json['paymentAuthRequest']['pareq']
        md = response_json['paymentAuthRequest']['md']
        term_url = response_json['paymentAuthRequest']['termUrl']
        enroll_reference = response_json['enrollReference']

        self.logger.info("Enroll reference: %s", enroll_reference)

        form_data = {
            'PaReq': pareq,
            'MD': md,
            'TermUrl': term_url
        }
        # print form_data to file but not tempfile
        with open("form_data.json", "w", encoding='utf-8') as f:
            f.write(json.dumps(form_data))

        odeme_sorgu = {
            "kanalKodu": "3",
            "dil": 0,
            "enrollReference": enroll_reference
        }

        # send odeme soru request
        odeme_sorgu_response = requests.post(api_constants.VB_ODEME_SORGU,
                                 headers=api_constants.REQUEST_HEADER,
                                 data=json.dumps(odeme_sorgu),
                                 timeout=10)
        odeme_sorgu_response_json = json.loads(odeme_sorgu_response.text)
        
        vspos_ref = odeme_sorgu_response_json['vsposReference']
        

        if response.status_code != 200:
            self.logger.error("Payment failed.")
            self.logger.error("Response: %s", response.text)
            return

        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as temp_file:
            temp_file.write(response.text.encode('utf-8'))
            temp_file_path = temp_file.name
            self.html_response = temp_file_path

        # Convert the data to a properly formatted string
        # data_str = json.dumps(self.user_data)
        # data_str_js = data_str.replace('"', '\\"')
        # self.driver.get("https://bilet.tcdd.gov.tr")
        # time.sleep(5)
        # driver.execute_script(
        #     f"window.localStorage.setItem('enrollees', \"{data_str_js}\");")
        # time.sleep(5)
        # driver.refresh()
        # time.sleep(5)
        # # To verify, you can retrieve the value like this
        # value = driver.execute_script(
        #     "return window.localStorage.getItem('enrollees');")
        # print(value)  # This should print your data

        self.driver.get(f"file:///{temp_file_path}")
        time.sleep(5000)
        self.driver.save_screenshot("payment_page.png")

        # Find the OTP input field and submit button
        try:
            text_input = self.driver.find_element(
                By.CSS_SELECTOR, "input[type='number'], input[type='text']")
            btn = self.driver.find_element(
                By.CSS_SELECTOR, "button[type='submit']")
            if text_input and btn and btn.text:
                pprint(btn.text)
                # TODO: get this from the USER
                user_input = input("Enter the OTP: ")
                text_input.send_keys(user_input)
                btn.click()
        except selenium.common.exceptions.NoSuchElementException:
            self.logger.error("OTP input field or submit button not found.")

        try:
            # Wait for the redirection from payment to the main page
            WebDriverWait(self.driver, 30).until(
                EC.url_contains("https://bilet.tcdd.gov.tr/"))
            current_url = self.driver.current_url
            if "odeme-sonuc" in current_url:
                self.is_payment_successful = True
                self.logger.info("Payment successful.")
                # take a screenshot
                time.sleep(10)
                self.driver.save_screenshot("payment_success.png")
            else:
                self.logger.error("Payment failed.")
                self.is_payment_successful = False
                self.driver.save_screenshot("payment_failed.png")
                # wait until element with some id is found
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located(("id", "some_id")))

        except TimeoutException:
            self.logger.error("Timeout while waiting for payment result.")


######################################################### INTERFACE AUTOMATION ####################################
    # def send_keys(self, element, string, speed=0.000001):
    #     """Send keys to the input field with a delay between each character.
    #     Args:
    #         string (str): The string to be sent.
    #         speed (float): The delay between each character (default is 0.1)."""
    #     for char in string:
    #         element.send_keys(char)
    #         time.sleep(speed)

    # def open_site(self):
    #     """Open the TCDD website using Selenium WebDriver."""
    #     self.driver.get("https://bilet.tcdd.gov.tr")
    #     # time.sleep(10)
    #     # self.driver.save_screenshot("site.png")
    #     # self.driver.quit()

    # def select_date_from_datepicker(self, date):
    #     """ Select a date from the date picker. Pfor
    #     Args:
    #         date (datetime): The date to be selected."""
    #     # date picker
    #     str_date = date.strftime("%Y-%m-%d")
    #     self.logger.debug("Selecting date: %s", str_date)
    #     daterangepicker_element = self.driver.find_element(
    #         By.XPATH, "//div[contains(@class, 'daterangepicker')]")
    #     date_picker = self.driver.find_element(
    #         By.CSS_SELECTOR, "div[class='datePickerInput departureDate']")
    #     # log the found elements
    #     self.logger.debug("Date picker input element: %s", date_picker)
    #     self.logger.debug("Date picker element: %s", daterangepicker_element)

    #     date_picker.click()
    #     self.logger.debug("Clicked on the date picker input element.")
    #     # wait for the date picker to be displayed
    #     self.logger.debug("Waiting for the date picker to be displayed.")
    #     wait = WebDriverWait(self.driver, timeout=3)
    #     wait.until(lambda d: daterangepicker_element.is_displayed())

    #     self.logger.debug(
    #         "Finding element with data-date attribute equal to %s", str_date)
    #     date_element = self.driver.find_element(
    #         By.CSS_SELECTOR, f"td[data-date='{str_date}']:not(.off)")
    #     self.logger.debug("Found date element: %s", date_element)
    #     self.logger.debug("Clicking on the date element.")
    #     date_element.click()
    #     wait.until(lambda d: not daterangepicker_element.is_displayed())
    #     self.logger.debug("Date picker is closed. Finding search button.")

    #     search_button = self.driver.find_element(
    #         By.CSS_SELECTOR, "button.btnSeferSearch")
    #     self.logger.debug("Clicking search button %s", search_button.tag_name)

    #     # date format as: 2024-04-12
    #     # self.driver.save_screenshot("date_picker.png")
    #     # self.driver.quit()

    # def fill_in_departure_arrival_input(self, departure_station, arrival_station, retries=3):
    #     """Fill in the departure and arrival stations.
    #     Args:
    #         departure_station (str): The departure station.
    #         arrival_station (str): The arrival station."""

    #     # get the station view names as they are used in the input fields
    #     for attempt in range(retries):
    #         try:
    #             departure_station_view_name = next(
    #                 (station['station_view_name'] for station in self.stations if station['station_name'] == departure_station), None)
    #             arrival_station_view_name = next(
    #                 (station['station_view_name'] for station in self.stations if station['station_name'] == arrival_station), None)

    #             departure_input = self.driver.find_element(
    #                 By.CSS_SELECTOR, f"input[name='Tren kalkış']")
    #             self.logger.debug("Clearing the departure input.")
    #             departure_input.click()
    #             # select all with ctrl+a and  delete with delete key
    #             departure_input.send_keys(Keys.CONTROL, 'a')
    #             departure_input.send_keys(Keys.DELETE)
    #             self.logger.debug("Clicked on the departure input.")

    #             self.send_keys(departure_input, departure_station_view_name)
    #             departure_input.send_keys(" denemete")

    #             self.logger.debug("Sent keys to the departure input.")
    #             # wait for the allStations element to be displayed
    #             # select element with class 'allStations' which has a button with id 'gidis' for gidis dropdown closest to the input element
    #             self.logger.debug(
    #                 "Waiting for the allStations element to be found.")
    #             all_stations = self.driver.find_element(
    #                 By.XPATH, "//div[@class='allStations']//button[contains(@id, 'gidis')]")

    #             self.logger.debug(
    #                 "Waiting for the allStations element to be displayed.")
    #             wait = WebDriverWait(self.driver, timeout=3)
    #             wait.until(lambda d: all_stations.is_displayed())
    #             self.logger.debug("AllStations element is displayed.")
    #             # click the first station
    #             self.logger.debug("Finding the first station element.")

    #             departure_station_dropdown_first = WebDriverWait(self.driver, 3).until(
    #                 EC.presence_of_element_located((By.XPATH, f"//div[@class='allStations']//*[contains(text(), '{departure_station_view_name}')]")
    #                                                ))
    #             html = departure_station_dropdown_first.get_property(
    #                 "innerHTML")
    #             self.logger.debug("dropdown first element: %s, tag: %s",
    #                               html, departure_station_dropdown_first.tag_name)
    #             wait.until(
    #                 lambda d: departure_station_dropdown_first.is_displayed())
    #             departure_station_dropdown_first.click()

    #             arrival_input = self.driver.find_element(
    #                 By.CSS_SELECTOR, f"input[name='Tren varış']")
    #             arrival_input.clear()
    #             arrival_input.click()
    #             arrival_input.send_keys(Keys.CONTROL, 'a')
    #             arrival_input.send_keys(Keys.DELETE)

    #             all_stations = self.driver.find_element(
    #                 By.XPATH, "//div[@class='allStations']//button[contains(@id, 'donus')]")
    #             wait.until(lambda d: all_stations.is_displayed())
    #             arrival_input.send_keys(arrival_station_view_name)
    #             # wait until you found the first station element, and assign it to arrival_station_dropdown_first
    #             arrival_station_dropdown_first = WebDriverWait(self.driver, 10).until(
    #                 lambda d: d.find_element(
    #                     By.XPATH, f"//div[@class='allStations']//*[contains(text(), '{arrival_station_view_name}')]")
    #             )

    #             html = arrival_station_dropdown_first.get_property("innerHTML")
    #             self.logger.debug("dropdown first element: %s, tag: %s",
    #                               html, arrival_station_dropdown_first.tag_name)

    #             wait.until(
    #                 lambda d: arrival_station_dropdown_first.is_displayed())
    #             arrival_station_dropdown_first.click()
    #             break
    #         except Exception as e:
    #             self.logger.error(
    #                 "Failed to fill in the departure and arrival stations: %s", str(e))
    #             if attempt < retries - 1:
    #                 self.logger.error(
    #                     "Retrying to fill in the departure and arrival stations.")
    #                 continue
    #             else:
    #                 self.logger.error(
    #                     "Failed to fill in the departure and arrival stations after %s retries.", retries)
    #                 raise

    # def click_search_button(self):
    #     """Click on the search button."""
    #     button = self.driver.find_element(
    #         By.XPATH, "//button[contains(contains(text(), 'Sefer Ara')]")
    #     button.click()

        # selenium.common.exceptions.StaleElementReferenceException
        # wait.until(lambda d: not all_stations.is_displayed())
###################################################### INTERFACE AUTOMATION ############################################################
