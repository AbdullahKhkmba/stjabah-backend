"""Business logic for Control Room incident management"""

import json
import uuid
from control_room.model.incident import Incident, IncidentStatus
from control_room.repository.in_memory_unit_repository import InMemoryUnitRepository
from control_room.model.unit import Unit, UnitStatus
from communication.websocket_communication import WebSocketCommunication
from typing import List

from control_room.service.incident_service import IncidentService

class UnitService:
    """Service layer for unit operations"""
    
    def __init__(self, unit_repository: InMemoryUnitRepository, incident_service: IncidentService, communication_channel: WebSocketCommunication):
        self.unit_repository = unit_repository
        self.incident_service = incident_service
        self.communication_channel = communication_channel
    
    def create_unit(self,id, x, y: float) -> Unit:
        """
        Create a new unit in the system
        
        Args:
            x: X coordinate
            y: Y coordinate
        
        Returns:
            Created unit object
        """
        unit = Unit(
            id=id,
            x=x,
            y=y,
        )
        created_unit = self.unit_repository.create(unit)
        
        return created_unit
    
    def get_unit_by_id(self, unit_id: str):
        """
        Retrieve unit by ID from repository
        
        Args:
            unit_id: ID of the unit to retrieve
        
        Returns:
            Unit object if found, None otherwise
        """
        return self.unit_repository.get_by_id(unit_id)
    
    def update_unit(self, unit_id: str, x: float, y: float):
        """
        Update unit coordinates

        Args:
            unit_id: ID of the unit
            x: New x coordinate
            y: New y coordinate
        """
        unit = self.unit_repository.get_by_id(unit_id)
        if not unit:
            raise ValueError(f"Unit with ID {unit_id} does not exist.")
        
        unit.x = x
        unit.y = y
        updated_unit = self.unit_repository.update(unit)
        return updated_unit
        
    def get_all_units(self) -> List[Unit]:
        """
        Get all units in the system
        """
        return self.unit_repository.get_all()
    
    def delete_unit(self, unit_id: str) -> bool:
        """
        Delete a unit from the system
        
        Args:
            unit_id: The unique identifier of the unit to delete
            
        Returns:
            True if unit was deleted successfully, False if unit was not found
        """
        return self.unit_repository.delete(unit_id)
    
    def resolve_unit(self, unit_id: str) -> Unit:
        """
        Mark a unit as resolved in the control room
        
        Args:
            unit_id: ID of the unit to resolve
        
        Returns:
            The updated unit object with resolved status
        
        Raises:
            ValueError: If unit with given ID does not exist
        """
        unit = self.unit_repository.get_by_id(unit_id)
        if not unit:
            raise ValueError(f"Unit with ID {unit_id} does not exist.")
        
        unit.status = UnitStatus.RESOLVED
        updated_unit = self.unit_repository.update(unit)

        incident_id = updated_unit.assigned_incident
        if incident_id:
            incident = self.incident_service.get_incident_by_id(incident_id)
            if incident:
                all_units = self.get_all_units()
                assigned_units = [
                    u for u in all_units
                    if u.assigned_incident == incident_id
                ]
                all_resolved = len(assigned_units) > 0 and all(
                    u.status == UnitStatus.RESOLVED
                    for u in assigned_units
                )
                if all_resolved:
                    self.incident_service.resolve_incident()
                    print(f"[Control Room] \U0001f389 Incident {incident.id} resolved (all units resolved)")
                else:
                    print(f"[Control Room] \U0001f6a7 Incident {incident.id} still in progress (some units not resolved)")

        return updated_unit
    
    def assign_incident_to_unit(self, unit_id: str, incident_id: str) -> Unit:
        """
        Assign an incident to a unit
        
        Args:
            unit_id: ID of the unit
            incident_id: ID of the incident to assign
        
        Returns:
            The updated unit object
        
        Raises:
            ValueError: If unit with given ID does not exist
        """
        unit = self.unit_repository.get_by_id(unit_id)
        if not unit:
            raise ValueError(f"Unit with ID {unit_id} does not exist.")
        
        unit.assigned_incident = incident_id
        updated_unit = self.unit_repository.update(unit)

        incident = self.incident_service.get_incident_by_id(incident_id)
        if incident is not None:
            self.incident_service.update_incident_status(incident_id, IncidentStatus.ACKNOWLEDGED)

        return updated_unit
