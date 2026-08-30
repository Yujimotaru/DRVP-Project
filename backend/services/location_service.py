"""
NITK Campus Mobility - Location Service.
Provides data access and filtering methods for NITK campus locations.
"""

import csv
from pathlib import Path
from typing import List, Optional
from backend.models.location import Location

# Default path to the locations CSV file
DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "locations.csv"


class LocationService:
    """Service class for managing and querying NITK campus locations."""

    def __init__(self, data_path: Optional[Path] = None) -> None:
        self.data_path = data_path or DEFAULT_DATA_PATH
        self._locations: List[Location] = []
        self._locations_by_id: dict[str, Location] = {}
        self.load_locations()

    def load_locations(self) -> None:
        """Loads and validates locations from the CSV file."""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Location dataset not found at: {self.data_path}")

        locations: List[Location] = []
        locations_by_id: dict[str, Location] = {}

        with open(self.data_path, mode="r", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Clean leading/trailing spaces in keys and values
                    cleaned_row = {k.strip(): v.strip() for k, v in row.items() if k is not None}
                    location = Location(
                        location_id=cleaned_row["location_id"],
                        name=cleaned_row["name"],
                        type=cleaned_row["type"],
                        campus=cleaned_row["campus"],
                        subzone=cleaned_row["subzone"],
                        capacity=int(cleaned_row["capacity"]),
                        peak_demand_weight=float(cleaned_row["peak_demand_weight"]),
                        morning_demand_weight=float(cleaned_row["morning_demand_weight"]),
                        lunch_demand_weight=float(cleaned_row["lunch_demand_weight"]),
                        evening_demand_weight=float(cleaned_row["evening_demand_weight"]),
                        night_demand_weight=float(cleaned_row["night_demand_weight"]),
                    )

                    if location.location_id in locations_by_id:
                        raise ValueError(f"Duplicate location_id '{location.location_id}' found at line {row_num}")

                    locations.append(location)
                    locations_by_id[location.location_id] = location
                except Exception as e:
                    raise ValueError(f"Error parsing row {row_num} in {self.data_path}: {e}") from e

        self._locations = locations
        self._locations_by_id = locations_by_id

    def get_all_locations(self) -> List[Location]:
        """Returns all loaded locations."""
        return list(self._locations)

    def get_location_by_id(self, location_id: str) -> Optional[Location]:
        """Returns a location by its ID, or None if not found."""
        return self._locations_by_id.get(location_id.strip())

    def get_locations_by_type(self, location_type: str) -> List[Location]:
        """Returns all locations matching the given type."""
        target_type = location_type.strip().lower()
        return [loc for loc in self._locations if loc.type.lower() == target_type]

    def get_locations_by_campus(self, campus: str) -> List[Location]:
        """Returns all locations belonging to a specific campus division ('EAST' or 'WEST')."""
        target_campus = campus.strip().upper()
        return [loc for loc in self._locations if loc.campus.upper() == target_campus]


# Default singleton instance for top-level convenience calls
_default_service: Optional[LocationService] = None


def get_default_service() -> LocationService:
    """Returns or initializes the default LocationService singleton."""
    global _default_service
    if _default_service is None:
        _default_service = LocationService()
    return _default_service


def get_all_locations() -> List[Location]:
    """Top-level helper to get all locations."""
    return get_default_service().get_all_locations()


def get_location_by_id(location_id: str) -> Optional[Location]:
    """Top-level helper to get a location by ID."""
    return get_default_service().get_location_by_id(location_id)


def get_locations_by_type(location_type: str) -> List[Location]:
    """Top-level helper to get locations by type."""
    return get_default_service().get_locations_by_type(location_type)


def get_locations_by_campus(campus: str) -> List[Location]:
    """Top-level helper to get locations by campus ('EAST' or 'WEST')."""
    return get_default_service().get_locations_by_campus(campus)
