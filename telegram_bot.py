from datetime import datetime
import logging
import pickle
import regex
from pprint import pprint
from uuid import uuid4
import requests
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    InlineQueryHandler,
    PicklePersistence,
    CallbackQueryHandler,
    ConversationHandler,
)
import inline_func
from trip_search import TripSearchApi
from trip import list_stations, Trip
from passenger import Passenger
from tasks import redis_client, find_trip_and_reserve, keep_reserving_seat
from celery.result import AsyncResult

# set httpx logger to warning
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
# logging.getLogger("telegram.ext.ConversationHandler").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


async def inline_funcs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline functions.

    Raises:
        AttributeError: If the query is not a valid method in the specified module.
    """
    command_list = ["stations", "query"]
    query = update.inline_query.query
    # if string is empty with stripped spaces
    query = query.strip()
    if not query:
        results = []
        for command in command_list:
            results.append(
                InlineQueryResultArticle(
                    id=uuid4(),
                    title=command,
                    description=f"Write {command} to get inline results",
                    input_message_content=InputTextMessageContent(command),
                )
            )
        await context.bot.answer_inline_query(update.inline_query.id, results)
        return

    command_str = query.split()[0]
    cmd_args = query.split()[1:]
    if command_str in command_list:
        results = []
        print("in command_list")
        _command = getattr(inline_func, command_str, None)
        # call the query variables string's named function from inline_func module
        if _command is None:
            raise AttributeError(
                f"{query} is not a valid method in the specified module."
            )
        if len(cmd_args) == 0:
            print("no cmd_args")
            results = _command()
        else:
            print("cmd_args")
            try:
                results = _command(*cmd_args)
            except TypeError as e:
                print(f"Error: {e}")

        print(len(results))
        print("answer_inline_query")
        await context.bot.answer_inline_query(update.inline_query.id, results)
        print("answer_inline_query")

        return
    print("not empty")


# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     """Send a message when the command /start is issued."""
#     for key, value in context.user_data.items():
#         print(f"{key}: {value}")
#         if isinstance(value, Passenger):
#             print(value.birthday)
#     await context.bot.send_message(
#         chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!"
#     )


# async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Echo the user message."""
#     await context.bot.send_message(
#         chat_id=update.effective_chat.id, text=update.message.text
#     )


# async def caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Handle the /caps command."""
#     text_caps = " ".join(context.args).upper()
#     await context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)


# async def res(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Handle the /res command."""
#     pass


# async def put(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Handle the /put command."""
#     logging.info("context.args: %s", context.args)
#     logging.info("value: %s", update.message.text.partition(" "))
#     key = str(uuid4())
#     value = update.message.text.partition(" ")[2]
#     passenger = Passenger(
#         "123456789", "can", "karakus", "birthday", "test@test.com", "05340771521", "E"
#     )

#     context.user_data[key] = passenger

#     await update.message.reply_text(f"Stored {value} with key {key}")


# states
(
    SELECTING_MAIN_ACTION,
    ADDING_PERSONAL_INFO,
    ADDING_CREDIT_CARD_INFO,
    SELECTING_TARIFF,
    SHOWING_INFO,
    BACK,
    TYPING_REPLY,
) = range(0, 7)
END = ConversationHandler.END


# Different constants for this example
(
    SELF,
    TRIP,
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
) = range(10, 26)


