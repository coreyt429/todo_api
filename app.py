"""
todo_api flask app to handle server side api

"""
from flask import Flask, request, jsonify, g, render_template
from flask_cors import CORS
import sys
import uuid
from tinydb import Query
import json
import base64
import threading
import logging
from flasgger import Swagger
# FIXME: this needs to be more elegant
sys.path.insert(0, "/home/coreyt/dev/todo_api")
from todo_storage import get_db
from todo_util import get_current_iso_timestamp, generate_key, token_required, apply_task_defaults, apply_template_defaults
from tasks_api import task_app
from templates_api import template_app

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

# Load configuration
with open('cfg.json') as file:
    cfg = json.load(file)

# Use a thread-local storage for database connections
local = threading.local()

app = Flask(__name__)
CORS(app, origins='*',
          methods=['GET', 'POST', 'PUT', 'DELETE'],
          allow_headers=['Content-Type', 'Authorization'],
          supports_credentials=True)

# Register the task_app blueprint
app.register_blueprint(task_app, url_prefix='/task')
app.register_blueprint(template_app, url_prefix='/template')

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
