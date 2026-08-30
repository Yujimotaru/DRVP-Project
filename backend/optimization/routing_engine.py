"""
NITK Campus Mobility - Routing Engine.
Wraps the existing campus graph service for optimization use.
Provides shortest distance, travel time, and path reconstruction.
"""

from pathlib import Path
from typing import List, Tuple

from backend.services.campus_graph_service import CampusGraphService


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class RoutingEngine:
    """
    Campus routing engine backed by the existing 54-node/70-edge graph.
    Uses Dijkstra's algorithm for shortest-path computation.
    """

    def __init__(self, graph_service: CampusGraphService = None) -> None:
        self.graph = graph_service or CampusGraphService()

    def get_shortest_distance(self, origin_id: str, destination_id: str) -> float:
        """Returns shortest road distance in km between two locations."""
        return self.graph.get_shortest_distance(origin_id, destination_id)

    def get_shortest_time(self, origin_id: str, destination_id: str) -> float:
        """Returns shortest travel time in minutes between two locations."""
        return self.graph.get_shortest_travel_time(origin_id, destination_id)

    def get_shortest_path(
        self, origin_id: str, destination_id: str
    ) -> Tuple[List[str], float, float]:
        """
        Returns (node_path, distance_km, time_min) for the shortest path.
        """
        return self.graph.get_shortest_path(origin_id, destination_id)

    def get_distance_matrix(self, location_ids: List[str]) -> dict:
        """
        Build a distance lookup dictionary for a set of locations.
        Returns dict with (origin, destination) -> distance_km.
        """
        matrix = {}
        for origin in location_ids:
            for dest in location_ids:
                if origin == dest:
                    matrix[(origin, dest)] = 0.0
                else:
                    matrix[(origin, dest)] = self.get_shortest_distance(origin, dest)
        return matrix

    def get_time_matrix(self, location_ids: List[str]) -> dict:
        """
        Build a time lookup dictionary for a set of locations.
        Returns dict with (origin, destination) -> time_min.
        """
        matrix = {}
        for origin in location_ids:
            for dest in location_ids:
                if origin == dest:
                    matrix[(origin, dest)] = 0.0
                else:
                    matrix[(origin, dest)] = self.get_shortest_time(origin, dest)
        return matrix