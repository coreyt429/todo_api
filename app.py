"""
todo_api flask app to handle server side api

"""
from flask import Flask, request, jsonify, g, render_template
from flask_cors import CORS

from functools import wraps
import uuid
from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage
from cryptography.fernet import Fernet
import json
import base64
from datetime import datetime, timezone, date
import shutil
import os
import threading
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Create a logger object
logger = logging.getLogger(__name__)


def get_current_iso_timestamp():
    return datetime.now(timezone.utc).isoformat()

class EncryptedJSONStorage(JSONStorage):
    def __init__(self, path, key):
        self.path = path
        super().__init__(path)
        self.fernet = Fernet(key)

    def read(self):
        with open(self.path, 'rb') as handle:
            encrypted_data = handle.read()
            if encrypted_data:
                decrypted_data = self.fernet.decrypt(encrypted_data)
                return json.loads(decrypted_data)
            else:
                return None

    def write(self, data):
        encrypted_data = self.fernet.encrypt(json.dumps(data).encode())
        with open(self.path, 'wb') as handle:
            handle.write(encrypted_data)


# Load configuration
with open('cfg.json') as file:
    cfg = json.load(file)

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


# Use a thread-local storage for database connections
local = threading.local()

app = Flask(__name__)
CORS(app, origins='*',
          methods=['GET', 'POST', 'PUT', 'DELETE'],
          allow_headers=['Content-Type', 'Authorization'],
          supports_credentials=True)
# FIXME: move all task handling code into a module to simplify the code here to just api code
# FIXME: move all actual db file handling to a storage layer under tasks
def get_db(**kwargs):
    # default tasks db
    file_name = f"encrypted_{g.user_id}.json"
    # templates db
    if kwargs.get('db', None) == 'template':
        file_name = f"encrypted_{g.user_id}_templates.json"
    
    # Get today's date in YYYYMMDD format
    today = date.today().strftime("%Y%m%d")
    
    # Define the backup file name
    backup_file_name = f"{file_name}.{today}"
    
    # Check if the backup file for today exists
    if not os.path.exists(backup_file_name):
        # If the original file exists, create a backup
        if os.path.exists(file_name):
            shutil.copy2(file_name, backup_file_name)
    
    # Use the encrypted storage
    return TinyDB(file_name, storage=lambda p: EncryptedJSONStorage(p, g.key))

def close_db(**kwargs):
    print(f"kwargs: {kwargs}")
    db_name = kwargs.get('db', None)
    if hasattr(local, 'db'):
        if db_name is None:
            # Close all databases
            for db in local.db.values():
                db.close()
            local.db.clear()
        else:
            # default tasks db
            file_name = f"encrypted_{g.user_id}.json"
            # templates db
            if kwargs.get('db', None) == 'template':
                file_name = f"encrypted_{g.user_id}_templates.json"
            if file_name in local.db:
                # Close specific database
                local.db[file_name].close()
                del local.db[file_name]

def generate_key():
    # Generate a new key using Fernet
    key = Fernet.generate_key()
    return key.decode()  # Convert the key from bytes to a string

####################################################################################################
#  HTML
####################################################################################################

@app.route('/')
def index():
    return render_template('index.html')


####################################################################################################
#  Key management
####################################################################################################

@app.route('/key', methods=['POST'])
def get_key():
    data = request.get_json()
    user_id = data.get('user_id')
    shared_secret = data.get('shared_secret')
    
    if not user_id or not shared_secret:
        return jsonify({"error": "Missing user_id or shared_secret"}), 400
    
    new_key = generate_key()
    # Combine user_id, shared_secret, and new_key into a single string
    combined_string = f"{user_id}:{shared_secret}:{new_key}"
    # Encode the combined string in base64
    api_key = base64.urlsafe_b64encode(combined_string.encode()).decode()
    
    return jsonify({"api_key": api_key})

####################################################################################################
#  /tasks - deprecated, once client API is fully updated, drop this section
####################################################################################################

# @app.route('/tasks', methods=['GET'])
# @app.route('/tasks/task_id/<string:task_id>', methods=['GET'])
# @token_required
# def get_tasks(task_id=None):
#     db = get_db()
#     if task_id:
#         # Get a specific task
#         Task = Query()
#         task = db.get(Task.task_id == task_id)
#         if task:
#             return jsonify(task)
#         else:
#             return jsonify({'message': 'Task not found'}), 404
#     else:
#         # Get all tasks
#         tasks = db.all()
#         return jsonify(tasks)

