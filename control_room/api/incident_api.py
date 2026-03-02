"""API handlers for Control Room incident endpoints"""
from control_room.model import incident
from flask import Blueprint, request, jsonify
import logging
import asyncio
from control_room.service.incident_service import IncidentService
from control_room.service.unit_service import UnitService

logger = logging.getLogger(__name__)

control_room_bp = Blueprint('control_room', __name__)

def init_control_room_api(incident_service: IncidentService, unit_service: UnitService):
    """Initialize the Control Room API with service dependencies"""
    control_room_bp.incident_service = incident_service
    control_room_bp.unit_service = unit_service
    return control_room_bp

@control_room_bp.route('/incidents/<incident_id>', methods=['GET'])
def get_incident_by_id(incident_id: str):
    try:
        incident = control_room_bp.incident_service.get_incident_by_id(incident_id)

        if incident is None:
            return jsonify({
                'error': 'Incident not found',
                'incident_id': incident_id
            }), 404
        
        return jsonify(incident.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error retrieving incident {incident_id}: {str(e)}")
        return jsonify({
            'error': 'Internal server error'
        }), 500

@control_room_bp.route('/incidents', methods=['GET'])
def list_incidents():
    try:
        incidents = control_room_bp.incident_service.get_all_incidents()
        incidents_data = [incident.to_dict() for incident in incidents]
        
        return jsonify(incidents_data), 200
        
    except Exception as e:
        logger.error(f"Error listing incidents: {str(e)}")
    
@control_room_bp.route('/incidents', methods=['POST'])
def create_incident():
    try:
        data = request.get_json()
        if data is None:
            return jsonify({
                'error': 'Invalid JSON payload'
            }), 400
        
        # Give error if the user try to create a new incident while there is still a one that is not resolved
        open_incidents = control_room_bp.incident_service.get_open_incidents()
        if len(open_incidents) > 0:
            return jsonify({
                'error': 'There is already an open incident. Please resolve it before creating a new one.',
                'open_incidents': [incident.to_dict() for incident in open_incidents]
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
        
        incident = control_room_bp.incident_service.create_incident(data['x'], data['y'])
        return jsonify(incident.to_dict()), 201

    except Exception as e:
        logger.error(f"Error creating incident: {str(e)}")
        return jsonify({
            'error': 'Internal server error'
        }), 500
    
@control_room_bp.route('/incidents/<incident_id>', methods=['DELETE'])
async def delete_incident(incident_id):
    """
    Delete an incident from the system
    
    Args:
        incident_id: The unique identifier of the incident to delete
    
    Returns:
        200: Incident deleted successfully with success message
        404: Incident not found with error message
    """    
    try:
        # We MUST await the service call because it is an async def
        deleted = await control_room_bp.incident_service.delete_incident(incident_id)
        return jsonify({"message": "Incident deleted successfully"}), 200

    except ValueError as e:
        # Catch the "Incident does not exist" error from your service
        return jsonify({'error': str(e)}), 404

    except Exception as e:
        logger.error(f"Error deleting incident {incident_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@control_room_bp.route('/incidents/<incident_id>', methods=['PUT'])
async def update_incident(incident_id):
    """
    Update incident coordinates
    Args:
        incident_id: The unique identifier of the incident to update
    Returns:
        200: Incident updated successfully with updated incident data
    """

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
    
    try:
        # We MUST await the service call because it is an async def
        incident = await control_room_bp.incident_service.update_incident(
            incident_id, 
            data['x'], 
            data['y']
        )
        return jsonify(incident.to_dict()), 200

    except ValueError as e:
        # Catch the "Incident does not exist" error from your service
        return jsonify({'error': str(e)}), 404

    except Exception as e:
        logger.error(f"Error updating incident {incident_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
    
@control_room_bp.route('/incidents/dispatch', methods=['POST'])
def dispatch_incident():
    """
    Dispatch the currently running incident to the Emergency Response Team (ERT).

    Behavior:
    - If there is no running (open) incident, return 400.
    - Otherwise dispatch the single running incident and return 200.
    """
    try:
        open_incidents = control_room_bp.incident_service.get_open_incidents()

        if not open_incidents:
            return jsonify({'error': 'No running incident to dispatch'}), 400

        incident = open_incidents[0]
        incident_id = incident.id

        # Run the async dispatch method
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(
                control_room_bp.incident_service.dispatch_incident(incident_id)
            )
            loop.close()
        except RuntimeError:
            # If there's already an event loop, use it
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run,
                        control_room_bp.incident_service.dispatch_incident(incident_id))
                    success = future.result()
            else:
                success = loop.run_until_complete(
                    control_room_bp.incident_service.dispatch_incident(incident_id)
                )

        if success:
            return jsonify({
                'message': 'Incident dispatched successfully',
                'incident': incident.to_dict()
            }), 200
        else:
            return jsonify({
                'error': 'Failed to dispatch incident'
            }), 500

    except Exception as e:
        logger.error(f"Error dispatching incident: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
    
# Add endpoint that return running incident (it is always one or zero)
# This endpoint will be used by control room frontend to show current location of the incident and assigned units
@control_room_bp.route('/incidents/open', methods=['GET'])
def get_open_incidents():
    try:
        open_incidents = control_room_bp.incident_service.get_open_incidents()
        open_incidents_data = [incident.to_dict() for incident in open_incidents]
        
        if not open_incidents_data:
            return jsonify({}), 200  # Return empty JSON if no open incidents
        
        return jsonify(open_incidents_data[0]), 200
        
    except Exception as e:
        logger.error(f"Error retrieving open incidents: {str(e)}")
        return jsonify({
            'error': 'Internal server error'
        }), 500
    
# Add endpoint to get assigned units info for the running incident (it is always one or zero)
@control_room_bp.route('/units/open_incident', methods=['GET'])
def get_units_for_open_incident():
    try:
        open_incidents = control_room_bp.incident_service.get_open_incidents()
        
        if not open_incidents:
            return jsonify({}), 200  # Return empty JSON if no open incidents
        
        incident = open_incidents[0]
        all_units = control_room_bp.unit_service.get_all_units()
        assigned_units_info = [
            unit.to_dict() for unit in all_units
            if unit.assigned_incident == incident.id
        ]
        
        return jsonify(assigned_units_info), 200
            
    except Exception as e:
        logger.error(f"Error retrieving assigned units for open incident: {str(e)}")
        return jsonify({
            'error': 'Internal server error'
        }), 500