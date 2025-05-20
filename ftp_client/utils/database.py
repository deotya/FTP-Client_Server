"""
Module for managing the SQLite database for storing FTP connections
"""

import os
import sqlite3
from pathlib import Path

class ConnectionDatabase:
    """Class for managing the FTP connections database"""
    
    def __init__(self, db_path=None):
        """
        Initializes the database for FTP connections
        
        Args:
            db_path (str, optional): Path to the database file. 
                                     If not specified, it will be created in the application directory.
        """
        if db_path is None:
            # Use a standard directory for storing application data
            app_data_dir = Path.home() / "AppData" / "Local" / "RemoteDesktop"
            os.makedirs(app_data_dir, exist_ok=True)
            self.db_path = str(app_data_dir / "ftp_connections.db")
        else:
            self.db_path = db_path
            
        self.init_db()
    
    def init_db(self):
        """Initializes the database and creates necessary tables if they do not exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create the table for FTP connections
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ftp_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            connection_type TEXT DEFAULT 'ftp',
            host TEXT NOT NULL,
            port INTEGER NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            key_file TEXT,
            key_passphrase TEXT,
            last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(host, port, username)
        )
        ''')
        
        # Check if we need to add columns for older versions of the database
        cursor.execute("PRAGMA table_info(ftp_connections)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'connection_type' not in column_names:
            cursor.execute("ALTER TABLE ftp_connections ADD COLUMN connection_type TEXT DEFAULT 'ftp'")
            
        if 'key_file' not in column_names:
            cursor.execute("ALTER TABLE ftp_connections ADD COLUMN key_file TEXT")
            
        if 'key_passphrase' not in column_names:
            cursor.execute("ALTER TABLE ftp_connections ADD COLUMN key_passphrase TEXT")
        
        conn.commit()
        conn.close()
    
    def save_connection(self, name, host, port, username, password, connection_type='ftp', key_file=None, key_passphrase=None):
        """
        Saves an FTP/SFTP connection to the database
        
        Args:
            name (str): Connection name
            host (str): Server address
            port (int): Server port
            username (str): Username
            password (str): User password
            connection_type (str): Connection type ('ftp' or 'sftp')
            key_file (str): Path to the private key file (optional)
            key_passphrase (str): Passphrase for the private key (optional)
            
        Returns:
            int: ID of the saved connection
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if the connection already exists
            cursor.execute(
                "SELECT id FROM ftp_connections WHERE host = ? AND port = ? AND username = ?", 
                (host, port, username)
            )
            result = cursor.fetchone()
            
            if result:
                # Update the existing connection
                connection_id = result[0]
                cursor.execute(
                    "UPDATE ftp_connections SET name = ?, password = ?, connection_type = ?, key_file = ?, key_passphrase = ?, last_used = CURRENT_TIMESTAMP WHERE id = ?",
                    (name, password, connection_type, key_file, key_passphrase, connection_id)
                )
            else:
                # Add a new connection
                cursor.execute(
                    "INSERT INTO ftp_connections (name, host, port, username, password, connection_type, key_file, key_passphrase) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (name, host, port, username, password, connection_type, key_file, key_passphrase)
                )
                connection_id = cursor.lastrowid
                
            conn.commit()
            return connection_id
            
        finally:
            conn.close()
    
    def get_connection(self, connection_id):
        """
        Retrieves connection details by ID
        
        Args:
            connection_id (int): Connection ID
            
        Returns:
            dict: Connection details or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT id, name, host, port, username, password, connection_type, key_file, key_passphrase FROM ftp_connections WHERE id = ?", 
                (connection_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "host": row[2],
                    "port": row[3],
                    "username": row[4],
                    "password": row[5],
                    "connection_type": row[6] if len(row) > 6 else "ftp",
                    "key_file": row[7] if len(row) > 7 else None,
                    "key_passphrase": row[8] if len(row) > 8 else None
                }
            return None
        finally:
            conn.close()
    
    def get_all_connections(self):
        """
        Retrieves all saved connections
        
        Returns:
            list: List of dictionaries containing connection details
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT id, name, host, port, username, connection_type, key_file FROM ftp_connections ORDER BY last_used DESC"
            )
            rows = cursor.fetchall()
            
            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "host": row[2],
                    "port": row[3],
                    "username": row[4],
                    "connection_type": row[5] if len(row) > 5 else "ftp",
                    "key_file": row[6] if len(row) > 6 else None
                } 
                for row in rows
            ]
        finally:
            conn.close()
    
    def delete_connection(self, connection_id):
        """
        Deletes an FTP connection by ID
        
        Args:
            connection_id (int): Connection ID
            
        Returns:
            bool: True if successfully deleted, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM ftp_connections WHERE id = ?", (connection_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close() 
    
    def update_last_used(self, connection_id):
        """
        Updates the last used timestamp of a connection
        
        Args:
            connection_id (int): Connection ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE ftp_connections SET last_used = CURRENT_TIMESTAMP WHERE id = ?",
                (connection_id,)
            )
            conn.commit()
        finally:
            conn.close() 