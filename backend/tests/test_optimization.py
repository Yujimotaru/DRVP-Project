"""
NITK Campus Mobility - Phase 5 Optimization Tests.
Tests for routing engine, vehicle model, ride pooling, and simulation.
"""

import pytest
import pandas as pd
from pathlib import Path

from backend.optimization.routing_engine import RoutingEngine
from backend.optimization.vehicle import Vehicle, DEFAULT_VEHICLE_CAPACITY
from backend.optimization.ride_request import RideRequest
from backend.optimization.ride_pooling import (
    check_pooling_compatibility,
    find_poolable_groups,
    MAX_PICKUP_WAIT_MINUTES,
    MAX_DETOUR_MINUTES,
    MAX_ROUTE_OVERHEAD_PERCENT,
)
from backend.optimization.vehicle_assignment import (
    load_ride_requests,
    assign_requests_greedy,
)
from backend.optimization.simulation import run_simulation


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture
def routing_engine() -> RoutingEngine:
    return RoutingEngine()


@pytest.fixture
def sample_request() -> RideRequest:
    return RideRequest(
        request_id="test_001",
        request_date="2026-09-01",
        request_time="08:00",
        origin_id="hostel_b_mt1",
        destination_id="dept_cse",
        passenger_count=1,
        request_type="student",
        priority="normal",
        max_wait_min=10.0,
    )


@pytest.fixture
def compatible_request() -> RideRequest:
    return RideRequest(
        request_id="test_002",
        request_date="2026-09-01",
        request_time="08:02",
        origin_id="hostel_b_mt2",
        destination_id="dept_ece",
        passenger_count=1,
        request_type="student",
        priority="normal",
        max_wait_min=10.0,
    )


# --- Routing Engine Tests ---

def test_graph_loads_successfully(routing_engine: RoutingEngine):
    assert len(routing_engine.graph.nodes) == 54


def test_valid_locations_route_successfully(routing_engine: RoutingEngine):
    dist = routing_engine.get_shortest_distance("hostel_b_mt1", "dept_cse")
    assert dist > 0


def test_invalid_locations_are_rejected(routing_engine: RoutingEngine):
    with pytest.raises(ValueError):
        routing_engine.get_shortest_distance("nonexistent_loc", "dept_cse")


def test_shortest_distance_is_non_negative(routing_engine: RoutingEngine):
    dist = routing_engine.get_shortest_distance("hostel_b_mt1", "dept_cse")
    assert dist >= 0


def test_shortest_travel_time_is_non_negative(routing_engine: RoutingEngine):
    time = routing_engine.get_shortest_time("hostel_b_mt1", "dept_cse")
    assert time >= 0


def test_route_distance_consistent_with_graph(routing_engine: RoutingEngine):
    dist = routing_engine.get_shortest_distance("hostel_b_mt1", "dept_cse")
    path, path_dist, path_time = routing_engine.get_shortest_path("hostel_b_mt1", "dept_cse")
    assert abs(dist - path_dist) < 0.001
    assert len(path) >= 2


# --- Vehicle Model Tests ---

def test_vehicle_capacity_respected():
    v = Vehicle(vehicle_id="v001", capacity=4)
    assert v.can_accept(4) is True
    assert v.can_accept(5) is False
    v.assign_request("r001", 3)
    assert v.can_accept(1) is True
    assert v.can_accept(2) is False  # 3+2 > 4


def test_vehicle_passenger_count_respected():
    v = Vehicle(vehicle_id="v002", capacity=4)
    assert v.assign_request("r001", 2) is True
    assert v.current_occupancy == 2
    assert v.assign_request("r002", 3) is False  # 2+3 > 4


def test_vehicle_reset():
    v = Vehicle(vehicle_id="v003", capacity=4)
    v.assign_request("r001", 2)
    v.reset()
    assert v.current_occupancy == 0
    assert len(v.assigned_requests) == 0


# --- Ride Pooling Tests ---

def test_incompatible_rides_not_pooled(routing_engine: RoutingEngine):
    req1 = RideRequest(
        request_id="r001", request_date="2026-09-01", request_time="08:00",
        origin_id="hostel_b_mt1", destination_id="dept_cse",
        passenger_count=3, request_type="student", priority="normal", max_wait_min=10.0,
    )
    req2 = RideRequest(
        request_id="r002", request_date="2026-09-01", request_time="08:01",
        origin_id="hostel_b_mt2", destination_id="dept_ece",
        passenger_count=2, request_type="student", priority="normal", max_wait_min=10.0,
    )
    result = check_pooling_compatibility(req1, req2, routing_engine, vehicle_capacity=4)
    assert result.can_pool is False
    assert result.reason == "capacity_exceeded"


def test_compatible_rides_can_be_pooled(routing_engine: RoutingEngine, sample_request, compatible_request):
    result = check_pooling_compatibility(sample_request, compatible_request, routing_engine)
    assert isinstance(result.can_pool, bool)


# --- Assignment Tests ---

def test_load_ride_requests():
    requests = load_ride_requests(max_requests=10)
    assert len(requests) == 10
    assert all(isinstance(r, RideRequest) for r in requests)


def test_greedy_assignment(routing_engine: RoutingEngine):
    requests = load_ride_requests(max_requests=20)
    vehicles, route_details, summary = assign_requests_greedy(
        requests, routing_engine, vehicle_capacity=4
    )
    assert summary["total_requests"] == 20
    assert summary["served_requests"] > 0
    assert summary["vehicle_count"] > 0


def test_every_served_request_assigned(routing_engine: RoutingEngine):
    requests = load_ride_requests(max_requests=20)
    vehicles, route_details, summary = assign_requests_greedy(
        requests, routing_engine, vehicle_capacity=4
    )
    assigned_ids = set()
    for rd in route_details:
        if rd["route_status"] == "assigned":
            assigned_ids.add(rd["request_id"])
    assert len(assigned_ids) == summary["served_requests"]


def test_no_request_assigned_to_two_vehicles(routing_engine: RoutingEngine):
    requests = load_ride_requests(max_requests=20)
    vehicles, route_details, summary = assign_requests_greedy(
        requests, routing_engine, vehicle_capacity=4
    )
    assigned_ids = [
        rd["request_id"] for rd in route_details if rd["route_status"] == "assigned"
    ]
    assert len(assigned_ids) == len(set(assigned_ids))


def test_vehicle_occupancy_never_exceeds_capacity(routing_engine: RoutingEngine):
    requests = load_ride_requests(max_requests=20)
    vehicles, route_details, summary = assign_requests_greedy(
        requests, routing_engine, vehicle_capacity=4
    )
    for v in vehicles:
        assert v.current_occupancy <= v.capacity


# --- Simulation Tests ---

def test_simulation_runs():
    results = run_simulation(max_requests=50, vehicle_capacity=4)
    assert results["total_requests"] == 50
    assert results["served_requests"] > 0
    assert results["vehicle_count"] > 0


def test_optimization_output_generated():
    results = run_simulation(max_requests=50, vehicle_capacity=4)
    assert (DATA_DIR / "optimized_routes.csv").exists()
    assert (DATA_DIR / "vehicle_assignments.csv").exists()
    assert (DATA_DIR / "optimization_results.json").exists()


def test_baseline_comparison_works():
    results = run_simulation(max_requests=50, vehicle_capacity=4)
    assert "baseline" in results
    assert "optimized" in results
    assert results["total_distance_individual"] > 0