# # consider combining GET, PUT, and DELETE into one handler on @app.route('/tasks/<string:task_id>', methods=['PUT', 'GET', 'DELETE'])
# # seperate with if request.method == 'GET':
# @app.route('/tasks/search/<string:query>', methods=['GET'])
# @app.route('/tasks/search/<string:field>/<string:query>', methods=['GET'])
# @app.route('/tasks/search', methods=['GET'])
# @token_required
# def get_tasks_search(query=None, field=None):
#     db = get_db()
#     if query:
#         # Get a specific task
#         results = []
#         Task = Query()
#         if field:
#             # how do I look for keyword in field?
#             for item in db.all():
#                 if query in item[field]:
#                     results.append(item)
#         else:
#             query = query.lower()
#             for item in db.all():
#                 if any(query in str(key).lower() or query in str(value).lower()
#                     for key, value in item.items()):
#                     results.append(item)
#     else:
#         # Get all tasks
#         results = db.all()
#     return jsonify(results)

# @app.route('/tasks', methods=['POST'])
# @token_required
# def post_tasks():
#     db = get_db()
#     task = request.json
#     task = apply_task_defaults(task)
#     if not task:
#         return jsonify({'message': 'No task provided'}), 400
#     task['task_id'] = str(uuid.uuid4())
#     # Create new task
#     db.insert(task)
#     return jsonify({'message': 'Task created successfully', 'task_id': task['task_id']}), 201

# # consider combining GET, PUT, and DELETE into one handler on @app.route('/tasks/<string:task_id>', methods=['PUT', 'GET', 'DELETE'])
# @app.route('/tasks/<string:task_id>', methods=['PUT'])
# @token_required
# def put_tasks(task_id):
#     db = get_db()
#     task = request.json
#     task = apply_task_defaults(task)
#     # FIXME:  default fields and timestamps should probably be handled in client code
#     task['timestamps']['updated'] = get_current_iso_timestamp()
#     if not task:
#         return jsonify({'message': 'No task provided'}), 400

#     if not 'task_id' in task:
#         task['task_id'] = task_id
#         # Update existing task
#     Task = Query()
#     result = db.update(task, Task.task_id == task['task_id'])
#     if result:
#         return jsonify({'message': 'Task updated successfully'}), 200
#     else:
#         return jsonify({'message': 'Task not found'}), 404

# # consider combining GET, PUT, and DELETE into one handler on @app.route('/tasks/<string:task_id>', methods=['PUT', 'GET', 'DELETE'])
# @app.route('/tasks/delete/<string:task_id>', methods=['DELETE'])
# @token_required
# def delete_task(task_id):
#     db = get_db()
#     Task = Query()
#     result = db.remove(Task.task_id == task_id)
#     if result:
#         return jsonify({'message': 'Task deleted successfully'}), 200
#     else:
#         return jsonify({'message': 'Task not found'}), 404

####################################################################################################
#  /task
####################################################################################################
@app.route('/task/search/<string:query>', methods=['GET'])
@app.route('/task/search/<string:field>/<string:query>', methods=['GET'])
@app.route('/task/search', methods=['GET'])
@token_required
def get_task_search(query=None, field=None):
    with db_lock:
        db = get_db()
        if query:
            query = query.lower()
            results = []
            if field:
                for item in db.all():
                    if query in item[field].lower():
                        results.append(item)
            else:
                for item in db.all():
                    if any(query in str(key).lower() or query in str(value).lower()
                        for key, value in item.items()):
                        results.append(item)
        else:
            # Get all tasks
            results = db.all()
        close_db()
        return jsonify(results)

def apply_task_defaults(task):
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

    return task


