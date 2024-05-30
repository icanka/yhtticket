import logging

logger = logging.getLogger(__name__)

default_settings = {
    "log_path": "bot_data/logs/",
}

__version__ = "0.0.1"
__author__ = "izzet can karakus"
__license__ = "MIT"


def configure():
    """Configure the bot with the given settings."""
    default_settings.update(default_settings)
    globals().update(default_settings)


if __name__ == "__main__":
    configure()
