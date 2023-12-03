# Get empty seats for each vagon in a trip
for trip in trips:
    pprint(trip['binisTarih'])
    pprint(trip['seferId'])
    vagon_req_body['seferBaslikId'] = trip['seferId']
    vagon_req_body['binisIstId'] = trip['binisIstasyonId']
    vagon_req_body['inisIstId'] = trip['inisIstasyonId']
    # get vagons
    response = requests.post(VAGON_SEARCH_ENDPOINT,
                             headers=REQUEST_HEADER, data=json.dumps(vagon_req_body), timeout=10)
    vagons_json = json.loads(response.text)
    for vagon in vagons_json['vagonBosYerList']:
        if vagon['vagonSiraNo'] == 4:
            pprint(f"vagon: {vagon}")
            vagon_harita_req_body['vagonSiraNo'] = vagon['vagonSiraNo']
            vagon_harita_req_body['seferBaslikId'] = vagon_req_body['seferBaslikId']
            # get vagon harita
            response = requests.post(VAGON_HARITA_ENDPOINT,
                                     headers=REQUEST_HEADER, data=json.dumps(vagon_harita_req_body), timeout=10)
            vagon_harita_json = json.loads(response.text)
            empty_seats = get_empty_vagon_seats(vagon_harita_json)

            pprint(empty_seats)
            pprint(len(get_empty_vagon_seats(vagon_harita_json)))
            for empty_seat in empty_seats:
                pprint(empty_seat)
                koltuk_sec_req_body['seferId'] = trip['seferId']
                koltuk_sec_req_body['vagonSiraNo'] = vagon['vagonSiraNo']
                koltuk_sec_req_body['koltukNo'] = empty_seat['koltukNo']
                koltuk_sec_req_body['binisIst'] = trip['binisIstasyonId']
                koltuk_sec_req_body['inisIst'] = trip['inisIstasyonId']

                pprint(json.dumps(koltuk_sec_req_body))
                pprint(koltuk_sec_req_body)
                # Send the request to the endpoint
                response = requests.post(SELECT_EMPTY_SEAT_ENDPOINT,
                                         headers=REQUEST_HEADER, data=json.dumps(koltuk_sec_req_body), timeout=10)
                response_json = json.loads(response.text)
                pprint(response_json)
            exit(0)
            # pprint(len(get_empty_vagon_seats(vagon_harita_json)))

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