FEATURE_HELP_MESSAGES = {
    "birthday": "Please enter your birthday in the format dd/mm/yyyy.",
    "tckn": "Please enter your T.C. number correctly.",
    "name": "Please enter your name correctly.",
    "surname": "Please enter your surname correctly.",
    "phone": "Please enter your phone number in the format 05xxxxxxxxx.",
    "email": "This looks like an invalid email adress.",
    "sex": "Please enter your sex as 'E' or 'K'.",
    "credit_card_no": "Please enter your credit card number correctly.",
    "credit_card_ccv": "Please enter your credit card CCV correctly.",
    "credit_card_exp": "Expiration formet: MMYY .",
    "tariff": "Select your tariff",
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask the user about their"""

    text = "Add, update or show your information. To abort, simply type /stop"
    keyboard = InlineKeyboardMarkup(MAIN_MENU_BUTTONS)

    # try:
    #     init_passenger(update, context)
    # except KeyError as exc:
    #     logging.error("KeyError: %s", exc)

    if context.user_data.get(IN_PROGRESS):
        try:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                text=text, reply_markup=keyboard
            )
        except AttributeError:
            await update.message.reply_text(text=text, reply_markup=keyboard)
    else:

        await update.message.reply_text(
            "Hi! I'm a YHTBot! I can help you with your ticket reservations and"
            "purchases. But first, I need some information from you.",
        )
        await update.message.reply_text(text=text, reply_markup=keyboard)
    context.user_data[IN_PROGRESS] = False
    context.user_data[CURRENT_STATE] = SELECTING_MAIN_ACTION
    return SELECTING_MAIN_ACTION


async def show_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show the information of the user."""
    button = [[InlineKeyboardButton("Back", callback_data=str(BACK))]]
    keyboard = InlineKeyboardMarkup(button)
    user_data = context.user_data
    text = (
        f"Name: {user_data.get('name', 'Not Provided')}\n"
        f"Surname: {user_data.get('surname', 'Not Provided')}\n"
        f"T.C.: {user_data.get('tckn', 'Not Provided')}\n"
        f"Birthday: {user_data.get('birthday', 'Not Provided')}\n"
        f"Sex: {user_data.get('sex', 'Not Provided')}\n"
        f"Phone: {user_data.get('phone', 'Not Provided')}\n"
        f"Email: {user_data.get('email', 'Not Provided')}\n"
        f"Tariff: {user_data.get('tariff', 'Not Provided')}\n"
        f"Credit Card No: {user_data.get('credit_card_no', 'Not Provided')}\n"
        f"Credit Card CCV: {user_data.get(
            'credit_card_ccv', 'Not Provided')}\n"
        f"Credit Card Exp: {user_data.get(
            'credit_card_exp', 'Not provided')}\n"
    )
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    user_data[IN_PROGRESS] = True
    user_data[CURRENT_STATE] = SHOWING_INFO
    logging.info("state: SHOWING_INFO")
    return SHOWING_INFO


