"""Utility functions for the todo app"""

from datetime import datetime, timezone
from functools import wraps
import base64
from cryptography.fernet import Fernet
from flask import request, jsonify, g

def apply_template_defaults(template):
    """Function to apply default values to a template"""
    # Ensure the template is a dictionary
    if not isinstance(template, dict):
        raise ValueError("Expected template to be a dictionary")

    # Set top-level defaults
    defaults = {
        'criteria': {
            'period': 'daily',
            'days': [1,2,3,4,5],
            'time': '17:00'
        },
        'timestamps': {}
    }
    
    for key, value in defaults.items():
        template.setdefault(key, value)
    
    # Ensure timestamps is a dictionary
    if not isinstance(template['timestamps'], dict):
        template['timestamps'] = {}

    # Set defaults within the timestamps dictionary
    template['timestamps'].setdefault('created', get_current_iso_timestamp())

    return template

def apply_task_defaults(task):
    """Function to apply default values to a task"""
    # Ensure the task is a dictionary
    if not isinstance(task, dict):
        raise ValueError("Expected task to be a dictionary")

    # Set top-level defaults
    defaults = {
        'parent': None,
        'status': 'not_started',
        'timestamps': {},
        'type': 'task'
    }

    for key, value in defaults.items():
        task.setdefault(key, value)
    
    # Ensure timestamps is a dictionary
    if not isinstance(task['timestamps'], dict):
        task['timestamps'] = {}

    # Set defaults within the timestamps dictionary
    task['timestamps'].setdefault('created', get_current_iso_timestamp())

    # if status is completed, we should set timstamp.completed
    if task['status'] == 'completed' and 'completed' not in task['timestamps']:
        task['timestamps']['completed'] = get_current_iso_timestamp()

    return task

def get_current_iso_timestamp():
    """Function to get the current time in ISO format"""
    return datetime.now(timezone.utc).isoformat()

def generate_key():
    """Function to generate a new key"""
    # Generate a new key using Fernet
    key = Fernet.generate_key()
    return key.decode()  # Convert the key from bytes to a string

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not token.startswith("Bearer "):
            return jsonify({'message': 'Invalid or missing token'}), 401
        
        api_key = token.split(" ")[1]
        try:
            decoded_key = base64.urlsafe_b64decode(api_key.encode()).decode()
            user_id, shared_secret, key = decoded_key.split(":")
        except Exception as e:
            return jsonify({'message': 'Invalid token format'}), 401
        # FIXME:  This does need to check user and shared secret against something
        # external
        #if user_id not in user_credentials or \
        #   user_credentials[user_id]['shared_secret'] != shared_secret or \
        #   user_credentials[user_id]['key'] != key:
        #    return jsonify({'message': 'Invalid token'}), 401
        
        # Store user_id and key in the global object
        g.user_id = user_id
        g.key = key
        
        return f(*args, **kwargs)
    return decorated

if __name__ == "__main__":
    print(f"generated key: {generate_key()}")
    print(f"current timestamp: {get_current_iso_timestamp()}")