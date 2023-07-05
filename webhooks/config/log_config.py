import os
import sys

from loguru import logger

STDOUT_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
FILE_LOG_LEVEL = "DEBUG"

# Remove default handler
logger.remove()

# Define custom formatter
formatter = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<green>{name}</green>:<green>{function}</green>:<green>{line}</green> | "
    "<level>{message}</level> - "
    "{extra[body]}"
)
logger.configure(extra={"body": ""})  # Default values for extra args

# Log to stdout
logger.add(sys.stdout, level=STDOUT_LOG_LEVEL, format=formatter, colorize=True)

# Log to a file
logger.add(
    "./logs/webhooks/{time}.log",
    rotation="00:00",  # new file is created at midnight
    retention="7 days",  # keep logs for up to 7 days
    enqueue=True,  # asynchronous
    level=FILE_LOG_LEVEL,
    format=formatter,
)

# Configure email notifications
# logger.add("smtp+ssl://username:password@host:port", level="CRITICAL")


# Export this logger
def get_logger(name: str):
    return logger.bind(name=name)