async def adding_self(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Add information about the user."""
    text = "Please provide me with your information."

    keyboard = InlineKeyboardMarkup(PERSON_MENU_BUTTONS)
    user_data = context.user_data
    if not user_data.get(IN_PROGRESS):
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        text = "Got it! What's next?"
        try:
            await update.message.reply_text(text=text, reply_markup=keyboard)
        except AttributeError:
            # we are coming from tariff maybe
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                text=text, reply_markup=keyboard
            )

    user_data[IN_PROGRESS] = False
    logging.info("returning ADDING_PERSONAL_INFO")
    user_data[CURRENT_STATE] = ADDING_PERSONAL_INFO
    return ADDING_PERSONAL_INFO


async def adding_credit_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Add credit card information about the user."""
    text = "Please provide me with your credit card information."

    keyboard = InlineKeyboardMarkup(CREDIT_CARD_MENU_BUTTONS)
    user_data = context.user_data
    if not user_data.get(IN_PROGRESS):
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        text = "Got it! What's next?"
        await update.message.reply_text(text=text, reply_markup=keyboard)

    user_data[IN_PROGRESS] = False
    logging.info("returning ADDING_CREDIT_CARD_INFO")
    user_data[CURRENT_STATE] = ADDING_CREDIT_CARD_INFO
    return ADDING_CREDIT_CARD_INFO


async def ask_for_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask the user for the information."""
    context.user_data[CURRENT_FEATURE] = update.callback_query.data
    text = FEATURE_HELP_MESSAGES[update.callback_query.data]
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text)
    logging.info("setting previous state to: %s", context.user_data[CURRENT_STATE])
    context.user_data[PREVIOUS_STATE] = context.user_data[CURRENT_STATE]
    context.user_data[CURRENT_STATE] = TYPING_REPLY
    return TYPING_REPLY


async def save_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save the user input."""
    feature = context.user_data[CURRENT_FEATURE]
    prev_state = context.user_data[PREVIOUS_STATE]
    logging.info("feature: %s", feature)
    try:
        re: str
        input_text = update.message.text
        match feature:
            case "birthday":
                re = r"^(\d{2})/(\d{2})/(\d{4})$"
                datetime.strptime(update.message.text, "%d/%m/%Y")
            case "tckn":
                re = r"^\d{11}$"
            case "name" | "surname":
                re = r"^[\p{L}\u0020]+$"
            case "phone":
                re = r"^0\d{10}$"
            case "sex":
                re = r"^[E|K|e|k]$"
                input_text = input_text.upper()
            case "email":
                re = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
            case "credit_card_no":
                re = r"^\d{16}$"
            case "credit_card_ccv":
                re = r"^\d{3}$"
            case "credit_card_exp":
                re = r"^\d{4}$"
                # MMYY to YYMM
                input_text = input_text[2:] + input_text[:2]
        if not regex.fullmatch(re, update.message.text):
            raise ValueError
    except ValueError:
        text = FEATURE_HELP_MESSAGES[feature]
        await update.message.reply_text(text=text)
        return TYPING_REPLY
    except AttributeError:
        # no update.message.text get callback_query.data
        input_text = update.callback_query.data
        logging.info("input_text: %s", input_text)

    input_text = input_text.strip()
    user_data = context.user_data
    user_data[user_data[CURRENT_FEATURE]] = input_text
    user_data[IN_PROGRESS] = True

    logging.info("prev_state: %s", prev_state)
    if prev_state == ADDING_PERSONAL_INFO:
        return await adding_self(update, context)
    elif prev_state == ADDING_CREDIT_CARD_INFO:
        return await adding_credit_card(update, context)


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End conversation from InlineKeyboardButton."""
    # logging.info("End conversation from InlineKeyboardButton. callbackquery_data: %s",
    #             update.callback_query.data)
    text = "See you next time!"
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text)

    context.user_data[CURRENT_STATE] = None
    return END


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End conversation by command."""
    await update.message.reply_text("Okay, bye!")
    return END


async def back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return to the previous state."""
    context.user_data[IN_PROGRESS] = True
    level = context.user_data[CURRENT_STATE]
    logging.info("level: %s", level)
    if level == ADDING_PERSONAL_INFO or level == ADDING_CREDIT_CARD_INFO:
        await start(update, context)
    elif level == SELECTING_TARIFF:
        await adding_self(update, context)
    logging.info("state: BACK")
    return BACK


async def unimplemented(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return END to end the conversation."""
    text = "This feature is not implemented yet."

    buttons = [[InlineKeyboardButton(text="Back", callback_data=str(BACK))]]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    context.user_data[IN_PROGRESS] = True
    context.user_data[CURRENT_STATE] = UNIMPLEMENTED
    logging.info("state: UNIMPLEMENTED")
    return UNIMPLEMENTED


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return END to end the conversation."""
    text = "Sorry, I didn't understand that command."
    # if context.user_data.get(CURRENT_FEATURE):
    #     text = FEATURE_HELP_MESSAGES[context.user_data[CURRENT_FEATURE]]
    state = context.user_data[CURRENT_STATE]
    logging.info("unknown command: current_state: %s", state)
    await update.message.reply_text(text=text)
    if state is not None:
        return state
    return END


async def res(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """handle the query result from inline query."""
    # get the message coming from command
    logging.info("context.args: %s", context.args)
    # check if the required information is provided
    try:
        logging.info("init_passenger")
        init_passenger(update, context)
        passenger = context.user_data[PASSENGER]
        logging.info(
            "mernis_dogrula: %s, %s, %s, %s",
            passenger.tckn,
            passenger.name,
            passenger.surname,
            passenger.birthday,
        )

    except KeyError as feature:
        logging.error("KeyError: %s", feature)
        await update.message.reply_text(
            f"{feature} is required, please update your information first."
        )
        return context.user_data.get(CURRENT_STATE, END)

    except ValueError as exc:
        logging.error("ValueError: %s", exc)
        await update.message.reply_text(
            "Mernis verification failed. Please update your information first.",
        )
        return context.user_data.get(CURRENT_STATE, END)

    except requests.exceptions.HTTPError as exc:
        logging.error("HTTPError: %s", "test")
        await update.message.reply_text(
            f"HTTPError {exc.errno}: Mernis verification failed."
        )
        return context.user_data.get(CURRENT_STATE, END)

    arg_string = update.message.text.partition(" ")[2]
    args = [arg.strip() for arg in arg_string.split("-")]
    from_, to_, from_date = args

    my_trip = Trip(from_, to_, from_date, passenger=passenger)
    logging.info("my_trip: from_date: %s,", my_trip.from_date)
    context.user_data[TRIP] = my_trip

    trips = my_trip.get_trips(check_satis_durum=False)

    # reply_keyboard = []
    inline_keyboard = []

    try:
        for trip in trips:
            time = datetime.strptime(trip["binisTarih"], my_trip.time_format)

            # reply_keyboard.append([datetime.strftime(time, my_trip.output_time_format)])
            # logging.info("time: %s", type(time))
            inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        text=datetime.strftime(time, my_trip.output_time_format),
                        callback_data=time,
                    )
                ]
            )
    except TypeError as exc:
        logging.error("TypeError: %s", exc)
        await update.message.reply_text("No trips found.")
        return context.user_data[CURRENT_STATE]

    # reply_keyboard_markup = ReplyKeyboardMarkup(
    #     reply_keyboard, one_time_keyboard=True,
    #     input_field_placeholder="Select the end range from date range to search for.")

    inline_keyboard_markup = InlineKeyboardMarkup(inline_keyboard)

    await update.message.reply_text(
        f"Okay lets get you started. I am going to search between {
            from_date} and your selected below date.",
        do_quote=True,
        reply_markup=inline_keyboard_markup,
    )
    logging.info(
        "returning context.user_data[CURRENT_STATE]: %s",
        context.user_data[CURRENT_STATE],
    )
    return context.user_data[CURRENT_STATE]


async def handle_datetime_type(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle the datetime type."""

    logging.info("handle_datetime_type")
    logging.info("context.args: %s", update.callback_query.data)
    my_trip = context.user_data[TRIP]
    time = datetime.strftime(update.callback_query.data, my_trip.output_time_format)
    my_trip.to_date = time
    logging.info(
        "my_trip: from_date %s, to_date: %s", my_trip.from_date, my_trip.to_date
    )

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text="Okay!.")
    return context.user_data[CURRENT_STATE]


