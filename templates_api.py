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


@template_app.route('/', methods=['GET', 'POST'])
@template_app.route('/<string:template_id>', methods=['GET', 'PUT', 'POST', 'DELETE'])
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
