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
from datetime import datetime
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
def _restore_timestamp_value(item):
    timestamps = item.get('timestamps') or {}
    candidate = timestamps.get('updated') or timestamps.get('created')
    if not candidate:
        return None
    try:
        return datetime.fromisoformat(str(candidate).replace('Z', '+00:00'))
    except ValueError:
        return None


def _restore_collection(collection_name, items, id_field, conflict_resolution):
    restored = 0
    skipped = 0
    query = Query()
    with get_db(db=collection_name) as db:
        for item in items:
            if not isinstance(item, dict):
                skipped += 1
                continue

            item_id = item.get(id_field)
            if not item_id:
                skipped += 1
                continue

            existing = db.get(query[id_field] == item_id)
            if existing is None:
                db.insert(item)
                restored += 1
                continue

            should_replace = conflict_resolution == 'overwrite'
            if conflict_resolution == 'newest':
                backup_ts = _restore_timestamp_value(item)
                existing_ts = _restore_timestamp_value(existing)
                if backup_ts is None:
                    should_replace = False
                elif existing_ts is None:
                    should_replace = True
                else:
                    should_replace = backup_ts >= existing_ts

            if should_replace:
                db.remove(query[id_field] == item_id)
                db.insert(item)
                restored += 1
            else:
                skipped += 1

    return restored, skipped


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


@app.route('/restore', methods=['POST'])
@token_required
def handle_restore():
    """
    Restore tasks and templates from a backup payload
    ---
    tags:
      - Backup
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            conflict_resolution:
              type: string
              enum: [newest, overwrite]
              example: overwrite
            tasks:
              type: array
              items:
                type: object
            templates:
              type: array
              items:
                type: object
    responses:
      200:
        description: Backup restored successfully
      400:
        description: Invalid restore payload
    """
    payload = request.get_json(silent=True) or {}
    conflict_resolution = payload.get('conflict_resolution')
    if conflict_resolution not in {'newest', 'overwrite'}:
        return jsonify({'message': 'Invalid conflict_resolution'}), 400

    tasks = payload.get('tasks') or []
    templates = payload.get('templates') or []
    if not isinstance(tasks, list):
        return jsonify({'message': 'tasks must be a list'}), 400
    if templates and not isinstance(templates, list):
        return jsonify({'message': 'templates must be a list'}), 400

    tasks_restored, tasks_skipped = _restore_collection('task', tasks, 'task_id', conflict_resolution)
    templates_restored, templates_skipped = _restore_collection(
        'template', templates, 'template_id', conflict_resolution
    )

    return jsonify(
        {
            'message': 'restore completed',
            'conflict_resolution': conflict_resolution,
            'tasks_restored': tasks_restored,
            'tasks_skipped': tasks_skipped,
            'templates_restored': templates_restored,
            'templates_skipped': templates_skipped,
        }
    )


@app.route('/menu', methods=['GET'])
def get_menu():
    """
    Get the menu structure
    ---
    tags:
      - Menu
    responses:
      200:
        description: A list of menu items
        schema:
          type: array
          items:
            type: object
            properties:
              title:
                type: string
                example: "Tasks"
              caption:
                type: string
                example: "Manage your tasks"
              icon:
                type: string
                example: "task"
              link:
                type: string
                example: "/tasks"
    """
    menu = [
        {
        "title": "Tools",
        "caption": "",
        "icon": "build",
        "link": "",
        "children": [
          {
            "title": "Locate",
            "caption": "",
            "icon": "",
            "link": "/#/locate",
          },
          {
            "title": "Tagtool",
            "caption": "",
            "icon": "",
            "link": "/#/tagtool",
          },
        ],
      },
      {
        "title": "Documentation",
        "caption": "",
        "icon": "school",
        "link": "",
        "children": [
          {
            "title": "Code",
            "caption": "",
            "icon": "",
            "link": "",
            "children": [
              {
                "title": "Quasar Framework",
                "caption": "quasar.dev",
                "icon": "school",
                "link": "https://quasar.dev",
                "parent": "Docs",
              },
            ],
          },
        ],
      },
      {
        "title": "Github",
        "caption": "github.com/quasarframework",
        "icon": "code",
        "link": "https://github.com/quasarframework",
      },
      {
        "title": "Social Media",
        "caption": "",
        "icon": "share",
        "link": "",
        "children": [
          {
            "title": "Discord Chat Channel",
            "caption": "chat.quasar.dev",
            "icon": "chat",
            "link": "https://chat.quasar.dev",
          },
          {
            "title": "Forum",
            "caption": "forum.quasar.dev",
            "icon": "record_voice_over",
            "link": "https://forum.quasar.dev",
          },
          {
            "title": "Twitter",
            "caption": "@quasarframework",
            "icon": "rss_feed",
            "link": "https://twitter.quasar.dev",
          },
          {
            "title": "Facebook",
            "caption": "@QuasarFramework",
            "icon": "public",
            "link": "https://facebook.quasar.dev",
          },
          {
            "title": "Quasar Awesome",
            "caption": "Community Quasar projects",
            "icon": "favorite",
            "link": "https://awesome.quasar.dev",
          },
        ],
      },
    ]
    return jsonify(menu)

