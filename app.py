from flask import Flask, request, jsonify, g

from functools import wraps
import uuid
from tinydb import TinyDB
from tinydb.storages import JSONStorage
from cryptography.fernet import Fernet
import json
import base64

class EncryptedJSONStorage(JSONStorage):
    def __init__(self, path, key):
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
        
        #if user_id not in user_credentials or \
        #   user_credentials[user_id]['shared_secret'] != shared_secret or \
        #   user_credentials[user_id]['key'] != key:
        #    return jsonify({'message': 'Invalid token'}), 401
        
        # Store user_id and key in the global object
        g.user_id = user_id
        g.key = key
        
        return f(*args, **kwargs)
    return decorated

app = Flask(__name__)


#db = TinyDB('todo_list.json')
def get_db():
    file_name = f"encrypted_{g.user_id}.json"
    # Use the encrypted storage
    return TinyDB(file_name, storage=lambda p: EncryptedJSONStorage(p, g.key))

def generate_key():
    # Generate a new key using Fernet
    key = Fernet.generate_key()
    return key.decode()  # Convert the key from bytes to a string

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

@app.route('/tasks', methods=['GET'])
@app.route('/tasks/task_id/<string:task_id>', methods=['GET'])
@token_required
def get_tasks(task_id=None):
    db = get_db()
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
    db = get_db()
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
    db = get_db()
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
    db = get_db()
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
    db = get_db()
    Task = Query()
    result = db.remove(Task.task_id == task_id)
    if result:
        return jsonify({'message': 'Task deleted successfully'}), 200
    else:
        return jsonify({'message': 'Task not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
