import asyncio
import sys
import threading
import logging
from pathlib import Path
from service.unit_service import UnitService
from flask import json, Flask
from flask_cors import CORS

# Add parent directory to Python path to resolve imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from communication.websocket_communication import WebSocketCommunication
from ert.api.unit_api import ert_bp, init_ert_api

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# get id from unit_info.json file
with open("ert/unit_info.json", "r") as f:
    unit_info = json.load(f)
    ert_id = unit_info["id"]

# --- Callbacks ---
async def on_new_incident(data):
    """Handle incoming incident from control room"""
    print(f"\n[ERT-{ert_id}] 🚨 RECEIVED INCIDENT: {data}")
    print(f"[ERT-{ert_id}] Preparing vehicle...")
    
    # handle the case where the send incident is empty (when an incident is deleted)
    if not data:
        print(f"[ERT-{ert_id}] Incident deleted. Clearing assigned incident and updating status.")
        unit_info["assigned_incident"] = None
        unit_info["status"] = "available"
        with open("ert/unit_info.json", "w") as f:
            json.dump(unit_info, f, indent=4)
        print(f"[ERT-{ert_id}] Updated unit info to available with no assigned incident.")
        return
    
    incident_id = data.get("id")
    unit_info["assigned_incident"] = data  # Store the full incident data
    
    # Update unit_info.json with assigned incident and status
    unit_info["status"] = "dispatched"
    with open("ert/unit_info.json", "w") as f:
        json.dump(unit_info, f, indent=4)
    print(f"[ERT-{ert_id}] Updated unit info with assigned incident: {incident_id}")
    
    # Send acknowledgment to control room
    acknowledgment = {
        "ert_id": ert_id,
        "incident_id": incident_id,
        "x": data.get("x", 100),
        "y": data.get("y", 200),
        "message": "Incident received successfully. ERT unit dispatched.",
        "status": "acknowledged"
    }
    
    await ert_comms.publish("acknowledgment", acknowledgment)
    print(f"[ERT-{ert_id}] ✅ Acknowledgment sent to control room")

# --- Main ERT Logic ---
ert_comms = WebSocketCommunication()

async def main():
    # 1. Connect to Hub and register in one call
    await ert_comms.connect(
        "ws://localhost:8765",
        client_type="ert",
        client_id=ert_id
    )
    print(f"[ERT-{ert_id}] Connected and registered with hub")
    
    # 2. Subscribe to Incidents
    await ert_comms.subscribe("new_incident", on_new_incident)
    print(f"[ERT-{ert_id}] Subscribed to incident notifications")
    
    # Comment out the simulation loop

    while True:
        # Simulate GPS coordinates
        # unit_service = UnitService()
        # unit_service.update_gps_location()

        # read x and y from unit_info.json file
        with open("ert/unit_info.json", "r") as f:
            unit_info = json.load(f)
            x = unit_info["x"]
            y = unit_info["y"]

        location_data = {
            "ert_id": ert_id,
            "x": x,
            "y": y
        }   
        
        print(f"[ERT-{ert_id}] Sending Location...")
        await ert_comms.publish("location", location_data)
        
        await asyncio.sleep(5)  # Send every 5 seconds

if __name__ == "__main__":
    # Initialize Unit Service with the connected communication channel
    unit_service = UnitService(communication_channel=ert_comms)
    
    # Create Flask app with ERT API
    app = Flask(__name__)
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    CORS(app)
    
    logger.info("📋 Registering ERT Unit API blueprints...")
    ert_bp_instance = init_ert_api(unit_service)
    app.register_blueprint(ert_bp_instance, url_prefix='/ert')
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return {
            'status': 'healthy',
            'service': 'emergency-response-system',
            'component': f'ert-{ert_id}'
        }, 200
    
    logger.info("✓ Flask application configured successfully")
    
    def run_flask():
        """Run Flask API server"""
        logger.info(f"🚀 Starting ERT-{ert_id} API server...")
        logger.info(f"   ERT Unit Location: http://127.0.0.1:5002/ert/unit/location")
        logger.info(f"   ERT Assigned Incident: http://127.0.0.1:5002/ert/assigned_incident/location")
        logger.info(f"   Health check: http://127.0.0.1:5002/health")
        
        app.run(
            host='127.0.0.1',
            port=5002,
            debug=False,
            use_reloader=False
        )
    
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=False)
    flask_thread.start()
    
    # Run WebSocket loop in main thread
    asyncio.run(main())