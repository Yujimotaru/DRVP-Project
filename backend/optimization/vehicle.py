"""
NITK Campus Mobility - Vehicle Model.
Simple representation of a campus shuttle/vehicle for ride-pooling.
"""

from dataclasses import dataclass, field
from typing import List, Optional


DEFAULT_VEHICLE_CAPACITY = 4


@dataclass
class Vehicle:
    """Represents a campus shuttle vehicle."""

    vehicle_id: str
    capacity: int = DEFAULT_VEHICLE_CAPACITY
    current_location: str = ""
    available_time: float = 0.0
    active: bool = True
    assigned_requests: List[str] = field(default_factory=list)
    current_occupancy: int = 0

    def can_accept(self, passenger_count: int) -> bool:
        """Check if vehicle can accept additional passengers."""
        return self.active and (self.current_occupancy + passenger_count <= self.capacity)

    def assign_request(self, request_id: str, passenger_count: int) -> bool:
        """Assign a request to this vehicle if capacity allows."""
        if not self.can_accept(passenger_count):
            return False
        self.assigned_requests.append(request_id)
        self.current_occupancy += passenger_count
        return True

    def drop_passengers(self, passenger_count: int) -> None:
        """Drop passengers at a stop."""
        self.current_occupancy = max(0, self.current_occupancy - passenger_count)

    def reset(self) -> None:
        """Reset vehicle state for a new simulation."""
        self.assigned_requests = []
        self.current_occupancy = 0
        self.available_time = 0.0
        self.active = True