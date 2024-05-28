"""This script is used to automate the ticket purchase process from TCDD website."""

from dataclasses import dataclass, field
import time
from datetime import datetime
import logging
from typing import Optional

import requests
import api_constants
from trip_search import TripSearchApi
from trip_search import SeatLockedException
from passenger import Passenger


@dataclass
class Seat:
    trip_json: dict = field(default=None, init=False)
    empty_seat_json: dict = field(default=None, init=False)
    seat_lock_response: dict = field(default=None, init=False)
    koltuk_lock_id_list: list = field(default_factory=list, init=False)
    lock_end_time: datetime = field(default=None, init=False)
    is_seat_reserved: bool = field(default=False, init=False)

@dataclass
class Trip:
    """Trip class to store trip details."""
    from_station: str
    to_station: str
    from_date: str
    to_date: Optional[str] = None
    passenger: Passenger = None
    seat_type: Optional[str] = None
    time_format: str = field(default="%b %d, %Y %I:%M:%S %p", init=False)
    output_time_format: str = field(default="%b %d, %H:%M", init=False)
    logger: logging.Logger = field(default=logging.getLogger(__name__), init=False)

    seat: Seat = field(default_factory=Seat, init=False)
