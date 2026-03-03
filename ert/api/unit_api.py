"""API handlers for ERT unit endpoints"""

from control_room.model import incident
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
                "lat": unit_info["lat"],
                "lng": unit_info["lng"]
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

        if 'lat' not in data:
            return jsonify({
                'error': 'Missing latitude coordinate'
            }), 400
        
        if not isinstance(data['lat'], (int, float)):
            return jsonify({
                'error': 'Invalid latitude coordinate'
            }), 400

        if 'lng' not in data:
            return jsonify({
                'error': 'Missing longitude coordinate'
            }), 400
        
        if not isinstance(data['lng'], (int, float)):
            return jsonify({
                'error': 'Invalid longitude coordinate'
            }), 400

        with open("ert/unit_info.json", "r") as f:
            unit_info = json.load(f)

        unit_info["lat"] = data["lat"]
        unit_info["lng"] = data["lng"]
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
<<<<<<< feature/late_ert_joiners
            if unit_info["assigned_incident"] is not None:
                location = {
                    "x": unit_info["assigned_incident"]["x"],
                    "y": unit_info["assigned_incident"]["y"]
                }
            else:
                location = {
                    "x": None,
                    "y": None
                }
                
=======
            location = {
                "lat": unit_info["assigned_incident"]["lat"],
                "lng": unit_info["assigned_incident"]["lng"]
            }
>>>>>>> main
        return jsonify(location), 200
    except Exception as e:
        logger.error(f"Error retrieving incident location: {str(e)}")
        return jsonify({
            'error': 'Internal server error'
        }), 500
    
@ert_bp.route('/incident/resolve', methods=['PUT'])
async def resolve_incident():   
    try:
        with open("ert/unit_info.json", "r") as f:
            unit_info = json.load(f)
            if unit_info["assigned_incident"] is None:
                return jsonify({
                    'error': 'No incident assigned to this unit'
                }), 400
            
        # We MUST await the service call because it is an async def
        await ert_bp.unit_service.resolve_assigned_incident(unit_info["id"])
        return jsonify({"message": "Incident resolved successfully"}), 200

    except ValueError as e:
        # Catch the "Incident does not exist" error from your service
        return jsonify({'error': str(e)}), 404

    except Exception as e:
        logger.error(f"Error resolving incident: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500