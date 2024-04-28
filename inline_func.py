from datetime import datetime
import logging
from pprint import pprint
from uuid import uuid4
from thefuzz import fuzz
from thefuzz import process
from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    InlineQueryHandler,
)
import dateparser
import trip


def stations():
    results = []
    stations = trip.list_stations()
    for station in stations:
        results.append(
            InlineQueryResultArticle(
                id=uuid4(),
                title=station,
                input_message_content=InputTextMessageContent(station),
            )
        )
    return results


def query(from_, to_, from_date=None):

    stns = trip.list_stations()
    from_ = process.extractOne(from_, stns)
    to_ = process.extractOne(to_, stns)
    from_ = from_[0]
    to_ = to_[0]

    my_trip = trip.Trip(from_, to_, from_date)
    trips = my_trip.get_trips()
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
        results.append(
            InlineQueryResultArticle(
                id=uuid4(),
                title=t["binisTarih"],
                description=message,
                input_message_content=InputTextMessageContent(f"{t['binisTarih']} {message}"),
            )
        )
    return results
