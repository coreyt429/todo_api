"""
todo_api flask app to handle server side api

"""
from flask import Flask, request, jsonify, g, render_template
from flask_cors import CORS
import sys
if sys.platform == "win32":
    import msvcrt as fcntl
else:
    import fcntl
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
from contextlib import contextmanager
from flasgger import Swagger

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

@contextmanager
def file_lock(lock_file):
    with open(lock_file, 'w') as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        except IOError:
            logger.warning(f"Waiting for lock on {lock_file}")
            fcntl.flock(f, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)

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
# Initialize Swagger
swagger = Swagger(app, template={
    "swagger": "2.0",
    "info": {
        "title": "Todo API",
        "description": "API documentation for the Todo API",
        "version": "1.0.0"
    },
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Authorization header using the Bearer scheme. Example: \"Authorization: Bearer {token}\""
        }
    },
    "security": [
        {
            "Bearer": []
        }
    ]
})

# FIXME: move all task handling code into a module to simplify the code here to just api code
# FIXME: move all actual db file handling to a storage layer under tasks
@contextmanager
def get_db(**kwargs):
    thread_info = f"PID: {os.getpid()}, Thread ID: {threading.get_ident()}"
    logger.debug(f"{thread_info} - Attempting to acquire database")

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
        db = TinyDB(file_name, storage=lambda p: EncryptedJSONStorage(p, g.key))
        try:
            yield db
        finally:
            db.close()
            logger.debug(f"{thread_info} - Database connection closed")

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
def post_key():
    """
    Create a new API key
    ---
    tags:
      - Key Management
    parameters:
      - in: body
        name: body
        description: User ID and shared secret
        required: true
        schema:
          type: object
          properties:
            user_id:
              type: string
              example: "user123"
            shared_secret:
              type: string
              example: "mysecret"
    responses:
      200:
        description: API key created successfully
        schema:
          type: object
          properties:
            api_key:
              type: string
              example: "base64encodedapikey"
      400:
        description: Missing user_id or shared_secret
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Missing user_id or shared_secret"
    """
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
#  /task
####################################################################################################
@app.route('/task/search', methods=['GET'])
@token_required
def get_task_search_all():
    """
    Get all tasks
    ---
    tags:
      - Tasks
    responses:
      200:
        description: A list of tasks
        schema:
          type: array
          items:
            type: object
            properties:
              task_id:
                type: string
                example: "123e4567-e89b-12d3-a456-426614174000"
              parent:
                type: string
                example: "parent_task_id"
              status:
                type: string
                example: "not_started"
              timestamps:
                type: object
                properties:
                  created:
                    type: string
                    example: "2023-01-01T00:00:00Z"
                  completed:
                    type: string
                    example: "2023-01-02T00:00:00Z"
              type:
                type: string
                example: "task"
    """
    with get_db() as db:
            # Get all tasks
            results = db.all()
    return jsonify(results)

@app.route('/task/search/<string:query>', methods=['GET'])
@token_required
def get_task_search(query):
    """
    Search tasks by query
    ---
    tags:
      - Tasks
    parameters:
      - in: path
        name: query
        type: string
        required: true
        description: The search query
    responses:
      200:
        description: A list of tasks matching the query
        schema:
          type: array
          items:
            type: object
            properties:
              task_id:
                type: string
                example: "123e4567-e89b-12d3-a456-426614174000"
              parent:
                type: string
                example: "parent_task_id"
              status:
                type: string
                example: "not_started"
              timestamps:
                type: object
                properties:
                  created:
                    type: string
                    example: "2023-01-01T00:00:00Z"
                  completed:
                    type: string
                    example: "2023-01-02T00:00:00Z"
              type:
                type: string
                example: "task"
    """
    with get_db() as db:
        query = query.lower()
        results = []
        for item in db.all():
            for key, value in item.items():
                if query in str(key).lower() or query in str(value).lower():
                    results.append(item)
                    break
    return jsonify(results)

