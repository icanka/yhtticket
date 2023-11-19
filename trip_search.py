import json
import requests
from datetime import datetime
from pprint import pprint


SEARCH_ENDPOINT = "https://api-yebsp.tcddtasimacilik.gov.tr/sefer/seferSorgula"
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




from_station = "İstanbul(Pendik)"
to_station = "Ankara Gar"

request_body = {
    "kanalKodu": 3,
    "dil": 0,
    "seferSorgulamaKriterWSDVO": {
        "satisKanali": 3,
        "binisIstasyonu": f"{from_station}",
        "binisIstasyonu_isHaritaGosterimi": 'false',
        "inisIstasyonu": f"{to_station}",
        "inisIstasyonu_isHaritaGosterimi": 'false',
        "seyahatTuru": 1,
        "gidisTarih": "Nov 20, 2023 00:00:00 AM",
        "bolgeselGelsin": 'false',
        "islemTipi": 0,
        "yolcuSayisi": 1,
        "aktarmalarGelsin": 'true',
        "binisIstasyonId": None,
        "inisIstasyonId": None
    }
}

# Load the JSON file
with open('station_list.json') as f:
    station_list = json.load(f)

# Find the station that matches from_station
    for station in station_list:
        if station['station_name'] == from_station:
            binisIstasyonId = station['station_id']
            request_body['seferSorgulamaKriterWSDVO']['binisIstasyonId'] = binisIstasyonId
        if station['station_name'] == to_station:
            inisIstasyonId = station['station_id']
            request_body['seferSorgulamaKriterWSDVO']['inisIstasyonId'] = inisIstasyonId
            
# Send the request to the endpoint
response = requests.post(SEARCH_ENDPOINT,
                         headers=REQUEST_HEADER, data=json.dumps(request_body))

response_json = json.loads(response.text)
sorted_trips = sorted(response_json['seferSorgulamaSonucList'], key=lambda trip: datetime.strptime(trip['binisTarih'], "%b %d, %Y %I:%M:%S %p"))
trips = list()

for trip in sorted_trips:
    if trip['satisDurum'] == 1 and trip['vagonHaritasindanKoltukSecimi'] == 1:
        # 0 is economy class and 1 is business class
        t = {}
        t['eco_empty_seat_count'] = trip['vagonTipleriBosYerUcret'][0]['kalanSayi'] - trip['vagonTipleriBosYerUcret'][0]['kalanEngelliKoltukSayisi']
        t['buss_empty_seat_count'] = trip['vagonTipleriBosYerUcret'][1]['kalanSayi'] - trip['vagonTipleriBosYerUcret'][1]['kalanEngelliKoltukSayisi']
        t['empty_seat_count'] = t['eco_empty_seat_count'] + t['buss_empty_seat_count']
        t['binisTarih'] = trip['binisTarih']
        t['inisTarih'] = trip['inisTarih']
        t['trenAdi'] = trip['trenAdi']
        t['seferAdi'] = trip['seferAdi']
        t['seferId'] = trip['seferId']
        trips.append(t)
        date_object = datetime.strptime(trip['binisTarih'], "%b %d, %Y %I:%M:%S %p")
        print(f"Economy class empty seat count: {t['eco_empty_seat_count']+t['buss_empty_seat_count']} -- {date_object.strftime('%H:%M')}")

# dump trips to json and then write to file
trips_json = json.dumps(trips)
with open('trips.json', 'w', encoding='utf-8') as file:
    file.write(trips_json)

# write repsonse to file
with open('response.json', 'w', encoding='utf-8') as file:
    file.write(response.text)