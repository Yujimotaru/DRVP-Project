"""
NITK Campus Mobility - Demand Generator Tests.
Unit and statistical distribution tests for Phase 3 synthetic ride requests.
"""

import pytest
import pandas as pd
from backend.services.demand_generator import DemandGenerator, generate_daily_requests, generate_requests
from backend.services.location_service import LocationService
from backend.services.campus_graph_service import CampusGraphService


@pytest.fixture
def generator() -> DemandGenerator:
    """Fixture providing a fresh DemandGenerator."""
    return DemandGenerator()


@pytest.fixture
def location_service() -> LocationService:
    """Fixture providing LocationService."""
    return LocationService()


@pytest.fixture
def graph_service() -> CampusGraphService:
    """Fixture providing CampusGraphService."""
    return CampusGraphService()


@pytest.fixture
def sample_requests(generator: DemandGenerator) -> list[dict]:
    """Generates a 3-day sample dataset for test validations."""
    return generator.generate_requests(start_date="2026-09-01", num_days=3, seed=42, base_requests_per_day=100)


def test_generated_request_ids_are_unique(sample_requests: list[dict]):
    """Requirement 1: All generated request IDs must be strictly unique."""
    req_ids = [r["request_id"] for r in sample_requests]
    assert len(req_ids) > 0
    assert len(req_ids) == len(set(req_ids)), "Duplicate request IDs found"


def test_every_origin_exists(sample_requests: list[dict], location_service: LocationService):
    """Requirement 2: Every origin_id references a valid location in locations.csv."""
    valid_ids = {loc.location_id for loc in location_service.get_all_locations()}
    for r in sample_requests:
        assert r["origin_id"] in valid_ids, f"Unknown origin_id '{r['origin_id']}'"


def test_every_destination_exists(sample_requests: list[dict], location_service: LocationService):
    """Requirement 3: Every destination_id references a valid location in locations.csv."""
    valid_ids = {loc.location_id for loc in location_service.get_all_locations()}
    for r in sample_requests:
        assert r["destination_id"] in valid_ids, f"Unknown destination_id '{r['destination_id']}'"


def test_origin_not_equal_to_destination(sample_requests: list[dict]):
    """Requirements 4 & 18: Origin and destination must never be the same location."""
    for r in sample_requests:
        assert r["origin_id"] != r["destination_id"], (
            f"Request '{r['request_id']}' has identical origin and destination: {r['origin_id']}"
        )


def test_passenger_count_range(sample_requests: list[dict]):
    """Requirement 5: Passenger count must be an integer between 1 and 4 inclusive."""
    for r in sample_requests:
        assert 1 <= r["passenger_count"] <= 4, f"Invalid passenger count: {r['passenger_count']}"


def test_valid_request_types(sample_requests: list[dict]):
    """Requirement 6: Request type must be one of student, staff, faculty."""
    valid_types = {"student", "staff", "faculty"}
    for r in sample_requests:
        assert r["request_type"] in valid_types, f"Invalid request_type: '{r['request_type']}'"


def test_valid_priorities(sample_requests: list[dict]):
    """Requirement 7: Priority must be normal or high."""
    valid_priorities = {"normal", "high"}
    for r in sample_requests:
        assert r["priority"] in valid_priorities, f"Invalid priority: '{r['priority']}'"


def test_max_wait_min_is_positive(sample_requests: list[dict]):
    """Requirement 8: Maximum wait time must be positive."""
    for r in sample_requests:
        assert r["max_wait_min"] > 0, f"Non-positive max_wait_min: {r['max_wait_min']}"


def test_all_trips_connected_in_graph(sample_requests: list[dict], graph_service: CampusGraphService):
    """Requirement 9: Every origin-destination pair must have a connected path in the Phase 2 graph."""
    for r in sample_requests[:50]: # Sample 50 trips
        dist = graph_service.get_shortest_distance(r["origin_id"], r["destination_id"])
        assert 0 < dist < float("inf"), f"Unconnected trip {r['origin_id']} -> {r['destination_id']}"


def test_reproducibility_with_same_seed(generator: DemandGenerator):
    """Requirement 10: Running generation with the same seed must produce identical results."""
    run1 = generator.generate_daily_requests(date="2026-09-01", seed=123, base_requests=100)
    run2 = generator.generate_daily_requests(date="2026-09-01", seed=123, base_requests=100)
    assert run1 == run2, "Different outputs generated for identical seed"


def test_different_seeds_produce_different_distributions(generator: DemandGenerator):
    """Requirement 11: Different seeds must produce different request streams."""
    run1 = generator.generate_daily_requests(date="2026-09-01", seed=100, base_requests=100)
    run2 = generator.generate_daily_requests(date="2026-09-01", seed=999, base_requests=100)
    assert run1 != run2, "Identical outputs generated for different seeds"


