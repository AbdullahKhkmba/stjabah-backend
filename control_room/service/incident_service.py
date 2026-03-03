"""Business logic for Control Room incident management"""

import uuid
from control_room.model import incident
from control_room.repository.in_memory_incident_repository import InMemoryIncidentRepository
from control_room.model.incident import Incident, IncidentStatus
from communication.websocket_communication import WebSocketCommunication
from typing import List

class IncidentService:
    def __init__(
        self,
        incident_repository: InMemoryIncidentRepository,
        communication_channel: WebSocketCommunication
    ):
        self.incident_repository = incident_repository
        self.communication_channel = communication_channel

    def create_incident(self, x: float, y: float) -> Incident:
        incident = Incident(
            x=x,
            y=y,
            status=IncidentStatus.CREATED
        )
        created_incident = self.incident_repository.create(incident)
        return created_incident

    def get_incident_by_id(self, incident_id: str):
        return self.incident_repository.get_by_id(incident_id)

    async def update_incident(self, incident_id: str, x: float, y: float):
        """
        Update incident coordinates

        Args:
            incident_id: ID of the incident
            x: New x coordinate
            y: New y coordinate
        """
        incident = self.incident_repository.get_by_id(incident_id)

        if not incident:
            raise ValueError(f"Incident with ID {incident_id} does not exist.")
        
        incident.x = x
        incident.y = y
        updated_incident = self.incident_repository.update(incident)

        if incident.status != IncidentStatus.CREATED:
            # Notify ERT units about the updated incident
            await self.communication_channel.publish(
                topic="active_incident",
                message=updated_incident.to_dict()
            )

        return updated_incident

    def get_all_incidents(self) -> List[Incident]:
        return self.incident_repository.get_all()
    
    async def delete_incident(self, incident_id: str) -> bool:
        """
        Delete an incident from the system
        
        Args:
            incident_id: The unique identifier of the incident to delete
            
        Returns:
            True if incident was deleted successfully, False if incident was not found
        """
        incident = self.incident_repository.get_by_id(incident_id)

        if incident is not None:
            if incident.status != IncidentStatus.CREATED:
                await self.communication_channel.publish(
                    topic="active_incident",
                    message={}
                )

        return self.incident_repository.delete(incident_id)

    def get_open_incidents(self) -> List[Incident]:
        all_incidents = self.incident_repository.get_all()
        open_incidents = [
            incident for incident in all_incidents
            if incident.status != IncidentStatus.RESOLVED
        ]
        return open_incidents

    async def dispatch_incident(self, incident_id: str):
        incident = self.incident_repository.get_by_id(incident_id)
        if incident is None:
            raise ValueError(f"Incident with ID {incident_id} does not exist.")
        
        # Notify ERT units about the incident and wait for acknowledgment
        self.update_incident_status(incident_id, IncidentStatus.DISPATCHED)
        
        await self.communication_channel.publish(
            topic="active_incident",
            message=incident.to_dict()
        )

        return True
    
    # Add method to update incident status in general
    def update_incident_status(self, incident_id: str, new_status: IncidentStatus):
        """
        Update the status of an incident
        
        Args:
            incident_id: ID of the incident
            new_status: New status to set
            
        Returns:
            Updated incident object
        """
        incident = self.incident_repository.get_by_id(incident_id)
        if not incident:
            raise ValueError(f"Incident with ID {incident_id} does not exist.")
        
        incident.status = new_status
        updated_incident = self.incident_repository.update(incident)
        
        return updated_incident

    async def resolve_incident(self):
        """
        Mark an incident as resolved
        
        Args:
            incident_id: ID of the incident to resolve
            
        Returns:
            Updated incident object
        """
        incident = self.get_open_incidents()[0] if self.get_open_incidents() else None
        if not incident:
            raise ValueError(f"Incident with ID {incident.id} does not exist.")
        
        incident.status = IncidentStatus.RESOLVED
        updated_incident = self.incident_repository.update(incident)

        await self.communication_channel.publish(
            topic="active_incident",
            message={}
        )
        
        return updated_incident
