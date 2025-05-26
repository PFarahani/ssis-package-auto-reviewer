import logging
from datetime import datetime
from config.constants import LOG_FORMAT, LOG_FILENAME_FORMAT

def configure_logging() -> logging.Logger:
    """Configure and return a logger with file and console handlers."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = LOG_FILENAME_FORMAT.format(timestamp=timestamp)
    
    logger = logging.getLogger("PackageAutoReview")
    logger.setLevel(logging.DEBUG)

    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # File handler
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # Formatter
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger