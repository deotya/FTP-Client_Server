"""
Module for managing and saving logs for the FTP client
"""

import os
import time
import datetime
import socket
from pathlib import Path

class FTPLogger:
    """
    Class for managing FTP connection logs
    """
    
    # Static variable to store the log file of the current application
    current_app_log_file = None
    current_app_log_path = None
    
    def __init__(self, log_dir="ftp_log"):
        """
        Initializes the logger
        
        Args:
            log_dir (str): The directory where logs will be saved
        """
        # Create the absolute path to the log directory
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.log_dir = base_dir / log_dir
        
        # Ensure the directory exists
        self.log_dir.mkdir(exist_ok=True)
        
        # Initialize the log file if there isn't already one for the current session
        if FTPLogger.current_app_log_file is None:
            self.create_new_log_file()
        else:
            # Use the existing file for the application session
            self.log_file = FTPLogger.current_app_log_file
            self.log_path = FTPLogger.current_app_log_path
            
        self.connection_id = None
        
    def create_new_log_file(self):
        """
        Creates a new log file for the application session
        """
        # Generate timestamp and file name
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        hostname = socket.gethostname()
        
        # Log file name (based on the application's timestamp)
        filename = f"ftp_client_log_{timestamp}.txt"
        self.log_path = self.log_dir / filename
        
        # Open the log file
        self.log_file = open(self.log_path, 'a', encoding='utf-8')
        
        # Save the reference at the class level
        FTPLogger.current_app_log_file = self.log_file
        FTPLogger.current_app_log_path = self.log_path
        
        # Write initialization information
        self.log(f"=== FTP Client Application started at {timestamp} ===")
        self.log(f"Client: {hostname}")
        self.log("="*50)
        
    def start_logging(self, host, port, username):
        """
        Starts a new logging session for a connection
        
        Args:
            host (str): The host to connect to
            port (int): The port used for the connection
            username (str): The username for authentication
        """
        # Generate timestamp and create a unique ID for the connection
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.connection_id = f"{timestamp}_{host}_{port}"
        
        # Write connection information to the current log file
        self.log(f"=== FTP Connection initiated at {timestamp} ===")
        self.log(f"Host: {host}")
        self.log(f"Port: {port}")
        self.log(f"User: {username}")
        self.log("="*50)
    
    def log(self, message):
        """
        Writes a message to the log file
        
        Args:
            message (str): The message to write to the log
        """
        if not self.log_file:
            # If the file is not initialized, create a new one
            self.create_new_log_file()
        
        # Add timestamp to the message
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        
        # Write to the file
        self.log_file.write(log_message + "\n")
        self.log_file.flush()  # Ensure immediate writing
        
    def close(self):
        """
        Closes the connection session in the log (does not close the file)
        """
        if self.log_file and self.connection_id:
            # Add a final message for the connection
            self.log(f"=== FTP Connection ended ===")
            self.connection_id = None
            
    @classmethod
    def close_app_log(cls):
        """
        Closes the application's log file
        """
        if cls.current_app_log_file:
            # Add a final message
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cls.current_app_log_file.write(f"[{timestamp}] === FTP Client Application closed ===\n")
            
            # Close the file
            cls.current_app_log_file.close()
            cls.current_app_log_file = None
            cls.current_app_log_path = None
            
    def __del__(self):
        """
        Ensures the connection session is closed when the object is destroyed
        """
        self.close() 