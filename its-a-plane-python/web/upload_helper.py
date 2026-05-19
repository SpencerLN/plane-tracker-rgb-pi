"""
Upload helper module for uploading map files to a remote server.

This module provides utilities for obtaining upload tokens and uploading
map files to a configured server endpoint.
"""

import logging
import os
from typing import Optional

import requests

# Configure module logger
logger = logging.getLogger(__name__)

# Pi B (server) URL - can be overridden via environment variable
SERVER_URL: str = os.environ.get("UPLOAD_SERVER_URL", "http://c0wsaysmoo.mynetgear.com:8081")


def get_upload_token() -> str:
    """
    Request a new upload token from the server.

    Contacts the configured server to obtain a single-use upload token
    that can be used for uploading files.

    Returns:
        str: The upload token if successful, empty string on failure.
    """
    try:
        resp = requests.get(f"{SERVER_URL}/get-token", timeout=5)
        resp.raise_for_status()
        token_line = resp.text.strip()
        # Expecting format: "Your upload token: <token>"
        token = token_line.split(":")[-1].strip()
        return token
    except Exception as e:
        logger.warning("Failed to get upload token: %s", e)
        return ""


def upload_map_to_server(local_path: str) -> str:
    """
    Upload a map file to the remote server using a dynamically obtained token.

    This function first obtains an upload token, then uploads the specified
    file to the server. The server returns the filename which is used to
    construct the public URL.

    Args:
        local_path: The local filesystem path to the map file to upload.

    Returns:
        str: The public URL of the uploaded file if successful,
             empty string on failure.
    """
    if not os.path.isfile(local_path):
        logger.warning("File not found: %s", local_path)
        return ""

    token = get_upload_token()
    if not token:
        return ""

    upload_url = f"{SERVER_URL}/upload/{token}"
    try:
        with open(local_path, "rb") as f:
            files = {"file": f}
            resp = requests.post(upload_url, files=files, timeout=10)
            resp.raise_for_status()
            # The server responds with "Uploaded as <filename>"
            uploaded_name = resp.text.strip().split("Uploaded as")[-1].strip()
            return f"https://c0wsaysmoo.mynetgear.com/maps/{uploaded_name}"
    except Exception as e:
        logger.warning("Failed to upload map: %s", e)
        return ""