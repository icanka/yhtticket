from datetime import datetime
import logging
from pprint import pprint
import re
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
SELECTING_MAIN_ACTION, ADDING_PERSONAL_INFO, ADDING_CREDIT_CARD_INFO = map(
    chr, range(3))
SHOW_INFO = map(chr, range(3, 4))
STOPPING = map(chr, range(4, 5))
TYPING_REPLY = map(chr, range(5, 6))


TEST = map(chr, range(7, 8))
# SELECTING_LEVEL = map(chr, range(2, 3))
# STOPPING, SHOWING = map(chr, range(3, 5))
# START_OVER = map(chr, range(5, 6))

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
    UNIMPLEMENTED,
) = map(chr, range(10, 23))


FEATURE_HELP_MESSAGES = {
    "birthday": "Please enter your birthday in the format dd/mm/yyyy.",
}


MAIN_MENU_BUTTONS = [
    [
        InlineKeyboardButton(
            "Personal Info", callback_data=str(ADDING_PERSONAL_INFO)),
        InlineKeyboardButton("Credit Card Info",
                             callback_data=str(ADDING_CREDIT_CARD_INFO))
    ],
    [
        InlineKeyboardButton("Show Info", callback_data=str(SHOW_INFO)),
        InlineKeyboardButton("Done", callback_data=str(STOPPING)),
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
        InlineKeyboardButton("Back", callback_data=str(END)),
    ]
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Start the conversation and ask the user about their"""
    text = "Add, update or show your information. To abort, simply type /stop"

    keyboard = InlineKeyboardMarkup(MAIN_MENU_BUTTONS)

    context.user_data[CURRENT_STATE] = SELECTING_MAIN_ACTION

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
    return SELECTING_MAIN_ACTION


async def adding_self(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Add information about the user."""
    context.user_data[CURRENT_STATE] = ADDING_PERSONAL_INFO
    text = "Please provide me with your information."

    keyboard = InlineKeyboardMarkup(PERSON_MENU_BUTTONS)

    if not context.user_data.get(IN_PROGRESS):
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        text = "Got it! What's next?"
        await update.message.reply_text(text=text, reply_markup=keyboard)

    context.user_data[IN_PROGRESS] = False
    return ADDING_PERSONAL_INFO


async def ask_for_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Ask the user for the information."""
    context.user_data[CURRENT_FEATURE] = update.callback_query.data
    text = f"Please provide your {update.callback_query.data}."
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text)
    context.user_data[CURRENT_STATE] = TYPING_REPLY
    return TYPING_REPLY


async def save_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Save the user input."""
    if context.user_data[CURRENT_FEATURE] == "birthday":
        try:
            datetime.strptime(update.message.text, "%d/%m/%Y")
        except ValueError:
            text = FEATURE_HELP_MESSAGES["birthday"]
            await update.message.reply_text(text=text)
            return TYPING_REPLY

    feature = context.user_data[CURRENT_FEATURE]
    try:
        regex: str
        match feature:
            case "birthday":
                regex = r"^(\d{2})/(\d{2})/(\d{4})$")
                datetime.strptime(update.message.text, "%d/%m/%Y")
            case "tckn":
                regex = r"^\d{11}$"
            case "name" | "surname":
                regex = r"^[a-zA-Z]+$"
            case "phone":
                regex = r"^\d{11}$"
            case "sex":
                regex = r"^[E|K]$"
            case "email":
                regex = regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        if not re.fullmatch(regex, update.message.text):
            raise ValueError
    except ValueError:
        text = FEATURE_HELP_MESSAGES[feature]
        await update.message.reply_text(text=text)
        return TYPING_REPLY


    user_data = context.user_data
    user_data[user_data[CURRENT_FEATURE]] = update.message.text
    user_data[IN_PROGRESS] = True
    user_data[CURRENT_FEATURE] = None
    return await adding_self(update, context)


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """End conversation from InlineKeyboardButton."""
    logging.info("End conversation from InlineKeyboardButton. callbackquery_data: %s",
                 update.callback_query.data)

    level = context.user_data[CURRENT_STATE]

    if level == ADDING_PERSONAL_INFO:
        # coming from adding personal info so we are back to start
        # This 'END' state is also mapped to the 'SELECTING_MAIN_ACTION' state in this case
        context.user_data[IN_PROGRESS] = True
        await start(update, context)
    else:
        # coming from start so we are ending the conversation
        text = "See you next time!"
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text)

    context.user_data[CURRENT_STATE] = None
    # log all user_data
    for key, value in context.user_data.items():
        logging.info(f"key: {key}, value: {value}")

    return END


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End conversation by command."""
    await update.message.reply_text("Okay, bye!")
    return STOPPING


async def unimplemented(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return END to end the conversation."""
    text = "This feature is not implemented yet."

    buttons = [[InlineKeyboardButton(
        text="Back", callback_data=str(UNIMPLEMENTED))]]
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    context.user_data[IN_PROGRESS] = True
    return UNIMPLEMENTED


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return END to end the conversation."""
    text = "Sorry, I didn't understand that command."
    if context.user_data.get(CURRENT_FEATURE):
        text = FEATURE_HELP_MESSAGES[context.user_data[CURRENT_FEATURE]]
    state = context.user_data[CURRENT_STATE]
    await update.message.reply_text(text=text)
    if state:
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

    my_persistance = PicklePersistence(filepath="my_persistence")

    app = (
        ApplicationBuilder()
        .token("***REMOVED***")
        .persistence(persistence=my_persistance)
        .build()
    )

    adding_self_conv_handler = ConversationHandler(
        entry_points = [CallbackQueryHandler(
            adding_self, pattern=f"^{ADDING_PERSONAL_INFO}$")],
        states = {
            ADDING_PERSONAL_INFO: [
                CallbackQueryHandler(ask_for_input, pattern=f"^name$"),
                CallbackQueryHandler(ask_for_input, pattern=f"^surname$"),
                CallbackQueryHandler(ask_for_input, pattern=f"^tckn$"),
                CallbackQueryHandler(ask_for_input, pattern=f"^birthday$"),
                CallbackQueryHandler(ask_for_input, pattern=f"^sex$"),
                CallbackQueryHandler(ask_for_input, pattern=f"^phone$"),
                CallbackQueryHandler(ask_for_input, pattern=f"^email$"),
                CallbackQueryHandler(end, pattern=f"^{END}$"),
            ],
            TYPING_REPLY: [
                # BIRTHDAY
                MessageHandler(filters.Regex(
                    r"^(\d{2})/(\d{2})/(\d{4})$") & (~filters.COMMAND), save_input),
                # TCKN
                MessageHandler(filters.Regex(r"^\d{11}$") & (
                    ~filters.COMMAND), save_input),
                MessageHandler(filters.TEXT & (
                    ~filters.COMMAND), unknown_command),
                # MessageHandler(filters.COMMAND, unknown_command),
            ],
        },
        fallbacks = [CommandHandler("stop", stop)],
        map_to_parent = {
            # End the child conversation and return to SELECTING_MAIN_ACTION state
            END: SELECTING_MAIN_ACTION,
            # End the whole conversation from within the child conversation.
            STOPPING: END,
        },
    )

    main_conv_handler = ConversationHandler(
        entry_points = [CommandHandler("start", start)],
        states = {
            SELECTING_MAIN_ACTION: [
                adding_self_conv_handler,
                # CallbackQueryHandler(adding_self, pattern=f"^{ADDING_PERSONAL_INFO}$"),
                CallbackQueryHandler(
                    unimplemented, pattern=f"^{ADDING_CREDIT_CARD_INFO}$"),
                CallbackQueryHandler(unimplemented, pattern=f"^{SHOW_INFO}$"),
                CallbackQueryHandler(end, pattern=f"^{STOPPING}$"),
            ],
            UNIMPLEMENTED: [
                CallbackQueryHandler(start, pattern=f"^{UNIMPLEMENTED}$"),
            ],

        },
        fallbacks = [
            CommandHandler("stop", stop),
            MessageHandler(filters.TEXT & (~filters.COMMAND), unknown_command),
        ],
    )

    app.add_handler(main_conv_handler)

    # echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    # app.add_handler(echo_handler)

    # caps_handler = CommandHandler("caps", caps)
    # app.add_handler(caps_handler)

    # inline_caps_handler = InlineQueryHandler(inline_funcs)
    # app.add_handler(inline_caps_handler)

    # app.add_handler(CommandHandler("put", put))
    # pprint(app.user_data)
    # pprint(app.chat_data)

    app.run_polling()


if __name__ == "__main__":
    main()
