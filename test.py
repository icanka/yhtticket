import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from _utils import find_value


driver = webdriver.Chrome()
driver.get('https://bilet.tcdd.gov.tr/')
driver.implicitly_wait(10)

_from = driver.find_element(by=By.NAME, value="Tren kalkış")
_to = driver.find_element(by=By.NAME, value="Tren varış")

_from.screenshot('_from.png')
_to.screenshot('_to.png')

_from.click()
_from.send_keys('istanbul pendik')

_from_station = driver.find_element(
    by=By.XPATH,
    value="//*[contains(text(), 'Tüm İstasyonlar')]/following-sibling::div[1]")
_from_station.screenshot('_from_station.png')
_from_station.click()
exit(0)

_station = _stations.find_element(by=By.XPATH, value=".//div[1]")
_station.screenshot('_station.png')

# _to.click()
# _to.send_keys('ankara gar')
time.sleep(10)
