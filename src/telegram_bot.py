""" Telegram bot functions. """

import asyncio
import logging
import pickle
import json
from datetime import datetime
from uuid import uuid4

import regex
import requests
from celery.result import AsyncResult
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Update,
)
from telegram.ext import ContextTypes

import inline_func
from passenger import Passenger, Seat, Tariff
from payment import Payment
from tasks.celery_tasks import (
    celery_app,
    find_trip_and_reserve,
    keep_reserving_seat,
    redis_client,
    run_indefinete_task,
    available_workers,
)
from tasks.trip import Trip
from tasks.trip_search import TripSearchApi
from constants import *  # pylint: disable=wildcard-import, unused-wildcard-import


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handlers = [logging.FileHandler("../bot_data/logs/bot.log"), logging.StreamHandler()]
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s"
)
for handler in handlers:
    handler.setFormatter(formatter)
    logger.addHandler(handler)

logger.info("Starting logger")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask the user about their"""
    if update.callback_query:
        logger.info(
            "Conversation with user_id: %s, chat_id: %s",
            update.callback_query.from_user.id,
            update.callback_query.message.chat_id,
        )
    else:
        logger.info(
            "Conversation with user_id: %s, chat_id: %s",
            update.message.from_user.id,
            update.message.chat_id,
        )
    text = "Add, update or show your information. To abort, simply type /stop"
    keyboard = InlineKeyboardMarkup(MAIN_MENU_BUTTONS)

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
                    description=f"Write {command} to see results",
                    input_message_content=InputTextMessageContent(command),
                )
            )
        await context.bot.answer_inline_query(update.inline_query.id, results)
        return

    command_str = query.split()[0]
    cmd_args = query.split()[1:]
    if command_str in command_list:
        results = []
        _command = getattr(inline_func, command_str, None)
        # call the query variables string's named function from inline_func module
        if _command is None:
            raise AttributeError(
                f"{query} is not a valid method in the specified module."
            )
        if len(cmd_args) == 0:
            logger.info("cmd_args: %s", cmd_args)
            results = _command()
        else:
            logger.info("cmd_args: %s", cmd_args)
            try:
                results = _command(*cmd_args)
            except TypeError as e:
                logger.error("TypeError: %s", e)

        await context.bot.answer_inline_query(update.inline_query.id, results)
        return


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
        f"Seat Type: {user_data.get('seat_type', 'Not Provided')}\n"
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
    logger.info("state: SHOWING_INFO")
    return SHOWING_INFO


async def show_trip_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show configure trip information"""
    logger.info("Showing trip info.")
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Back", callback_data=str(BACK))]]
    )
    context.user_data[IN_PROGRESS] = True
    context.user_data[CURRENT_STATE] = SHOWING_TRIP_INFO
    trip = context.user_data.get(TRIP)
    if trip is None:
        text = "No trip is configured yet. Please search for a trip first."
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return SHOWING_TRIP_INFO

    logger.info("chat_id: %s", update.callback_query.message.chat_id)
    await update_trip_lock_end_time(trip, update.callback_query.message.chat_id)

    if trip.is_reservation_expired():
        logger.info("Reservation is expired. lock_end_time: %s", trip.lock_end_time)
        # trip.reset_reservation_data()
        text = (
            f"From: *{trip.from_station}*\n"
            f"To: *{trip.to_station}*\n"
            f"From Date: *{trip.from_date}*\n"
            f"To Date: *{trip.to_date}*\n"
        )
        if trip.empty_seat_json is not None:
            text += "*Reservation Expired*\n"
        else:
            text += "*No seat is currently reserved.*\n"
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard, parse_mode="Markdown"
        )
        return SHOWING_TRIP_INFO
    else:
        time_diff = trip.lock_end_time - datetime.now()
        time_diff = time_diff.total_seconds() // 60
        text = (
            f"From: *{trip.from_station}*\n"
            f"To: *{trip.to_station}*\n"
            f"From Date: *{trip.from_date}*\n"
            f"To Date: *{trip.to_date}*\n"
            f"Reserved Trip: *{trip.trip_json.get('binisTarih')}*\n"
            f"Reserved Vagon: *{trip.empty_seat_json.get('vagonSiraNo')}*\n"
            f"Reserved Seat: *{trip.empty_seat_json.get('koltukNo')}*\n"
            f"Remaining Reserve Time: *{time_diff}* min.\n"
        )
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard, parse_mode="Markdown"
        )
        return SHOWING_TRIP_INFO


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
    logger.info("returning ADDING_PERSONAL_INFO")
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
    logger.info("returning ADDING_CREDIT_CARD_INFO")
    user_data[CURRENT_STATE] = ADDING_CREDIT_CARD_INFO
    return ADDING_CREDIT_CARD_INFO


