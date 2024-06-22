""" This module is the main module of the project. It creates the bot and runs it. """

from datetime import datetime
import logging
import os
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    InlineQueryHandler,
    PicklePersistence,
    CallbackQueryHandler,
    ConversationHandler,
)
from apscheduler.events import (
    EVENT_JOB_SUBMITTED,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_ERROR,
    EVENT_JOB_MISSED,
    EVENT_JOB_MAX_INSTANCES,
)
from update_processor import CustomUpdateProcessor
from scheduler_listeners import (
    submit_listener,
    mis_listener,
    max_instances_listener,
    job_executed_listener,
)
from telegram_bot import *  # pylint: disable=wildcard-import, unused-wildcard-import
from constants import *  # pylint: disable=wildcard-import


logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handlers = [logging.FileHandler("../bot_data/logs/main.log"), logging.StreamHandler()]
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s"
)

# get bot token from environment
if os.getenv("BOT_TOKEN") is None:
    logger.error("BOT_TOKEN is not set in the environment")
    raise ValueError("BOT_TOKEN is not set in the environment")

BOT_TOKEN = os.environ.get("BOT_TOKEN")

for handler in handlers:
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def main() -> None:
    """Run the bot."""
    logger.info("Starting the bot")
    # get PERSISTENCE_FILE from environment
    if os.getenv("PERSISTENCE_FILE_PATH") is None:
        logger.error("Persistence file path is not set in the environment")
        raise ValueError("PERSISTENCE_FILE_PATH is not set in the environment")
    my_persistance = PicklePersistence(filepath=os.environ.get("PERSISTENCE_FILE_PATH"))
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .arbitrary_callback_data(True)
        .persistence(persistence=my_persistance)
        .concurrent_updates(
            CustomUpdateProcessor(max_concurrent_updates=BOT_MAX_CONCURRENT_UPTADES)
        )
        .build()
    )

    scheduler_configuration = {
        "max_instances": APS_SCHEDULER_MAX_INSTANCES,
        "coalesce": True,
        "misfire_grace_time": 10,  # default misfire time
    }
    scheduler = app.job_queue.scheduler
    scheduler.configure()
    scheduler.configure(
        job_defaults=scheduler_configuration, **app.job_queue.scheduler_configuration
    )
    scheduler.add_listener(submit_listener, EVENT_JOB_SUBMITTED)
    scheduler.add_listener(mis_listener, EVENT_JOB_MISSED)
    scheduler.add_listener(max_instances_listener, EVENT_JOB_MAX_INSTANCES)
    scheduler.add_listener(job_executed_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    fallback_handlers = [
        CommandHandler("stop", stop),
        CommandHandler("res", res),
        CallbackQueryHandler(handle_datetime_type, pattern=datetime),
        MessageHandler(filters.COMMAND, unknown_command),
    ]

    sex_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(selecting_sex, pattern="^sex$")],
        states={
            SELECTING_SEX: [
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
            # save_input returnes this state so we need to map it
            ADDING_PERSONAL_INFO: ADDING_PERSONAL_INFO,
        },
    )

    seat_type_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(selecting_seat_type, pattern="^seat_type$")],
        states={
            SELECTING_SEAT_TYPE: [
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
            # save_input returnes this state so we need to map it
            ADDING_PERSONAL_INFO: ADDING_PERSONAL_INFO,
        },
    )

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
            # save_input returnes this state so we need to map it
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
                seat_type_conv_handler,
                sex_conv_handler,
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

    search_menu_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(search_menu, pattern=f"^{SEARCH_MENU}$")],
        states={
            SEARCH_MENU: [
                CallbackQueryHandler(start_res, pattern="^start_search$"),
                CallbackQueryHandler(reset_search, pattern="^reset_search$"),
                CallbackQueryHandler(reset_search, pattern="^stop_search$"),
                CallbackQueryHandler(search_status, pattern="^search_status$"),
                CallbackQueryHandler(
                    proceed_to_payment, pattern="^proceed_to_payment$"
                ),
                CallbackQueryHandler(back, pattern=f"^{BACK}$"),
            ],
        },
        fallbacks=fallback_handlers,
        map_to_parent={
            # End the child conversation and return to SELECTING_MAIN_ACTION state
            BACK: SELECTING_MAIN_ACTION,
            UNIMPLEMENTED: UNIMPLEMENTED,
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
                search_menu_conv_handler,
                CallbackQueryHandler(show_info, pattern=f"^{SHOWING_INFO}$"),
                CallbackQueryHandler(show_trip_info, pattern=f"^{SHOWING_TRIP_INFO}$"),
                CallbackQueryHandler(end, pattern=f"^{END}$"),
            ],
            SHOWING_INFO: [
                CallbackQueryHandler(start, pattern=f"^{BACK}$"),
            ],
            SHOWING_TRIP_INFO: [
                CallbackQueryHandler(start, pattern=f"^{BACK}$"),
            ],
            UNIMPLEMENTED: [
                CallbackQueryHandler(start, pattern=f"^{BACK}$"),
            ],
        },
        fallbacks=fallback_handlers,
    )

    inline_caps_handler = InlineQueryHandler(inline_funcs)
    datetime_type_handler = CallbackQueryHandler(handle_datetime_type, pattern=datetime)
    res_handler = CommandHandler("res", res)
    unknown_command_handler = MessageHandler(filters.COMMAND, unknown_command)

    app.add_handlers(
        [
            main_conv_handler,
            inline_caps_handler,
            res_handler,
            datetime_type_handler,
            unknown_command_handler,
        ]
    )
    app.run_polling()


if __name__ == "__main__":
    main()