# async def second_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """handle the query result from inline query."""
#     # get the message coming from command
#     logging.info("context.args: %s", context.args)
#     # context.args as one string
#     arg_string = update.message.text.partition(" ")[2]


def init_passenger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /init_passenger command."""
    # get the message coming from command

    # make sure all the required information is provided
    for feature in FEATURE_HELP_MESSAGES:
        if context.user_data.get(feature) is None:
            logging.info("KeyError: %s", feature)
            raise KeyError(feature)
    # create a passenger object
    passenger = Passenger(
        tckn=context.user_data["tckn"],
        name=context.user_data["name"],
        surname=context.user_data["surname"],
        birthday=context.user_data["birthday"],
        email=context.user_data["email"],
        phone=context.user_data["phone"],
        sex=context.user_data["sex"],
        tariff=context.user_data["tariff"],
        credit_card_no=context.user_data["credit_card_no"],
        credit_card_ccv=context.user_data["credit_card_ccv"],
        credit_card_exp=context.user_data["credit_card_exp"],
    )

    if not TripSearchApi.is_mernis_correct(passenger):
        raise ValueError("Mernis verification failed for passenger.")

    context.user_data[PASSENGER] = passenger
    logging.info("Passenger: %s.", context.user_data[PASSENGER])


async def delete_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Delete the key from the user_data."""
    key = context.args[0]
    if key in context.user_data:
        del context.user_data[key]
        text = f"Key {key} deleted."
    else:
        text = f"Key {key} not found."
    await update.message.reply_text(text=text)
    return context.user_data[CURRENT_STATE]


