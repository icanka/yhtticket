import json
import requests
from datetime import datetime
from pprint import pprint


SEATS_IDS = [13371893752, 13371893753, 16801693056, 16801693057]

def get_empty_vagon_seats(vagon_json):

    vagon_yerlesim = vagon_json['vagonHaritasiIcerikDVO']['vagonYerlesim']
    koltuk_durumlari = vagon_json['vagonHaritasiIcerikDVO']['koltukDurumlari']
    pprint(len(koltuk_durumlari))
    index_dict = {d['koltukNo'] : d for d in koltuk_durumlari if 'koltukNo' in d}
    pprint(len(index_dict))
    merged_list = []
    for seat in vagon_yerlesim:
        seat_no = seat.get('koltukNo')
        if seat_no:
            merged_dict = {**seat, **index_dict.get(seat_no, {})}
            merged_list.append(merged_dict)
    return merged_list


SEARCH_ENDPOINT = "https://api-yebsp.tcddtasimacilik.gov.tr/sefer/seferSorgula"
VAGON_SEARCH_ENDPOINT = "https://api-yebsp.tcddtasimacilik.gov.tr/vagon/vagonBosYerSorgula"
VAGON_HARITA_ENDPOINT = "https://api-yebsp.tcddtasimacilik.gov.tr/vagon/vagonHaritasindanYerSecimi"
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


vagon_harita_req_body = {
    "kanalKodu": "3",
    "dil": 0,
    "seferBaslikId": None,
    "vagonSiraNo": None,
    "binisIst": from_station,
    "InisIst": to_station,
}

vagon_req_body = {
    "kanalKodu": "3",
    "dil": 0,
    "seferBaslikId": None,
    "binisIstId": None,
    "inisIstId": None
}

koltuk_sec_req_body = {
    "kanalKodu": "3",
    "dil": 0,
    "seferId": 39260008468,
    "vagonSiraNo": 8,
    "koltukNo": "1b",
    "cinsiyet": "E",
    "binisIst": 234516104,
    "inisIst": 234516259,
    "dakika": 10,
    "huawei": 'false'
}

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
        "gidisTarih": "Nov 30, 2023 00:00:00 AM",
        "bolgeselGelsin": 'false',
        "islemTipi": 0,
        "yolcuSayisi": 1,
        "aktarmalarGelsin": 'true',
        "binisIstasyonId": None,
        "inisIstasyonId": None
    }
}

# return a list of dictionaries


def get_active_vagons(json_data):
    active_vagons = list()
    for item in json_data:
        for vagon in item['vagonListesi']:
            if vagon['aktif'] == True:
                v = {'vagonBaslikId': vagon['vagonBaslikId'],
                     'vagonSiraNo': vagon['vagonSiraNo']}
                active_vagons.append(v)
    return active_vagons


# Load the JSON file
with open('station_list.json') as f:
    station_list = json.load(f)

# Find the station that matches from_station
    for station in station_list:
        if station['station_name'] == from_station:
            binisIstasyonId = station['station_id']
            vagon_req_body['binisIstId'] = binisIstasyonId
            request_body['seferSorgulamaKriterWSDVO']['binisIstasyonId'] = binisIstasyonId
        if station['station_name'] == to_station:
            inisIstasyonId = station['station_id']
            vagon_req_body['inisIstId'] = inisIstasyonId
            request_body['seferSorgulamaKriterWSDVO']['inisIstasyonId'] = inisIstasyonId

# Send the request to the endpoint
response = requests.post(SEARCH_ENDPOINT,
                         headers=REQUEST_HEADER, data=json.dumps(request_body), timeout=10)

response_json = json.loads(response.text)
sorted_trips = sorted(response_json['seferSorgulamaSonucList'], key=lambda trip: datetime.strptime(
    trip['binisTarih'], "%b %d, %Y %I:%M:%S %p"))
trips = list()

