import logging
import os
from datetime import datetime

def setup_logger(name=__name__, log_file=None, level=logging.INFO):
    """
    Set up a logger with console and file handlers.
    
    Parameters:
        name (str): Logger name
        log_file (str): Path to log file. If None, uses a default path with timestamp
        level (int): Logging level
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Set default log file with timestamp if not provided
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(logs_dir, f"{timestamp}.log")
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Create console handler and set level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Create file handler and set level
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Add formatter to handlers
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Default logger
logger = setup_logger('ai_classics')
