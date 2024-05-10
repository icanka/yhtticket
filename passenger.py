"""Passenger class to store passenger details."""
import logging
from typing import Optional
import api_constants
from dataclasses import dataclass, field
logger = logging.getLogger(__name__)


def get_tariff(tariff: str) -> int:
    """Get the tariff value from the given tariff."""
    return api_constants.TARIFFS[tariff.upper()]


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
    tariff: Optional[str] = "1"


# create a passenger object
passenger = Passenger("18700774442", "izzet can", "karakus",
                      "14/07/1994", "test@test.com", "05340771521", "E")

print(passenger)