@app.route('/locate', methods=['GET'])
def locate():
    """
    Get the locate page content
    ---
    tags:
      - Locate
    responses:
      200:
        description: Locate page content
        schema:
          type: object
          properties:
            title:
              type: string
              example: "Locate Page"
            description:
              type: string
              example: "This is the locate page."
    """
    locate_results = [
      {"id": 1, "name": "Item 1", "description": "Description for Item 1"},
      {"id": 2, "name": "Item 2", "description": "Description for Item 2"},
      {"id": 3, "name": "Item 3", "description": "Description for Item 3"},
      {"id": 4, "name": "Item 4", "description": "Description for Item 4"},
      {"id": 5, "name": "Item 5", "description": "Description for Item 5"},
      {"id": 6, "name": "Item 6", "description": "Description for Item 6"},
      {"id": 7, "name": "Item 7", "description": "Description for Item 7"},
      {"id": 8, "name": "Item 8", "description": "Description for Item 8"},
      {"id": 9, "name": "Item 9", "description": "Description for Item 9"},
      {"id": 10, "name": "Item 10", "description": "Description for Item 10"},
      {"id": 11, "name": "Item 11", "description": "Description for Item 11"},
      {"id": 12, "name": "Item 12", "description": "Description for Item 12"},
      {"id": 13, "name": "Item 13", "description": "Description for Item 13"},
      {"id": 14, "name": "Item 14", "description": "Description for Item 14"},
      {"id": 15, "name": "Item 15", "description": "Description for Item 15"},
      {"id": 16, "name": "Item 16", "description": "Description for Item 16"},
      {"id": 17, "name": "Item 17", "description": "Description for Item 17"},
      {"id": 18, "name": "Item 18", "description": "Description for Item 18"},
      {"id": 19, "name": "Item 19", "description": "Description for Item 19"},
      {"id": 20, "name": "Item 20", "description": "Description for Item 20"},
      {"id": 21, "name": "Item 21", "description": "Description for Item 21"},
      {"id": 22, "name": "Item 22", "description": "Description for Item 22"},
      {"id": 23, "name": "Item 23", "description": "Description for Item 23"},
      {"id": 24, "name": "Item 24", "description": "Description for Item 24"},
      {"id": 25, "name": "Item 25", "description": "Description for Item 25"},
      {"id": 26, "name": "Item 26", "description": "Description for Item 26"},
      {"id": 27, "name": "Item 27", "description": "Description for Item 27"},
      {"id": 28, "name": "Item 28", "description": "Description for Item 28"},
      {"id": 29, "name": "Item 29", "description": "Description for Item 29"},
      {"id": 30, "name": "Item 30", "description": "Description for Item 30"},
      {"id": 31, "name": "Item 31", "description": "Description for Item 31"},
      {"id": 32, "name": "Item 32", "description": "Description for Item 32"},
      {"id": 33, "name": "Item 33", "description": "Description for Item 33"},
      {"id": 34, "name": "Item 34", "description": "Description for Item 34"},
      {"id": 35, "name": "Item 35", "description": "Description for Item 35"},
      {"id": 36, "name": "Item 36", "description": "Description for Item 36"},
      {"id": 37, "name": "Item 37", "description": "Description for Item 37"},
      {"id": 38, "name": "Item 38", "description": "Description for Item 38"},
      {"id": 39, "name": "Item 39", "description": "Description for Item 39"},
      {"id": 40, "name": "Item 40", "description": "Description for Item 40"},
      {"id": 41, "name": "Item 41", "description": "Description for Item 41"},
      {"id": 42, "name": "Item 42", "description": "Description for Item 42"},
      {"id": 43, "name": "Item 43", "description": "Description for Item 43"},
      {"id": 44, "name": "Item 44", "description": "Description for Item 44"},
      {"id": 45, "name": "Item 45", "description": "Description for Item 45"},
      {"id": 46, "name": "Item 46", "description": "Description for Item 46"},
      {"id": 47, "name": "Item 47", "description": "Description for Item 47"},
      {"id": 48, "name": "Item 48", "description": "Description for Item 48"},
      {"id": 49, "name": "Item 49", "description": "Description for Item 49"},
      {"id": 50, "name": "Item 50", "description": "Description for Item 50"},
    ]
    return jsonify(locate_results)

if __name__ == '__main__':
    app.run(debug=True)
