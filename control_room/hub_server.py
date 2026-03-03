import asyncio
import json
import websockets
from collections import defaultdict

# Store subscriptions: topic -> set of connected sockets
subscriptions = defaultdict(set)
connected_clients = set()
client_info = {}  # websocket -> {'type': 'cr'/'ert', 'id': str}
websocket_handlers = None  # Will be set by cr_main.py
active_incident = None  # Global variable to hold the current active incident state

async def handler(websocket):
    print(f"Client connected: {websocket.remote_address}")
    connected_clients.add(websocket)
    client_id = None
    client_type = None
    global active_incident

    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")
            topic = data.get("topic")
            
            # 0. Handle Client Registration (identify CR or ERT)
            if msg_type == "register":
                client_type = data.get("client_type")  # 'cr' or 'ert'
                client_id = data.get("client_id")  # unit ID or 'control_room'
                client_info[websocket] = {"type": client_type, "id": client_id}
                print(f"[HUB SERVER] - Client registered: {client_type.upper()} - {client_id}")
                continue

            if msg_type == "subscribe":
                subscriptions[topic].add(websocket)
                
                if topic == "active_incident" and active_incident:
                    try:
                        print("[HUB SERVER] - Sending current active incident to new subscriber")
                        await websocket.send(json.dumps({
                            "topic": topic,
                            "payload": active_incident
                        }))
                    except TypeError as e:
                        print(f"[HUB SERVER] - ERROR: Failed to serialize active_incident: {e}")

                print(f"[HUB SERVER] - Client subscribed to '{topic}'")

            # 2. Handle Publish Requests
            elif msg_type == "publish":
                payload = data.get("payload")
                print(f"[HUB SERVER] - Broadcasting message on '{topic}': {payload}")
                if topic == "active_incident":
                    active_incident = payload  # Update the active incident state

                # Forward the message to everyone subscribed to this topic
                # EXCLUDING the sender (optional, usually desired)
                if topic in subscriptions:
                    # Create the standard message format
                    response = json.dumps({
                        "topic": topic,
                        "payload": payload
                    })
                    
                    # Send to all subscribers
                    subscribers = subscriptions[topic]
                    for subscriber in subscribers:
                        # Optional: Don't echo back to sender if you don't want to
                        # if subscriber != websocket: 
                        await subscriber.send(response)

    except websockets.exceptions.ConnectionClosed:
        print(f"[HUB SERVER] - Client disconnected: {websocket.remote_address}")
    finally:
        # Cleanup
        connected_clients.remove(websocket)
        for topic in subscriptions:
            subscriptions[topic].discard(websocket)
        
        # Handle disconnection for ERT units
        if websocket in client_info:
            info = client_info[websocket]
            client_type = info.get("type")
            client_id = info.get("id")
            
            # Call handler for ERT disconnection to remove from incident assignments
            if client_type == "ert" and websocket_handlers:
                try:
                    # Schedule the handler as a task
                    task = asyncio.create_task(websocket_handlers.handle_disconnection(client_id))
                except Exception as e:
                    print(f"Error handling disconnection for {client_id}: {e}")
            
            del client_info[websocket]

async def main(handlers=None):
    # Set the handlers reference for disconnect handling
    global websocket_handlers
    websocket_handlers = handlers
    
    # Listen on all interfaces (0.0.0.0) on port 8765
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("Hub Server started on ws://0.0.0.0:8765")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())