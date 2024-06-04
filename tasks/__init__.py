import logging


logger = logging.getLogger("tasks")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("bot_data/logs/tasks.log")
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)