async def ask_for_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask the user for the information."""
    context.user_data[CURRENT_FEATURE] = update.callback_query.data
    logger.info("current_feature: %s", context.user_data[CURRENT_FEATURE])
    text = FEATURE_HELP_MESSAGES[update.callback_query.data]
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text)
    logger.info(
        "current_state: TYPING_REPLY, previous_state: %s",
        context.user_data[CURRENT_STATE],
    )
    logger.info("setting previous state to: %s", context.user_data[CURRENT_STATE])
    context.user_data[PREVIOUS_STATE] = context.user_data[CURRENT_STATE]
    context.user_data[CURRENT_STATE] = TYPING_REPLY
    return TYPING_REPLY


async def save_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save the user input."""
    feature = context.user_data[CURRENT_FEATURE]
    prev_state = context.user_data[PREVIOUS_STATE]
    logger.info("feature: %s", feature)
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
            logger.error("ValueError: %s", update.message.text)
            raise ValueError
    except ValueError:
        text = FEATURE_HELP_MESSAGES[feature]
        await update.message.reply_text(text=text)
        return TYPING_REPLY
    except AttributeError:
        # no update.message.text get callback_query.data
        input_text = update.callback_query.data
        logger.info("input_text: %s", input_text)

    input_text = input_text.strip()
    user_data = context.user_data
    user_data[user_data[CURRENT_FEATURE]] = input_text
    user_data[IN_PROGRESS] = True

    logger.info("prev_state: %s", prev_state)
    if prev_state == ADDING_PERSONAL_INFO:
        return await adding_self(update, context)
    elif prev_state == ADDING_CREDIT_CARD_INFO:
        return await adding_credit_card(update, context)


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End conversation from InlineKeyboardButton."""
    # logger.info("End conversation from InlineKeyboardButton. callbackquery_data: %s",
    #             update.callback_query.data)
    text = "See you next time!"
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text)

    context.user_data[CURRENT_STATE] = None
    return END


async def stop(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    """End conversation by command."""
    await update.message.reply_text("Okay, bye!")
    return END


async def back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return to the previous state."""
    context.user_data[IN_PROGRESS] = True
    level = context.user_data[CURRENT_STATE]
    logger.info("level: %s", level)
    if level == SELECTING_TARIFF or level == SELECTING_SEAT_TYPE:
        logger.info("SELECTING_TARIFF or SELECTING_SEAT_TYPE")
        await adding_self(update, context)
    else:
        logger.info("default case: start(update, context)")
        await start(update, context)
    logger.info("state: BACK")
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
    logger.info("state: UNIMPLEMENTED")
    return UNIMPLEMENTED


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return END to end the conversation."""
    text = "Sorry, I didn't understand that command."
    state = context.user_data.get(CURRENT_STATE)
    logger.info("unknown command: current_state: %s", state)
    await update.message.reply_text(text=text)
    if state is not None:
        return state
    return END


async def res(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """handle the query result from inline query. This let's you set the trip information."""
    # get the message coming from command
    logger.info("context.args: %s", context.args)
    # check if the required information is provided
    await set_passenger(update, context)
    passenger = context.user_data.get(PASSENGER, None)
    if passenger is None:
        await update.message.reply_text("Need passenger.")
        return context.user_data.get(CURRENT_STATE, END)

    arg_string = update.message.text.partition(" ")[2]
    args = [arg.strip() for arg in arg_string.split("-")]
    from_, to_, from_date = args

    my_trip = Trip(from_, to_, from_date, passenger=passenger)
    logger.info("my_trip: from_date: %s,", my_trip.from_date)
    context.user_data[TRIP] = my_trip

    trips = my_trip.get_trips(check_satis_durum=False)
    inline_keyboard = []

    try:
        for trip in trips:
            _time = datetime.strptime(trip["binisTarih"], my_trip.time_format)
            inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        text=datetime.strftime(_time, my_trip.output_time_format),
                        callback_data=_time,
                    )
                ]
            )
    except TypeError as exc:
        logger.error("TypeError: %s", exc)
        await update.message.reply_text("No trips found.")

    inline_keyboard_markup = InlineKeyboardMarkup(inline_keyboard)

    await update.message.reply_text(
        f"Okay lets get you started. I am going to search between {
            from_date} and your selected below date.",
        do_quote=True,
        reply_markup=inline_keyboard_markup,
    )
    logger.info(
        "returning context.user_data[CURRENT_STATE]: %s",
        context.user_data[CURRENT_STATE],
    )
    return context.user_data.get(CURRENT_STATE, END)


