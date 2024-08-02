from flask import Flask, jsonify, request
from tinydb import TinyDB, Query
import json
from functools import wraps
import uuid

# Load configuration
with open('cfg.json') as file:
    cfg = json.load(file)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or token != f"Bearer {cfg['AUTH_TOKEN']}":
            return jsonify({'message': 'Invalid or missing token'}), 401
        return f(*args, **kwargs)
    return decorated

app = Flask(__name__)
db = TinyDB('todo_list.json')

@app.route('/tasks', methods=['GET'])
@app.route('/tasks/task_id/<string:task_id>', methods=['GET'])
@token_required
def get_tasks(task_id=None):
    if task_id:
        # Get a specific task
        Task = Query()
        task = db.get(Task.task_id == task_id)
        if task:
            return jsonify(task)
        else:
            return jsonify({'message': 'Task not found'}), 404
    else:
        # Get all tasks
        tasks = db.all()
        return jsonify(tasks)

# consider combining GET, PUT, and DELETE into one handler on @app.route('/tasks/<string:task_id>', methods=['PUT', 'GET', 'DELETE'])
# seperate with if request.method == 'GET':
@app.route('/tasks/search/<string:query>', methods=['GET'])
@app.route('/tasks/search/<string:field>/<string:query>', methods=['GET'])
@app.route('/tasks/search', methods=['GET'])
@token_required
def get_tasks_search(query=None, field=None):
    if query:
        # Get a specific task
        results = []
        Task = Query()
        if field:
            # how do I look for keyword in field?
            for item in db.all():
                if query in item[field]:
                    results.append(item)
        else:
            query = query.lower()
            for item in db.all():
                if any(query in str(key).lower() or query in str(value).lower()
                    for key, value in item.items()):
                    results.append(item)
    else:
        # Get all tasks
        results = db.all()
    return jsonify(results)

@app.route('/tasks', methods=['POST'])
@token_required
def post_tasks():
    task = request.json
    if not task:
        return jsonify({'message': 'No task provided'}), 400
    task['task_id'] = str(uuid.uuid4())
    # Create new task
    db.insert(task)
    return jsonify({'message': 'Task created successfully', 'task_id': task['task_id']}), 201

# consider combining GET, PUT, and DELETE into one handler on @app.route('/tasks/<string:task_id>', methods=['PUT', 'GET', 'DELETE'])
@app.route('/tasks/<string:task_id>', methods=['PUT'])
@token_required
def put_tasks(task_id):
    task = request.json
    if not task:
        return jsonify({'message': 'No task provided'}), 400

    if not 'task_id' in task:
        task['task_id'] = task_id
        # Update existing task
    Task = Query()
    result = db.update(task, Task.task_id == task['task_id'])
    if result:
        return jsonify({'message': 'Task updated successfully'}), 200
    else:
        return jsonify({'message': 'Task not found'}), 404

# consider combining GET, PUT, and DELETE into one handler on @app.route('/tasks/<string:task_id>', methods=['PUT', 'GET', 'DELETE'])
@app.route('/tasks/delete/<string:task_id>', methods=['DELETE'])
@token_required
def delete_task(task_id):
    Task = Query()
    result = db.remove(Task.task_id == task_id)
    if result:
        return jsonify({'message': 'Task deleted successfully'}), 200
    else:
        return jsonify({'message': 'Task not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
