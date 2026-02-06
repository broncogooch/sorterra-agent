# =============================================================================
# SHAREPOINT TOOLKIT FOR AGENTS
# =============================================================================
# This file exposes high-level functions for AI Agents to interact with SharePoint.
# It handles authentication automatically using environment variables.

import os
import msal
import json
from dotenv import load_dotenv
from sharepoint_client import SharePointSorter

# Load environment variables once
load_dotenv()

# Global config
SITE_URL = os.getenv("SHAREPOINT_SITE_URL")
CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")
THUMBPRINT = os.getenv("THUMBPRINT")
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH")

def _get_sorter():
    """
    Internal helper to get an authenticated SharePointSorter instance.
    Authentication is handled here so the Agent doesn't need to worry about it.
    """
    if not all([SITE_URL, CLIENT_ID, THUMBPRINT, PRIVATE_KEY_PATH]):
        raise ValueError("Missing environment variables for SharePoint connection.")
    
    return SharePointSorter(
        SITE_URL, 
        CLIENT_ID, 
        thumbprint=THUMBPRINT, 
        private_key_path=PRIVATE_KEY_PATH, 
        tenant_id=TENANT_ID
    )

# =============================================================================
# INSPECTION TOOLS (The "Look" Phase)
# =============================================================================

def list_folder_contents(folder_relative_url):
    """
    Lists all files in a specific SharePoint folder.
    
    Args:
        folder_relative_url (str): The server-relative URL (e.g. /sites/SiteName/Shared Documents/Folder).
        
    Returns:
        list[dict]: A list of file dictionaries containing 'name' and 'serverRelativeUrl'.
    """
    sorter = _get_sorter()
    files = sorter.get_files_in_folder(folder_relative_url)
    return [{"name": f.name, "serverRelativeUrl": f.serverRelativeUrl} for f in files]

def get_folder_hierarchy(folder_relative_url):
    """
    Scans the folder structure to understand the layout (subfolders and files).
    
    Args:
        folder_relative_url (str): The server-relative URL to scan.
        
    Returns:
        dict: A nested dictionary representing the folder structure.
    """
    sorter = _get_sorter()
    return sorter.scan_folder_structure(folder_relative_url)

# =============================================================================
# ACTION TOOLS (The "Act" Phase)
# =============================================================================

def move_document(file_url, destination_folder_url):
    """
    Moves a document to a destination folder.
    
    Args:
        file_url (str): The server-relative URL of the file to move.
        destination_folder_url (str): The server-relative URL of the destination folder.
        
    Returns:
        str: Success message.
    """
    sorter = _get_sorter()
    
    # Ensure destination exists
    sorter.create_folder(destination_folder_url)
    
    # Move
    sorter.move_file(file_url, destination_folder_url)
    return f"Successfully moved {file_url} to {destination_folder_url}"

def secure_move_document(file_url, destination_folder_url, source_permissions_folder_url):
    """
    Moves a document AND copies the permissions from a source folder to that document.
    Use this when moving files out of a secure folder to ensure they remain secure.
    
    Args:
        file_url (str): The file to move.
        destination_folder_url (str): Where to move it.
        source_permissions_folder_url (str): The folder to copy permissions FROM (e.g. 'Secure Uploads').
        
    Returns:
        str: Success message.
    """
    sorter = _get_sorter()
    
    # 1. Read Permissions
    permissions = sorter.get_folder_permissions(source_permissions_folder_url)
    
    # 2. Ensure Dest Exists
    sorter.create_folder(destination_folder_url)
    
    # 3. Move
    sorter.move_file(file_url, destination_folder_url)
    
    # 4. Apply Permissions
    file_name = file_url.split('/')[-1]
    new_file_url = f"{destination_folder_url.rstrip('/')}/{file_name}"
    
    sorter.apply_unique_permissions(new_file_url, permissions)
    return f"Moved {file_name} and applied {len(permissions)} unique permission entries."

def create_directory(folder_url, color_hex=None):
    """
    Creates a folder and optionally sets its color.
    
    Args:
        folder_url (str): The full server-relative path to create.
        color_hex (str, optional): SharePoint color tag (e.g. "1" for Dark Red).
    """
    sorter = _get_sorter()
    sorter.create_folder(folder_url)
    
    if color_hex:
        sorter.set_folder_color(folder_url, color_hex)
        return f"Created folder {folder_url} with color {color_hex}"
    
    return f"Created folder {folder_url}"
