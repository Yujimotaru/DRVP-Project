"""
NITK Campus Mobility - Simulation Engine.
Runs dynamic vehicle routing and ride-pooling simulation.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from .routing_engine import RoutingEngine
from .vehicle import Vehicle, DEFAULT_VEHICLE_CAPACITY
from .ride_request import RideRequest
from .vehicle_assignment import load_ride_requests, assign_requests_greedy, assign_requests_ortools


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def run_baseline_scenario(
    requests: List[RideRequest],
    routing_engine: RoutingEngine,
) -> Dict:
    """
    Scenario A: Individual rides.
    Each request served independently by a dedicated vehicle run.
    """
    total_distance = 0.0
    total_travel_time = 0.0
    vehicle_count = 0

    for req in requests:
        dist = routing_engine.get_shortest_distance(req.origin_id, req.destination_id)
        time = routing_engine.get_shortest_time(req.origin_id, req.destination_id)
        total_distance += dist
        total_travel_time += time
        vehicle_count += 1

    return {
        "scenario": "individual_rides",
        "total_requests": len(requests),
        "served_requests": len(requests),
        "unserved_requests": 0,
        "vehicle_count": vehicle_count,
        "total_distance_km": round(total_distance, 3),
        "total_travel_time_min": round(total_travel_time, 2),
        "average_wait_time_min": 0.0,
        "average_detour_min": 0.0,
        "pooling_rate": 0.0,
        "average_occupancy": 1.0,
        "maximum_occupancy": 1,
    }


def run_optimized_scenario(
    requests: List[RideRequest],
    routing_engine: RoutingEngine,
    vehicle_capacity: int = DEFAULT_VEHICLE_CAPACITY,
    use_ortools: bool = False,
) -> Tuple[List[Vehicle], List[Dict], Dict]:
    """
    Scenario B: Optimized ride pooling.
    Requests are grouped where feasible.
    """
    if use_ortools:
        vehicles, route_details, summary = assign_requests_ortools(
            requests, routing_engine, vehicle_capacity
        )
    else:
        vehicles, route_details, summary = assign_requests_greedy(
            requests, routing_engine, vehicle_capacity
        )

    # Calculate optimized metrics
    total_distance = sum(r["distance"] for r in route_details if r["route_status"] == "assigned")
    total_travel_time = sum(r["travel_time"] for r in route_details if r["route_status"] == "assigned")
    pooled_count = sum(1 for r in route_details if r.get("pooled", False))
    served = summary["served_requests"]
    total = summary["total_requests"]

    pooling_rate = (pooled_count / served * 100.0) if served > 0 else 0.0

    # Calculate average occupancy
    if vehicles:
        total_occupancy = sum(
            sum(
                next(
                    (req.passenger_count for req in requests if req.request_id == rid),
                    0,
                )
                for rid in v.assigned_requests
            )
            for v in vehicles
        )
        avg_occupancy = total_occupancy / len(vehicles) if vehicles else 0.0
        max_occupancy = max(
            sum(
                next(
                    (req.passenger_count for req in requests if req.request_id == rid),
                    0,
                )
                for rid in v.assigned_requests
            )
            for v in vehicles
        ) if vehicles else 0
    else:
        avg_occupancy = 0.0
        max_occupancy = 0

    optimized = {
        "scenario": "optimized_pooling",
        "total_requests": total,
        "served_requests": served,
        "unserved_requests": summary["unserved_requests"],
        "vehicle_count": summary["vehicle_count"],
        "total_distance_km": round(total_distance, 3),
        "total_travel_time_min": round(total_travel_time, 2),
        "average_wait_time_min": 0.0,
        "average_detour_min": 0.0,
        "pooling_rate": round(pooling_rate, 2),
        "average_occupancy": round(avg_occupancy, 2),
        "maximum_occupancy": max_occupancy,
    }

    return vehicles, route_details, optimized


def run_simulation(
    max_requests: int = 100,
    vehicle_capacity: int = DEFAULT_VEHICLE_CAPACITY,
    use_ortools: bool = False,
) -> Dict:
    """
    Run complete simulation with both scenarios.
    Returns comparison results.
    """
    # Load requests
    requests = load_ride_requests(max_requests=max_requests)
    routing_engine = RoutingEngine()

    # Run baseline
    baseline = run_baseline_scenario(requests, routing_engine)

    # Run optimized
    vehicles, route_details, optimized = run_optimized_scenario(
        requests, routing_engine, vehicle_capacity, use_ortools
    )

    # Calculate savings
    distance_saved = baseline["total_distance_km"] - optimized["total_distance_km"]
    distance_saved_pct = (
        (distance_saved / baseline["total_distance_km"] * 100.0)
        if baseline["total_distance_km"] > 0
        else 0.0
    )
    trips_saved = baseline["vehicle_count"] - optimized["vehicle_count"]
    trips_saved_pct = (
        (trips_saved / baseline["vehicle_count"] * 100.0)
        if baseline["vehicle_count"] > 0
        else 0.0
    )

    results = {
        "total_requests": len(requests),
        "served_requests": optimized["served_requests"],
        "unserved_requests": optimized["unserved_requests"],
        "vehicle_count": optimized["vehicle_count"],
        "vehicle_capacity": vehicle_capacity,
        "total_distance_individual": baseline["total_distance_km"],
        "total_distance_optimized": optimized["total_distance_km"],
        "distance_saved": round(distance_saved, 3),
        "distance_saved_percent": round(distance_saved_pct, 2),
        "total_travel_time_individual": baseline["total_travel_time_min"],
        "total_travel_time_optimized": optimized["total_travel_time_min"],
        "vehicle_trips_saved": trips_saved,
        "vehicle_trips_saved_percent": round(trips_saved_pct, 2),
        "average_wait_time": optimized["average_wait_time_min"],
        "average_detour": optimized["average_detour_min"],
        "pooling_rate": optimized["pooling_rate"],
        "average_occupancy": optimized["average_occupancy"],
        "maximum_occupancy": optimized["maximum_occupancy"],
        "baseline": baseline,
        "optimized": optimized,
    }

    # Save outputs
    _save_outputs(route_details, vehicles, results)

    return results


def _save_outputs(
    route_details: List[Dict],
    vehicles: List[Vehicle],
    results: Dict,
) -> None:
    """Save simulation outputs to CSV and JSON files."""
    # Save optimized routes
    routes_df = pd.DataFrame(route_details)
    routes_df.to_csv(DATA_DIR / "optimized_routes.csv", index=False)

    # Save vehicle assignments
    vehicle_data = []
    for v in vehicles:
        vehicle_data.append({
            "vehicle_id": v.vehicle_id,
            "capacity": v.capacity,
            "assigned_requests": len(v.assigned_requests),
            "current_occupancy": v.current_occupancy,
        })
    vehicles_df = pd.DataFrame(vehicle_data)
    vehicles_df.to_csv(DATA_DIR / "vehicle_assignments.csv", index=False)

    # Save results JSON
    with open(DATA_DIR / "optimization_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    results = run_simulation(max_requests=100)
    print(f"Simulation complete.")
    print(f"Requests: {results['total_requests']}")
    print(f"Served: {results['served_requests']}")
    print(f"Vehicles: {results['vehicle_count']}")
    print(f"Pooling rate: {results['pooling_rate']:.1f}%")
    print(f"Distance saved: {results['distance_saved']:.3f} km ({results['distance_saved_percent']:.1f}%)")