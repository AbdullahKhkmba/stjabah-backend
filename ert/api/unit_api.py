"""API handlers for ERT unit endpoints"""

from flask import Blueprint, json, request, jsonify
import logging
import asyncio

from ert.service.unit_service import UnitService

logger = logging.getLogger(__name__)

ert_bp = Blueprint('ert', __name__)

def init_ert_api(unit_service: UnitService):
    """Initialize the ERT API with service dependencies"""
    ert_bp.unit_service = unit_service
    return ert_bp

@ert_bp.route('/unit/location', methods=['GET'])
def get_unit_location():
    try:
        with open("ert/unit_info.json", "r") as f:
            unit_info = json.load(f)
            location = {
                "x": unit_info["x"],
                "y": unit_info["y"]
            }
        return jsonify(location), 200
    except Exception as e:
        logger.error(f"Error retrieving unit location: {str(e)}")
        return jsonify({
            'error': 'Internal server error'
        }), 500

@ert_bp.route('/unit', methods=['GET'])
def get_unit_info():
    try:
        with open("ert/unit_info.json", "r") as f:
            unit_info = json.load(f)
        return jsonify(unit_info), 200
    except Exception as e:
        logger.error(f"Error retrieving unit info: {str(e)}")
        return jsonify({
            'error': 'Internal server error'
        }), 500
    
@ert_bp.route('/unit/location', methods=['PUT'])
def update_unit_location():
    try:
        data = request.get_json()
        if data is None:
            return jsonify({
                'error': 'Invalid JSON payload'
            }), 400

        if 'x' not in data:
            return jsonify({
                'error': 'Missing x coordinate'
            }), 400
        
        if not isinstance(data['x'], (int, float)):
            return jsonify({
                'error': 'Invalid x coordinate'
            }), 400

        if 'y' not in data:
            return jsonify({
                'error': 'Missing y coordinate'
            }), 400
        
        if not isinstance(data['y'], (int, float)):
            return jsonify({
                'error': 'Invalid y coordinate'
            }), 400

        with open("ert/unit_info.json", "r") as f:
            unit_info = json.load(f)

        unit_info["x"] = data["x"]
        unit_info["y"] = data["y"]

        with open("ert/unit_info.json", "w") as f:
            json.dump(unit_info, f, indent=2)

        return jsonify(unit_info), 200
    except Exception as e:
        logger.error(f"Error updating unit location: {str(e)}")
        return jsonify({
            'error': 'Internal server error'
        }), 500

@ert_bp.route('/incident/location', methods=['GET'])
def get_incident_location():
    try:
        with open("ert/unit_info.json", "r") as f:
            unit_info = json.load(f)
            location = {
                "x": unit_info["assigned_incident"]["x"],
                "y": unit_info["assigned_incident"]["y"]
            }
        return jsonify(location), 200
    except Exception as e:
        logger.error(f"Error retrieving incident location: {str(e)}")
        return jsonify({
            'error': 'Internal server error'
        }), 500
    
@ert_bp.route('/incident/resolve', methods=['PUT'])
def resolve_incident():
    try:
        # check that an incident is assigned to the unit before trying to resolve it
        with open("ert/unit_info.json", "r") as f:
            unit_info = json.load(f)
            if unit_info["assigned_incident"] is None:
                return jsonify({
                    'error': 'No incident assigned to this unit'
                }), 400
            
        asyncio.run(ert_bp.unit_service.resolve_incident())

        return jsonify({
            'message': 'Incident resolved successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error resolving incident: {str(e)}")
        return jsonify({
            'error': 'Internal server error'
        }), 500