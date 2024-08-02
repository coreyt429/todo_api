from flask import Flask, jsonify, request
from tinydb import TinyDB
import json
from functools import wraps

# Load configuration
with open('cfg.json') as file:
    cfg = json.load(file)  # Changed from json.loads(file) to json.load(file)

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

if __name__ == '__main__':
    app.run(debug=True)
