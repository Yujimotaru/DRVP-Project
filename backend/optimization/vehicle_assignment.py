"""
NITK Campus Mobility - Vehicle Assignment Optimization.
Uses OR-Tools to assign requests to vehicles with ride-pooling.
Falls back to greedy assignment if OR-Tools is unavailable.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .ride_request import RideRequest
from .vehicle import Vehicle, DEFAULT_VEHICLE_CAPACITY
from .routing_engine import RoutingEngine
from .ride_pooling import check_pooling_compatibility, find_poolable_groups


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_ride_requests(csv_path: Optional[Path] = None, max_requests: int = 0) -> List[RideRequest]:
    """
    Load ride requests from the Phase 3 CSV file.
    If max_requests > 0, limit to that many requests.
    """
    path = csv_path or DATA_DIR / "ride_requests.csv"
    df = pd.read_csv(path)

    if max_requests > 0:
        df = df.head(max_requests)

    requests = []
    for _, row in df.iterrows():
        req = RideRequest(
            request_id=row["request_id"],
            request_date=row["request_date"],
            request_time=row["request_time"],
            origin_id=row["origin_id"],
            destination_id=row["destination_id"],
            passenger_count=int(row["passenger_count"]),
            request_type=row["request_type"],
            priority=row["priority"],
            max_wait_min=float(row["max_wait_min"]),
            status=row.get("status", "pending"),
        )
        requests.append(req)

    return requests


def assign_requests_greedy(
    requests: List[RideRequest],
    routing_engine: RoutingEngine,
    vehicle_capacity: int = DEFAULT_VEHICLE_CAPACITY,
    max_vehicles: int = 50,
) -> Tuple[List[Vehicle], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Greedy assignment algorithm.
    Processes requests chronologically and assigns to existing vehicles
    when pooling is compatible, or creates new vehicles when necessary.
    """
    vehicles: List[Vehicle] = []
    assignments: Dict[str, str] = {}
    route_details: List[Dict[str, Any]] = []

    sorted_requests = sorted(requests, key=lambda r: r.request_datetime)

    for request in sorted_requests:
        assigned = False

        for vehicle in vehicles:
            if not vehicle.can_accept(request.passenger_count):
                continue

            if vehicle.assigned_requests:
                last_req_id = vehicle.assigned_requests[-1]
                last_req = next(
                    (r for r in sorted_requests if r.request_id == last_req_id), None
                )
                if last_req:
                    check = check_pooling_compatibility(
                        last_req, request, routing_engine, vehicle_capacity
                    )
                    if check.can_pool:
                        vehicle.assign_request(request.request_id, request.passenger_count)
                        assignments[request.request_id] = vehicle.vehicle_id
                        route_details.append({
                            "vehicle_id": vehicle.vehicle_id,
                            "request_id": request.request_id,
                            "pickup_order": len(vehicle.assigned_requests),
                            "origin_id": request.origin_id,
                            "destination_id": request.destination_id,
                            "passenger_count": request.passenger_count,
                            "distance": routing_engine.get_shortest_distance(
                                request.origin_id, request.destination_id
                            ),
                            "travel_time": routing_engine.get_shortest_time(
                                request.origin_id, request.destination_id
                            ),
                            "wait_time": 0.0,
                            "pooled": True,
                            "route_status": "assigned",
                        })
                        assigned = True
                        break

        if not assigned:
            if len(vehicles) >= max_vehicles:
                route_details.append({
                    "vehicle_id": "unserved",
                    "request_id": request.request_id,
                    "pickup_order": 0,
                    "origin_id": request.origin_id,
                    "destination_id": request.destination_id,
                    "passenger_count": request.passenger_count,
                    "distance": 0.0,
                    "travel_time": 0.0,
                    "wait_time": 0.0,
                    "pooled": False,
                    "route_status": "unserved",
                })
                continue

            vehicle_id = f"vehicle_{len(vehicles) + 1:03d}"
            new_vehicle = Vehicle(
                vehicle_id=vehicle_id,
                capacity=vehicle_capacity,
                current_location=request.origin_id,
            )
            new_vehicle.assign_request(request.request_id, request.passenger_count)
            vehicles.append(new_vehicle)
            assignments[request.request_id] = vehicle_id
            route_details.append({
                "vehicle_id": vehicle_id,
                "request_id": request.request_id,
                "pickup_order": 1,
                "origin_id": request.origin_id,
                "destination_id": request.destination_id,
                "passenger_count": request.passenger_count,
                "distance": routing_engine.get_shortest_distance(
                    request.origin_id, request.destination_id
                ),
                "travel_time": routing_engine.get_shortest_time(
                    request.origin_id, request.destination_id
                ),
                "wait_time": 0.0,
                "pooled": False,
                "route_status": "assigned",
            })

    summary: Dict[str, Any] = {
        "total_requests": len(requests),
        "served_requests": len(assignments),
        "unserved_requests": len(requests) - len(assignments),
        "vehicle_count": len(vehicles),
        "vehicle_capacity": vehicle_capacity,
    }

    return vehicles, route_details, summary


