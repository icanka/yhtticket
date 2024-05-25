""" This module is the main module of the project. It creates the bot and runs it. """

from datetime import datetime
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
from update_processor import CustomUpdateProcessor
from telegram_bot import *
from constants import *


def main() -> None:
    """Run the bot."""
    my_persistance = PicklePersistence(filepath="my_persistence")

    app = (
        ApplicationBuilder()
        .token("***REMOVED***")
        .arbitrary_callback_data(True)
        .persistence(persistence=my_persistance)
        .concurrent_updates(CustomUpdateProcessor(3))
        .build()
    )
    fallback_handlers = [
        CommandHandler("stop", stop),
        CommandHandler("res", res),
        CommandHandler("print_state", print_state),
        CallbackQueryHandler(handle_datetime_type, pattern=datetime),
        MessageHandler(filters.COMMAND, unknown_command),
    ]

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

    proceed_to_payment_handler = CommandHandler(
        "proceed_to_payment", proceed_to_payment
    )
    app.add_handler(proceed_to_payment_handler)

    set_passenger_handler = CommandHandler("set_passenger", set_passenger)
    app.add_handler(set_passenger_handler)

    check_search_status_handler = CommandHandler(
        "check_search_status", check_search_status
    )
    app.add_handler(check_search_status_handler)

    get_set_current_trip_handler = CommandHandler(
        "get_set_current_trip", get_set_current_trip
    )
    app.add_handler(get_set_current_trip_handler)

    unknown_command_handler = MessageHandler(filters.COMMAND, unknown_command)
    app.add_handler(unknown_command_handler)

    # app.add_handler(CommandHandler("put", put))
    # pprint(app.user_data)
    # pprint(app.chat_data)

    app.run_polling()


if __name__ == "__main__":
    main()
