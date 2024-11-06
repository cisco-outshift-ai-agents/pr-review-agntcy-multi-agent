import logging

# Constants for log levels
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

def setup_logging(name: str = "", log_level: int = logging.INFO, log_type: str = "console", log_file: str = ""):
    """
    Set up logging based on the log_type parameter.
    
    Parameters:
    - log_type (str): Type of logging. Options are 'console', 'file', or 'google_cloud'.
    - log_file (str): Path to log file for file-based logging; ignored for other log types.
    
    Returns:
    - logger (logging.Logger): Configured logger instance.
    """
    # Create a logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.propagate = False
    
    # Clear any existing handlers (useful for reconfiguration)
    logger.handlers.clear()
    
    # Common formatter
    formatter = logging.Formatter(LOG_FORMAT)

    if log_type == "file":
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(f"Configured File Logging to '{log_file}'")
    
    elif log_type == "console":
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.info("Configured Console Logging")
    
    else:
        logger.warning(f"Unknown log_type '{log_type}'; defaulting to console logging")
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.info("Configured Console Logging")

    return logger

def setup_console_logging(name: str = "", log_level: int = logging.INFO):
    """
    Set up console logging.
    
    Parameters:
    - log_level (int): Logging level for the logger.
    
    Returns:
    - logger (logging.Logger): Configured logger instance.
    """
    return setup_logging(name=name, log_level=log_level, log_type="console")

def setup_file_logging(name: str = "", log_level: int = logging.INFO, log_file: str = "app.log"):
    """
    Set up file logging.
    
    Parameters:
    - log_level (int): Logging level for the logger.
    - log_file (str): Path to log file for file-based logging.
    
    Returns:
    - logger (logging.Logger): Configured logger instance.
    """
    return setup_logging(name=name, log_level=log_level, log_type="file", log_file=log_file)