@app.route('/task', methods=['GET', 'POST'])
@app.route('/task/<string:task_id>', methods=['GET', 'PUT', 'POST', 'DELETE'])
@token_required
def handle_task(task_id=None):
    logger.debug(f"{request.method} /task/{task_id}")
    logger.debug("Waiting on lock")
    logger.debug("Got lock")
    db = get_db(db='task')
    query = Query()

    # Handle POST and PUT requests (add and update)
    if request.method in ['POST', 'PUT']:
        task = apply_task_defaults(request.json)
        logger.debug(json.dumps(task, indent=2))
        # Generate a new task_id if not provided in the path
        if not task_id:
            task_id = str(uuid.uuid4())

        # Set task_id in the JSON if not provided
        task.setdefault('task_id', task_id)
        # if status is completed, we should set timstamp.completed
        if task['status'] == 'completed' and 'completed' not in task['timestamps']:
            task['timestamps']['completed'] = get_current_iso_timestamp()
        
        # FIXME: we should .lower() field names before saving
        if request.method == 'POST':
            result = db.insert(task)
            close_db(db='task')
            if result:
                return jsonify({
                    'message': 'task created successfully',
                    'task_id': task['task_id']
                }), 201
            return jsonify({'message': 'Failed to create task'}), 503
        
        # Update the task if method is PUT
        # result = db.update(task, query.task_id == task['task_id'])
        # if result:
        #     return jsonify({'message': 'task updated successfully'}), 200
        # return jsonify({'message': 'task not found'}), 404
        query = Query()
        
        # Check if the template exists
        existing = db.get(query.task_id == task['task_id'])
        task['timestamps']['updated'] = get_current_iso_timestamp()
        if existing:
            # Remove the existing template
            db.remove(query.task_id == task['task_id'])
            # Insert the new task
            db.insert(task)
            close_db(db='task')
            return jsonify({'message': 'Task updated successfully'}), 200
        else:
            close_db(db='task')
            return jsonify({'message': 'Task not found'}), 404


    # Handle DELETE request
    if request.method == 'DELETE':
        # FIXME: check for children first so we don't cause orphans
        children = db.get(query.parent == task_id)
        if children:
            close_db(db='task')
            return jsonify({'message': 'delete would cause orphans'}), 403
        result = db.remove(query.task_id == task_id)
        close_db(db='task')
        if result:
            return jsonify({'message': 'task deleted successfully'}), 200
        return jsonify({'message': 'task not found'}), 404

    # Handle GET requests
    if task_id:
        # Get a specific task
        task = db.get(query.task_id == task_id)
        close_db(db='task')
        if task:
            return jsonify(task)
        return jsonify({'message': 'task not found'}), 404

    # Get all tasks if no task_id is provided
    tasks = db.all()
    close_db(db='task')
    return jsonify(tasks)

####################################################################################################
#  /template
####################################################################################################
def apply_template_defaults(template):
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


@app.route('/template', methods=['GET', 'POST'])
@app.route('/template/<string:template_id>', methods=['GET', 'PUT', 'POST', 'DELETE'])
@token_required
def handle_template(template_id=None):
    logger.debug(f"{request.method} /template/{template_id}")
    #if request.json: 
    logger.debug("Waiting on lock")
    with db_lock:
        logger.debug("Got lock")
        db = get_db(db='template')
        query = Query()

        # Handle POST and PUT requests (add and update)
        if request.method in ['POST', 'PUT']:
            template = apply_template_defaults(request.json)
            logger.debug(json.dumps(template, indent=2))
            # Generate a new template_id if not provided in the path
            if not template_id:
                template_id = str(uuid.uuid4())

            # Set template_id in the JSON if not provided
            template.setdefault('template_id', template_id)
            if request.method == 'POST':
                result = db.insert(template)
                close_db(db='template')
                if result:
                    return jsonify({
                        'message': 'Template created successfully',
                        'template_id': template['template_id']
                    }), 201
                return jsonify({'message': 'Failed to create template'}), 503
            
            # Update the template if method is PUT
            #result = db.update(template, query.template_id == template['template_id'])
            #if result:
            #    return jsonify({'message': 'Template updated successfully'}), 200
            #return jsonify({'message': 'Template not found'}), 404
            query = Query()
            
            # Check if the template exists
            existing = db.get(query.template_id == template['template_id'])
            template['timestamps']['updated'] = get_current_iso_timestamp()
            if existing:
                # Remove the existing template
                db.remove(query.template_id == template['template_id'])
                # Insert the new template
                db.insert(template)
                close_db(db='template')
                return jsonify({'message': 'Template updated successfully'}), 200
            else:
                close_db(db='template')
                return jsonify({'message': 'Template not found'}), 404

        # Handle DELETE request
        if request.method == 'DELETE':
            result = db.remove(query.template_id == template_id)
            close_db(db='template')
            if result:
                return jsonify({'message': 'Template deleted successfully'}), 200
            return jsonify({'message': 'Template not found'}), 404

        # Handle GET requests
        if template_id:
            # Get a specific template
            template = db.get(query.template_id == template_id)
            close_db(db='template')
            if template:
                return jsonify(template)
            return jsonify({'message': 'Template not found'}), 404

        # Get all templates if no template_id is provided
        templates = db.all()
        close_db(db='template')
        return jsonify(templates)

@app.teardown_appcontext
def teardown_db(exception):
    close_db()


if __name__ == '__main__':
    app.run(debug=True)