async def handle_datetime_type(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle the datetime type from the inline query selection."""

    logger.info("handle_datetime_type")
    logger.info("context.args: %s", update.callback_query.data)
    my_trip = context.user_data[TRIP]
    _time = datetime.strftime(update.callback_query.data, my_trip.output_time_format)
    my_trip.to_date = _time
    logger.info(
        "my_trip: from_date %s, to_date: %s", my_trip.from_date, my_trip.to_date
    )

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text="Okay!.")
    return context.user_data.get(CURRENT_STATE, END)


async def start_search(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Callback for the reservation process."""
    user_data = context.job.data
    task_id = user_data.get("task_id")
    trip = user_data.get(TRIP)

    if task_id:
        # get active tasks
        tasks = await get_user_task(task_id)
        if tasks:
            for task in tasks:
                logger.info("Found celery task with id: %s", task_id)
                await context.bot.send_message(
                    chat_id=context.job.chat_id,
                    text=f"*Oops*, You already have a running task in progress: *{task['name']}*",
                    parse_mode="Markdown",
                )
                await asyncio.sleep(3)
                return user_data.get(CURRENT_STATE, END)

    logger.info("trip: %s, type: %s", trip, type(trip))
    logger.info("trip.passenger: %s", trip.passenger)
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=f"*BEEEP*, starting to search for trip *{
            trip.from_station}* to *{trip.to_station}* on *{trip.from_date}*.",
        parse_mode="Markdown",
    )
    # reset old reservation data
    trip.reset_reservation_data()
    # serialize the trip object
    trip_ = pickle.dumps(trip)
    # start the celery task
    task = find_trip_and_reserve.delay(trip_)
    # save the task id to the context
    logger.info("SETTING TASK_ID: %s", task.id)
    user_data["task_id"] = task.id

    return user_data.get(CURRENT_STATE, END)


