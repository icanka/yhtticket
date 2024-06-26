""" Custom Update Processor """

import logging
import os
from typing import Dict, Awaitable
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    BaseUpdateProcessor,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handlers = [logging.FileHandler("../bot_data/logs/update_processor.log")]
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s"
)
for handler in handlers:
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# check if AUTH_USER_IDS is set in the environment
if os.environ.get("AUTH_USER_IDS") is None:
    logger.error("AUTH_USER_IDS is not set in the environment")
    raise ValueError("AUTH_USER_IDS is not set in the environment")


class CustomUpdateProcessor(BaseUpdateProcessor):
    """Simple implementation of a custom update processor that logs the updates."""

    async def do_process_update(self, update: Dict, coroutine: Awaitable[any]) -> None:
        """Sequential processing of updates for the same user.
        This method is called for each update that is received from the Telegram server

        We dont want to process multiple updates from the same user concurrently,
        to not to deal with all consequences comes with it such as race conditions.

        But we also want to process updates from different users concurrently.
        """
        user_id = update.effective_user.id
        if user_id not in self.auth_user_ids:
            logger.error(
                "Unauthorized user ID found in update: %s", update.effective_user
            )
            coroutine.close()
            return

        if user_id is None:
            logger.error(
                "Cannot process update: No user ID found in update: %s", update
            )
            coroutine.close()
            return

        # check if a lock for this user ID is already acquired
        if user_id not in self.user_locks:
            # if not, create a new lock and add it to the dictionary
            logger.info("Creating new lock for user ID: %s", user_id)
            self.user_locks[user_id] = asyncio.Lock()

        # Get the lock for this user ID
        logger.info("Acquiring lock for user ID: %s", user_id)
        user_lock = self.user_locks[user_id]

        # Acquire the lock using async with to ensure exclusive access
        async with user_lock:
            try:
                logger.info("Processing update: %s", update)
                await coroutine
            except Exception as e:  # pylint: disable=broad-except
                logger.error("Error processing update: %s", e, exc_info=True)
                coroutine.close()
        logger.info("Releasing lock for user ID: %s", user_id)

    def __init__(self, **kwargs) -> None:
        super().__init__(max_concurrent_updates=kwargs.get("max_concurrent_updates", 1))
        print("AUTH_USER_IDS: {}".format(os.environ.get("AUTH_USER_IDS", "")))
        logger.info("AUTH_USER_IDS: %s", os.environ.get("AUTH_USER_IDS", ""))
        self.user_locks = {}
        self.auth_user_ids = [
            int(user_id) for user_id in os.environ.get("AUTH_USER_IDS", "").split(",")
        ]

    async def initialize(self) -> None:
        logger.info("Initializing update processor")

    async def shutdown(self) -> None:
        logger.info("Shutting down update processor")
        self.user_locks = None
        self.auth_user_ids = None


async def say_hello(update: Update, _: ContextTypes) -> None:
    """Send a message when the command /start is issued."""
    user = update.message.from_user
    await update.message.reply_text(f"Hello {user.first_name}!")
    return 0


def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = (
        Application.builder()
        .token("YOUR_TOKEN")
        .concurrent_updates(CustomUpdateProcessor(max_concurrent_updates=3))
        .build()
    )

    say_hello_handler = CommandHandler("hi", say_hello)
    application.add_handler(say_hello_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