def assign_requests_ortools(
    requests: List[RideRequest],
    routing_engine: RoutingEngine,
    vehicle_capacity: int = DEFAULT_VEHICLE_CAPACITY,
    max_vehicles: int = 50,
) -> Tuple[List[Vehicle], List[Dict[str, Any]], Dict[str, Any]]:
    """
    OR-Tools based assignment with ride-pooling.
    Uses a simplified VRP approach.
    Falls back to greedy if OR-Tools fails.
    """
    try:
        from ortools.constraint_solver import routing_enums_pb2, pywrapcp

        return _solve_with_ortools(
            requests, routing_engine, vehicle_capacity, max_vehicles
        )
    except Exception:
        vehicles, route_details, summary = assign_requests_greedy(
            requests, routing_engine, vehicle_capacity, max_vehicles
        )
        return vehicles, route_details, summary


def _solve_with_ortools(
    requests: List[RideRequest],
    routing_engine: RoutingEngine,
    vehicle_capacity: int,
    max_vehicles: int,
) -> Tuple[List[Vehicle], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Solve using OR-Tools VRP with capacity constraints.
    """
    from ortools.constraint_solver import routing_enums_pb2, pywrapcp

    n = min(len(requests), 50)
    active_requests = requests[:n]

    locations = ["depot_main_gate"]
    pickup_indices: Dict[str, int] = {}
    delivery_indices: Dict[str, int] = {}

    for req in active_requests:
        pickup_idx = len(locations)
        locations.append(req.origin_id)
        pickup_indices[req.request_id] = pickup_idx

        delivery_idx = len(locations)
        locations.append(req.destination_id)
        delivery_indices[req.request_id] = delivery_idx

    num_locations = len(locations)

    dist_matrix: List[List[int]] = []
    for i in range(num_locations):
        row: List[int] = []
        for j in range(num_locations):
            if i == j:
                row.append(0)
            else:
                d = routing_engine.get_shortest_distance(locations[i], locations[j])
                row.append(int(d * 1000))
        dist_matrix.append(row)

    num_vehicles = min(max_vehicles, n)
    manager = pywrapcp.RoutingIndexManager(num_locations, num_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return dist_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    demands = [0] * num_locations
    for req in active_requests:
        demands[pickup_indices[req.request_id]] = req.passenger_count

    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return max(0, demands[from_node])

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,
        [vehicle_capacity] * num_vehicles,
        True,
        "Capacity",
    )

    solver = routing.solver()
    for req in active_requests:
        pickup = manager.NodeToIndex(pickup_indices[req.request_id])
        delivery = manager.NodeToIndex(delivery_indices[req.request_id])
        routing.AddPickupAndDelivery(pickup, delivery)
        solver.Add(routing.VehicleVar(pickup) == routing.VehicleVar(delivery))

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    )
    search_parameters.time_limit.FromSeconds(10)

    solution = routing.SolveWithParameters(search_parameters)

    vehicles: List[Vehicle] = []
    route_details: List[Dict[str, Any]] = []
    assignments: Dict[str, str] = {}

    if solution:
        for vehicle_id in range(num_vehicles):
            index = routing.Start(vehicle_id)
            vehicle = Vehicle(
                vehicle_id=f"vehicle_{vehicle_id + 1:03d}",
                capacity=vehicle_capacity,
            )

            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                next_index = solution.Value(routing.NextVar(index))

                if node != 0:
                    for req in active_requests:
                        if pickup_indices.get(req.request_id) == node:
                            vehicle.assign_request(req.request_id, req.passenger_count)
                            assignments[req.request_id] = vehicle.vehicle_id
                            route_details.append({
                                "vehicle_id": vehicle.vehicle_id,
                                "request_id": req.request_id,
                                "pickup_order": len(vehicle.assigned_requests),
                                "origin_id": req.origin_id,
                                "destination_id": req.destination_id,
                                "passenger_count": req.passenger_count,
                                "distance": routing_engine.get_shortest_distance(
                                    req.origin_id, req.destination_id
                                ),
                                "travel_time": routing_engine.get_shortest_time(
                                    req.origin_id, req.destination_id
                                ),
                                "wait_time": 0.0,
                                "pooled": len(vehicle.assigned_requests) > 1,
                                "route_status": "assigned",
                            })
                            break

                index = next_index

            if vehicle.assigned_requests:
                vehicles.append(vehicle)

    for req in requests[n:]:
        route_details.append({
            "vehicle_id": "unserved",
            "request_id": req.request_id,
            "pickup_order": 0,
            "origin_id": req.origin_id,
            "destination_id": req.destination_id,
            "passenger_count": req.passenger_count,
            "distance": 0.0,
            "travel_time": 0.0,
            "wait_time": 0.0,
            "pooled": False,
            "route_status": "unserved",
        })

    summary: Dict[str, Any] = {
        "total_requests": len(requests),
        "served_requests": len(assignments),
        "unserved_requests": len(requests) - len(assignments),
        "vehicle_count": len(vehicles),
        "vehicle_capacity": vehicle_capacity,
    }

    return vehicles, route_details, summary