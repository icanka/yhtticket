import json
from _utils import find_value
import requests
import json

# Create an empty set
hst_stations = list()
STATION_LIST_ENDPOINT = 'https://api-yebsp.tcddtasimacilik.gov.tr/istasyon/istasyonYukle'
REQUEST_BODY = '{"kanalKodu":"3","dil":1,"tarih":"Nov 10, 2011 12:00:00 AM","satisSorgu":true}'
REQUEST_HEADER = {
    "Host": "api-yebsp.tcddtasimacilik.gov.tr",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,tr-TR;q=0.8,tr;q=0.5,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
    "Authorization": "Basic ZGl0cmF2b3llYnNwOmRpdHJhMzQhdm8u",
    "Content-Type": "application/json",
    "Origin": "https://bilet.tcdd.gov.tr",
    "Connection": "keep-alive",
    "Referer": "https://bilet.tcdd.gov.tr/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site"
}

# Send the request to the endpoint
response = requests.post(STATION_LIST_ENDPOINT,
                         headers=REQUEST_HEADER, data=REQUEST_BODY)
# Parse the JSON response
data = json.loads(response.text)

for item in data['istasyonBilgileriList']:
    if "YHT" in item['stationTrainTypes']:
        station = {}
        station['station_name'] = find_value(item, 'istasyonAdi')
        station['station_code'] = find_value(item, 'istasyonKodu')
        station['station_id'] = find_value(item, 'istasyonId')
        hst_stations.append(station)

stations_json = json.dumps(hst_stations)
# Write JSON to file
with open('station_list.json', 'w', encoding='utf-8') as file:
    file.write(stations_json)
