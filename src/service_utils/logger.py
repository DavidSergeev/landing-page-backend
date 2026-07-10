import logging
import src.resources.constants as constant


def get_logger(name: str =__file__, level: int = logging.INFO) -> logging.Logger:
    """Return a configured logger with a consistent format."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(fmt=constant.LOG_FORMAT, datefmt=constant.DATE_FORMAT))
        logger.addHandler(handler)

    logger.setLevel(level)
    logger.propagate = False
    return logger
