import copy
import os
import sys

from loguru import logger

STDOUT_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
FILE_LOG_LEVEL = "DEBUG"

# Define custom formatter for this module
formatter = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<blue>{name}</blue>:<blue>{function}</blue>:<blue>{line}</blue> | "
    "<level>{message}</level> - "
    "{extra[body]}"
)

# This will hold our logger instances
loggers = {}


def get_log_file_path() -> str:
    # The absolute path of this file's directory
    CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))

    # Get parent directory of 'config', which is the module name (app, endorser, etc)
    module_name = os.path.basename(os.path.dirname(CONFIG_DIR))

    # Move up two levels to get to the project root directory
    BASE_DIR = os.path.dirname(os.path.dirname(CONFIG_DIR))

    # Define the logging dir with
    LOG_DIR = os.path.join(BASE_DIR, f"logs/{module_name}")
    return os.path.join(LOG_DIR, "{time:YYYY-MM-DD}.log")


# Export this logger
def get_logger(name: str):
    # Get the main module name
    main_module_name = name.split(".")[0]

    # Check if a logger for this name already exists
    if main_module_name in loggers:
        return loggers[main_module_name].bind(name=name)

    # Remove default handler from global logger
    logger.remove()

    # Make a deep copy of the global logger
    logger_ = copy.deepcopy(logger)

    logger_.configure(extra={"body": ""})  # Default values for extra args

    # Log to stdout
    logger_.add(sys.stdout, level=STDOUT_LOG_LEVEL, format=formatter, colorize=True)

    # Log to a file
    logger_.add(
        get_log_file_path(),
        rotation="00:00",  # new file is created at midnight
        retention="7 days",  # keep logs for up to 7 days
        enqueue=True,  # asynchronous
        level=FILE_LOG_LEVEL,
        format=formatter,
    )

    # Configure email notifications
    # logger_.add("smtp+ssl://username:password@host:port", level="CRITICAL")

    # Store the logger in the dictionary
    loggers[main_module_name] = logger_

    # Return a logger bound with the full name including the submodule
    return logger_.bind(name=name)
