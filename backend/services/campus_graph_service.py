"""
NITK Campus Mobility - Campus Graph Service.
Provides graph traversal, neighborhood queries, and shortest-path computation (Dijkstra)
over the NITK road network.
"""

import csv
import heapq
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

DEFAULT_NODES_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_nodes.csv"
DEFAULT_EDGES_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_edges.csv"


class CampusGraphService:
    """Service for managing the NITK campus road graph and calculating shortest paths."""

    def __init__(
        self,
        nodes_path: Optional[Path] = None,
        edges_path: Optional[Path] = None,
    ) -> None:
        self.nodes_path = nodes_path or DEFAULT_NODES_PATH
        self.edges_path = edges_path or DEFAULT_EDGES_PATH
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.node_by_loc_id: Dict[str, str] = {}
        self.loc_id_by_node: Dict[str, str] = {}
        self.edges: List[Dict[str, Any]] = []
        self.adjacency: Dict[str, List[Tuple[str, float, float, str]]] = {} # node -> [(neighbor, dist_km, time_min, edge_id)]
        
        self.load_nodes()
        self.load_edges()

    def load_nodes(self) -> Dict[str, Dict[str, Any]]:
        """Loads campus nodes from CSV."""
        if not self.nodes_path.exists():
            raise FileNotFoundError(f"Campus nodes file not found at: {self.nodes_path}")

        nodes = {}
        node_by_loc_id = {}
        loc_id_by_node = {}

        with open(self.nodes_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cleaned = {k.strip(): v.strip() for k, v in row.items() if k is not None}
                nid = cleaned["node_id"]
                lid = cleaned["location_id"]
                node_data = {
                    "node_id": nid,
                    "location_id": lid,
                    "name": cleaned["name"],
                    "latitude": float(cleaned["latitude"]) if cleaned["latitude"] else None,
                    "longitude": float(cleaned["longitude"]) if cleaned["longitude"] else None,
                    "campus": cleaned["campus"],
                    "node_type": cleaned["node_type"],
                    "coordinate_source": cleaned["coordinate_source"],
                    "coordinate_confidence": cleaned["coordinate_confidence"],
                }
                nodes[nid] = node_data
                node_by_loc_id[lid] = nid
                loc_id_by_node[nid] = lid

        self.nodes = nodes
        self.node_by_loc_id = node_by_loc_id
        self.loc_id_by_node = loc_id_by_node
        self.adjacency = {nid: [] for nid in nodes}
        return self.nodes

    def load_edges(self) -> List[Dict[str, Any]]:
        """Loads road graph edges from CSV and constructs the adjacency list."""
        if not self.edges_path.exists():
            raise FileNotFoundError(f"Campus edges file not found at: {self.edges_path}")

        edges = []
        with open(self.edges_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cleaned = {k.strip(): v.strip() for k, v in row.items() if k is not None}
                u = cleaned["from_node"]
                v = cleaned["to_node"]
                dist = float(cleaned["distance_km"])
                time_val = float(cleaned["estimated_time_min"])
                is_bidi = cleaned["bidirectional"].lower() in {"true", "1", "yes"}
                crosses = cleaned["crosses_nh66"].lower() in {"true", "1", "yes"}

                edge_data = {
                    "edge_id": cleaned["edge_id"],
                    "from_node": u,
                    "to_node": v,
                    "distance_km": dist,
                    "estimated_time_min": time_val,
                    "road_type": cleaned["road_type"],
                    "crosses_nh66": crosses,
                    "bidirectional": is_bidi,
                    "source": cleaned["source"],
                    "confidence": cleaned["confidence"],
                }
                edges.append(edge_data)

                if u in self.adjacency:
                    self.adjacency[u].append((v, dist, time_val, cleaned["edge_id"]))
                if is_bidi and v in self.adjacency:
                    self.adjacency[v].append((u, dist, time_val, cleaned["edge_id"]))

        self.edges = edges
        return self.edges

    def _resolve_node_id(self, identifier: str) -> str:
        """Resolves whether an identifier is a node_id or a location_id."""
        clean_id = identifier.strip()
        if clean_id in self.nodes:
            return clean_id
        if clean_id in self.node_by_loc_id:
            return self.node_by_loc_id[clean_id]
        raise ValueError(f"Unknown node or location identifier: '{identifier}'")

    def get_neighbors(self, node_id: str) -> List[Tuple[str, float, float]]:
        """Returns adjacent nodes as a list of (neighbor_node_id, distance_km, estimated_time_min)."""
        nid = self._resolve_node_id(node_id)
        return [(neighbor, dist, t) for neighbor, dist, t, _ in self.adjacency.get(nid, [])]

    def _dijkstra(
        self,
        origin_node: str,
        destination_node: str,
        weight_key: str = "distance",
    ) -> Tuple[List[str], float, float]:
        """
        Executes Dijkstra's algorithm between origin and destination nodes.
        weight_key: 'distance' (optimizes distance_km) or 'time' (optimizes estimated_time_min).
        Returns: (path_node_ids, total_distance_km, total_time_min).
        """
        if origin_node == destination_node:
            return [origin_node], 0.0, 0.0

        # Priority queue stores (cost, current_node, dist_accum, time_accum, path)
        pq: List[Tuple[float, str, float, float, List[str]]] = [(0.0, origin_node, 0.0, 0.0, [origin_node])]
        visited: Dict[str, float] = {}

        while pq:
            cost, u, d_acc, t_acc, path = heapq.heappop(pq)

            if u in visited and visited[u] <= cost:
                continue
            visited[u] = cost

            if u == destination_node:
                return path, round(d_acc, 3), round(t_acc, 2)

            for neighbor, d_val, t_val, _ in self.adjacency.get(u, []):
                edge_cost = d_val if weight_key == "distance" else t_val
                next_cost = cost + edge_cost
                if neighbor not in visited or next_cost < visited[neighbor]:
                    heapq.heappush(
                        pq,
                        (
                            next_cost,
                            neighbor,
                            d_acc + d_val,
                            t_acc + t_val,
                            path + [neighbor],
                        ),
                    )

        raise ValueError(f"No path found between {origin_node} and {destination_node}")

    def get_shortest_distance(self, origin_id: str, destination_id: str) -> float:
        """Returns the shortest path road distance in km between two locations/nodes."""
        u = self._resolve_node_id(origin_id)
        v = self._resolve_node_id(destination_id)
        _, dist_km, _ = self._dijkstra(u, v, weight_key="distance")
        return dist_km

    def get_shortest_travel_time(self, origin_id: str, destination_id: str) -> float:
        """Returns the shortest travel time in minutes between two locations/nodes."""
        u = self._resolve_node_id(origin_id)
        v = self._resolve_node_id(destination_id)
        _, _, time_min = self._dijkstra(u, v, weight_key="time")
        return time_min

    def get_shortest_path(
        self,
        origin_id: str,
        destination_id: str,
        optimize_for: str = "distance",
    ) -> Tuple[List[str], float, float]:
        """
        Returns (node_path, total_distance_km, total_travel_time_min) for shortest path.
        optimize_for: 'distance' or 'time'.
        """
        u = self._resolve_node_id(origin_id)
        v = self._resolve_node_id(destination_id)
        return self._dijkstra(u, v, weight_key=optimize_for)


# Default singleton instance
_default_graph_service: Optional[CampusGraphService] = None


def get_default_graph_service() -> CampusGraphService:
    """Returns or initializes the default CampusGraphService instance."""
    global _default_graph_service
    if _default_graph_service is None:
        _default_graph_service = CampusGraphService()
    return _default_graph_service


def get_shortest_distance(origin_id: str, destination_id: str) -> float:
    """Module-level helper to get shortest distance."""
    return get_default_graph_service().get_shortest_distance(origin_id, destination_id)


def get_shortest_travel_time(origin_id: str, destination_id: str) -> float:
    """Module-level helper to get shortest travel time."""
    return get_default_graph_service().get_shortest_travel_time(origin_id, destination_id)


def get_shortest_path(
    origin_id: str, destination_id: str, optimize_for: str = "distance"
) -> Tuple[List[str], float, float]:
    """Module-level helper to get shortest path."""
    return get_default_graph_service().get_shortest_path(origin_id, destination_id, optimize_for)
