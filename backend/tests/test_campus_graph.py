"""
NITK Campus Mobility - Campus Graph Tests.
Validates the geographic road network, node coordinates, edge topology,
East-West underpass routing, and Dijkstra shortest path calculations.
"""

import pytest
from backend.services.location_service import LocationService
from backend.services.campus_graph_service import (
    CampusGraphService,
    get_shortest_distance,
    get_shortest_travel_time,
    get_shortest_path,
)


@pytest.fixture
def graph_service() -> CampusGraphService:
    """Fixture providing a freshly loaded CampusGraphService."""
    return CampusGraphService()


@pytest.fixture
def location_service() -> LocationService:
    """Fixture providing a freshly loaded LocationService."""
    return LocationService()


def test_every_phase1_location_has_a_node(
    graph_service: CampusGraphService, location_service: LocationService
):
    """Requirement 1: Every Phase 1 location has a corresponding campus node."""
    locations = location_service.get_all_locations()
    assert len(locations) == 54
    for loc in locations:
        assert loc.location_id in graph_service.node_by_loc_id, (
            f"Phase 1 location '{loc.location_id}' ({loc.name}) has no corresponding node in campus_nodes.csv"
        )


def test_every_node_has_valid_coords_or_is_unresolved(graph_service: CampusGraphService):
    """Requirement 2: Every node has valid latitude/longitude within NITK bounding box OR is explicitly marked unresolved."""
    for nid, node in graph_service.nodes.items():
        if node["coordinate_source"] == "unresolved":
            assert node["coordinate_confidence"] == "low"
        else:
            lat = node["latitude"]
            lon = node["longitude"]
            assert lat is not None and lon is not None, f"Node '{nid}' is missing coordinates"
            # NITK Surathkal geographic bounding box (~13.00 to 13.02 N, 74.78 to 74.80 E)
            assert 13.000 <= lat <= 13.020, f"Node '{nid}' latitude {lat} outside NITK bounding box"
            assert 74.780 <= lon <= 74.800, f"Node '{nid}' longitude {lon} outside NITK bounding box"


def test_no_duplicate_node_ids(graph_service: CampusGraphService):
    """Requirement 3: No duplicate node IDs exist in the dataset."""
    node_ids = list(graph_service.nodes.keys())
    assert len(node_ids) == len(set(node_ids)), "Duplicate node IDs detected"


def test_no_duplicate_location_ids(graph_service: CampusGraphService):
    """Requirement 4: No duplicate location IDs mapped in campus nodes."""
    loc_ids = [n["location_id"] for n in graph_service.nodes.values()]
    assert len(loc_ids) == len(set(loc_ids)), "Duplicate location IDs detected in campus_nodes.csv"


def test_every_edge_references_valid_nodes(graph_service: CampusGraphService):
    """Requirement 5: Every edge references existing and valid nodes."""
    for edge in graph_service.edges:
        u = edge["from_node"]
        v = edge["to_node"]
        assert u in graph_service.nodes, f"Edge '{edge['edge_id']}' references unknown from_node '{u}'"
        assert v in graph_service.nodes, f"Edge '{edge['edge_id']}' references unknown to_node '{v}'"


def test_edge_distances_are_positive(graph_service: CampusGraphService):
    """Requirement 6: All edge road distances are strictly positive."""
    for edge in graph_service.edges:
        assert edge["distance_km"] > 0, f"Edge '{edge['edge_id']}' has non-positive distance: {edge['distance_km']}"


def test_edge_travel_times_are_positive(graph_service: CampusGraphService):
    """Requirement 7: All edge travel times are strictly positive."""
    for edge in graph_service.edges:
        assert edge["estimated_time_min"] > 0, (
            f"Edge '{edge['edge_id']}' has non-positive travel time: {edge['estimated_time_min']}"
        )


def test_east_west_campus_classification_preserved(
    graph_service: CampusGraphService, location_service: LocationService
):
    """Requirement 8: East/West campus classifications match Phase 1 exactly."""
    for loc in location_service.get_all_locations():
        nid = graph_service.node_by_loc_id[loc.location_id]
        node = graph_service.nodes[nid]
        assert node["campus"] == loc.campus, (
            f"Campus mismatch for {loc.location_id}: Phase 1={loc.campus}, Node={node['campus']}"
        )


