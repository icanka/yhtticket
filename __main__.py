import logging
from datetime import datetime
from pprint import pprint
import api_constants
from payment import SeleniumPayment
from cli import Trip


def main():
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
    my_trip = Trip(from_station, to_station, from_date, to_date, seat_type)

    p = SeleniumPayment()
    # find trip
    trips = my_trip.find_trip()

    # pprint(tripst)
    pprint(len(trips))

    if len(trips) > 0:
        # ready selenium

        trip = trips[0]
        dep_date = datetime.strptime(
            trip['binisTarih'], "%b %d, %Y %I:%M:%S %p")

        # pprint(f"Departure date: {dep_date.strftime('%Y-%m-%d')}")
        # with open(f'trip_{datetime.now().strftime("%Y-%m-%d")}.json', 'w', encoding='utf-8') as file:
        #    file.write(json.dumps(trip))

        # reserve seat
        reserved_seat_data = my_trip.reserve_seat(trip)
        p.reserved_seat_data = reserved_seat_data
        
        
        # ready the page with selenium

        trip_str = reserved_seat_data['trip']['binisTarih']
        reserved_seat = reserved_seat_data['reserved_seat']
        seat_str = reserved_seat_data['reserved_seat']['koltukNo']
        vagon_str = reserved_seat_data['reserved_seat']['vagonSiraNo']
        end_time = reserved_seat_data['lock_end_time']
        seat_lock_response = reserved_seat_data['seat_lock_response']

        pprint(f"Lock will end at {end_time}")
        # pprint(trip)
        pprint(
            f"Seat {seat_str} in vagon {vagon_str} is reserved for trip {trip_str}")
        p.trip = trip
        p.reserved_seat = reserved_seat
        p.seat_lock_response = seat_lock_response

        # p.process_payment()
        # p = SeleniumPayment(
        #     trip=trip,
        #     empty_seat=empty_seat,
        #     seat_lck_json=seat_lock_response,
        #     tariff='TSK')
        # p.process_payment()
        pprint(p.trip)
        pprint(p.reserved_seat)
        pprint(p.seat_lock_response)
        pprint(p.tariff)


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
