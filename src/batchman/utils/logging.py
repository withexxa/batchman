import logging
import sys

# Configure the batchman logger with both console and file handlers.

# Default configuration: show INFO and above
logger = logging.getLogger("batchman")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Console output configuration: show WARNING and above
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File output configuration: show DEBUG and above
file_handler = logging.FileHandler("batchman.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Prevent the logger from propagating to the root logger
logger.propagate = False