def test_valid_east_west_connection(graph_service: CampusGraphService):
    """Requirement 9: There is a valid East-West crossing edge in the graph."""
    crossing_edges = [e for e in graph_service.edges if e["crosses_nh66"]]
    assert len(crossing_edges) > 0, "No NH-66 crossing edge found in road graph"
    for e in crossing_edges:
        u_campus = graph_service.nodes[e["from_node"]]["campus"]
        v_campus = graph_service.nodes[e["to_node"]]["campus"]
        assert (u_campus == "WEST" and v_campus == "EAST") or (u_campus == "EAST" and v_campus == "WEST"), (
            f"Crossing edge '{e['edge_id']}' does not span between EAST and WEST"
        )


def test_graph_not_arbitrary_all_to_all(graph_service: CampusGraphService):
    """Requirement 10: Graph follows sparse road topology rather than dense all-to-all connectivity."""
    num_nodes = len(graph_service.nodes)
    num_edges = len(graph_service.edges)
    # Dense graph would have N*(N-1)/2 = 54*53/2 = 1431 edges. Sparse physical road graph should have << 200 edges.
    assert num_edges < 150, f"Graph appears overly connected with {num_edges} edges"
    assert num_edges > num_nodes, f"Graph lacks sufficient connectivity with {num_edges} edges for {num_nodes} nodes"


def test_graph_connectivity_and_reachability(graph_service: CampusGraphService):
    """Requirement 11: Graph is fully connected; every location can reach every other location."""
    node_ids = list(graph_service.nodes.keys())
    for nid in node_ids[:10]: # Check reachability from sample origins
        for target in node_ids:
            dist = graph_service.get_shortest_distance(nid, target)
            assert dist < float("inf"), f"Node '{nid}' cannot reach '{target}'"


def test_distance_to_self_is_zero(graph_service: CampusGraphService):
    """Requirement 12: Shortest path distance from any node/location to itself is zero."""
    for nid in graph_service.nodes:
        assert graph_service.get_shortest_distance(nid, nid) == 0.0


def test_travel_time_to_self_is_zero(graph_service: CampusGraphService):
    """Requirement 13: Travel time from any node/location to itself is zero."""
    for nid in graph_service.nodes:
        assert graph_service.get_shortest_travel_time(nid, nid) == 0.0


def test_shortest_path_symmetry(graph_service: CampusGraphService):
    """Requirement 14: Shortest path distance is symmetric across bidirectional road edges."""
    sample_pairs = [
        ("node_main_building", "node_dept_cse"),
        ("node_hostel_b_block1", "node_dept_mech"),
        ("node_hostel_g_gh1", "node_lhc_a"),
        ("node_central_library", "node_dept_it"),
    ]
    for u, v in sample_pairs:
        d_uv = graph_service.get_shortest_distance(u, v)
        d_vu = graph_service.get_shortest_distance(v, u)
        assert abs(d_uv - d_vu) < 1e-4, f"Distance asymmetry detected between {u} and {v}: {d_uv} vs {d_vu}"


def test_no_negative_distances_or_times(graph_service: CampusGraphService):
    """Requirement 15: No negative shortest path distances or travel times exist."""
    for edge in graph_service.edges:
        assert edge["distance_km"] >= 0
        assert edge["estimated_time_min"] >= 0


def test_required_sample_routes(graph_service: CampusGraphService):
    """Tests the 5 required conceptual routes across campus."""
    routes = [
        ("hostel_b_block1", "loc_main_building", "Boys Hostel -> Main Building"),
        ("hostel_b_mt1", "dept_cse", "Boys Hostel MT-1 -> CSE"),
        ("loc_main_building", "dept_cse", "Main Building -> CSE"),
        ("loc_central_library", "dept_it", "Central Library -> IT"),
        ("hostel_g_gh1", "loc_lhc_a", "Girls Hostel GH-1 -> LHC-A"),
    ]

    for orig, dest, label in routes:
        path, dist, t_min = graph_service.get_shortest_path(orig, dest)
        assert len(path) >= 2, f"Path for '{label}' too short"
        assert dist > 0, f"Distance for '{label}' must be positive"
        assert t_min > 0, f"Travel time for '{label}' must be positive"
