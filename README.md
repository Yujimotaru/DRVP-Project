# Intelligent Campus Mobility & Ride-Sharing System
**Smart India Hackathon 2026 — Prototype Project**

Optimizing campus transportation at **NITK Surathkal** through shared mobility, demand prediction, mechanical fleet modeling, and dynamic vehicle routing.

---

## 1. Project Objective

College campuses like NITK experience concentrated, time-sensitive transit demand between hostels, academic departments, lecture halls, libraries, dining messes, and transit gates. This prototype models:
- Short-horizon ride demand prediction across campus zones.
- Spatiotemporal ride-pooling to group compatible transit requests.
- Dynamic Vehicle Routing Problem with Time Windows and Ride-Pooling (DVRPTW-RP) using Google OR-Tools.
- Mechanical fleet and energy consumption constraints.

---

## 2. Project Architecture & Phases

### Phase 1: Campus Data Foundation
- 54 validated campus locations across major landmarks, academic departments, boys hostels, girls hostels, and official 2025 messes.
- Pydantic models, LocationService query layer, and unit test suite.

### Phase 2: Campus Geographic Graph & Road Network
- **Campus Nodes (`backend/data/campus_nodes.csv`)**: 54 geolocated nodes based on OpenStreetMap and verified campus positions.
- **Campus Road Graph (`backend/data/campus_edges.csv`)**: 70 connected road/path segments with conservative speed assumptions in `backend/data/mobility_assumptions.json`.
- **NH-66 Underpass Crossing**: Explicit gateway edges ensuring valid, realistic East-West campus routing.
- **Shortest Path Matrices (`distance_matrix.csv`, `travel_time_matrix.csv`)**: Precomputed $54 \times 54$ shortest-path distances and travel times via Dijkstra's algorithm.
- **Graph Service (`backend/services/campus_graph_service.py`)**: Traversal, adjacency, and dynamic Dijkstra routing API.

### Phase 3: Synthetic Campus Demand Generator
- **Demand Config (`backend/data/demand_generation_config.json`)**: Configurable diurnal parameters across 7 time windows.
- **Reproducible Generator (`backend/services/demand_generator.py`)**: Seeded stochastic trip generation influenced by Phase 1 demand weights and Phase 2 graph connectivity.
- **Baseline Dataset (`backend/data/ride_requests.csv`)**: ~5,000 synthetic ride requests across 30 simulation days.
- **Demand Analysis Engine (`backend/services/demand_analysis.py`)**: Breakdown of hourly demand, top origins/destinations, passenger loads, and average trip metrics.

---

## 3. Current Folder Structure

```
DVRP Project/
├── backend/
│   ├── __init__.py
│   ├── data/
│   │   ├── campus_edges.csv
│   │   ├── campus_nodes.csv
│   │   ├── demand_generation_config.json
│   │   ├── distance_matrix.csv
│   │   ├── locations.csv
│   │   ├── mobility_assumptions.json
│   │   ├── ride_requests.csv
│   │   └── travel_time_matrix.csv
│   ├── models/
│   │   ├── __init__.py
│   │   └── location.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── campus_graph_service.py
│   │   ├── demand_analysis.py
│   │   ├── demand_generator.py
│   │   └── location_service.py
│   └── tests/
│       ├── __init__.py
│       ├── test_campus_graph.py
│       ├── test_demand_generator.py
│       └── test_locations.py
├── frontend/
│   └── .gitkeep
├── docs/
│   ├── geographic-data.md
│   ├── nitk-campus.md
│   ├── synthetic-demand.md
│   └── unresolved-geography.md
├── AGENTS.md
├── PROJECT_SPEC.md
└── README.md
```

---

## 4. How to Run Tests

### Prerequisites
Ensure Python 3.10+ and dependencies (`pandas`, `numpy`, `pydantic`, `pytest`) are installed:
```powershell
pip install pandas numpy pydantic pytest
```

### Running All Tests
```powershell
python -m pytest backend/tests/ -v
```

### Running Demand Analysis Summary
```powershell
python -c "from backend.services.demand_analysis import DemandAnalyzer; a = DemandAnalyzer(); print(a.generate_summary_report())"
```
