from telegram import InlineKeyboardButton
from telegram.ext import ConversationHandler


(
    SELECTING_MAIN_ACTION,
    ADDING_PERSONAL_INFO,
    ADDING_CREDIT_CARD_INFO,
    SELECTING_TARIFF,
    SELECTING_SEAT_TYPE,
    SELECTING_SEX,
    SHOWING_INFO,
    BACK,
    TYPING_REPLY,
) = range(0, 9)

END = ConversationHandler.END


# Different constants for this example
(
    SELF,
    TRIP,
    PAYMENT,
    PASSENGER,
    NAME,
    SURNAME,
    TC,
    BIRTHDAY,
    SEX,
    PHONE,
    EMAIL,
    IN_PROGRESS,
    FEATURES,
    CURRENT_FEATURE,
    CURRENT_STATE,
    PREVIOUS_STATE,
    UNIMPLEMENTED,
    PAYMENT_IN_PROGRESS,
) = range(10, 28)


FEATURE_HELP_MESSAGES = {
    "birthday": "Please enter your birthday in the format dd/mm/yyyy.",
    "tckn": "Please enter your T.C. number.",
    "name": "Please enter your name.",
    "surname": "Please enter your surname.",
    "phone": "Please enter your phone number in the format 05xxxxxxxxx.",
    "email": "Please enter a valid email address.",
    "sex": "Please enter your sex as 'E' or 'K'.",
    "credit_card_no": "Please enter your credit card number.",
    "credit_card_ccv": "Please enter your credit card CCV.",
    "credit_card_exp": "Expiration format: MMYY .",
    "tariff": "Select your tariff",
    "seat_type": "Select your seat type",
}


MAIN_MENU_BUTTONS = [
    [
        InlineKeyboardButton("Personal Info", callback_data=str(ADDING_PERSONAL_INFO)),
        InlineKeyboardButton(
            "Credit Card Info", callback_data=str(ADDING_CREDIT_CARD_INFO)
        ),
    ],
    [
        InlineKeyboardButton("Show Info", callback_data=str(SHOWING_INFO)),
        InlineKeyboardButton("Done", callback_data=str(END)),
    ],
]


PERSON_MENU_BUTTONS = [
    [
        InlineKeyboardButton("Name", callback_data="name"),
        InlineKeyboardButton("Surname", callback_data="surname"),
        InlineKeyboardButton("T.C", callback_data="tckn"),
        InlineKeyboardButton("Birthday", callback_data="birthday"),
        InlineKeyboardButton("Seat Type", callback_data="seat_type"),
    ],
    [
        InlineKeyboardButton(
            "Tariff",
            callback_data="tariff",
        ),
        InlineKeyboardButton("Phone", callback_data="phone"),
        InlineKeyboardButton("Email", callback_data="email"),
        InlineKeyboardButton("Sex", callback_data="sex"),
        InlineKeyboardButton("Back", callback_data=str(BACK)),
    ],
]

SEAT_TYPE_MENU_BUTTONS = [
    [
        InlineKeyboardButton("Business", callback_data="Business"),
        InlineKeyboardButton("Economy", callback_data="Economy"),
    ],
    [
        InlineKeyboardButton("Any", callback_data="Any"),
        InlineKeyboardButton("Back", callback_data=str(BACK)),
    ],
]

SEX_MENU_BUTTONS = [
    [
        InlineKeyboardButton("Male", callback_data="E"),
        InlineKeyboardButton("Female", callback_data="K"),
    ],
    [
        InlineKeyboardButton("Back", callback_data=str(BACK)),
    ],
]

TARIFF_MENU_BUTTONS = [
    [
        InlineKeyboardButton("Tam", callback_data="Tam"),
        InlineKeyboardButton("Tsk", callback_data="Tsk"),
    ],
    [
        InlineKeyboardButton("Back", callback_data=str(BACK)),
    ],
]

CREDIT_CARD_MENU_BUTTONS = [
    [
        InlineKeyboardButton("Credit Card No", callback_data="credit_card_no"),
        InlineKeyboardButton("CCV", callback_data="credit_card_ccv"),
    ],
    [
        InlineKeyboardButton("Exp", callback_data="credit_card_exp"),
        InlineKeyboardButton("Back", callback_data=str(BACK)),
    ],
]