@app.route('/task/search/<string:field>/<string:query>', methods=['GET'])
@token_required
def get_task_search_field(query, field):
    """
    Search tasks by field and query
    ---
    tags:
      - Tasks
    parameters:
      - in: path
        name: field
        type: string
        required: true
        description: The field to search in
      - in: path
        name: query
        type: string
        required: true
        description: The search query
    responses:
      200:
        description: A list of tasks matching the field and query
        schema:
          type: array
          items:
            type: object
            properties:
              task_id:
                type: string
                example: "123e4567-e89b-12d3-a456-426614174000"
              parent:
                type: string
                example: "parent_task_id"
              status:
                type: string
                example: "not_started"
              timestamps:
                type: object
                properties:
                  created:
                    type: string
                    example: "2023-01-01T00:00:00Z"
                  completed:
                    type: string
                    example: "2023-01-02T00:00:00Z"
              type:
                type: string
                example: "task"
    """
    with get_db() as db:
        query = query.lower()
        results = []
        for item in db.all():
            if query in item.get(field, '').lower():
                results.append(item)
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

    # if status is completed, we should set timstamp.completed
    if task['status'] == 'completed' and 'completed' not in task['timestamps']:
        task['timestamps']['completed'] = get_current_iso_timestamp()

    return task


@app.route('/task', methods=['POST'])
@token_required
def post_task():
    """
    Create a new task
    ---
    tags:
      - Tasks
    parameters:
      - in: body
        name: body
        description: The task to create
        required: true
        schema:
          type: object
          properties:
            parent:
              type: string
              example: "parent_task_id"
            status:
              type: string
              example: "not_started"
            timestamps:
              type: object
              properties:
                created:
                  type: string
                  example: "2023-01-01T00:00:00Z"
                completed:
                  type: string
                  example: "2023-01-02T00:00:00Z"
            type:
              type: string
              example: "task"
    responses:
      201:
        description: Task created successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: "task created successfully"
            task_id:
              type: string
              example: "123e4567-e89b-12d3-a456-426614174000"
      400:
        description: Invalid input
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Invalid input"
      503:
        description: Failed to create task
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Failed to create task"
    """
    logger.debug(f"{request.method} /task")
    # Handle POST and PUT requests (add and update)
    task = apply_task_defaults(request.json)
    logger.debug(json.dumps(task, indent=2))
    # Generate a new task_id
    task_id = str(uuid.uuid4())
    # Set task_id in the JSON if not provided
    task.setdefault('task_id', task_id)
    
    # FIXME: we should .lower() field names before saving
    with get_db(db='task') as db:
        result = db.insert(task)
    if result:
        return jsonify({
            'message': 'task created successfully',
            'task_id': task['task_id']
        }), 201
    return jsonify({'message': 'Failed to create task'}), 503





@app.route('/task/<string:task_id>', methods=['PUT'])
@token_required
def put_task(task_id):
    """
    Update an existing task or create a new one if task_id is not provided.
    ---
    put:
      summary: Update an existing task
      description: Update an existing task by task_id or create a new one if task_id is not provided.
      parameters:
        - in: path
          name: task_id
          required: false
          description: The ID of the task to update.
          schema:
            type: string
        - in: body
          name: task
          required: true
          description: The task data to update.
          schema:
            type: object
            properties:
              task_id:
                type: string
                description: The ID of the task.
              status:
                type: string
                description: The status of the task.
              timestamps:
                type: object
                properties:
                  completed:
                    type: string
                    format: date-time
                    description: The completion timestamp of the task.
                  updated:
                    type: string
                    format: date-time
                    description: The last updated timestamp of the task.
      responses:
        200:
          description: Task updated successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  message:
                    type: string
                    example: Task updated successfully
        404:
          description: Task not found
          content:
            application/json:
              schema:
                type: object
                properties:
                  message:
                    type: string
                    example: Task not found
    """

    logger.debug(f"{request.method} /task/{task_id}")
    query = Query()

    # Handle  PUT requests (update)
    task = apply_task_defaults(request.json)
    logger.debug(json.dumps(task, indent=2))
    # Generate a new task_id if not provided in the path
    if not task_id:
        task_id = str(uuid.uuid4())

    # Set task_id in the JSON if not provided
    task.setdefault('task_id', task_id)
    
    # Update the task if method is PUT
    with get_db(db='task') as db:
        # Check if the template exists
        existing = db.get(query.task_id == task['task_id'])

    task['timestamps']['updated'] = get_current_iso_timestamp()
    if existing:
        with get_db(db='task') as db:
            # Remove the existing template
            db.remove(query.task_id == task['task_id'])
            # Insert the new task
            db.insert(task)
        return jsonify({'message': 'Task updated successfully'}), 200
    else:
        return jsonify({'message': 'Task not found'}), 404

