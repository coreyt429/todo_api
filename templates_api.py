"""
todo_api flask template_app to handle server side api

"""
from flask import request, jsonify, blueprints
import uuid
from tinydb import Query
import json
import logging
from todo_util import token_required, get_current_iso_timestamp, apply_template_defaults
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

template_app = blueprints.Blueprint('template_app', __name__)

####################################################################################################
#  /template
####################################################################################################
@template_app.route('/search', methods=['GET'])
@token_required
def get_template_search_all():
    """
    Get all templates
    ---
    tags:
      - Templates
    responses:
      200:
        description: A list of templates
        schema:
          type: array
          items:
            type: object
            properties:
              template_id:
                type: string
                example: "123e4567-e89b-12d3-a456-426614174000"
              parent:
                type: string
                example: "parent_template_id"
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
                example: "template"
    """
    with get_db() as db:
            # Get all templates
            results = db.all()
    return jsonify(results)

@template_app.route('/search/<string:query>', methods=['GET'])
@token_required
def get_template_search(query):
    """
    Search templates by query
    ---
    tags:
      - Templates
    parameters:
      - in: path
        name: query
        type: string
        required: true
        description: The search query
    responses:
      200:
        description: A list of templates matching the query
        schema:
          type: array
          items:
            type: object
            properties:
              template_id:
                type: string
                example: "123e4567-e89b-12d3-a456-426614174000"
              parent:
                type: string
                example: "parent_template_id"
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
                example: "template"
    """
    with get_db() as db:
        query = query.lower()
        results = []
        for item in db.all():
            for key, value in item.items():
                if query in str(key).lower() or query in str(value).lower():
                    results.template_append(item)
                    break
    return jsonify(results)

@template_app.route('/search/<string:field>/<string:query>', methods=['GET'])
@token_required
def get_template_search_field(query, field):
    """
    Search templates by field and query
    ---
    tags:
      - Templates
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
        description: A list of templates matching the field and query
        schema:
          type: array
          items:
            type: object
            properties:
              template_id:
                type: string
                example: "123e4567-e89b-12d3-a456-426614174000"
              parent:
                type: string
                example: "parent_template_id"
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
                example: "template"
    """
    with get_db() as db:
        query = query.lower()
        results = []
        for item in db.all():
            if query in item.get(field, '').lower():
                results.template_append(item)
    return jsonify(results)


@template_app.route('/', methods=['POST'])
@token_required
def post_template():
    """
    Create a new template
    ---
    tags:
      - Templates
    parameters:
      - in: body
        name: body
        description: The template to create
        required: true
        schema:
          type: object
          properties:
            parent:
              type: string
              example: "parent_template_id"
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
              example: "template"
    responses:
      201:
        description: Template created successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: "template created successfully"
            template_id:
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
        description: Failed to create template
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Failed to create template"
    """
    logger.debug(f"{request.method} /template")
    # Handle POST and PUT requests (add and update)
    template = apply_template_defaults(request.json)
    logger.debug(json.dumps(template, indent=2))
    # Generate a new template_id
    template_id = str(uuid.uuid4())
    # Set template_id in the JSON if not provided
    template.setdefault('template_id', template_id)
    
    # FIXME: we should .lower() field names before saving
    with get_db(db='template') as db:
        result = db.insert(template)
    if result:
        return jsonify({
            'message': 'template created successfully',
            'template_id': template['template_id']
        }), 201
    return jsonify({'message': 'Failed to create template'}), 503





@template_app.route('/<string:template_id>', methods=['PUT'])
@token_required
def put_template(template_id):
    """
    Update an existing template or create a new one if template_id is not provided.
    ---
    tags:
      - Templates
    put:
      summary: Update an existing template
      description: Update an existing template by template_id or create a new one if template_id is not provided.
      parameters:
        - in: path
          name: template_id
          required: false
          description: The ID of the template to update.
          schema:
            type: string
        - in: body
          name: template
          required: true
          description: The template data to update.
          schema:
            type: object
            properties:
              template_id:
                type: string
                description: The ID of the template.
              status:
                type: string
                description: The status of the template.
              timestamps:
                type: object
                properties:
                  completed:
                    type: string
                    format: date-time
                    description: The completion timestamp of the template.
                  updated:
                    type: string
                    format: date-time
                    description: The last updated timestamp of the template.
      responses:
        200:
          description: Template updated successfully
          content:
            template_application/json:
              schema:
                type: object
                properties:
                  message:
                    type: string
                    example: Template updated successfully
        404:
          description: Template not found
          content:
            template_application/json:
              schema:
                type: object
                properties:
                  message:
                    type: string
                    example: Template not found
    """

    logger.debug(f"{request.method} /template/{template_id}")
    query = Query()

    # Handle  PUT requests (update)
    template = apply_template_defaults(request.json)
    logger.debug(json.dumps(template, indent=2))
    # Generate a new template_id if not provided in the path
    if not template_id:
        template_id = str(uuid.uuid4())

    # Set template_id in the JSON if not provided
    template.setdefault('template_id', template_id)
    
    # Update the template if method is PUT
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

