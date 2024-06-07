""" Telegram bot functions. """

import asyncio
import logging
import pickle
import time
from datetime import datetime, timedelta
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
    test_task_,
)
from tasks.trip import Trip
from tasks.trip_search import TripSearchApi
from constants import *  # pylint: disable=wildcard-import, unused-wildcard-import


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handlers = [logging.FileHandler("bot_data/logs/bot.log"), logging.StreamHandler()]
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
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Back", callback_data=str(BACK))]]
    )
    context.user_data[IN_PROGRESS] = True
    context.user_data[CURRENT_STATE] = SHOWING_TRIP_INFO
    trip = context.user_data.get(TRIP)
    if trip is None:
        text = "No trip is configured."
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return SHOWING_TRIP_INFO

    trip.update_fields()
    if trip.is_seat_reserved is False:
        text = (
            f"From: {trip.from_station}\n"
            f"To: {trip.to_station}\n"
            f"From Date: {trip.from_date}\n"
            f"To Date: {trip.to_date}\n"
            "Seat is not reserved yet or reservation is expired."
        )
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return SHOWING_TRIP_INFO
    else:
        time_diff = trip.lock_end_time - datetime.now()
        time_diff = time_diff.total_seconds() // 60
        text = (
            f"From: {trip.from_station}\n"
            f"To: {trip.to_station}\n"
            f"From Date: {trip.from_date}\n"
            f"To Date: {trip.to_date}\n"
            f"Reserved Vagon: {trip.empty_seat_json.get('vagonSiraNo')}\n"
            f"Reserved Seat: {trip.empty_seat_json.get('koltukNo')}\n"
            f"Remaining Reserve Time: {time_diff} min.\n"
        )
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
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


async def start_res(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the reservation process."""
    task_id = context.user_data.get("task_id")
    trip = context.user_data.get(TRIP)

    if trip is None:
        await update.message.reply_text("Please search for a trip first.")
        return context.user_data.get(CURRENT_STATE, END)
    elif task_id is not None:
        logger.info("checking task with task_id: %s", task_id)
        i = celery_app.control.inspect()
        tasks = [t for task in i.active().values() for t in task if t["id"] == task_id]

        for task in tasks:
            if task["id"] == task_id:
                logger.info("found celery task with task_id: %s", task_id)
                await update.message.reply_text(
                    f"You already have already have a task in progress: {task['name']}"
                )
                return context.user_data.get(CURRENT_STATE, END)
            else:
                # just stale task_id
                logger.info("No active task with id: %s", context.user_data["task_id"])
    # if trip.koltuk_lock_id_list is not empty and lock time is not passed
    elif trip.koltuk_lock_id_list and trip.lock_end_time > datetime.now() - timedelta(
        seconds=60
    ):
        text = f"{trip.empty_seat_json['koltukNo']} in vagon {trip.empty_seat_json['vagonSiraNo']
                                                              } is already reserved. Issue command /res or /reset_search to start over. lock_end_time: {trip.lock_end_time}"
        await update.message.reply_text(text=text)
        return context.user_data.get(CURRENT_STATE, END)

    await set_passenger(update, context)
    passenger = context.user_data.get(PASSENGER)
    # maybe user directly calls this method, so trip passenger is None
    if passenger is not None:
        logger.info("Setting trip.passenger")
        trip.passenger = passenger

    logger.info("user_trip: %s", trip)
    chat_id = update.message.chat_id
    # run the callback_1 function after 3 seconds once

    context.job_queue.run_once(
        start_search,
        1,
        data=context.user_data,
        chat_id=chat_id,
        job_kwargs={"misfire_grace_time": 30},
    )

    # runa job every 10 seconds
    context.job_queue.run_repeating(
        check_search_status,
        first=30,
        interval=60,
        data=context.user_data,
        chat_id=chat_id,
        job_kwargs={"misfire_grace_time": 30},
    )
    jobs = context.job_queue.jobs()
    logger.info("Job queue: %s, len: %s", jobs, len(jobs))
    return context.user_data.get(CURRENT_STATE, END)


async def start_search(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Callback for the reservation process."""
    task_id = context.job.data.get("task_id")
    trip = context.job.data.get(TRIP)

    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=f"BEEEP, starting to search for trip with id {
            trip.from_station} to {trip.to_station} on {trip.from_date}.",
    )
    await asyncio.sleep(2)

    if task_id:
        # get active tasks
        i = celery_app.control.inspect()
        tasks = [t for task in i.active().values() for t in task if t["id"] == task_id]
        for task in tasks:

            logger.info("Found celery task with id: %s", task_id)
            await context.bot.send_message(
                chat_id=context.job.chat_id,
                text=f"Oops, You already have a running task in progress: {task['name']}",
            )
            return context.job.data.get(CURRENT_STATE, END)

    logger.info("trip: %s, type: %s", trip, type(trip))
    logger.info("trip.passenger: %s", trip.passenger)

    # serialize the trip object
    trip_ = pickle.dumps(trip)
    # start the celery task
    task = find_trip_and_reserve.delay(trip_)
    # save the task id to the context
    logger.info("SETTING TASK_ID: %s", task.id)
    context.job.data["task_id"] = task.id
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text="Search task started.",
    )

    return context.job.data.get(CURRENT_STATE, END)


