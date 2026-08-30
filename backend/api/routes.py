from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.location_service import (
    get_all_locations,
    get_location_by_id,
)

from backend.services.campus_graph_service import (
    get_shortest_distance,
    get_shortest_travel_time,
    get_shortest_path,
)

from backend.services.demand_analysis import (
    DemandAnalyzer,
)

from backend.optimization.ride_request import (
    RideRequest,
)

from backend.optimization.ride_pooling import (
    find_poolable_groups,
)

from backend.optimization.routing_engine import (
    RoutingEngine,
)

from backend.optimization.vehicle_assignment import (
    assign_requests_greedy,
)


router = APIRouter(
    prefix="/api",
    tags=["NITK Smart Mobility"],
)


# ============================================================
# LOCATION ENDPOINTS
# ============================================================

@router.get("/map/nodes")
def get_map_nodes():
    """Return campus graph nodes with geographic coordinates."""

    from pathlib import Path
    import pandas as pd

    data_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "campus_nodes.csv"
    )

    if not data_path.exists():
        raise HTTPException(
            status_code=404,
            detail="campus_nodes.csv not found",
        )

    df = pd.read_csv(data_path)

    required_columns = [
        "node_id",
        "location_id",
        "name",
        "latitude",
        "longitude",
        "campus",
        "node_type",
        "coordinate_source",
        "coordinate_confidence",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise HTTPException(
            status_code=500,
            detail=f"Missing columns: {missing_columns}",
        )

    nodes = df[required_columns].copy()

    nodes = nodes.where(
        pd.notna(nodes),
        None,
    )

    return {
        "count": len(nodes),
        "nodes": nodes.to_dict(
            orient="records"
        ),
    }
@router.get("/locations")
def locations():
    """
    Return all campus locations.
    """

    locations_data = get_all_locations()

    return {
        "count": len(locations_data),
        "locations": [
            location.model_dump()
            if hasattr(location, "model_dump")
            else location.dict()
            for location in locations_data
        ],
    }


@router.get("/locations/{location_id}")
def location(location_id: str):
    """
    Return a single campus location.
    """

    result = get_location_by_id(location_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Location not found: {location_id}",
        )

    if hasattr(result, "model_dump"):
        return result.model_dump()

    return result.dict()


# ============================================================
# ROUTING ENDPOINT
# ============================================================


@router.get("/route/{origin_id}/{destination_id}")
def route(
    origin_id: str,
    destination_id: str,
):
    """
    Calculate shortest route between two campus locations.
    """

    try:
        distance = get_shortest_distance(
            origin_id,
            destination_id,
        )

        travel_time = get_shortest_travel_time(
            origin_id,
            destination_id,
        )

        path = get_shortest_path(
            origin_id,
            destination_id,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    return {
        "origin_id": origin_id,
        "destination_id": destination_id,
        "distance_km": distance,
        "travel_time_minutes": travel_time,
        "path": path,
    }


# ============================================================
# DEMAND SUMMARY
# ============================================================


@router.get("/demand/summary")
def demand_summary():
    """
    Return summary statistics for ride demand.
    """

    try:
        analyzer = DemandAnalyzer()

        return analyzer.generate_summary_report()

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# RIDE REQUEST MODEL
# ============================================================


class RideRequestInput(BaseModel):

    request_id: str = Field(
        ...,
        description="Unique ride request ID",
    )

    request_date: str = Field(
        ...,
        description="Request date YYYY-MM-DD",
    )

    request_time: str = Field(
        ...,
        description="Request time HH:MM:SS",
    )

    origin_id: str = Field(
        ...,
        description="Origin location ID",
    )

    destination_id: str = Field(
        ...,
        description="Destination location ID",
    )

    passenger_count: int = Field(
        default=1,
        ge=1,
        le=4,
    )

    request_type: str = Field(
        default="student",
    )

    priority: str = Field(
        default="normal",
    )

    max_wait_min: float = Field(
        default=10.0,
        ge=0,
    )


# ============================================================
# BASIC RIDE REQUEST ENDPOINT
# ============================================================


@router.post("/rides/request")
def create_ride_request(
    request: RideRequestInput,
):
    """
    Validate a new ride request.
    """

    origin = get_location_by_id(
        request.origin_id
    )

    if origin is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Origin location not found: "
                f"{request.origin_id}"
            ),
        )

    destination = get_location_by_id(
        request.destination_id
    )

    if destination is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Destination location not found: "
                f"{request.destination_id}"
            ),
        )

    if request.origin_id == request.destination_id:
        raise HTTPException(
            status_code=400,
            detail="Origin and destination must be different.",
        )

    return {
        "status": "accepted",
        "request": request.model_dump(),
    }


