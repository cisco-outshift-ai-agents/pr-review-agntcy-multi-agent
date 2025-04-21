# Copyright 2025 Cisco Systems, Inc. and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os

# Constants for log levels
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
DEFAULT_LOGGER_NAME = "alfred-prcoach"


def setup_logging(name: str = DEFAULT_LOGGER_NAME, log_level: int = logging.INFO, log_type: str = "console", log_file: str = ""):
    """
    Set up logging based on the log_type parameter.

    Parameters:
    - log_type (str): Type of logging. Options are 'console', 'file', or 'google_cloud'.
    - log_file (str): Path to log file for file-based logging; ignored for other log types.

    Returns:
    - logger (logging.Logger): Configured logger instance.
    """
    # Create a logger
    global logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.propagate = False
    level_name = logging.getLevelName(log_level)

    # Clear any existing handlers (useful for reconfiguration)
    logger.handlers.clear()

    # Common formatter
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)

    if log_type == "file":
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(f"Configured File Logging to '{log_file}', level: {level_name}")

    elif log_type == "console":
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.info(f"Configured Console Logging, level: {level_name}")

    else:
        logger.warning(f"Unknown log_type '{log_type}'; defaulting to console logging")
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.info(f"Configured Console Logging, level: {level_name}")

    return logger


def setup_console_logging(name: str = DEFAULT_LOGGER_NAME, log_level: int = logging.INFO):
    """
    Set up console logging.

    Parameters:
    - log_level (int): Logging level for the logger.

    Returns:
    - logger (logging.Logger): Configured logger instance.
    """
    return setup_logging(name=name, log_level=log_level, log_type="console")


def setup_file_logging(name: str = DEFAULT_LOGGER_NAME, log_level: int = logging.INFO, log_file: str = "app.log"):
    """
    Set up file logging.

    Parameters:
    - log_level (int): Logging level for the logger.
    - log_file (str): Path to log file for file-based logging.

    Returns:
    - logger (logging.Logger): Configured logger instance.
    """
    return setup_logging(name=name, log_level=log_level, log_type="file", log_file=log_file)


def setup_default_logging():
    log_level_str = os.getenv("LOG_LEVEL", "INFO")
    log_level = logging.getLevelName(log_level_str)

    return setup_console_logging(log_level=log_level)


# Initialize the default logger
logger = setup_default_logging()
