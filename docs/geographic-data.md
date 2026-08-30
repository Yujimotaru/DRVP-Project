# NITK Campus Mobility — Geographic Data Specification & Graph Model

## 1. Overview & Geographic Foundation

Phase 2 models the **54 verified NITK campus locations** as a spatial road network graph. The model encompasses:
- Geographic coordinates for each campus facility.
- A connected graph of 70 bidirectional road/path edges representing real campus circulation corridors.
- An explicit **NH-66 Underpass Crossing** serving as the sole authorized gateway between East and West campus.
- Precomputed $54 \times 54$ shortest-path road distance and travel time matrices computed using Dijkstra's algorithm.

---

## 2. Coordinate Sources & Confidence Breakdown

Each location node in [`backend/data/campus_nodes.csv`](file:///c:/Users/jonah/OneDrive/Desktop/DVRP%20Project/backend/data/campus_nodes.csv) is categorized by source and confidence:

| Coordinate Source | Confidence | Count | Percentage | Representative Entities |
| :--- | :---: | :---: | :---: | :--- |
| **OpenStreetMap (`openstreetmap`)** | `high` | **38** | 70.4% | Main Gate, Main Building, Central Library, e-Library, LHC-B, ECE, EEE, IT, Mech, Civil, Chem, MME, Mining, MACS, Physics, Chemistry, HSSM, WROE, Boys Hostels (Blocks 1–5, 6 Pushpagiri, 7, 8, MT 1–3, Brahmagiri, Shivalik), GH 2, GH 5, GH 6, Mega Mess, Boys Co-op, Girls Co-op, Suprabha Boys |
| **Estimated (`estimated`)** | `high` | **9** | 16.7% | CSE (Tech cluster wing), Mess halls attached to specific blocks (B1, B2, B3, B4, B5, B7, B8, PG-Brahmagiri, PG-Pushpagiri) |
| **Estimated (`estimated`)** | `medium` | **7** | 13.0% | LHC-A (adjacent to LHC-B), Suprabha Girls (GH complex), GH 1, GH 3, GH 4, GB Mess |
| **Unresolved (`unresolved`)** | `low` | **0** | 0.0% | None (all 54 locations geolocated with medium to high confidence) |
| **Total** | — | **54** | **100.0%** | — |

---

## 3. Road Distance & Travel Time Methodology

### 3.1 Road Distances (`distance_km`)
- Distances for road segments are derived from the Haversine formula on OpenStreetMap coordinate nodes, incorporating a standard road winding factor (~1.15 for campus roads, ~1.05 for pedestrian walkways, and ~1.30 for underpass approach ramps).
- Shortest path distances between arbitrary pairs of locations are computed strictly via **Dijkstra's shortest path algorithm** over the campus graph rather than direct straight-line Euclidean distance.

### 3.2 Vehicle Speed & Travel Time Estimation (`estimated_time_min`)
Travel times are calculated using the velocity parameters defined in [`backend/data/mobility_assumptions.json`](file:///c:/Users/jonah/OneDrive/Desktop/DVRP%20Project/backend/data/mobility_assumptions.json):

$$\text{estimated\_time\_min} = \left(\frac{\text{distance\_km}}{\text{speed\_kmh}}\right) \times 60$$

| Road Classification | Assumed Speed | Application Scope |
| :--- | :---: | :--- |
| `internal_campus_road` | **20 km/h** | Primary thoroughfares: NITK Spine, Main Gate Avenue, Engineering Ring Road, Beach Road. |
| `slow_campus_road` | **15 km/h** | Secondary hostel corridors, delivery lanes, and parking loops. |
| `underpass_crossing` | **15 km/h** | Vehicle underpass ramp and tunnel passage beneath NH-66. |
| `walking_path` | **5 km/h** | Pedestrian walkways, academic plazas, and mess approach paths. |

> [!NOTE]
> Speed and travel time figures are **simulation assumptions** chosen for conservative campus safety and vehicle modeling, and are **not measured empirical traffic records** from NITK Surathkal.

---

## 4. East-West Campus Underpass Connectivity

NITK Surathkal is physically bisected by National Highway 66:
- All West-bound trips (e.g. from East hostels/academic buildings to CSE/ECE/EEE/IT) and East-bound trips are **strictly routed through the NH-66 Underpass Crossing edge** (`edge_004`, `edge_005`, `edge_006`).
- No direct highway crossings or arbitrary shortcuts across NH-66 are permitted in the mobility graph.

---

## 5. Limitations of the Geographic Model

1. **Elevation Profile**: Campus terrain is modeled on a 2D planar sphere (Haversine); coastal topographical elevation differences are not yet factored into mechanical gradients.
2. **Pedestrian vs. Motorized Exclusivity**: All 70 edges are currently modeled as shared-transit links suitable for electric campus shuttles; future phases may define separate pedestrian-only graph overlays if necessary.
3. **Temporal Congestion**: Edge traversal speeds are currently static baseline values and do not simulate dynamic time-of-day traffic friction.