def test_morning_hostel_to_academic_flow_ratio(generator: DemandGenerator, location_service: LocationService):
    """Requirement 12: Morning peak (07:00-10:00) should have high concentration of hostel -> academic trips."""
    morning_period = {
        "start_time": "07:00",
        "end_time": "10:00",
        "weight_column": "morning_demand_weight",
        "flow_preferences": {
            "hostel_to_lecture_hall": 0.45,
            "hostel_to_department": 0.35,
            "hostel_to_library": 0.10,
            "general": 0.10
        }
    }
    import numpy as np
    rng = np.random.default_rng(42)
    reqs = generator.generate_requests_for_time_window("2026-09-01", morning_period, count=200, rng=rng)
    
    hostel_ids = {l.location_id for l in location_service.get_locations_by_type("hostel_boys") + location_service.get_locations_by_type("hostel_girls")}
    academic_ids = {l.location_id for l in location_service.get_locations_by_type("department") + location_service.get_locations_by_type("lecture_hall") + location_service.get_locations_by_type("library")}

    hostel_to_academic_count = sum(1 for r in reqs if r["origin_id"] in hostel_ids and r["destination_id"] in academic_ids)
    ratio = hostel_to_academic_count / len(reqs)
    assert ratio >= 0.70, f"Expected morning hostel->academic ratio >= 0.70, got {ratio:.2f}"


def test_lunch_to_mess_flow_ratio(generator: DemandGenerator, location_service: LocationService):
    """Requirement 13: Lunch peak (12:00-14:30) should have high concentration of trips toward messes."""
    lunch_period = {
        "start_time": "12:00",
        "end_time": "14:30",
        "weight_column": "lunch_demand_weight",
        "flow_preferences": {
            "department_to_mess": 0.50,
            "lecture_hall_to_mess": 0.30,
            "library_to_mess": 0.10,
            "general": 0.10
        }
    }
    import numpy as np
    rng = np.random.default_rng(42)
    reqs = generator.generate_requests_for_time_window("2026-09-01", lunch_period, count=200, rng=rng)
    
    mess_ids = {l.location_id for l in location_service.get_locations_by_type("mess")}
    to_mess_count = sum(1 for r in reqs if r["destination_id"] in mess_ids)
    ratio = to_mess_count / len(reqs)
    assert ratio >= 0.70, f"Expected lunch to-mess ratio >= 0.70, got {ratio:.2f}"


def test_evening_library_and_suprabha_ratio(generator: DemandGenerator, location_service: LocationService):
    """Requirement 14: Evening peak (17:00-20:00) should favor library and canteen destinations."""
    evening_period = {
        "start_time": "17:00",
        "end_time": "20:00",
        "weight_column": "evening_demand_weight",
        "flow_preferences": {
            "hostel_to_library": 0.30,
            "department_to_library": 0.20,
            "hostel_to_suprabha": 0.20,
            "hostel_to_coop": 0.15,
            "general": 0.15
        }
    }
    import numpy as np
    rng = np.random.default_rng(42)
    reqs = generator.generate_requests_for_time_window("2026-09-01", evening_period, count=200, rng=rng)
    
    target_ids = {l.location_id for l in location_service.get_locations_by_type("library") + location_service.get_locations_by_type("canteen") + location_service.get_locations_by_type("cooperative_society")}
    evening_target_count = sum(1 for r in reqs if r["destination_id"] in target_ids)
    ratio = evening_target_count / len(reqs)
    assert ratio >= 0.65, f"Expected evening target ratio >= 0.65, got {ratio:.2f}"


def test_dataset_contains_multiple_simulation_dates(sample_requests: list[dict]):
    """Requirement 15: Dataset spans across multiple simulation dates."""
    dates = {r["request_date"] for r in sample_requests}
    assert len(dates) == 3, f"Expected 3 simulation dates, found {len(dates)}"


def test_dataset_contains_multiple_time_periods(sample_requests: list[dict]):
    """Requirement 16: Requests are distributed across multiple diurnal time hours."""
    hours = {r["request_time"].split(":")[0] for r in sample_requests}
    assert len(hours) >= 10, f"Expected at least 10 active hours, got {len(hours)}"


def test_students_form_majority(sample_requests: list[dict]):
    """Requirement 17: Students form the vast majority of generated ride requests (> 75%)."""
    student_count = sum(1 for r in sample_requests if r["request_type"] == "student")
    ratio = student_count / len(sample_requests)
    assert ratio > 0.75, f"Expected student ratio > 0.75, got {ratio:.2f}"
