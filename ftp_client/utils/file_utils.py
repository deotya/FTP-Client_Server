"""
Utilities for managing files and directories
"""

import os
import shutil
import datetime
import stat
import re
import platform
from PyQt5.QtWidgets import QMessageBox

def get_file_size_str(size):
    """Converts a file size into a readable format"""
    try:
        size = int(size)
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size/1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size/(1024*1024):.1f} MB"
        else:
            return f"{size/(1024*1024*1024):.1f} GB"
    except:
        return str(size)

def get_file_type(path):
    """Returns the type of the file (directory or file)"""
    if os.path.isdir(path):
        return "directory"
    return "file"

def get_local_files(directory):
    """
    Retrieves a list of files and directories from the specified local path
    Returns a list of dictionaries with file information
    """
    files_data = []
    
    # Add .. for navigating up
    files_data.append({
        'name': '..',
        'type': 'directory',
        'size': '0',
        'modified': '',
        'path': os.path.abspath(os.path.join(directory, os.pardir))
    })
    
    try:
        items = os.listdir(directory)
        for item in items:
            item_path = os.path.join(directory, item)
            
            # Get file statistics
            try:
                stats = os.stat(item_path)
                size = stats.st_size
                modified_time = datetime.datetime.fromtimestamp(stats.st_mtime)
                modified_str = modified_time.strftime("%d.%m.%Y %H:%M:%S")
                
                # Determine the type of the item
                item_type = "directory" if os.path.isdir(item_path) else "file"
                
                files_data.append({
                    'name': item,
                    'type': item_type,
                    'size': str(size),
                    'modified': modified_str,
                    'path': item_path
                })
            except Exception as e:
                print(f"Error retrieving information for {item_path}: {str(e)}")
    except Exception as e:
        print(f"Error listing directory {directory}: {str(e)}")
        
    return files_data

def create_directory(path):
    """Creates a directory at the specified path"""
    try:
        os.makedirs(path, exist_ok=True)
        return True, "Directory created successfully"
    except Exception as e:
        return False, f"Error creating directory: {str(e)}"
        
def delete_file(path):
    """Deletes a file at the specified path"""
    try:
        if os.path.isfile(path):
            os.remove(path)
            return True, "File deleted successfully"
        else:
            return False, "The specified path is not a file"
    except Exception as e:
        return False, f"Error deleting file: {str(e)}"
        
def delete_directory(path):
    """Deletes a directory and all its contents"""
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
            return True, "Directory deleted successfully"
        else:
            return False, "The specified path is not a directory"
    except Exception as e:
        return False, f"Error deleting directory: {str(e)}"
        
def rename_item(old_path, new_path):
    """Renames a file or directory"""
    try:
        shutil.move(old_path, new_path)
        return True, "Item renamed successfully"
    except Exception as e:
        return False, f"Error renaming item: {str(e)}"
        
def copy_file(src, dst):
    """Copies a file from source to destination"""
    try:
        # Check if the destination is a directory
        if os.path.isdir(dst):
            # If so, append the file name to the destination path
            dst = os.path.join(dst, os.path.basename(src))
            
        # Copy the file
        shutil.copy2(src, dst)
        return True, "File copied successfully"
    except Exception as e:
        return False, f"Error copying file: {str(e)}"
        
def get_drives():
    """Returns a list of all available disk drives"""
    if platform.system() == "Windows":
        # For Windows, list all drive letters from A to Z
        drives = []
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = f"{letter}:"
            if os.path.exists(drive):
                drives.append(drive)
        return drives
    else:
        # For Linux/Unix, return only /
        return ["/"]
        
def safe_path_join(base, *paths):
    """
    Safely joins paths, preventing relative path injection
    that could lead to directory traversal
    """
    # Ensure all path components are safe
    safe_parts = []
    for path in paths:
        # Remove any component that tries to traverse up (..)
        if path == ".." or path.startswith("../") or path.startswith("/.."):
            continue
        safe_parts.append(path)
    
    # Join the base path with the safe parts
    result = os.path.join(base, *safe_parts)
    
    # Ensure the result is within the base directory
    if not os.path.abspath(result).startswith(os.path.abspath(base)):
        return base
    
    return result

def confirm_delete(parent, item_type, item_name):
    """Requests user confirmation for deletion"""
    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Warning)
    msg_box.setWindowTitle("Delete Confirmation")
    msg_box.setText(f"Are you sure you want to delete the {item_type} '{item_name}'?")
    msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg_box.setDefaultButton(QMessageBox.No)
    return msg_box.exec_() == QMessageBox.Yes
        
def get_parent_directory(path):
    """Returns the parent directory of the specified path"""
    return os.path.abspath(os.path.join(path, os.pardir)) 