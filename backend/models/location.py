"""
NITK Campus Mobility - Location Pydantic Model.
Defines data structures and validations for campus locations.
"""

from typing import Literal
from pydantic import BaseModel, Field, field_validator

CampusType = Literal["EAST", "WEST"]

VALID_LOCATION_TYPES = {
    "gate",
    "administrative",
    "library",
    "cooperative_society",
    "canteen",
    "lecture_hall",
    "department",
    "hostel_boys",
    "hostel_girls",
    "mess",
}


class Location(BaseModel):
    """Represents a discrete physical location on the NITK campus."""

    location_id: str = Field(..., description="Unique identifier for the location")
    name: str = Field(..., description="Human-readable name of the location")
    type: str = Field(..., description="Category/type of location")
    campus: CampusType = Field(..., description="Campus division relative to NH-66 (EAST or WEST)")
    subzone: str = Field(..., description="Campus subzone descriptor")
    capacity: int = Field(..., ge=0, description="Estimated occupancy/holding capacity")
    peak_demand_weight: float = Field(..., ge=0.0, le=1.0, description="Overall peak simulation demand weight [0, 1]")
    morning_demand_weight: float = Field(..., ge=0.0, le=1.0, description="Morning simulation demand weight [0, 1]")
    lunch_demand_weight: float = Field(..., ge=0.0, le=1.0, description="Lunch period simulation demand weight [0, 1]")
    evening_demand_weight: float = Field(..., ge=0.0, le=1.0, description="Evening simulation demand weight [0, 1]")
    night_demand_weight: float = Field(..., ge=0.0, le=1.0, description="Night simulation demand weight [0, 1]")

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        cleaned_type = value.strip().lower()
        if cleaned_type not in VALID_LOCATION_TYPES:
            raise ValueError(f"Invalid location type: '{value}'. Must be one of: {sorted(VALID_LOCATION_TYPES)}")
        return cleaned_type

    @field_validator("campus")
    @classmethod
    def validate_campus(cls, value: str) -> str:
        cleaned_campus = value.strip().upper()
        if cleaned_campus not in {"EAST", "WEST"}:
            raise ValueError(f"Invalid campus: '{value}'. Must be 'EAST' or 'WEST'")
        return cleaned_campus