async def check_search_status(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Check the status of the task."""
    task_id = context.job.data.get("task_id")
    logger.info("task_id: %s", task_id)
    task_ = None
    if task_id is None:
        await context.bot.send_message(
            chat_id=context.job.chat_id,
            text="No search task in progress. Removing job.",
        )
        context.job.schedule_removal()
        return context.job.data.get(CURRENT_STATE, END)

    # try active tasks first
    tasks = await get_user_task(task_id)
    if tasks:
        logger.info("tasks len: %s", len(tasks))
        for task in tasks:
            logger.info("task_name : %s", task["name"])
            if task["name"] != "tasks.celery_tasks.find_trip_and_reserve":
                logger.info("No active search task in progress. Removing this job.")
                context.job.schedule_removal()
                return context.job.data.get(CURRENT_STATE, END)
            elif task["id"] == task_id:
                logger.info("Found search task with task_id: %s", task_id)
                task_ = AsyncResult(task_id)

    # maybe task finished before we checked active tasks, so try to get the result anyway
    # if task if none
    if task_ is None:
        logger.info("Getting task with id: %s", task_id)
        task_ = AsyncResult(task_id)

    if task_.ready():
        logger.info("Task is ready")
        if not task_.successful():
            # get the exception
            logger.error("Search task failed. Removing this job.")
            context.job.schedule_removal()

        logger.info("Getting the result of the task.")
        result = task_.get()
        my_trip = pickle.loads(result)

        logger.info("setting context trip")
        context.job.data[TRIP] = my_trip

        logger.info("SETTING TASK_ID: None")
        context.job.data["task_id"] = None
        logger.warning("Revoking task with id: %s", task_id)
        task_.revoke()

        logger.info("Starting job keep_seat_lock.")
        context.job_queue.run_once(
            keep_seat_lock,
            3,
            data=context.job.data,
            chat_id=context.job.chat_id,
            job_kwargs={"misfire_grace_time": 60},
        )
        logger.info("Job queue: %s", context.job_queue.jobs())

        logger.info(
            "This job: %s has completed its purpose, removing it.", context.job.name
        )
        text = (
            "FOUND TRIP!\n"
            f"Reserved Trip: *{my_trip.trip_json.get('binisTarih')}*\n"
            f"Reserved Vagon: *{my_trip.empty_seat_json.get('vagonSiraNo')}*\n"
            f"Reserved Seat: *{my_trip.empty_seat_json.get('koltukNo')}*\n"
        )
        # notify the user
        await context.bot.send_message(
            chat_id=context.job.chat_id,
            text=text,
            parse_mode="Markdown",
        )

        # remove this job
        context.job.schedule_removal()

    return context.job.data.get(CURRENT_STATE, END)


async def keep_seat_lock(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Keep the seat lock until the user progresses to payment."""
    trip = context.job.data.get(TRIP)
    task = keep_reserving_seat.delay(pickle.dumps(trip), context.job.chat_id)
    logger.info("Setting task_id to context.user_data")
    # save the task id to the context
    logger.warning("SETTING TASK_ID: %s", task.id)
    context.job.data["task_id"] = task.id
    return context.job.data.get(CURRENT_STATE, END)


async def proceed_to_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Proceed to payment."""
    # get currently running tasks
    await update.callback_query.answer()
    keyboard = InlineKeyboardMarkup(SEARCH_MENU_BUTTONS)
    task_id = context.user_data.get("task_id")
    logger.info("task_id: %s", task_id)
    trip = context.user_data.get(TRIP)

    await update_trip_lock_end_time(trip, update.callback_query.message.chat_id)
    if trip and trip.is_reservation_expired():
        if trip.empty_seat_json is not None:
            text = "*Reservation Expired.*"
        else:
            text = "*No seat is currently reserved.*"
        await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard, parse_mode="Markdown"
        )
        return context.user_data.get(CURRENT_STATE, END)

    if trip is None:
        text = "No trip is configured yet. Please search for a trip first."
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return context.user_data.get(CURRENT_STATE, END)

    tasks = await get_user_task(task_id)

    if tasks:
        for task in tasks:
            if task["name"] == "tasks.celery_tasks.find_trip_and_reserve":
                logger.info("You still have a task in progress.")
                await update.callback_query.edit_message_text(
                    text="*You still have an ongoing search in progress.*",
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
                return context.user_data.get(CURRENT_STATE, END)

            elif task["name"] == "tasks.celery_tasks.keep_reserving_seat":
                # stop the keep_seat_lock job to get the trip object
                # then start it again to keep the seat lock in case payment fails
                redis_client.set(task_id, 1, ex=600)
                # wait for the task to finish but also with a timeout
                task_ = AsyncResult(task_id)
                trip_ = task_.get(timeout=30)
                trip = pickle.loads(trip_)

                logger.info("Trip from keep_reserving_seat aquired.")
                logger.info("Setting context trip.")

                context.user_data[TRIP] = trip
                # keep the seat lock
                job = context.job_queue.run_once(
                    keep_seat_lock,
                    3,
                    data=context.user_data,
                    chat_id=update.callback_query.message.chat_id,
                    job_kwargs={"misfire_grace_time": 60},
                )

    logger.info("We can proceed to payment. Everything looks fine.")
    # set the passenger object, for if the user has changed some information
    await set_passenger(update, context)

    p = Payment()
    p.trip = trip
    logger.info("Setting context payment object.")
    context.user_data[PAYMENT] = p

    try:
        p.set_price()
        p.set_payment_url()
    except ValueError as exc:
        # propably credit card information is not correct
        await asyncio.sleep(1)
        await update.callback_query.edit_message_text(
            text=f"{exc}", reply_markup=keyboard
        )
        return context.user_data.get(CURRENT_STATE, END)

    await update.callback_query.edit_message_text(
        f' Here is your <a href="{p.current_payment_url}">Payment Link</a>',
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    # we have succesfully created the payment url, now we can check the payment status
    # But first stop any other check_payment jobs
    for job in context.job_queue.jobs():
        # if the check_payment belongs to the same chat_id
        if job.name == "check_payment" and job.chat_id == update.message.chat_id:
            logger.info(
                "Removing job with name: %s, chat_id: %s before starting a new one",
                job.name,
                job.chat_id,
            )
            job.schedule_removal()

    # now start checking payment run every 10 seconds until 3 minutes have passed
    context.job_queue.run_repeating(
        check_payment,
        data=context.user_data,
        chat_id=update.callback_query.message.chat_id,
        interval=10,
        first=30,
        last=300,
        job_kwargs={"misfire_grace_time": 30},
    )
    return context.user_data.get(CURRENT_STATE, END)


async def check_payment(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Check the payment status."""
    # get job queue
    job_queue = context.job_queue
    for job in job_queue.jobs():
        logger.info("job: %s", job)

    logger.info("Checking payment status.")

    p = context.job.data.get(PAYMENT)
    task_id = context.job.data.get("task_id")

    try:
        if p.is_payment_success():

            logger.info("Payment is successful. Creating ticket.")
            # await context.bot.send_message(chat_id=context.job.chat_id, text=text)
            if p.ticket_reservation():

                logger.info("ticket: %s", p.ticket_reservation_info)
                logger.info("Stopping keep_seat_lock.")
                redis_client.set(task_id, 1, ex=600)

                task = AsyncResult(task_id)
                task.revoke(timeout=30, terminate=True)

                logger.info("Removing this job: %s", context.job.name)
                context.job.schedule_removal()

                logger.info("TICKET RESERVATION IS SUCCESSFUL.")
                logger.info("TICKET: %s", p.ticket_reservation_info)
                text = (
                    f"Ticket is created successfully.\n"
                    f"pnrNo: {p.ticket_reservation_info.get("biletRezOzetList")[0].get("pnrNO")}\n"
                )
                await context.bot.send_message(
                    chat_id=context.job.chat_id,
                    text=text,
                )
                # context.job.data[TRIP] = None

    except ValueError as exc:
        logger.error("%s", exc)
        if "hata" in exc.args[0]:
            logger.info("Sending error message to user.")
            await context.bot.send_message(
                chat_id=context.job.chat_id, text=exc.args[0]
            )
            context.job.schedule_removal()
    except requests.exceptions.RequestException as rexc:
        logger.error("%s", rexc)


async def set_passenger(
    update: Update, context: ContextTypes.DEFAULT_TYPE, mernis_check=True
) -> Passenger:
    """Wrapper for init_passenger. Handles exceptions. See: init_passenger()"""
    try:
        logger.info("init_passenger")
        init_passenger(update, context, mernis_check)

    except KeyError as feature:
        logger.error("KeyError: %s", feature)
        await update.message.reply_text(
            f"{feature} is required, please update your information first."
        )
        return context.user_data.get(CURRENT_STATE, END)

    except ValueError as exc:
        logger.error("ValueError: %s", exc)
        await update.message.reply_text(
            "Mernis verification failed. Please update your information first.",
        )
        return context.user_data.get(CURRENT_STATE, END)

    except requests.exceptions.HTTPError as exc:
        logger.error("HTTPError: %s", exc)
        await update.message.reply_text(
            "Mernis verification failed. Please update your information first.",
        )
        return context.user_data.get(CURRENT_STATE, END)


def init_passenger(_: Update, context: ContextTypes.DEFAULT_TYPE, mernis_check=True):
    """Handle the /init_passenger command. Sets user_data[PASSENGER]."""
    # get the message coming from command

    # make sure all the required information is provided
    for feature in FEATURE_HELP_MESSAGES:
        if context.user_data.get(feature) is None:
            logger.info("KeyError: %s", feature)
            raise KeyError(feature)

    match context.user_data.get("seat_type"):
        case "Business":
            seat_type = Seat.BUSS
        case "Economy":
            seat_type = Seat.ECO
        case "Any":
            seat_type = Seat.ANY
        case _:
            seat_type = Seat.ANY

    match context.user_data.get("tariff"):
        case "Tam":
            tariff = Tariff.TAM
        case "Tsk":
            tariff = Tariff.TSK
        case _:
            tariff = Tariff.TAM

    # create a passenger object
    passenger = Passenger(
        tckn=context.user_data["tckn"],
        name=context.user_data["name"],
        surname=context.user_data["surname"],
        birthday=context.user_data["birthday"],
        email=context.user_data["email"],
        phone=context.user_data["phone"],
        sex=context.user_data["sex"],
        seat_type=seat_type,
        tariff=tariff,
        credit_card_no=context.user_data["credit_card_no"],
        credit_card_ccv=context.user_data["credit_card_ccv"],
        credit_card_exp=context.user_data["credit_card_exp"],
    )
    # sometimes mernis check fails, so we need to retry
    if mernis_check:
        TripSearchApi.is_mernis_correct(passenger)

    logger.info("Setting context passenger object.")
    context.user_data[PASSENGER] = passenger
    if context.user_data.get(TRIP):
        logger.info("Setting trip.passenger object.")
        context.user_data.get(TRIP).passenger = passenger


async def selecting_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Select the tariff."""
    logger.info("Selecting tariff.")
    # set this to ADDING_PERSONAL_INFO to return to the previous state
    context.user_data[PREVIOUS_STATE] = ADDING_PERSONAL_INFO
    context.user_data[CURRENT_STATE] = SELECTING_TARIFF
    context.user_data[CURRENT_FEATURE] = update.callback_query.data
    text = "Select your tariff."
    keyboard = InlineKeyboardMarkup(TARIFF_MENU_BUTTONS)
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    return SELECTING_TARIFF


async def selecting_seat_type(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Select the seat type."""
    logger.info("Selecting seat type.")
    # set this to ADDING_PERSONAL_INFO to return to the previous state
    context.user_data[PREVIOUS_STATE] = ADDING_PERSONAL_INFO
    context.user_data[CURRENT_STATE] = SELECTING_SEAT_TYPE
    context.user_data[CURRENT_FEATURE] = update.callback_query.data
    text = "Select your seat type."
    keyboard = InlineKeyboardMarkup(SEAT_TYPE_MENU_BUTTONS)
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    return SELECTING_SEAT_TYPE


async def selecting_sex(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Select sex"""
    logger.info("Selecting sex.")
    context.user_data[PREVIOUS_STATE] = ADDING_PERSONAL_INFO
    context.user_data[CURRENT_STATE] = SELECTING_SEX
    context.user_data[CURRENT_FEATURE] = update.callback_query.data
    text = "Select your sex."
    keyboard = InlineKeyboardMarkup(SEX_MENU_BUTTONS)
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    return SELECTING_SEX


async def reset_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Reset the search task."""

    logger.info("Resetting search.")
    keyboard = InlineKeyboardMarkup(SEARCH_MENU_BUTTONS)
    text = ""
    removed_task = await remove_user_task(context)
    removed_queued_jobs = await remove_queued_jobs(context)

    if update.callback_query.data == "reset_search":
        text = "Search has been reset."
        if context.user_data.get(TRIP):
            context.user_data.get(TRIP).reset_reservation_data()

    elif update.callback_query.data == "stop_search":
        if removed_task or removed_queued_jobs:
            text = "Search has been stopped."
        else:
            text = "No task in progress to cancel."

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    return context.user_data.get(CURRENT_STATE, END)


async def remove_user_task(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove the user jobs and tasks."""

    tasks = await get_user_task(context.user_data.get("task_id"))
    if tasks:
        task_id = context.user_data.get("task_id")
        for task in tasks:
            logger.info("Revoking task with id: %s", task_id)
            task = AsyncResult(task_id)
            task.revoke(terminate=True)
            logger.warning("SETTING TASK_ID: None")
        context.user_data["task_id"] = None
        return True
    return False


async def remove_queued_jobs(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove the queued jobs."""
    if len(context.job_queue.jobs()) > 0:
        for job in context.job_queue.jobs():
            job.schedule_removal()
        return True
    return False


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


async def print_state(_: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Print the current state."""

    logger.info("current_state: %s", context.user_data.get(CURRENT_STATE))
    logger.info("previous_State: %s", context.user_data.get(PREVIOUS_STATE))
    trip = context.user_data.get(TRIP)
    payment = context.user_data.get(PAYMENT, None)

    text = f"{trip.lock_end_time if trip else None}"
    logger.info("payment: %s", payment)
    logger.info("trip: %s", trip)
    logger.info("lock_end_time: %s", text)
    return context.user_data.get(CURRENT_STATE, END)


async def print_trip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Print the current state."""
    trip = context.user_data.get(TRIP)
    passenger = context.user_data.get(PASSENGER)
    logger.info("trip: %s", trip)
    logger.info("trip.passenger: %s", trip.passenger)
    logger.info("passenger: %s", passenger)
    if trip is not None:
        reply_text = (
            f"From: {trip.from_station}\n"
            f"To: {trip.to_station}\n"
            f"From Date: {trip.from_date}\n"
            f"To Date: {trip.to_date}\n"
            f"Tariff: {context.user_data.get('tariff')}\n"
            f"Seat Type: {context.user_data.get('seat_type')}\n"
        )
        await update.message.reply_text(text=reply_text)
    return context.user_data.get(CURRENT_STATE, END)


async def get_set_current_trip(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Get the current trip from the task and set it to context.user_data."""

    # get task from task and set it to context.user_data

    logger.info("get_set_current_trip")
    i = celery_app.control.inspect()
    active_tasks = i.active()
    tasks = [t for task in active_tasks.values() for t in task]
    logger.info("tasks: %s", tasks)

    for task in tasks:
        task_ = AsyncResult(task["id"])
        redis_client.set(task["id"], 1, ex=60)
        result = task_.get()
        trip = pickle.loads(result)
        context.user_data[TRIP] = trip
        context.job_queue.run_once(
            keep_seat_lock, 3, data=context.user_data, chat_id=update.message.chat_id
        )
        return context.user_data.get(CURRENT_STATE, END)
    return context.user_data.get(CURRENT_STATE, END)


async def check_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Check the status of the task."""
    i = celery_app.control.inspect()
    text = "You have no running task."
    task_id = context.user_data.get("task_id")
    # log job queue
    jobs = context.job_queue.jobs()
    logger.info("Job queue: %s, len: %s", jobs, len(jobs))
    logger.info("task_id: %s", task_id)
    if task_id is not None:
        active_tasks = i.active()
        logger.info("active_tasks len: %s", len(active_tasks.values()))
        for task in active_tasks.values():

            for t in task:
                logger.info("active_task name: %s", t["name"])
                logger.info("active_task id: %s", t["id"])
                if t["id"] == task_id:
                    task_ = AsyncResult(task_id)
                    logger.info("task name: %s", t["name"])
                    task_name = t["name"].split(".")[2]
                    text = f"You have currently running a task: {
                        task_name}, status: {task_.status}."
                    break
    await update.message.reply_text(text=text)
    return context.user_data.get(CURRENT_STATE, END)


async def start_res(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the search process."""
    keyboard = InlineKeyboardMarkup(SEARCH_MENU_BUTTONS)
    await update.callback_query.answer()

    task_id = context.user_data.get("task_id")
    trip = context.user_data.get(TRIP)
    chat_id = update.callback_query.message.chat_id

    if trip is None:
        await update.callback_query.edit_message_text(
            text="No trip is configured yet. Please search for a trip first.",
            reply_markup=keyboard,
        )
        return context.user_data.get(CURRENT_STATE, END)
    elif task_id:
        tasks = await get_user_task(task_id)
        if tasks:
            await update.callback_query.edit_message_text(
                text="You already have a task in progress",
                reply_markup=keyboard,
            )
            return context.user_data.get(CURRENT_STATE, END)
        else:
            # just stale task_id, log it
            logger.warning(
                "No task found associated with task_id: %s",
                context.user_data["task_id"],
            )

    await update_trip_lock_end_time(trip, chat_id)
    if not trip.is_reservation_expired:
        text = (
            f"*{trip.empty_seat_json['koltukNo']}* in vagon *{trip.empty_seat_json['vagonSiraNo']}*"
            f"is already reserved. Seat lock will expire at: *{trip.lock_end_time}*"
        )
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        return context.user_data.get(CURRENT_STATE, END)

    if available_workers() < 1:
        await update.callback_query.edit_message_text(
            text="No worker available. Please try again later.",
            reply_markup=keyboard,
        )
        return context.user_data.get(CURRENT_STATE, END)

    await set_passenger(update, context)
    # run the search job and accompanying check_search_status job
    context.job_queue.run_once(
        start_search,
        3,
        data=context.user_data,
        chat_id=chat_id,
        job_kwargs={"misfire_grace_time": 60},
    )
    context.job_queue.run_repeating(
        check_search_status,
        first=30,
        interval=60,
        data=context.user_data,
        chat_id=chat_id,
        job_kwargs={"misfire_grace_time": 60},
    )
    return context.user_data.get(CURRENT_STATE, END)


async def search_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the search menu."""
    context.user_data[IN_PROGRESS] = True
    context.user_data[CURRENT_STATE] = SEARCH_MENU
    text = "Select your search option."
    keyboard = InlineKeyboardMarkup(SEARCH_MENU_BUTTONS)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    return SEARCH_MENU


async def search_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Check the search status."""
    task_id = context.user_data.get("task_id")
    keyboard = InlineKeyboardMarkup(SEARCH_MENU_BUTTONS)

    jobs = context.job_queue.jobs()
    text = ""
    if jobs:
        text += "Queued Jobs\n"
        for job in jobs:
            text += f"  {job.name}\n"
    else:
        text += "No queued jobs\n"

    if task_id:
        tasks = await get_user_task(task_id)
        if tasks:
            text += "Active Tasks\n"
            for task in tasks:
                name = task["name"].split(".")[-1]  # get the last part of the task name
                text += f"  {name}\n"
        else:
            text += "No active tasks\n"
    else:
        text += "No active tasks\n"
    text = text.strip()
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return context.user_data.get(CURRENT_STATE, END)


async def get_user_task(task_id: str) -> list[dict] | None:
    """Get the user task."""
    i = celery_app.control.inspect()
    tasks = [t for task in i.active().values() for t in task if t["id"] == task_id]
    if tasks:
        return tasks
    return None


async def update_trip_lock_end_time(trip: Trip, chat_id: int) -> None:
    """Update the trip lock end time."""
    logger.info("Updating trip lock end time.")
    chat_data = redis_client.get(str(chat_id))
    logger.info("Successfully connected to redis.")

    if chat_data:
        chat_data = json.loads(chat_data)
        lock_end_time = datetime.strptime(chat_data["lock_end_time"], trip.time_format)
        trip.lock_end_time = lock_end_time
        logger.info("Trip lock end time updated.")
    else:
        logger.info("No chat_data found.")


########################################################################################
# create a test function that starts a job that runs every 10 seconds
async def test_job(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Test the job."""
    try:
        await update.callback_query.answer()
        chat_id = update.callback_query.message.chat_id
    except AttributeError:
        chat_id = update.message.chat_id

    for i in range(1):
        job = context.job_queue.run_repeating(
            callback=check_search_status,
            first=0,
            interval=10,
            data=context.user_data,
            chat_id=chat_id,
        )
    # wait until the job is actually executed
    return context.user_data.get(CURRENT_STATE, END)


# create test_job_callback that sends a message to the user
async def test_job_callback(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Test the job callback."""
    logger.info("test_job_callback")
    task_id = context.job.data.get("task_id")
    task_ = AsyncResult(task_id)
    logger.info("task_: %s", task_)

    return context.job.data.get(CURRENT_STATE, END)


async def start_test_check_payment(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Start the test check_payment."""
    context.job_queue.run_repeating(
        check_payment,
        data=context.user_data,
        chat_id=update.message.chat_id,
        interval=10,
        first=0,
        last=300,
        job_kwargs={"misfire_grace_time": 30},
    )
    return context.user_data.get(CURRENT_STATE, END)


async def test_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Test the celery task."""
    # create test_task celery task and print its id
    task = run_indefinete_task.delay()
    # set the task_id to the context
    logger.info("SETTING TASK_ID: %s", task.id)
    # context.job.data["task_id"] = task.id
    # logger.info("task_id: %s", context.job.data["task_id"])
    return context.user_data.get(CURRENT_STATE, END)


async def test_wait_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Test the wait command."""
    logger.info("test_wait_command for user: %s", update.message.chat_id)
    await asyncio.sleep(100)
    return context.user_data.get(CURRENT_STATE, END)


async def send_redis_key(_: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send the redis key."""
    # get chat_id
    stop_task_id = context.user_data.get("task_id")

    redis_client.set(stop_task_id, 1, ex=600)
    logger.info("stop_task_id: %s", stop_task_id)
    return context.user_data.get(CURRENT_STATE, END)


async def check_payment_test(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Check the payment status."""
    # chat_id = context.job.data.get("chat_id")
    logger.info("chat_data: %s", context.job.chat_id)

    logger.info("TEST METHOD.Sleeping for 60 seconds.")
    asyncio.sleep(60)
    return context.job.data.get(CURRENT_STATE, END)


async def print_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Print the user data."""
    logger.info("user_data: %s", context.user_data)
    logger.info("--------------key, value----------------")
    for key, value in context.user_data.items():
        logger.info("%s: %s", key, value)
    return context.user_data.get(CURRENT_STATE, END)