async def start_res(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the reservation process."""

    trip = context.user_data.get(TRIP)
    # maybe user directly calls this method, so trip passenger is None
    passenger = context.user_data.get(PASSENGER)
    if passenger is not None and trip.passenger is None:
        trip.passenger = passenger
    else:
        await update.message.reply_text(
            "Please use /res first with inline 'query' method."
        )
        return context.user_data.get(CURRENT_STATE, END)

    if trip is None:
        await update.message.reply_text("Please search for a trip first.")
        return context.user_data.get(CURRENT_STATE, END)
    elif context.user_data.get("task_id") is not None:
        await update.message.reply_text("You already have a search in progress.")
        return context.user_data.get(CURRENT_STATE, END)
    elif trip.koltuk_lock_id_list:
        text = f"{trip.empty_seat_json['koltukNo']} in vagon {trip.empty_seat_json['vagonSiraNo']
                                                              } is already reserved. Issue command /res or /reset_search to start over. lock_end_time: {trip.lock_end_time}"
        await update.message.reply_text(text=text)
        return context.user_data.get(CURRENT_STATE, END)

    logging.info("user_trip: %s", trip)
    chat_id = update.message.chat_id
    # run the callback_1 function after 3 seconds once

    context.job_queue.run_once(start_search, 3, data=context.user_data, chat_id=chat_id)

    # runa job every 10 seconds
    context.job_queue.run_repeating(
        check_task_status, 10, data=context.user_data, chat_id=chat_id
    )

    # if user_trip is not None:
    #     user_trip_bytes = pickle.dumps(user_trip)
    #     task = tripp.delay(user_trip_bytes)
    #     tas
    # await update.message.reply_text("I'm starting to search.")
    # logging.info("started searching reservation.")

    return context.user_data.get(CURRENT_STATE, END)


async def start_search(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Callback for the reservation process."""
    trip = context.job.data.get(TRIP)
    logging.info("trip: %s", trip)
    # serialize the trip object
    trip_ = pickle.dumps(trip)
    # start the celery task
    task = find_trip_and_reserve.delay(trip_)
    # save the task id to the context
    context.job.data["task_id"] = task.id
    context.job.data["task_name"] = "find_trip_and_reserve"

    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=f"BEEEP, starting to search for trip with id {trip.from_station} to {trip.to_station} on {trip.from_date}.",
    )
    return context.job.data.get(CURRENT_STATE, END)