async def check_search_status(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Check the status of the task."""
    task_id = context.job.data.get("task_id")
    task_ = None
    if task_id is None:
        await context.bot.send_message(
            chat_id=context.job.chat_id,
            text="No search task in progress. Removing job.",
        )
        context.job.schedule_removal()
        return context.job.data.get(CURRENT_STATE, END)

    # try active tasks first
    i = celery_app.control.inspect()
    active_tasks = i.active()
    logger.info("active_tasks: %s", len(active_tasks))
    for task in active_tasks.values():
        for t in task:
            logger.info("task_name : %s", t["name"])
            if t["name"] != "tasks.celery_tasks.find_trip_and_reserve":
                await context.bot.send_message(
                    chat_id=context.job.chat_id,
                    text="No search task in progress. Removing job.",
                )
                context.job.schedule_removal()
                return context.job.data.get(CURRENT_STATE, END)
            elif t["id"] == task_id:
                logger.info("Found celery task with id: %s", task_id)
                task_ = AsyncResult(task_id)

    # maybe task finished before we checked active tasks, so query the result
    if task_ is None:
        logger.info("task is None.")
        task_ = AsyncResult(task_id)

    if task_.ready():
        logger.info("Task is ready")
        if not task_.successful():
            # get the exception
            logger.info("Task failed.")
            await context.bot.send_message(
                chat_id=context.job.chat_id,
                text="Search task failed. Please try again.",
            )
            context.job.schedule_removal()

        result = task_.get()
        my_trip = pickle.loads(result)
        context.job.data[TRIP] = my_trip

        dtime = datetime.strptime(my_trip.trip_json["binisTarih"], my_trip.time_format)
        dtime = datetime.strftime(dtime, my_trip.output_time_format)

        await context.bot.send_message(
            chat_id=context.job.chat_id,
            text=f"Seat {my_trip.empty_seat_json['koltukNo']} in vagon {
                my_trip.empty_seat_json['vagonSiraNo']} is reserved for trip {dtime}",
        )
        await context.bot.send_message(
            chat_id=context.job.chat_id,
            text="Keeping the seat lock until you progress to payment.",
        )
        logger.warning("SETTING TASK_ID: None")
        context.job.data["task_id"] = None
        logger.info("Revoking task with id: %s", task_id)
        task_.revoke()

        logger.info("Starting job keep_seat_lock.")
        context.job_queue.run_once(
            keep_seat_lock,
            3,
            data=context.job.data,
            chat_id=context.job.chat_id,
            job_kwargs={"misfire_grace_time": 60},
        )
        context.bot.send_message(
            chat_id=context.job.chat_id,
            text="Keeping the seat locked.",
        )

        logger.info("Removing job with name: %s", context.job.name)
        # remove this job
        context.job.schedule_removal()

        jobs = context.job_queue.jobs()
        logger.info("Job queue: %s", jobs)

    return context.job.data.get(CURRENT_STATE, END)


async def keep_seat_lock(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Keep the seat lock until the user progresses to payment."""
    trip = context.job.data.get(TRIP)
    task = keep_reserving_seat.delay(pickle.dumps(trip))
    logger.info("Setting task_id to context.user_data")
    # save the task id to the context
    logger.warning("SETTING TASK_ID: %s", task.id)
    context.job.data["task_id"] = task.id
    return context.job.data.get(CURRENT_STATE, END)


async def proceed_to_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Proceed to payment."""
    # get currently running tasks
    update.callback_query.answer()
    keyboard = InlineKeyboardMarkup(SEARCH_MENU_BUTTONS)

    if context.user_data.get(TRIP) is None:
        text = "No trip is configured yet. Please search for a trip first."
        logger.info(text)
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return context.user_data.get(CURRENT_STATE, END)

    i = celery_app.control.inspect()
    active_tasks = i.active()
    task_id = context.user_data.get("task_id")
    logger.info("task_id: %s", task_id)

    tasks = [t for task in active_tasks.values() for t in task if t["id"] == task_id]

    for task in tasks:

        if task["name"] == "tasks.celery_tasks.find_trip_and_reserve":
            logger.info("You still have a task in progress.")
            update.callback_query.edit_message_text(
                text="You still have an ongoing search in progress.",
                reply_markup=keyboard,
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

            logger.info("Trip from keep_reserving_seat task: %s", trip)
            logger.info("Setting trip to context.user_data.")

            context.user_data[TRIP] = trip
            # keep the seat lock
            job = context.job_queue.run_once(
                keep_seat_lock,
                0,
                data=context.user_data,
                chat_id=update.message.chat_id,
                job_kwargs={"misfire_grace_time": 60},
            )

            # wait until job is actually started

    trip = context.user_data.get(TRIP)
    # dont allow to proceed to payment if the seat lock time is about to expire
    if trip.is_reservation_expired:
        text = "We cannot proceed to payment. Seat lock is expired or not reserved yet."
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        logger.info(text)

    else:
        # set the passenger object, for if the user has changed some information
        await update.callback_query.edit_message_text(
            "Confirming passenger information."
        )
        await asyncio.sleep(2)
        await set_passenger(update, context)
        await update.callback_query.edit_message_text("Proceeding to payment.")
        await asyncio.sleep(2)
        logger.info("We can proceed to payment. Everything looks fine.")
        # set the passenger object for trip
        trip.passenger = context.user_data.get(PASSENGER)

        p = Payment()
        logger.info("Setting payment object to context.user_data[PAYMENT]")
        context.user_data[PAYMENT] = p
        p.trip = trip
        logger.info("Passenger: %s", trip.passenger)

        try:
            await update.callback_query.edit_message_text("Confirming ticket price.")
            await asyncio.sleep(2)
            p.set_price()
            await update.callback_query.edit_message_text("Setting payment url.")
            await asyncio.sleep(2)
            p.set_payment_url()
        except ValueError as exc:
            # propably credit card information is not correct
            await update.callback_query.edit_message_text(
                text=f"{exc}", reply_markup=keyboard
            )
            return context.user_data.get(CURRENT_STATE, END)

        await update.callback_query.edit_message_text(
            f' Here is your <a href="{p.current_payment_url}">Payment Link</a>',
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
            data=[context.user_data, update.message],
            chat_id=update.message.chat_id,
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

    logger.info("task_id: %s", task_id)
    logger.info("p.trip.passenger: %s", p.trip.passenger.name)

    try:
        if p.is_payment_success():

            text = "Payment is successful. Creating ticket."
            await context.bot.send_message(chat_id=context.job.chat_id, text=text)
            logger.info("Payment is successful. Creating ticket.")

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
                await context.bot.send_message(
                    chat_id=context.job.chat_id,
                    text=f"Ticket is created. {p.ticket_reservation_info}",
                )

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
    return context.job.data.get(CURRENT_STATE, END)


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

    context.user_data[PASSENGER] = passenger
    logger.info("passenger object set to context.user_data[PASSENGER].")
    logger.info("passenger: %s.", context.user_data[PASSENGER])


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
    await update.callback_query.answer()

    logger.info("Resetting search.")
    keyboard = InlineKeyboardMarkup(SEARCH_MENU_BUTTONS)

    await update.callback_query.edit_message_text(
        text="Stopping tasks and jobs...", reply_markup=keyboard
    )
    await remove_user_job(update, context)

    if update.callback_query.data == "reset_search":
        if context.user_data.get(TRIP):
            await update.callback_query.edit_message_text(
                text="Clearing trip reservation data.", reply_markup=keyboard
            )
            await asyncio.sleep(3)
            context.user_data.get(TRIP).reset_reservation_data()

    await update.callback_query.edit_message_text(text="Done.", reply_markup=keyboard)
    return context.user_data.get(CURRENT_STATE, END)


async def remove_user_job(_: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Remove the user jobs and tasks."""
    logger.info("Removing user job.")

    for job in context.job_queue.jobs():
        job.schedule_removal()

    if context.user_data.get("task_id"):
        task_id = context.user_data.get("task_id")
        logger.info("Revoking task with id: %s", task_id)
        task = AsyncResult(task_id)
        task.revoke(terminate=True)
        logger.warning("SETTING TASK_ID: None")
        context.user_data["task_id"] = None
    else:
        logger.info("No task_id found. Sleeping for 3 seconds.")
        await asyncio.sleep(3)

    return context.user_data.get(CURRENT_STATE, END)


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


async def search_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the search menu."""
    context.user_data[IN_PROGRESS] = True
    context.user_data[CURRENT_STATE] = SEARCH_MENU
    text = "Select your search option."
    keyboard = InlineKeyboardMarkup(SEARCH_MENU_BUTTONS)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    return SEARCH_MENU


########################################################################################
# create a test function that starts a job that runs every 10 seconds
async def test_job(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Test the job."""
    update.callback_query.answer()
    chat_id = update.callback_query.message.chat_id
    logger.info("Starting test job.")
    for i in range(1):
        logger.info("RUNNING THE %sth TIME", i)
        job = context.job_queue.run_repeating(
            test_job_callback,
            first=0,
            interval=5,
            data=context.user_data,
            chat_id=chat_id,
            job_kwargs={"misfire_grace_time": 1},
        )
        time.sleep(10)
        logger.info("Job id: %s", job.id)
    # wait until the job is actually executed
    return context.user_data.get(CURRENT_STATE, END)


# create test_job_callback that sends a message to the user
async def test_job_callback(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Test the job callback."""
    logger.info("Running test job callback.")
    await asyncio.sleep(100)
    await context.bot.send_message(
        chat_id=context.job.chat_id, text="This is a test job callback."
    )
    return context.job.data.get(CURRENT_STATE, END)


async def start_test_check_payment(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Start the test check_payment."""
    for r in range(1):
        logger.info("RUNNING THE %sth TIME", r)
        context.job_queue.run_repeating(
            check_payment_test,
            data=context.user_data,
            chat_id=update.message.chat_id,
            interval=10,
            first=0,
            last=300,
            job_kwargs={"misfire_grace_time": 3},
        )
    return context.user_data.get(CURRENT_STATE, END)


async def test_task(_: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Test the celery task."""
    # create test_task celery task and print its id
    task = test_task_.delay()
    # set the task_id to the context
    context.user_data["task_id"] = task.id
    logger.info("task_id: %s", task.id)
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