# ============================================================
# REAL-TIME OPTIMIZATION
# ============================================================


class OptimizationInput(BaseModel):

    requests: List[RideRequestInput] = Field(
        ...,
        min_length=1,
        description="Ride requests to optimize",
    )

    vehicle_capacity: int = Field(
        default=4,
        ge=1,
        le=4,
    )

    max_vehicles: int = Field(
        default=50,
        ge=1,
    )


@router.post("/rides/optimize")
def optimize_rides(
    payload: OptimizationInput,
):
    """
    Run the Phase 5 ride-pooling and vehicle-assignment
    engine using requests supplied through the API.
    """

    try:

        # ----------------------------------------------------
        # VALIDATE REQUESTS
        # ----------------------------------------------------

        ride_requests: List[RideRequest] = []

        for request in payload.requests:

            origin = get_location_by_id(
                request.origin_id
            )

            if origin is None:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Origin location not found: "
                        f"{request.origin_id}"
                    ),
                )

            destination = get_location_by_id(
                request.destination_id
            )

            if destination is None:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Destination location not found: "
                        f"{request.destination_id}"
                    ),
                )

            if request.origin_id == request.destination_id:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Origin and destination must be different "
                        f"for request {request.request_id}."
                    ),
                )

            ride_request = RideRequest(
                request_id=request.request_id,
                request_date=request.request_date,
                request_time=request.request_time[:5],
                origin_id=request.origin_id,
                destination_id=request.destination_id,
                passenger_count=request.passenger_count,
                request_type=request.request_type,
                priority=request.priority,
                max_wait_min=request.max_wait_min,
                status="pending",
            )

            ride_requests.append(
                ride_request
            )

        # ----------------------------------------------------
        # ROUTING ENGINE
        # ----------------------------------------------------

        routing_engine = RoutingEngine()

        # ----------------------------------------------------
        # POOLING ANALYSIS
        # ----------------------------------------------------

        pool_pairs = find_poolable_groups(
            ride_requests,
            routing_engine,
            vehicle_capacity=payload.vehicle_capacity,
        )

        # ----------------------------------------------------
        # VEHICLE ASSIGNMENT
        # ----------------------------------------------------

        vehicles, assignments, summary = (
            assign_requests_greedy(
                ride_requests,
                routing_engine,
                vehicle_capacity=payload.vehicle_capacity,
                max_vehicles=payload.max_vehicles,
            )
        )

        # ----------------------------------------------------
        # SERIALIZE VEHICLES
        # ----------------------------------------------------

        vehicle_data: List[Dict[str, Any]] = []

        for vehicle in vehicles:

            if hasattr(vehicle, "__dict__"):
                vehicle_data.append(
                    dict(vehicle.__dict__)
                )
            else:
                vehicle_data.append(
                    {
                        "vehicle": str(vehicle)
                    }
                )

        # ----------------------------------------------------
        # RETURN RESULT
        # ----------------------------------------------------

        return {
            "status": "optimized",

            "input_request_count": len(
                ride_requests
            ),

            "poolable_pairs": [
                {
                    "request_index_1": pair[0],
                    "request_index_2": pair[1],
                }
                for pair in pool_pairs
            ],

            "poolable_pair_count": len(
                pool_pairs
            ),

            "vehicle_count": len(
                vehicles
            ),

            "vehicles": vehicle_data,

            "assignments": assignments,

            "optimization_summary": summary,
        }

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Ride optimization failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        )


# ============================================================
# SAVED OPTIMIZATION RESULTS
# ============================================================


@router.get("/optimization/results")
def optimization_results():
    """
    Return the latest saved Phase 5 optimization outputs.
    """

    from pathlib import Path
    import json
    import pandas as pd

    base_dir = Path(__file__).resolve().parents[2]

    data_dir = (
        base_dir
        / "backend"
        / "data"
    )

    result: Dict[str, Any] = {}

    vehicle_file = (
        data_dir
        / "vehicle_assignments.csv"
    )

    routes_file = (
        data_dir
        / "optimized_routes.csv"
    )

    summary_file = (
        data_dir
        / "optimization_results.json"
    )

    if vehicle_file.exists():

        df = pd.read_csv(
            vehicle_file
        )

        result["vehicle_assignments"] = (
            df.to_dict(
                orient="records"
            )
        )

    if routes_file.exists():

        df = pd.read_csv(
            routes_file
        )

        result["optimized_routes"] = (
            df.to_dict(
                orient="records"
            )
        )

    if summary_file.exists():

        with open(
            summary_file,
            "r",
            encoding="utf-8",
        ) as file:

            result[
                "optimization_summary"
            ] = json.load(file)

    return result