async def check_task_status(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Check the status of the task."""

    if context.job.data.get("task_id") is None:
        await context.bot.send_message(
            chat_id=context.job.chat_id, text="No in progress task."
        )
        return context.job.data.get(CURRENT_STATE, END)

    task_id = context.job.data.get("task_id")
    task = AsyncResult(task_id)

    if task.ready():
        logging.info("Task is ready")
        result = task.get()
        my_trip = pickle.loads(result)
        context.job.data[TRIP] = my_trip

        time = datetime.strptime(my_trip.trip_json["binisTarih"], my_trip.time_format)
        time = datetime.strftime(time, my_trip.output_time_format)

        await context.bot.send_message(
            chat_id=context.job.chat_id,
            text=f"Seat {my_trip.empty_seat_json['koltukNo']} in vagon {my_trip.empty_seat_json['vagonSiraNo']} is reserved for trip {time}",
        )
        await context.bot.send_message(
            chat_id=context.job.chat_id,
            text="Keeping the seat lock until you progress to payment.",
        )
        logger.info("Setting task_id to None.")
        context.job.data["task_id"], context.job.data["task_name"] = None, None
        logger.info("Revoking task with id: %s", task.id)
        task.revoke()
        logger.info("Starting job keep_seat_lock.")
        context.job_queue.run_once(
            keep_seat_lock, 3, data=context.job.data, chat_id=context.job.chat_id
        )

        logger.info("Removing job with name: %s", context.job.name)
        # remove this job
        context.job.schedule_removal()

        jobs = context.job_queue.jobs()
        logger.info("Job queue: %s", jobs)

    return context.job.data.get(CURRENT_STATE, END)


async def keep_seat_lock(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Keep the seat lock until the user progresses to payment."""

    # unset redis flag in case it is set
    logger.info("Unsetting stop_reserve_seat_flag")
    redis_client.delete("stop_reserve_seat_flag")

    logger.info("Keeping the seat lock.")

    trip = context.job.data.get(TRIP)
    task = keep_reserving_seat.delay(pickle.dumps(trip))
    context.job.data["task_id"] = task.id
    context.job.data["task_name"] = "keep_reserving_seat"
    return context.job.data.get(CURRENT_STATE, END)


async def reset_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Reset the search task."""
    trip = context.user_data.get(TRIP)

    # reset the fields
    if trip:
        trip.trip_json = None
        trip.empty_seat_json = None
        trip.seat_lock_response = None
        trip.lock_end_time = None
        trip.is_seat_reserved = False
        trip.koltuk_lock_id_list = []

    # remove all jobs
    for job in context.job_queue.jobs():
        job.schedule_removal()

    # revoke the user task
    if context.user_data.get("task_id") is not None:
        task_id = context.user_data.get("task_id")
        logger.info("Revoking task with id: %s", task_id)
        task = AsyncResult(task_id)
        task.revoke(terminate=True)
        context.user_data["task_id"], context.user_data["task_name"] = None, None

    await update.message.reply_text("Search is reset. You can start a new search.")
    return context.user_data.get(CURRENT_STATE, END)


async def check_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Check the status of the task."""
    task_id = context.user_data.get("task_id")
    if task_id is not None:
        task = AsyncResult(task_id)
        task_name = context.user_data.get("task_name")
        text = f"You have currently running a task: {task_name}, status: {task.status}."
    else:
        text = "You have no running task."
    await update.message.reply_text(text=text)
    return context.user_data.get(CURRENT_STATE, END)


# async def test_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Return END to end the conversation."""
#     text = "You are in the test method."
#     logging.info("You are in the test method. callback_query_data: %s",
#                  update.callback_query.data)
#     await update.callback_query.answer()
#     await update.callback_query.edit_message_text(text=text)
#     return TEST


async def selecting_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Select the tariff."""
    logging.info("Selecting tariff.")
    # set this to ADDING_PERSONAL_INFO to return to the previous state
    context.user_data[PREVIOUS_STATE] = ADDING_PERSONAL_INFO
    context.user_data[CURRENT_STATE] = SELECTING_TARIFF
    context.user_data[CURRENT_FEATURE] = update.callback_query.data
    text = "Select your tariff."
    keyboard = InlineKeyboardMarkup(TARIFF_MENU_BUTTONS)
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    return SELECTING_TARIFF


async def print_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Print the current state."""
    logging.info("current_state: %s", context.user_data[CURRENT_STATE])
    logging.info("previous_State: %s", context.user_data[PREVIOUS_STATE])
    trip = context.user_data.get(TRIP)
    text = f"{trip.lock_end_time}"
    logger.info("lock_end_time: %s", text)
    return context.user_data[CURRENT_STATE]


async def print_trip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Print the current state."""
    trip = context.user_data.get(TRIP)

    if trip is not None:
        reply_text = (
            f"From: {trip.from_station}\n"
            f"To: {trip.to_station}\n"
            f"From Date: {trip.from_date}\n"
            f"To Date: {trip.to_date}\n"
            f"Tariff: {trip.passenger.tariff}\n"
            f"Seat Type: {str(trip.seat_type)}\n"
        )
        await update.message.reply_text(text=reply_text)
    return context.user_data.get(CURRENT_STATE, END)


def main() -> None:
    """Run the bot."""
    my_persistance = PicklePersistence(filepath="my_persistence")

    app = (
        ApplicationBuilder()
        .token("***REMOVED***")
        .arbitrary_callback_data(True)
        .persistence(persistence=my_persistance)
        .build()
    )
    job_queue = app.job_queue
    fallback_handlers = [
        CommandHandler("stop", stop),
        CommandHandler("res", res),
        CommandHandler("print_state", print_state),
        CallbackQueryHandler(handle_datetime_type, pattern=datetime),
        MessageHandler(filters.COMMAND, unknown_command),
    ]

    tariff_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(selecting_tariff, pattern="^tariff$")],
        states={
            SELECTING_TARIFF: [
                CallbackQueryHandler(back, pattern=f"^{BACK}$"),
                CallbackQueryHandler(save_input),
            ],
        },
        fallbacks=fallback_handlers,
        map_to_parent={
            # End the child conversation and return to SELECTING_MAIN_ACTION state
            BACK: ADDING_PERSONAL_INFO,
            # End the whole conversation from within the child conversation.
            END: END,
            # save_input returned state so we need to map it
            ADDING_PERSONAL_INFO: ADDING_PERSONAL_INFO,
        },
    )

    adding_self_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                adding_self,
                pattern=f"^{
                                 ADDING_PERSONAL_INFO}$",
            )
        ],
        states={
            ADDING_PERSONAL_INFO: [
                tariff_conv_handler,
                CallbackQueryHandler(ask_for_input, pattern="^name$"),
                CallbackQueryHandler(ask_for_input, pattern="^surname$"),
                CallbackQueryHandler(ask_for_input, pattern="^tckn$"),
                CallbackQueryHandler(ask_for_input, pattern="^birthday$"),
                CallbackQueryHandler(ask_for_input, pattern="^sex$"),
                CallbackQueryHandler(ask_for_input, pattern="^phone$"),
                CallbackQueryHandler(ask_for_input, pattern="^email$"),
                CallbackQueryHandler(back, pattern=f"^{BACK}$"),
            ],
            TYPING_REPLY: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), save_input),
            ],
        },
        fallbacks=fallback_handlers,
        map_to_parent={
            # End the child conversation and return to SELECTING_MAIN_ACTION state
            BACK: SELECTING_MAIN_ACTION,
            # End the whole conversation from within the child conversation.
            END: END,
        },
    )

    adding_credit_card_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                adding_credit_card, pattern=f"^{ADDING_CREDIT_CARD_INFO}$"
            )
        ],
        states={
            ADDING_CREDIT_CARD_INFO: [
                CallbackQueryHandler(ask_for_input, pattern="^credit_card_no$"),
                CallbackQueryHandler(ask_for_input, pattern="^credit_card_ccv$"),
                CallbackQueryHandler(ask_for_input, pattern="^credit_card_exp$"),
                CallbackQueryHandler(back, pattern=f"^{BACK}$"),
            ],
            TYPING_REPLY: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), save_input),
            ],
        },
        fallbacks=fallback_handlers,
        map_to_parent={
            # End the child conversation and return to SELECTING_MAIN_ACTION state
            BACK: SELECTING_MAIN_ACTION,
            # End the whole conversation from within the child conversation.
            END: END,
        },
    )

    main_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_MAIN_ACTION: [
                adding_self_conv_handler,
                adding_credit_card_conv_handler,
                # CallbackQueryHandler(adding_self, pattern=f"^{ADDING_PERSONAL_INFO}$"),
                CallbackQueryHandler(
                    unimplemented, pattern=f"^{ADDING_CREDIT_CARD_INFO}$"
                ),
                CallbackQueryHandler(show_info, pattern=f"^{SHOWING_INFO}$"),
                CallbackQueryHandler(end, pattern=f"^{END}$"),
            ],
            SHOWING_INFO: [
                CallbackQueryHandler(start, pattern=f"^{BACK}$"),
            ],
            UNIMPLEMENTED: [
                CallbackQueryHandler(start, pattern=f"^{BACK}$"),
            ],
        },
        fallbacks=fallback_handlers,
    )
    inline_caps_handler = InlineQueryHandler(inline_funcs)

    app.add_handler(main_conv_handler)
    app.add_handler(inline_caps_handler)

    # echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    # app.add_handler(echo_handler)

    res_handler = CommandHandler("res", res)
    app.add_handler(res_handler)

    init_handler = CommandHandler("init_passenger", init_passenger)
    app.add_handler(init_handler)
    delete_key_handler = CommandHandler("delete_key", delete_key)
    app.add_handler(delete_key_handler)
    # app.add_handler(inline_caps_handler)

    print_state_handler = CommandHandler("print_state", print_state)
    app.add_handler(print_state_handler)

    datetime_type_handler = CallbackQueryHandler(handle_datetime_type, pattern=datetime)
    app.add_handler(datetime_type_handler)

    start_reservation_handler = CommandHandler("start_res", start_res)
    app.add_handler(start_reservation_handler)

    reset_search_handler = CommandHandler("reset_search", reset_search)
    app.add_handler(reset_search_handler)

    check_task_handler = CommandHandler("check_task", check_task)
    app.add_handler(check_task_handler)

    print_trip_handler = CommandHandler("print_trip", print_trip)
    app.add_handler(print_trip_handler)
    # app.add_handler(CommandHandler("put", put))
    # pprint(app.user_data)
    # pprint(app.chat_data)

    app.run_polling()


if __name__ == "__main__":
    main()