for trip in sorted_trips:
    if trip['satisDurum'] == 1 and trip['vagonHaritasindanKoltukSecimi'] == 1:
        # 0 is economy class and 1 is business class
        try:
            t = {}
            t['vagons'] = get_active_vagons(trip['vagonTipleriBosYerUcret'])
            t['eco_empty_seat_count'] = trip['vagonTipleriBosYerUcret'][0]['kalanSayi'] - \
                trip['vagonTipleriBosYerUcret'][0]['kalanEngelliKoltukSayisi']
            t['buss_empty_seat_count'] = trip['vagonTipleriBosYerUcret'][1]['kalanSayi'] - \
                trip['vagonTipleriBosYerUcret'][1]['kalanEngelliKoltukSayisi']
            t['empty_seat_count'] = t['eco_empty_seat_count'] + \
                t['buss_empty_seat_count']
            t['binisTarih'] = trip['binisTarih']
            t['inisTarih'] = trip['inisTarih']
            t['trenAdi'] = trip['trenAdi']
            t['seferAdi'] = trip['seferAdi']
            t['seferId'] = trip['seferId']
            t['binisIstasyonId'] = request_body['seferSorgulamaKriterWSDVO']['binisIstasyonId']
            t['inisIstasyonId'] = request_body['seferSorgulamaKriterWSDVO']['inisIstasyonId']
            trips.append(t)
            date_object = datetime.strptime(
                trip['binisTarih'], "%b %d, %Y %I:%M:%S %p")
            print(
                f"Economy class empty seat count: {t['eco_empty_seat_count']+t['buss_empty_seat_count']} -- {date_object.strftime('%H:%M')}")
        except IndexError:  # no business class, just ignore
            pass

# dump trips to json and then write to file
trips_json = json.dumps(trips)
with open('trips.json', 'w', encoding='utf-8') as file:
    file.write(trips_json)

for trip in trips:
    if trip['empty_seat_count'] > 0:
        vagon_req_body['seferBaslikId'] = trip['seferId']

for trip in trips:
    if trip['seferId'] == 39433411143:
        vagon_req_body['seferBaslikId'] = trip['seferId']
        vagon_req_body['binisIstId'] = trip['binisIstasyonId']
        vagon_req_body['inisIstId'] = trip['inisIstasyonId']
        # Send the request to the endpoint
        response = requests.post(VAGON_SEARCH_ENDPOINT,
                                 headers=REQUEST_HEADER, data=json.dumps(vagon_req_body), timeout=10)
        response_json = json.loads(response.text)
        for vagon in response_json['vagonBosYerList']:
            if vagon['vagonSiraNo'] == 8:
                vagon_harita_req_body['vagonSiraNo'] = vagon['vagonSiraNo']
                vagon_harita_req_body['seferBaslikId'] = vagon_req_body['seferBaslikId']
                # Send the request to the endpoint
                response = requests.post(VAGON_HARITA_ENDPOINT,
                                         headers=REQUEST_HEADER, data=json.dumps(vagon_harita_req_body), timeout=10)
                response_json = json.loads(response.text)


# Get empty seats for each vagon in a trip
for trip in trips:
    pprint(trip['binisTarih'])
    vagon_req_body['seferBaslikId'] = trip['seferId']
    vagon_req_body['binisIstId'] = trip['binisIstasyonId']
    vagon_req_body['inisIstId'] = trip['inisIstasyonId']
    # get vagons
    response = requests.post(VAGON_SEARCH_ENDPOINT,
                             headers=REQUEST_HEADER, data=json.dumps(vagon_req_body), timeout=10)
    vagons_json = json.loads(response.text)
    for vagon in vagons_json['vagonBosYerList']:
        pprint(vagon)
        vagon_harita_req_body['vagonSiraNo'] = vagon['vagonSiraNo']
        vagon_harita_req_body['seferBaslikId'] = vagon_req_body['seferBaslikId']
        # get vagon harita
        response = requests.post(VAGON_HARITA_ENDPOINT,
                                 headers=REQUEST_HEADER, data=json.dumps(vagon_harita_req_body), timeout=10)
        vagon_harita_json = json.loads(response.text)
        pprint(get_empty_vagon_seats(vagon_harita_json))
        pprint(len(get_empty_vagon_seats(vagon_harita_json)))
        exit(0)

    # for yerlesim in vagon_yerlesim:

        # for koltuk in vagon_harita_json['koltukBilgileri']:
        #     if koltuk['koltukDurumu'] == 0:
        #         print(koltuk['koltukNo'])
        #         koltuk_sec_req_body['seferId'] = trip['seferId']
        #         koltuk_sec_req_body['vagonSiraNo'] = vagon['vagonSiraNo']
        #         koltuk_sec_req_body['koltukNo'] = koltuk['koltukNo']
        #         # Send the request to the endpoint
        #         response = requests.post(VAGON_HARITA_ENDPOINT,
        #                                  headers=REQUEST_HEADER, data=json.dumps(koltuk_sec_req_body), timeout=10)
        #         response_json = json.loads(response.text)
        #         pprint(response_json)
        #         exit(0)


# write repsonse to fila
with open('response.json', 'w', encoding='utf-8') as file:
    file.write(response.text)
