# NITK Campus Mobility — Synthetic Demand Generation Specification

## 1. Simulation Context & Synthetic Data Disclaimer

> [!IMPORTANT]
> **Synthetic Simulation Data Notice**: All ride requests, timestamps, passenger loads, and origin-destination pairs generated in Phase 3 are **synthetic simulation data** created solely for algorithmic benchmarking, dynamic ride-pooling, demand prediction modeling, and OR-Tools route optimization. They **do not represent measured empirical traffic statistics, logs, or surveys** from the NITK Surathkal administration or student body.

---

## 2. Diurnal Temporal Model & Peak Generation

Ride demand is distributed across **7 distinct diurnal time windows** reflecting university operational cycles:

| Period ID | Time Window | Relative Volume | Dominant Behavioral Dynamic |
| :--- | :---: | :---: | :--- |
| `early_morning` | **05:00–07:00** | **5%** | Early risers, sports ground transit, gate drop-offs. |
| `morning_peak` | **07:00–10:00** | **28%** | **Morning Class Rush**: Heavy transit from Boys & Girls Hostels to Lecture Halls (LHC-A/B) and Academic Departments. |
| `mid_day` | **10:00–12:00** | **10%** | Inter-departmental lab sessions, faculty consultations, academic core movements. |
| `lunch_peak` | **12:00–14:30** | **24%** | **Lunch Rush**: Heavy movement from Academic Departments, Lecture Halls, and Libraries to Dining Messes. |
| `afternoon` | **14:30–17:00** | **10%** | Mess return to labs/departments, afternoon seminars, library research. |
| `evening_peak` | **17:00–20:00** | **15%** | **Evening Peak**: Transit to Central Library, e-Library, Suprabha Canteens, and Cooperative Stores. |
| `night` | **20:00–23:00** | **8%** | Library closing, dinner/canteen dispersal, and return transit to Hostels. |

---

## 3. Spatial Origin-Destination (OD) Modeling

Rather than sampling origins and destinations uniformly, trip pairs are generated using **functional transition matrices** weighted by Phase 1 location demand weights:

1. **Origin Weighting**: Candidate origins $O$ are sampled with probability:
   $$P(o) \propto w_{\text{origin}}(\text{period}) \times \text{Capacity}(o)^{0.2}$$
2. **Destination Weighting**: Candidate destinations $D$ are sampled with probability:
   $$P(d) \propto w_{\text{dest}}(\text{period}) \times \text{Capacity}(d)^{0.2}$$
3. **Constraints**:
   - $Origin \neq Destination$ (self-trips are strictly eliminated).
   - $D(Origin, Destination) < \infty$ (origin and destination must be mutually connected via the Phase 2 road network).

---

## 4. User Classes & Parameter Distributions

Configured in [`backend/data/demand_generation_config.json`](file:///c:/Users/jonah/OneDrive/Desktop/DVRP%20Project/backend/data/demand_generation_config.json):

### 4.1 Request Type Distribution
- **Student**: **85.0%** (primary campus transit riders).
- **Staff**: **10.0%** (administrative and laboratory technical staff).
- **Faculty**: **5.0%** (professors and academic instructors).

### 4.2 Passenger Count Distribution
- **1 Passenger**: **70.0%** (solo commuter).
- **2 Passengers**: **20.0%** (pair travel / peer commute).
- **3 Passengers**: **7.0%** (small study group).
- **4 Passengers**: **3.0%** (group commute / full shuttle party).

### 4.3 Priority & Maximum Wait Tolerance (`max_wait_min`)
- **`normal` Priority (90%)**: Maximum acceptable wait sampled uniformly in **[8.0, 15.0] minutes**.
- **`high` Priority (10%)**: Urgency requests (exam rush, scheduled meetings) with wait sampled in **[4.0, 8.0] minutes**.

---

## 5. Random Seed & Simulation Reproducibility

Every generation run uses NumPy's `np.random.default_rng(seed)`:
- Invoking `generate_requests(seed=42)` produces the **exact identical sequence of 5,132 requests**.
- Different seeds (e.g. `seed=100`) produce varied stochastic demand profiles while preserving underlying diurnal and spatial distributions.

---

## 6. Simulation Limitations

1. **Weather Invariance**: Demand does not currently simulate heavy monsoon rain spikes typical of coastal Karnataka.
2. **Calendar Invariance**: The baseline 30-day run models active weekday academic demand without explicit weekend/holiday schedule reductions.
3. **No Dynamic Price Sensitivity**: Demand is inelastic to potential future fare or battery charging incentives.