@app.route('/task/<string:task_id>', methods=['POST'])
@token_required
def post_task_deprecated(task_id):
    """
    Create a new task (deprecated)
    ---
    tags:
      - Tasks
    parameters:
      - in: path
        name: task_id
        type: string
        required: true
        description: The ID of the task to create
      - in: body
        name: body
        description: The task to create
        required: true
        schema:
          type: object
          properties:
            parent:
              type: string
              example: "parent_task_id"
            status:
              type: string
              example: "not_started"
            timestamps:
              type: object
              properties:
                created:
                  type: string
                  example: "2023-01-01T00:00:00Z"
                completed:
                  type: string
                  example: "2023-01-02T00:00:00Z"
            type:
              type: string
              example: "task"
    responses:
      201:
        description: Task created successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: "task created successfully"
            task_id:
              type: string
              example: "123e4567-e89b-12d3-a456-426614174000"
      400:
        description: Invalid input
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Invalid input"
      503:
        description: Failed to create task
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Failed to create task"
    """
    logger.debug(f"{request.method} /task/{task_id}")
    query = Query()

    # Handle POST requests (add and update)
    task = apply_task_defaults(request.json)
    logger.debug(json.dumps(task, indent=2))
    # Generate a new task_id if not provided in the path
    if not task_id:
        task_id = str(uuid.uuid4())

    # Set task_id in the JSON if not provided
    task.setdefault('task_id', task_id)
    
    # FIXME: we should .lower() field names before saving
    with get_db(db='task') as db:
        result = db.insert(task)
    if result:
        return jsonify({
            'message': 'task created successfully',
            'task_id': task['task_id']
        }), 201
    return jsonify({'message': 'Failed to create task'}), 503
    
    
@app.route('/task/<string:task_id>', methods=['GET'])
@token_required
def get_task(task_id):
    """
    Get a specific task by its ID
    ---
    tags:
      - Tasks
    parameters:
      - name: task_id
        in: path
        type: string
        required: true
        description: The ID of the task to retrieve
    responses:
      200:
        description: The task with the specified ID
        schema:
          type: object
          properties:
            task_id:
              type: string
              example: "123e4567-e89b-12d3-a456-426614174000"
            parent:
              type: string
              example: "parent_task_id"
            status:
              type: string
              example: "not_started"
            timestamps:
              type: object
              properties:
                created:
                  type: string
                  example: "2023-01-01T00:00:00Z"
                completed:
                  type: string
                  example: "2023-01-02T00:00:00Z"
            type:
              type: string
              example: "task"
      404:
        description: Task not found
        schema:
          type: object
          properties:
            message:
              type: string
              example: "task not found"
    """
    logger.debug(f"{request.method} /task/{task_id}")
    query = Query()
    with get_db(db='task') as db:
        # Get a specific task
        task = db.get(query.task_id == task_id)
    if task:
        return jsonify(task)
    return jsonify({'message': 'task not found'}), 404

@app.route('/task', methods=['GET'])
@token_required
def get_task_list():
    """
    Get all tasks
    ---
    tags:
      - Tasks
    responses:
      200:
        description: A list of tasks
        schema:
          type: array
          items:
            type: object
            properties:
              task_id:
                type: string
                example: "123e4567-e89b-12d3-a456-426614174000"
              parent:
                type: string
                example: "parent_task_id"
              status:
                type: string
                example: "not_started"
              timestamps:
                type: object
                properties:
                  created:
                    type: string
                    example: "2023-01-01T00:00:00Z"
                  completed:
                    type: string
                    example: "2023-01-02T00:00:00Z"
              type:
                type: string
                example: "task"
    """
    logger.debug(f"{request.method} /task")
    with get_db(db='task') as db:
        # Get all tasks if no task_id is provided
        tasks = db.all()
    return jsonify(tasks)
        
