"""Passenger class to store passenger details."""

import logging
from typing import Optional
from dataclasses import dataclass

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
    tariff: Optional[int] = Tariff.TAM
    seat_type: Optional[int] = None
