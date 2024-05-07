import logging
from typing import Dict
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


WAITING = ConversationHandler.WAITING
TIMEOUT = ConversationHandler.TIMEOUT
END = ConversationHandler.END

MAIN_CHOOSING, TYPING_REPLY, TYPING_CHOICE = range(3)
reply_keyboard = [
    ["1", "2"],
    ["Done"],
    ["Done"],
    ["Done"],
    ["Done"],
    ["Done"],
    ["Done"],
    ["Done"],
    ["Done"],
    ["Done"],
    ["Done"],
    ["Done"],
    
]

second_reply_keyboard = [
    ["2.1", "2.2"],
    ["Done"]
]

markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
inner_markup = ReplyKeyboardMarkup(second_reply_keyboard, one_time_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! My name is Doctor Botter.",
        reply_markup=markup,
    )

    logger.info("youre now in state MAIN_CHOOSING: %s", MAIN_CHOOSING)
    return MAIN_CHOOSING


async def regular_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data["choice"] = text
    await update.message.reply_text(
        f"Your {text.lower()}? Yes, I would love to hear about that!")

    logger.info("youre now in state TYPING_REPLY: %s", TYPING_REPLY)
    return TYPING_REPLY


async def received_information(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    await update.message.reply_text(
        "You've told me your {}. Thank you for letting me know!".format(text),
        reply_markup=markup,
    )

    logger.info("youre now in state: MAIN_CHOOSING %s", MAIN_CHOOSING)
    return MAIN_CHOOSING


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data: Dict[str, str] = context.user_data
    if "choice" in user_data:
        del user_data["choice"]

    await update.message.reply_text(
        f"Thank you! I hope I can help you again sometime.",
        reply_markup=ReplyKeyboardRemove(),
    )

    logger.info("youre now in state END: %s", ConversationHandler.END)
    return END

async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(update.message.text)
    await update.message.reply_text("I'm sorry, I didn't understand that choice. Please try again.")

    logger.info("TIMEOUT")
    return MAIN_CHOOSING




async def inner_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["previous"] = "inner"
    await update.message.reply_text(
        "Hi! Youre in inner conversation.",
        reply_markup=inner_markup,
    )

    logger.info("youre now in state TYPING_REPLY: %s", TYPING_REPLY)
    return TYPING_REPLY


async def sorry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "I'mmmm sorry, I didn't understand that choice. Please try again.",
        reply_markup=markup,
    )

    logger.info("youre now in state END: %s", END)
    return END




def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token("***REMOVED***").build()


    inner_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^2$"), inner_conversation)],
        states={
                TYPING_REPLY: [
                    MessageHandler(
                    filters.TEXT & ~(filters.COMMAND |
                                     filters.Regex("^Done$")),
                    received_information,
                )
            ],
        },
        
        fallbacks=[MessageHandler(filters.Regex("^Done$"), sorry)],
    )

    # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_CHOOSING: [
                MessageHandler(
                    filters.Regex(
                        "^1$"), regular_choice
                ),
                inner_conv_handler,
            ],
            TYPING_REPLY: [
                MessageHandler(
                    filters.TEXT & ~(filters.COMMAND |
                                     filters.Regex("^Done$")),
                    received_information,
                )
            ],
            ConversationHandler.WAITING: [
                MessageHandler(
                    filters.ALL, timeout
                )
            ],                
        },
        fallbacks=[MessageHandler(filters.Regex("^Done$"), done)],
    )

    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    
    
if __name__ == "__main__":
    main()