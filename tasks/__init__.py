import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s"
)

stream_handler = logging.StreamHandler()
file_handler = logging.FileHandler("bot_data/logs/tasks.log")

logger.addHandler(stream_handler)
logger.addHandler(file_handler)
