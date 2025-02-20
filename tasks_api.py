"""
todo_api flask task_app to handle server side api

"""
from flask import request, jsonify, blueprints
import uuid
from tinydb import Query
import json
import logging
from todo_util import token_required, get_current_iso_timestamp, apply_task_defaults
from todo_storage import get_db

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

task_app = blueprints.Blueprint('task_app', __name__)

####################################################################################################
#  /task
####################################################################################################
@task_app.route('/search', methods=['GET'])
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

@task_app.route('/search/<string:query>', methods=['GET'])
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
                    results.task_append(item)
                    break
    return jsonify(results)

@task_app.route('/search/<string:field>/<string:query>', methods=['GET'])
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
                results.task_append(item)
    return jsonify(results)


@task_app.route('/', methods=['POST'])
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





@task_app.route('/<string:task_id>', methods=['PUT'])
@token_required
def put_task(task_id):
    """
    Update an existing task or create a new one if task_id is not provided.
    ---
    tags:
      - Tasks
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
            task_application/json:
              schema:
                type: object
                properties:
                  message:
                    type: string
                    example: Task updated successfully
        404:
          description: Task not found
          content:
            task_application/json:
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

@task_app.route('/<string:task_id>', methods=['POST'])
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
    
    
@task_app.route('/<string:task_id>', methods=['GET'])
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

@task_app.route('/', methods=['GET'])
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
        
@task_app.route('/<string:task_id>', methods=['DELETE'])
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
        type: string
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

if __name__ == '__main__':
    task_app.run(debug=True)