@template_app.route('/<string:template_id>', methods=['POST'])
@token_required
def post_template_deprecated(template_id):
    """
    Create a new template (deprecated)
    ---
    tags:
      - Templates
    parameters:
      - in: path
        name: template_id
        type: string
        required: true
        description: The ID of the template to create
      - in: body
        name: body
        description: The template to create
        required: true
        schema:
          type: object
          properties:
            parent:
              type: string
              example: "parent_template_id"
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
              example: "template"
    responses:
      201:
        description: Template created successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: "template created successfully"
            template_id:
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
        description: Failed to create template
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Failed to create template"
    """
    logger.debug(f"{request.method} /template/{template_id}")
    query = Query()

    # Handle POST requests (add and update)
    template = apply_template_defaults(request.json)
    logger.debug(json.dumps(template, indent=2))
    # Generate a new template_id if not provided in the path
    if not template_id:
        template_id = str(uuid.uuid4())

    # Set template_id in the JSON if not provided
    template.setdefault('template_id', template_id)
    
    # FIXME: we should .lower() field names before saving
    with get_db(db='template') as db:
        result = db.insert(template)
    if result:
        return jsonify({
            'message': 'template created successfully',
            'template_id': template['template_id']
        }), 201
    return jsonify({'message': 'Failed to create template'}), 503
    
    
@template_app.route('/<string:template_id>', methods=['GET'])
@token_required
def get_template(template_id):
    """
    Get a specific template by its ID
    ---
    tags:
      - Templates
    parameters:
      - name: template_id
        in: path
        type: string
        required: true
        description: The ID of the template to retrieve
    responses:
      200:
        description: The template with the specified ID
        schema:
          type: object
          properties:
            template_id:
              type: string
              example: "123e4567-e89b-12d3-a456-426614174000"
            parent:
              type: string
              example: "parent_template_id"
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
              example: "template"
      404:
        description: Template not found
        schema:
          type: object
          properties:
            message:
              type: string
              example: "template not found"
    """
    logger.debug(f"{request.method} /template/{template_id}")
    query = Query()
    with get_db(db='template') as db:
        # Get a specific template
        template = db.get(query.template_id == template_id)
    if template:
        return jsonify(template)
    return jsonify({'message': 'template not found'}), 404

@template_app.route('/', methods=['GET'])
@token_required
def get_template_list():
    """
    Get all templates
    ---
    tags:
      - Templates
    responses:
      200:
        description: A list of templates
        schema:
          type: array
          items:
            type: object
            properties:
              template_id:
                type: string
                example: "123e4567-e89b-12d3-a456-426614174000"
              parent:
                type: string
                example: "parent_template_id"
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
                example: "template"
    """
    logger.debug(f"{request.method} /template")
    with get_db(db='template') as db:
        # Get all templates if no template_id is provided
        templates = db.all()
    return jsonify(templates)
        
@template_app.route('/<string:template_id>', methods=['DELETE'])
@token_required
def delete_template(template_id):
    """
    Delete a template by its ID.

    This endpoint deletes a template from the database if it exists and has no child templates.
    If the template has child templates, it returns a 403 status code to prevent orphaned templates.

    ---
    tags:
      - Templates
    parameters:
      - name: template_id
        in: path
        type: string
        required: true
        description: The ID of the template to delete.
    responses:
      200:
        description: Template deleted successfully.
        schema:
          type: object
          properties:
            message:
              type: string
              example: template deleted successfully
      403:
        description: Delete would cause orphans.
        schema:
          type: object
          properties:
            message:
              type: string
              example: delete would cause orphans
      404:
        description: Template not found.
        schema:
          type: object
          properties:
            message:
              type: string
              example: template not found
    """
    logger.debug(f"{request.method} /template/{template_id}")
    query = Query()
    with get_db(db='template') as db:
        children = db.get(query.parent == template_id)
    if children:
        return jsonify({'message': 'delete would cause orphans'}), 403
    with get_db(db='template') as db:
        result = db.remove(query.template_id == template_id)
    if result:
        return jsonify({'message': 'template deleted successfully'}), 200
    return jsonify({'message': 'template not found'}), 404

if __name__ == '__main__':
    template_app.run(debug=True)
