""" This module contains the SeleniumPayment class for handling Selenium-based payment operations."""
import tempfile
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


class SeleniumPayment:
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

    def __init__(self, *args, max_wait_time=120, **kwargs):
        """
        Initializes a new instance of the SeleniumPayment class.

        Args:
            max_wait_time (int): Maximum wait time in seconds for page loading (default: 120).
            *args: Additional arguments to be passed to the Chrome options.
            **kwargs: Additional keyword arguments to be set as instance attributes.
        """
        self.options = Options()
        self.options.add_argument("--disable-notifications")
        self.options.add_argument("--disable-geolocation")
        self.options.add_argument("--disable-application-cache")
        self.options.add_argument("--disable-cache")
        # self.options.add_argument("--headless")
        self.options.add_argument("--disable-infobars")
        self.options.add_argument("--mute-audio")
        # self.options.add_argument("--disable-gpu")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--disable-extensions")
        self.options.add_argument("--disable-software-rasterizer")
        self.options.add_argument("--disable-setuid-sandbox")
        self.options.add_argument("--disable-sandbox")
        self.options.add_argument("--single-process")
        self.options.add_argument("--ignore-certificate-errors")
        self.options.add_argument("--ignore-ssl-errors")
        self.options.add_argument("--disable-logging")
        self.max_wait_time = max_wait_time
        # add args values to options
        for arg in args:
            self.options.add_argument(arg)

        # add kwargs as instance attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

    def open_html_with_selenium(self, response):
        """
        Opens an HTML response using Selenium WebDriver.

        Args:
            response (requests.Response): The response object containing the HTML content.

        Raises:
            TimeoutException: If the page loading takes too much time.
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as temp_file:
            temp_file.write(response.encode('utf-8'))
            temp_file_path = temp_file.name

            driver = webdriver.Chrome(options=self.options)
            driver.get(f"file:///{temp_file_path}")
            driver.implicitly_wait(10)
            try:
                WebDriverWait(driver, self.max_wait_time).until(
                    EC.url_contains("https://bilet.tcdd.gov.tr/"))
            except TimeoutException:
                print("Loading took too much time!")
