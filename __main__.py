import json
import logging
from datetime import datetime
from pprint import pprint
import api_constants
from payment import SeleniumPayment
from cli import Trip


def main():
    """Main function to run the script."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s',
        handlers=[
            # logging.FileHandler('trip_search.log'),
            logging.StreamHandler()
        ]
    )

    from_station = 'Ankara Gar'
    to_station = 'İstanbul(Pendik)'
    from_date = '29 April 17:00'
    to_date = '29 April 17:30'
    seat_type = 'eco'
    tariff = 'tsk'
    my_trip = Trip(from_station, to_station, from_date, to_date, tariff, seat_type)

    p = SeleniumPayment()
    # find trip
    trips = my_trip.find_trip()
    if len(trips) > 0:
        trip = trips[0]
        pprint(type(trip))
        my_trip.trip_json = trip
        my_trip.reserve_seat()
        p.trip = my_trip
        my_trip.reserve_seat_data['lock_end_time'] = "2022-04-29 17:00:00"

        # write to file
        with open(f'trip_{datetime.now().strftime("%H%M")}.json', 'w', encoding='utf-8') as file:
            file.write(json.dumps(p.trip.trip_json))
        # write reserved seat data to file
        with open(f'reserved_seat_{datetime.now().strftime("%H%M")}.json', 'w', encoding='utf-8') as file:
            file.write(json.dumps(my_trip.reserve_seat_data))

        # ready the page with selenium
        trip_str = my_trip.trip_json['binisTarih']
        seat_str = my_trip.reserve_seat_data['koltukNo']
        vagon_str = my_trip.reserve_seat_data['vagonSiraNo']
        end_time = my_trip.lock_end_time

        pprint(f"Lock will end at {end_time}")
        # pprint(trip)
        pprint(
            f"Seat {seat_str} in vagon {vagon_str} is reserved for trip {trip_str}")

        # p.process_payment()
        # p = SeleniumPayment(
        #     trip=trip,
        #     empty_seat=empty_seat,
        #     seat_lck_json=seat_lock_response,
        #     tariff='TSK')
        # p.process_payment()


# while True:
#     trips = search_trips(from_station, to_station, from_date, to_date)
#     pprint(f"Total of {len(trips)} trips found")
#     if len(trips) == 0:
#         pprint("No trips found")
#         time.sleep(3)
#     else:
#         # clear the console
#         for trip in trips:
#             pprint("Checking for empty seats")
#             trip = get_empty_seats_trip(trip, from_station, to_station)
#             # pprint(trip)
#             os.system('cls' if os.name == 'nt' else 'clear')
#             if trip['empty_seat_count'] > 0:
#                 pprint("Found empty seats")
#                 try:
#                     seat_lock_json_result, empty_seat = select_first_empty_seat(
#                         trip)
#                     combined_data = {
#                         'trip': trip,
#                         'seat_lock_json_result': seat_lock_json_result,
#                         'empty_seat': empty_seat,
#                     }
#                     with open(f'/tmp/trip_{datetime.now().strftime("%Y%m%d%H%M%S")}.json', 'w', encoding='utf-8') as file:
#                         file.write(json.dumps(combined_data))
#                 except Exception as e:
#                     pprint(e)

#                 # p = SeleniumPayment(
#                 #     trip=trip,
#                 #     empty_seat=empty_seat,
#                 #     seat_lck_json=seat_lock_json_result,
#                 #     tariff='TSK')
#                 # p.process_payment()

if __name__ == "__main__":
    main()
