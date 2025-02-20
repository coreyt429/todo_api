"""
todo_api flask app to handle server side api

"""
import sys
import os
import threading
import logging
import json
from datetime import date
import shutil
from contextlib import contextmanager
from flask import g
from tinydb import TinyDB
from tinydb.storages import JSONStorage
from cryptography.fernet import Fernet
if sys.platform == "win32":
    import msvcrt as fcntl
else:
    import fcntl # pylint: disable=import-error
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Create a logger object
logger = logging.getLogger(__name__)

@contextmanager
def file_lock(lock_file):
    """Function to acquire a file lock"""
    with open(lock_file, 'w', encoding='utf-8') as file:
        try:
            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        except IOError:
            logger.warning("Waiting for lock on %s", lock_file)
            fcntl.flock(file, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(file, fcntl.LOCK_UN)

class EncryptedJSONStorage(JSONStorage):
    """Class to store data in encrypted JSON format"""
    def __init__(self, path, key):
        self.path = path
        super().__init__(path)
        self.fernet = Fernet(key)

    def read(self):
        """Function to read the data from the file"""
        with open(self.path, 'rb') as handle:
            encrypted_data = handle.read()
            if encrypted_data:
                decrypted_data = self.fernet.decrypt(encrypted_data)
                return json.loads(decrypted_data)
            return None

    def write(self, data):
        """Function to write the data to the file"""
        encrypted_data = self.fernet.encrypt(json.dumps(data).encode())
        with open(self.path, 'wb') as handle:
            handle.write(encrypted_data)

@contextmanager
def get_db(**kwargs):
    """Function to get the database connection"""
    thread_info = f"PID: {os.getpid()}, Thread ID: {threading.get_ident()}"
    logger.debug("%s - Attempting to acquire database", thread_info)

    # default tasks db
    file_name = f"encrypted_{g.user_id}.json"
    # templates db
    if kwargs.get('db', None) == 'template':
        file_name = f"encrypted_{g.user_id}_templates.json"
    # Get today's date in YYYYMMDD format
    today = date.today().strftime("%Y%m%d")

    # Define the backup file name
    backup_file_name = f"{file_name}.{today}"

    lock_file = f"{file_name}.lock"

    with file_lock(lock_file):
        logger.debug("Got lock")
        # Check if the backup file for today exists
        if not os.path.exists(backup_file_name):
            # If the original file exists, create a backup
            if os.path.exists(file_name):
                shutil.copy2(file_name, backup_file_name)
        data_base = TinyDB(file_name, storage=lambda p: EncryptedJSONStorage(p, g.key))
        try:
            yield data_base
        finally:
            data_base.close()
            logger.debug("%s - Database connection closed", thread_info)


if __name__ == '__main__':
    print("todo_storage doesn't do anything by itself")
