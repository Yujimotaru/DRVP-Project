"""
NITK Campus Mobility - Ride Request Model.
Represents a single ride request from the Phase 3 dataset.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class RideRequest:
    """Represents a single ride request from ride_requests.csv."""

    request_id: str
    request_date: str
    request_time: str
    origin_id: str
    destination_id: str
    passenger_count: int
    request_type: str
    priority: str
    max_wait_min: float
    status: str = "pending"

    @property
    def request_datetime(self) -> datetime:
        """Combine date and time into a datetime object."""
        return datetime.strptime(
            f"{self.request_date} {self.request_time}", "%Y-%m-%d %H:%M"
        )

    @property
    def is_high_priority(self) -> bool:
        return self.priority == "high"

    def __repr__(self) -> str:
        return (
            f"RideRequest({self.request_id}, {self.origin_id}->{self.destination_id}, "
            f"pax={self.passenger_count})"
        )