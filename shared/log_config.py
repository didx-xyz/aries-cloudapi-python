import copy
import os
import sys

import orjson
from loguru import logger

STDOUT_LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
FILE_LOG_LEVEL = os.getenv("FILE_LOG_LEVEL", "DEBUG").upper()
ENABLE_FILE_LOGGING = os.getenv("ENABLE_FILE_LOGGING", "").upper() == "TRUE"
DISABLE_COLORIZE_LOGS = os.getenv("DISABLE_COLORIZE_LOGS", "").upper() == "TRUE"
ENABLE_SERIALIZE_LOGS = os.getenv("ENABLE_SERIALIZE_LOGS", "").upper() == "TRUE"

colorize = not DISABLE_COLORIZE_LOGS
serialize = ENABLE_SERIALIZE_LOGS

# Create a mapping of module name to color
color_map = {
    "app": "blue",
    "endorser": "yellow",
    "trustregistry": "magenta",
    "webhooks": "green",
}


# Define custom formatter for this module
def formatter_builder(color: str):
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        f"<{color}>{{name}}</{color}>:<{color}>{{function}}</{color}>:<{color}>{{line}}</{color}> | "
        "<level>{message}</level> | "
        "{extra[body]}"
    )


# Define custom formatter for serialized logs
def _serialize_record(record):
    # Handle exceptions as default
    exception = record["exception"]

    if exception is not None:
        exception = {
            "type": None if exception.type is None else exception.type.__name__,
            "value": exception.value,
            "traceback": bool(exception.traceback),
        }

    # Define subset of serialized record - combining message + extra into the text field
    message = record["message"]
    extra = record["extra"].get("body")
    message_with_body = f"{message} | {extra}"
    subset = {
        "text": message_with_body,
        "record": {
            # "elapsed": {
            #     "repr": record["elapsed"],
            #     "seconds": record["elapsed"].total_seconds(),
            # },
            "exception": exception,
            # "extra": record["extra"],
            "file": {"name": record["file"].name, "path": record["file"].path},
            "function": record["function"],
            "level": {
                "icon": record["level"].icon,
                "name": record["level"].name,
                "no": record["level"].no,
            },
            "line": record["line"],
            # "message": record["message"],
            "module": record["module"],
            "name": record["name"],
            "process": {"id": record["process"].id, "name": record["process"].name},
            "thread": {"id": record["thread"].id, "name": record["thread"].name},
            "time": {"repr": record["time"], "timestamp": record["time"].timestamp()},
        },
    }

    record["extra"]["serialized"] = orjson.dumps(subset, default=str).decode("utf-8")
    return "{extra[serialized]}\n"


# This will hold our logger instances
loggers = {}


def get_log_file_path(main_module_name) -> str:
    # The absolute path of this file's directory
    CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))

    # Move up one level to get to the project root directory
    BASE_DIR = os.path.dirname(CONFIG_DIR)

    # Define the logging dir with
    LOG_DIR = os.path.join(BASE_DIR, f"logs/{main_module_name}")
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

    if not serialize:
        # Get the color for this module and build formatter
        color = color_map.get(main_module_name, "blue")  # Default to blue if no mapping
        formatter = formatter_builder(color)

        # Log to stdout
        logger_.add(
            sys.stdout,
            level=STDOUT_LOG_LEVEL,
            format=formatter,
            colorize=colorize,
        )
    else:  # serialization is enabled:
        logger_.add(
            sys.stdout,
            level=STDOUT_LOG_LEVEL,
            format=_serialize_record,  # Use our custom serialization formatter
        )

    # Log to a file
    if ENABLE_FILE_LOGGING:
        try:
            logger_.add(
                get_log_file_path(main_module_name),
                rotation="00:00",  # new file is created at midnight
                retention="7 days",  # keep logs for up to 7 days
                enqueue=True,  # asynchronous
                level=FILE_LOG_LEVEL,
                format=formatter_builder("blue"),
                serialize=serialize,
            )
        except PermissionError:
            logger_.warning(
                "Permission error caught when trying to create log file. "
                "Continuing without file logging for `{}` in `{}`",
                name,
                main_module_name,
            )

    # Store the logger in the dictionary
    loggers[main_module_name] = logger_

    # Return a logger bound with the full name including the submodule
    return logger_.bind(name=name)
