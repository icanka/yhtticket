from datetime import datetime
import logging
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
logging.getLogger("httpx").setLevel(logging.WARNING)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    for key, value in context.user_data.items():
        print(f"{key}: {value}")
        if isinstance(value, Passenger):
            print(value.birthday)
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!"
    )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Echo the user message."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=update.message.text
    )


async def caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /caps command."""
    text_caps = " ".join(context.args).upper()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)


async def res(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /res command."""
    pass


async def put(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /put command."""
    logging.info("context.args: %s", context.args)
    logging.info("value: %s", update.message.text.partition(" "))
    key = str(uuid4())
    value = update.message.text.partition(" ")[2]
    passenger = Passenger(
        "123456789", "can", "karakus", "birthday", "test@test.com", "05340771521", "E"
    )

    context.user_data[key] = passenger

    await update.message.reply_text(f"Stored {value} with key {key}")


async def init_passenger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /init_passenger command."""
    pass






























# Stages

START_ROUTES, END_ROUTES = range(2)

# Callback data

ONE, TWO, THREE, FOUR = range(4)


async def starttt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send message on `/start`."""

    # Get user that sent /start and log his name

    user = update.message.from_user

    # Build InlineKeyboard where each button has a displayed text

    # and a string as callback_data

    # The keyboard is a list of button rows, where each row is in turn

    # a list (hence `[[...]]`).

    keyboard = [
        [
            InlineKeyboardButton("1", callback_data=str(ONE)),
            InlineKeyboardButton("2", callback_data=str(TWO)),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send message with text and appended InlineKeyboard

    await update.message.reply_text(
        "Start handler, Choose a route", reply_markup=reply_markup
    )

    # Tell ConversationHandler that we're in state `FIRST` now

    return START_ROUTES


async def start_over(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt same text & keyboard as `start` does but not as new message"""

    # Get CallbackQuery from Update

    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed

    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery

    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("1", callback_data=str(ONE)),
            InlineKeyboardButton("2", callback_data=str(TWO)),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Instead of sending a new message, edit the message that

    # originated the CallbackQuery. This gives the feeling of an

    # interactive menu.

    await query.edit_message_text(
        text="Start handler, Choose a route", reply_markup=reply_markup
    )

    return START_ROUTES


async def one(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show new choice of buttons"""

    query = update.callback_query

    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("3", callback_data=str(THREE)),
            InlineKeyboardButton("4", callback_data=str(FOUR)),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="First CallbackQueryHandler, Choose a route", reply_markup=reply_markup
    )

    return START_ROUTES


async def two(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show new choice of buttons"""

    query = update.callback_query

    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("1", callback_data=str(ONE)),
            InlineKeyboardButton("3", callback_data=str(THREE)),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="Second CallbackQueryHandler, Choose a route", reply_markup=reply_markup
    )

    


async def three(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show new choice of buttons. This is the end point of the conversation."""

    query = update.callback_query

    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("Yes, let's do it again!", callback_data=str(ONE)),
            InlineKeyboardButton("Nah, I've had enough ...", callback_data=str(TWO)),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="Third CallbackQueryHandler. Do want to start over?",
        reply_markup=reply_markup,
    )

    # Transfer to conversation state `SECOND`

    return END_ROUTES


async def four(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show new choice of buttons"""

    query = update.callback_query

    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("2", callback_data=str(TWO)),
            InlineKeyboardButton("3", callback_data=str(THREE)),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="Fourth CallbackQueryHandler, Choose a route", reply_markup=reply_markup
    )

    return START_ROUTES


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Returns `ConversationHandler.END`, which tells the

    ConversationHandler that the conversation is over.

    """

    query = update.callback_query

    await query.answer()

    await query.edit_message_text(text="See you next time!")

    return ConversationHandler.END


def main() -> None:

    my_persistance = PicklePersistence(filepath="my_persistence")

    app = (
        ApplicationBuilder()
        .token("***REMOVED***")
        .persistence(persistence=my_persistance)
        .build()
    )


    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    app.add_handler(echo_handler)

    caps_handler = CommandHandler("caps", caps)
    app.add_handler(caps_handler)

    inline_caps_handler = InlineQueryHandler(inline_funcs)
    app.add_handler(inline_caps_handler)

    #app.add_handler(CommandHandler("starttt", starttt))

    app.add_handler(CommandHandler("put", put))
    pprint(app.user_data)
    pprint(app.chat_data)

    # print all user_data

    conv_handler = ConversationHandler(

        entry_points=[CommandHandler("start", starttt)],

        states={

            START_ROUTES: [

                CallbackQueryHandler(one, pattern="^" + str(ONE) + "$"),

                CallbackQueryHandler(two, pattern="^" + str(TWO) + "$"),

                CallbackQueryHandler(three, pattern="^" + str(THREE) + "$"),

                CallbackQueryHandler(four, pattern="^" + str(FOUR) + "$"),

            ],

            END_ROUTES: [

                CallbackQueryHandler(start_over, pattern="^" + str(ONE) + "$"),

                CallbackQueryHandler(end, pattern="^" + str(TWO) + "$"),

            ],

        },

        fallbacks=[CommandHandler("starttt", starttt)],

    )


    # Add ConversationHandler to application that will be used for handling updates

    app.add_handler(conv_handler)


    app.run_polling()


if __name__ == "__main__":
    main()