@app.route('/task/<string:task_id>', methods=['DELETE'])
@token_required
def delete_task(task_id):
    """
    Delete a task by its ID.

    This endpoint deletes a task from the database if it exists and has no child tasks.
    If the task has child tasks, it returns a 403 status code to prevent orphaned tasks.

    ---
    tags:
      - Tasks
    parameters:
      - name: task_id
        in: path
        type: integer
        required: true
        description: The ID of the task to delete.
    responses:
      200:
        description: Task deleted successfully.
        schema:
          type: object
          properties:
            message:
              type: string
              example: task deleted successfully
      403:
        description: Delete would cause orphans.
        schema:
          type: object
          properties:
            message:
              type: string
              example: delete would cause orphans
      404:
        description: Task not found.
        schema:
          type: object
          properties:
            message:
              type: string
              example: task not found
    """
    logger.debug(f"{request.method} /task/{task_id}")
    query = Query()
    with get_db(db='task') as db:
        children = db.get(query.parent == task_id)
    if children:
        return jsonify({'message': 'delete would cause orphans'}), 403
    with get_db(db='task') as db:
        result = db.remove(query.task_id == task_id)
    if result:
        return jsonify({'message': 'task deleted successfully'}), 200
    return jsonify({'message': 'task not found'}), 404


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
    query = Query()

    #if request.json: 
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
            with get_db(db='template') as db:
                result = db.insert(template)
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
        
        with get_db(db='template') as db:
            # Check if the template exists
            existing = db.get(query.template_id == template['template_id'])
        template['timestamps']['updated'] = get_current_iso_timestamp()
        if existing:
            with get_db(db='template') as db:
                # Remove the existing template
                db.remove(query.template_id == template['template_id'])
                # Insert the new template
                db.insert(template)
            return jsonify({'message': 'Template updated successfully'}), 200
        else:
            return jsonify({'message': 'Template not found'}), 404

    # Handle DELETE request
    if request.method == 'DELETE':
        with get_db(db='template') as db:
            result = db.remove(query.template_id == template_id)
        if result:
            return jsonify({'message': 'Template deleted successfully'}), 200
        return jsonify({'message': 'Template not found'}), 404

    # Handle GET requests
    if template_id:
        # Get a specific template
        with get_db(db='template') as db:
            template = db.get(query.template_id == template_id)
        if template:
            return jsonify(template)
        return jsonify({'message': 'Template not found'}), 404

    with get_db(db='template') as db:
        # Get all templates if no template_id is provided
        templates = db.all()
    return jsonify(templates)

####################################################################################################
#  /backup
####################################################################################################
@app.route('/backup', methods=['GET'])
@token_required
def handle_backup():
    """
    Get a backup of all tasks and templates
    ---
    tags:
      - Backup
    responses:
      200:
        description: A backup of all tasks and templates
        schema:
          type: object
          properties:
            templates:
              type: array
              items:
                type: object
                properties:
                  template_id:
                    type: string
                    example: "123e4567-e89b-12d3-a456-426614174000"
                  criteria:
                    type: object
                    properties:
                      period:
                        type: string
                        example: "daily"
                      days:
                        type: array
                        items:
                          type: integer
                          example: 1
                      time:
                        type: string
                        example: "17:00"
                  timestamps:
                    type: object
                    properties:
                      created:
                        type: string
                        example: "2023-01-01T00:00:00Z"
                      updated:
                        type: string
                        example: "2023-01-02T00:00:00Z"
            tasks:
              type: array
              items:
                type: object
                properties:
                  task_id:
                    type: string
                    example: "123e4567-e89b-12d3-a456-426614174000"
                  parent:
                    type: string
                    example: "parent_task_id"
                  status:
                    type: string
                    example: "not_started"
                  timestamps:
                    type: object
                    properties:
                      created:
                        type: string
                        example: "2023-01-01T00:00:00Z"
                      completed:
                        type: string
                        example: "2023-01-02T00:00:00Z"
                  type:
                    type: string
                    example: "task"
    """
    backup = {}
    with get_db(db='template') as db:
        # Get all templates if no template_id is provided
        backup['templates'] = db.all()
    with get_db() as db:
        # Get all templates if no template_id is provided
        backup['tasks'] = db.all()
    return jsonify(backup)


if __name__ == '__main__':
    app.run(debug=True)
