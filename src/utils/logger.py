def get_logger(name: str):
    return logging.getLogger(name)

import logging
import os
import sys

def get_logger(name: str):
    """
    Initializes and returns a logger that writes to both a file and the console.
    This version automatically creates the 'logs' directory if it doesn't exist.
    """
    # Define the path for the logs directory relative to this file's location.
    # This makes the path robust, regardless of where the script is run from.
    logs_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    
    # Create the logs directory if it does not already exist.
    os.makedirs(logs_dir, exist_ok=True)
    
    log_file_path = os.path.join(logs_dir, 'app.log')
    
    # --- Set up the logger ---
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Prevent duplicate handlers if the logger is called multiple times
    if not logger.handlers:
        # File handler
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)
        
        # Add handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        
    return logger
    