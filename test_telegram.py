import logging
from typing import Dict, Awaitable
import asyncio
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    BaseUpdateProcessor,
)


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class MyUpdateProcessor(BaseUpdateProcessor):
    """Simple implementation of a custom update processor that logs the updates."""

    def __init__(self, max_concurrent_updates: int):
        super().__init__(max_concurrent_updates)
        self.user_locks = {}

    async def do_process_update(self, update: Dict, coroutine: Awaitable[any]) -> None:
        logger.info("PROCESSING UPDATE-----------------------------------")
        user_id = update.get("message", {}).get("from_user", {}).get("id")
        
        if user_id is None:
            logger.info("Update does not contain user information.")
            return

        # check if a lock for this user ID is already acquired
        if user_id not in self.user_locks:
            # if not, create a new lock and add it to the dictionary
            self.user_locks[user_id] = asyncio.Lock()

        # Get the lock for this user ID
        user_lock = self.user_locks[user_id]

        # Acquire the lock using async with to ensure exclusive access
        async with user_lock:
            try:
                # Simulate some processing time
                logger.info("Processing update for user %s", user_id)
                await asyncio.sleep(5)
                await coroutine
            except Exception as e:
                logger.error("Error processing update: %s", e, exc_info=True)


        await asyncio.sleep(5)
        # logger.info(f"Received update: %s", update)
        logger.info("User: %s", update["message"]["from_user"]["id"])
        # logger.info("coroutine: %s", coroutine)
        logger.info("Running coroutine %s, type: %s", coroutine, type(coroutine))
        await coroutine
        logger.info("Finished coroutine")

    async def initialize(self) -> None:
        logger.info("Initializing update processor")

    async def shutdown(self) -> None:
        logger.info("Shutting down update processor")


async def say_hello(update: Update, context: ContextTypes) -> None:
    """Send a message when the command /start is issued."""
    user = update.message.from_user
    await update.message.reply_text(f"Hello {user.first_name}!")
    return 0


def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = (
        Application.builder()
        .token("***REMOVED***")
        .concurrent_updates(MyUpdateProcessor(10))
        .build()
    )

    say_hello_handler = CommandHandler("hi", say_hello)
    application.add_handler(say_hello_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
