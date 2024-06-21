from datetime import datetime
import logging
from uuid import uuid4
import requests
from thefuzz import process
from telegram import InlineQueryResultArticle, InputTextMessageContent
import tasks.trip as trip

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handlers = [
    logging.FileHandler("../bot_data/logs/inline_funcs.log"),
    logging.StreamHandler(),
]
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s"
)
for handler in handlers:
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def stations():
    """List all stations."""
    results = []
    station_list = trip.list_stations()
    for station in station_list:
        results.append(
            InlineQueryResultArticle(
                id=uuid4(),
                title=station,
                input_message_content=InputTextMessageContent(station),
            )
        )
    return results


def query(from_, to_, from_date=None):
    """Search for trips from from_ to to_ on from_date."""
    try:
        station_list = trip.list_stations()
    except requests.exceptions.HTTPError as e:
        logging.error("Error while listing stations: %s", e)
        return [
            InlineQueryResultArticle(
                id=uuid4(),
                title=f"{e.__class__.__name__}",
                input_message_content=InputTextMessageContent(
                    "Error while listing stations"
                ),
            )
        ]
    # get the most closest station name to the given station name, fuzzy matching
    from_ = process.extractOne(from_, station_list)
    to_ = process.extractOne(to_, station_list)
    from_ = from_[0]
    to_ = to_[0]
    logging.info("Searching for trips from %s to %s on %s", from_, to_, from_date)

    my_trip = trip.Trip(from_, to_, from_date)
    # check_satis_durum=False to get all trips for listing purposes
    trips = my_trip.get_trips(check_satis_durum=False)
    results = []

    if not trips:
        return [
            InlineQueryResultArticle(
                id=uuid4(),
                title="No trips found",
                input_message_content=InputTextMessageContent("No trips found"),
            )
        ]
    for t in trips:
        message = f"Bussiness: {t['buss_empty_seat_count']} Economy: {t['eco_empty_seat_count']}"
        time = datetime.strptime(t["binisTarih"], my_trip.time_format)

        results.append(
            InlineQueryResultArticle(
                id=uuid4(),
                title=datetime.strftime(time, my_trip.output_time_format),
                description=message,
                input_message_content=InputTextMessageContent(
                    f"/res {my_trip.from_station} - {my_trip.to_station} - {datetime.strftime(time, my_trip.output_time_format)}"
                ),
            )
        )
    return results
