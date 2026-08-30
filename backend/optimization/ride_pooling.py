"""
NITK Campus Mobility - Ride Pooling Compatibility.
Determines whether two or more ride requests can be pooled into a single vehicle.
"""

from dataclasses import dataclass
from typing import List, Tuple

from .ride_request import RideRequest
from .routing_engine import RoutingEngine


MAX_PICKUP_WAIT_MINUTES = 10.0
MAX_DETOUR_MINUTES = 8.0
MAX_ROUTE_OVERHEAD_PERCENT = 40.0


@dataclass
class PoolingCheck:
    """Result of a pooling compatibility check."""
    can_pool: bool
    reason: str
    detour_minutes: float = 0.0
    combined_distance: float = 0.0
    individual_distance: float = 0.0


def check_pooling_compatibility(
    request1: RideRequest,
    request2: RideRequest,
    routing_engine: RoutingEngine,
    vehicle_capacity: int = 4,
) -> PoolingCheck:
    """
    Check if two ride requests can be pooled together.

    Criteria:
    1. Combined passenger count must not exceed vehicle capacity.
    2. Requests must be within a reasonable time window.
    3. The detour for pooling must be within acceptable limits.
    """

    # Check capacity
    combined_passengers = request1.passenger_count + request2.passenger_count
    if combined_passengers > vehicle_capacity:
        return PoolingCheck(
            can_pool=False,
            reason="capacity_exceeded",
            detour_minutes=0.0,
        )

    # Check time window compatibility
    time_diff = abs(
        (request1.request_datetime - request2.request_datetime).total_seconds() / 60.0
    )
    if time_diff > MAX_PICKUP_WAIT_MINUTES:
        return PoolingCheck(
            can_pool=False,
            reason="time_window_exceeded",
            detour_minutes=0.0,
        )

    # Calculate individual direct distances
    dist1 = routing_engine.get_shortest_distance(
        request1.origin_id, request1.destination_id
    )
    dist2 = routing_engine.get_shortest_distance(
        request2.origin_id, request2.destination_id
    )
    individual_distance = dist1 + dist2

    # Calculate pooled route distance
    # Try both pickup orderings and choose the shorter one
    # Route A: pickup1 -> pickup2 -> dropoff1 -> dropoff2
    route_a = _calculate_pooled_route_distance(
        request1, request2, routing_engine, order="AB"
    )
    # Route B: pickup1 -> pickup2 -> dropoff2 -> dropoff1
    route_b = _calculate_pooled_route_distance(
        request1, request2, routing_engine, order="BA"
    )

    combined_distance = min(route_a, route_b)

    # Calculate detour
    if individual_distance > 0:
        overhead_percent = ((combined_distance - individual_distance) / individual_distance) * 100.0
    else:
        overhead_percent = 0.0

    if overhead_percent > MAX_ROUTE_OVERHEAD_PERCENT:
        return PoolingCheck(
            can_pool=False,
            reason="excessive_detour",
            detour_minutes=0.0,
            combined_distance=combined_distance,
            individual_distance=individual_distance,
        )

    # Calculate detour time
    detour_distance = combined_distance - individual_distance
    # Approximate: use average speed from routing
    if detour_distance > 0:
        direct_time = routing_engine.get_shortest_time(
            request1.origin_id, request1.destination_id
        )
        if dist1 > 0:
            avg_speed_km_per_min = dist1 / max(direct_time, 0.1)
            detour_minutes = detour_distance / max(avg_speed_km_per_min, 0.1)
        else:
            detour_minutes = 0.0
    else:
        detour_minutes = 0.0

    if detour_minutes > MAX_DETOUR_MINUTES:
        return PoolingCheck(
            can_pool=False,
            reason="detour_time_exceeded",
            detour_minutes=detour_minutes,
            combined_distance=combined_distance,
            individual_distance=individual_distance,
        )

    return PoolingCheck(
        can_pool=True,
        reason="compatible",
        detour_minutes=detour_minutes,
        combined_distance=combined_distance,
        individual_distance=individual_distance,
    )


def _calculate_pooled_route_distance(
    request1: RideRequest,
    request2: RideRequest,
    routing_engine: RoutingEngine,
    order: str = "AB",
) -> float:
    """
    Calculate total distance for a pooled route.
    order="AB": pickup1 -> pickup2 -> dropoff1 -> dropoff2
    order="BA": pickup1 -> pickup2 -> dropoff2 -> dropoff1
    """
    if order == "AB":
        legs = [
            (request1.origin_id, request2.origin_id),
            (request2.origin_id, request1.destination_id),
            (request1.destination_id, request2.destination_id),
        ]
    else:
        legs = [
            (request1.origin_id, request2.origin_id),
            (request2.origin_id, request2.destination_id),
            (request2.destination_id, request1.destination_id),
        ]

    total = 0.0
    for origin, dest in legs:
        total += routing_engine.get_shortest_distance(origin, dest)

    return total


def find_poolable_groups(
    requests: List[RideRequest],
    routing_engine: RoutingEngine,
    vehicle_capacity: int = 4,
) -> List[Tuple[int, int]]:
    """
    Find all pairs of requests that can be pooled.
    Returns list of (index1, index2) tuples.
    """
    poolable = []
    for i in range(len(requests)):
        for j in range(i + 1, len(requests)):
            result = check_pooling_compatibility(
                requests[i], requests[j], routing_engine, vehicle_capacity
            )
            if result.can_pool:
                poolable.append((i, j))
    return poolable