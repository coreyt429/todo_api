"""Utility functions for the todo app"""

from datetime import datetime, timezone
from cryptography.fernet import Fernet

def get_current_iso_timestamp():
    """Function to get the current time in ISO format"""
    return datetime.now(timezone.utc).isoformat()

def generate_key():
    """Function to generate a new key"""
    # Generate a new key using Fernet
    key = Fernet.generate_key()
    return key.decode()  # Convert the key from bytes to a string

if __name__ == "__main__":
    print(f"generated key: {generate_key()}")
    print(f"current timestamp: {get_current_iso_timestamp()}")