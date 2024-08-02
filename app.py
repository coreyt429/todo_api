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
@token_required
def get_tasks():
    tasks = db.all()
    return jsonify(tasks)

@app.route('/tasks', methods=['PUT'])
@token_required
def put_tasks():
    task = request.json
    if not task:
        return jsonify({'message': 'No task provided'}), 400

    if 'taskId' in task:
        # Update existing task
        Task = Query()
        result = db.update(task, Task.taskId == task['taskId'])
        if result:
            return jsonify({'message': 'Task updated successfully'}), 200
        else:
            return jsonify({'message': 'Task not found'}), 404
    else:
        # Create new task
        task['taskId'] = str(uuid.uuid4())
        db.insert(task)
        return jsonify({'message': 'Task created successfully', 'taskId': task['taskId']}), 201

@app.route('/tasks/<string:task_id>', methods=['DELETE'])
@token_required
def delete_task(task_id):
    Task = Query()
    result = db.remove(Task.taskId == task_id)
    if result:
        return jsonify({'message': 'Task deleted successfully'}), 200
    else:
        return jsonify({'message': 'Task not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)