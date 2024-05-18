"""Passenger class to store passenger details."""
import logging
from typing import Optional
import api_constants
from dataclasses import dataclass, field
logger = logging.getLogger(__name__)


class Seat:
    """Seat class to store seat details."""
    BUSS: int = 17001
    ECO: int = 17002
    ANY = None


class Tariff:
    """Tariff class to store tariff details."""
    TSK: int = 11750067704
    TAM: int = 1

Seat.__getattribut
@dataclass(frozen=True)
class Passenger:
    """Passenger class to store passenger details."""
    tckn: str
    name: str
    surname: str
    birthday: str
    email: str
    phone: str
    sex: str
    credit_card_no: Optional[str] = None
    credit_card_ccv: Optional[str] = None
    credit_card_exp: Optional[str] = None
    tariff: Optional[int] = None
    seat_type: Optional[int] = None


# create a passenger object
passenger = Passenger("18700774442", "izzet can", "karakus",
                      "14/07/1994", "test@test.com", "05340771521", "E")

print(passenger)
