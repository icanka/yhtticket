from datetime import datetime
import logging
import regex
from pprint import pprint
from uuid import uuid4
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
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
from trip import Passenger, list_stations

# set httpx logger to warning
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext.ConversationHandler").setLevel(logging.DEBUG)


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


# async def init_passenger(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Handle the /init_passenger command."""
#     pass


# states
SELECTING_MAIN_ACTION, ADDING_PERSONAL_INFO, ADDING_CREDIT_CARD_INFO, SHOWING_INFO, BACK, TYPING_REPLY = range(
    0, 6)
END = ConversationHandler.END


# Different constants for this example
(
    SELF,
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
) = range(10, 24)


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
}


MAIN_MENU_BUTTONS = [
    [
        InlineKeyboardButton(
            "Personal Info", callback_data=str(ADDING_PERSONAL_INFO)),
        InlineKeyboardButton("Credit Card Info",
                             callback_data=str(ADDING_CREDIT_CARD_INFO))
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
        InlineKeyboardButton("Phone", callback_data="phone"),
        InlineKeyboardButton("Email", callback_data="email"),
        InlineKeyboardButton("Sex", callback_data="sex"),
        InlineKeyboardButton("Back", callback_data=str(BACK)),
    ]
]

CREDIT_CARD_MENU_BUTTONS = [
    [
        InlineKeyboardButton("Credit Card No", callback_data="credit_card_no"),
        InlineKeyboardButton("CCV", callback_data="credit_card_ccv"),
    ],
    [
        InlineKeyboardButton("Exp", callback_data="credit_card_exp"),
        InlineKeyboardButton("Back", callback_data=str(BACK)),
    ]
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask the user about their"""
    text = "Add, update or show your information. To abort, simply type /stop"

    keyboard = InlineKeyboardMarkup(MAIN_MENU_BUTTONS)

    if context.user_data.get(IN_PROGRESS):
        try:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
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
    text = f"Name: {user_data.get('name', 'Not Provided')}\n" \
        f"Surname: {user_data.get('surname', 'Not Provided')}\n" \
        f"T.C.: {user_data.get('tckn', 'Not Provided')}\n" \
        f"Birthday: {user_data.get('birthday', 'Not Provided')}\n" \
        f"Sex: {user_data.get('sex', 'Not Provided')}\n" \
        f"Phone: {user_data.get('phone', 'Not Provided')}\n" \
        f"Email: {user_data.get('email', 'Not Provided')}\n" \
        f"Credit Card No: {user_data.get('credit_card_no', 'Not Provided')}\n" \
        f"Credit Card CCV: {user_data.get('credit_card_ccv', 'Not Provided')}\n" \
        f"Credit Card Exp: {user_data.get('credit_card_exp', 'Not provided')}\n"
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
        await update.message.reply_text(text=text, reply_markup=keyboard)

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
    text = f"Please provide your {update.callback_query.data}."
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
                re = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
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
    logging.info("state: BACK")
    return BACK


async def unimplemented(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return END to end the conversation."""
    text = "This feature is not implemented yet."

    buttons = [[InlineKeyboardButton(
        text="Back", callback_data=str(BACK))]]
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
    await update.message.reply_text(text=text)
    if state:
        print(state)
        logging.info("state: -%s-", state)
        return state
    return END


# async def test_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Return END to end the conversation."""
#     text = "You are in the test method."
#     logging.info("You are in the test method. callback_query_data: %s",
#                  update.callback_query.data)
#     await update.callback_query.answer()
#     await update.callback_query.edit_message_text(text=text)
#     return TEST

def main() -> None:
    """Run the bot."""
    my_persistance = PicklePersistence(filepath="my_persistence")

    app = (
        ApplicationBuilder()
        .token("***REMOVED***")
        .persistence(persistence=my_persistance)
        .build()
    )

    fallback_handlers = [CommandHandler("stop", stop), MessageHandler(
        filters.COMMAND, unknown_command)]

    adding_self_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            adding_self, pattern=f"^{ADDING_PERSONAL_INFO}$")],
        states={
            ADDING_PERSONAL_INFO: [
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
        entry_points=[CallbackQueryHandler(
            adding_credit_card, pattern=f"^{ADDING_CREDIT_CARD_INFO}$")],
        states={
            ADDING_CREDIT_CARD_INFO: [
                CallbackQueryHandler(
                    ask_for_input, pattern="^credit_card_no$"),
                CallbackQueryHandler(
                    ask_for_input, pattern="^credit_card_ccv$"),
                CallbackQueryHandler(
                    ask_for_input, pattern="^credit_card_exp$"),
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
                    unimplemented, pattern=f"^{ADDING_CREDIT_CARD_INFO}$"),
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

    # caps_handler = CommandHandler("caps", caps)
    # app.add_handler(caps_handler)

    # app.add_handler(inline_caps_handler)

    # app.add_handler(CommandHandler("put", put))
    # pprint(app.user_data)
    # pprint(app.chat_data)

    app.run_polling()


if __name__ == "__main__":
    main()
