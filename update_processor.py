""" Custom Update Processor """
import logging
from typing import Dict, Awaitable
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    BaseUpdateProcessor,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class CustomUpdateProcessor(BaseUpdateProcessor):
    """Simple implementation of a custom update processor that logs the updates."""

    async def do_process_update(self, update: Dict, coroutine: Awaitable[any]) -> None:
        """Sequential processing of updates for the same user.
        This method is called for each update that is received from the Telegram server
        
        We dont want to process multiple updates from the same user concurrently, 
        To not deal with all consequences comes with it.
        
        But we also want to process updates from different users concurrently.
        """
        try:
            user_id = update["message"]["from_user"]["id"]
        except KeyError:
            user_id = None
        if user_id is None:
            return

        # check if a lock for this user ID is already acquired
        if user_id not in self.user_locks:
            # if not, create a new lock and add it to the dictionary
            logger.info("Creating lock for user %s", user_id)
            self.user_locks[user_id] = asyncio.Lock()

        # Get the lock for this user ID
        user_lock = self.user_locks[user_id]

        # Acquire the lock using async with to ensure exclusive access
        async with user_lock:
            try:
                # Simulate some processing time
                logger.info("Processing update for user %s", user_id)
                await asyncio.sleep(30)
                await coroutine
                logger.info("Finished processing update for user %s", user_id)
            except Exception as e:
                logger.error("Error processing update: %s", e, exc_info=True)

    async def initialize(self) -> None:
        logger.info("Initializing update processor")
        self.user_locks = {}

    async def shutdown(self) -> None:
        logger.info("Shutting down update processor")
        self.user_locks = None


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
        .concurrent_updates(MyUpdateProcessor(5))
        .build()
    )

    say_hello_handler = CommandHandler("hi", say_hello)
    application.add_handler(say_hello_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
