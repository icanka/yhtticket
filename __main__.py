from datetime import datetime
import json
import os
from pprint import pprint
import time
from trip_search import get_empty_seats_trip, search_trips, select_first_empty_seat


from_station = 'Ankara Gar'
to_station = 'İstanbul(Pendik)'
from_date = '5 April 15:30'
to_date = '5 April 17:30'

while True:
    trips = search_trips(from_station, to_station, from_date, to_date)
    pprint(f"Total of {len(trips)} trips found")
    if len(trips) == 0:
        pprint("No trips found")
        time.sleep(3)
    else:
        # clear the console
        for trip in trips:
            pprint("Checking for empty seats")
            trip = get_empty_seats_trip(trip, from_station, to_station)
            # pprint(trip)
            os.system('cls' if os.name == 'nt' else 'clear')
            if trip['empty_seat_count'] > 0:
                pprint("Found empty seats")
                try:
                    seat_lock_json_result, empty_seat = select_first_empty_seat(
                        trip)
                    combined_data = {
                        'trip': trip,
                        'seat_lock_json_result': seat_lock_json_result,
                        'empty_seat': empty_seat,
                    }
                    with open(f'/tmp/trip_{datetime.now().strftime("%Y%m%d%H%M%S")}.json', 'w', encoding='utf-8') as file:
                        file.write(json.dumps(combined_data))
                except Exception as e:
                    pprint(e)

                # p = SeleniumPayment(
                #     trip=trip,
                #     empty_seat=empty_seat,
                #     seat_lck_json=seat_lock_json_result,
                #     tariff='TSK')
                # p.process_payment()
