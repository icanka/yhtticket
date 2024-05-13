import json
import logging
from datetime import datetime
from pprint import pprint
import api_constants
import time
from payment import SeleniumPayment
from trip import Trip
from passenger import Passenger
from inline_func import query


def main():
    """Main function to run the script."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('trip_search.log'),
            logging.StreamHandler()
        ]
    )

    tckn = "18700774442"
    name = "izzet can"
    surname = "karakuş"
    # birthday = "Jul 14, 1994 03:00:00 AM"
    birthday = "14/07/1994"
    email = "izzetcankarakus@gmail.com"
    phone = "05340771521"
    sex = "E"
    credit_card_no = "4506347008156065"
    # credit_card_no = "6501700150491393"
    credit_card_ccv = "035"
    # credit_card_ccv = "777"
    credit_card_exp = "2406"
    # credit_card_exp = "3004"

    passenger = Passenger(tckn, name, surname, birthday, email,
                          phone, sex, credit_card_no, credit_card_ccv, credit_card_exp)

    from_station = 'İstanbul(Pendik)'
    to_station = 'Ankara Gar'
    from_date = '30 May 20:00'
    to_date = None  # '27 April 17:00'
    seat_type = 'buss'
    tariff = 'tsk'

    # query(from_station, to_station, from_date)

    my_trip = Trip(from_station, to_station, from_date,
                   to_date, passenger, tariff, seat_type)

    # my_trip.api.is_mernis_correct(passenger)

    p = SeleniumPayment()
    # find trip
    trips = my_trip.find_trip()
    #trips = my_trip.get_trips(check_satis_durum=False)
    # pprint(trips)
    pprint(f"Total of {len(trips)} trips found")
    for trip in trips:
        pprint(
            f"eco: {trip['eco_empty_seat_count']} - buss: {trip['buss_empty_seat_count']}")

    if len(trips) > 0:
        trip = trips[0]
        my_trip.trip_json = trip
        logging.info("Reserving: %s", trip.get('binisTarih'))
        my_trip.reserve_seat()
        p.trip = my_trip

        while True:
            payment_url: str = ''
            time.sleep(10)
            p.trip.reserve_seat()
            p.set_price()
            p.set_payment_url()
            logging.info("Payment URL: %s", p.current_payment_url)
            # compare urls
            
            
            # p.ticket_reservation()


        # my_trip.reserve_seat_data['lock_end_time'] = "2022-04-29 17:00:00"
        # write to file
        # with open(f'trip_{datetime.now().strftime("%H%M")}.json', 'w', encoding='utf-8') as file:
        #    file.write(json.dumps(p.trip.trip_json))
        # write reserved seat data to file
        # with open(f'reserved_seat_{datetime.now().strftime("%H%M")}.json', 'w', encoding='utf-8') as file:
        #    file.write(json.dumps(my_trip.reserve_seat_data))

        # ready the page with selenium
        trip_str = my_trip.trip_json['binisTarih']
        seat_str = my_trip.empty_seat_json['koltukNo']
        vagon_str = my_trip.empty_seat_json['vagonSiraNo']
        end_time = my_trip.lock_end_time

        pprint(f"Lock will end at {end_time}")
        # pprint(trip)
        pprint(
            f"Seat {seat_str} in vagon {vagon_str} is reserved for trip {trip_str}")



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
