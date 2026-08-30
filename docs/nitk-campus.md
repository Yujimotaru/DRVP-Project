# NITK Surathkal — Campus Geography & Location Data Specification

## 1. Overview and East/West Campus Concept

The National Institute of Technology Karnataka (NITK), Surathkal spans across a ~295-acre campus along the Arabian Sea coast in Mangalore, Karnataka. 

A defining structural feature of the NITK campus is its geographic division by **National Highway 66 (NH-66)** (formerly NH-17). The highway physically bisects the campus into two distinct operational zones:
1. **West Campus (Beach Side / Tech Side)**: Located towards the Arabian Sea, housing key circuit and computing branches.
2. **East Campus (Main Side / Residential & Core Academic Side)**: Located inland across NH-66, housing administrative headquarters, core engineering departments, science departments, libraries, lecture hall complexes, hostel blocks, dining halls, and cooperative stores.

Pedestrian and vehicular movement between the East and West sides occurs via designated underpasses/overpasses, establishing a natural clustering and transit boundary for campus mobility routing.

---

## 2. Campus Division & Subzones

### West Campus (`WEST`)
The West Campus primarily contains the technological and circuit branches:
* **Computer Science & Engineering (CSE)**
* **Electronics & Communication Engineering (ECE)**
* **Electrical & Electronics Engineering (EEE)**
* **Information Technology (IT)**

### East Campus (`EAST`)
The East Campus contains the majority of the institute's academic, residential, dining, and administrative infrastructure:
* **Administrative & Landmark Centers**: Main Building, Main Gate.
* **Libraries & Academic Centers**: Central Library, e-Library, Lecture Hall Complex A (LHC-A), Lecture Hall Complex B (LHC-B).
* **Core Engineering & Sciences**:
  * Mechanical Engineering
  * Civil Engineering
  * Chemical Engineering
  * Metallurgical & Materials Engineering (MME)
  * Mining Engineering
  * Mathematical & Computational Sciences (MACS)
  * Physics
  * Chemistry
  * School of Humanities, Social Sciences and Management (HSSM)
  * Water Resources and Ocean Engineering (WROE)
* **Residential Blocks**:
  * Boys Hostels (Blocks 1–8 including Block 6 Pushpagiri, Mega Towers 1–3 Everest/Himalaya/Kailash, Brahmagiri PG, Shivalik)
  * Girls Hostels (GH 1–6: Ganga, Kaveri, Yamuna, Sharavathi, Netravathi, Godavari)
* **Dining & Commercial Facilities**:
  * Official Boys/General Messes (11 locations per 2025 Mess Location Chart)
  * Canteens (Suprabha – Boys Side, Suprabha – Girls Side)
  * Co-operative Societies (Boys Co-op Society, Girls Co-op Society)

---

## 3. Location Inventory & Categories

The Phase 1 dataset (`backend/data/locations.csv`) models **54 discrete locations**:

| Category | Count | Classification | Example Locations |
| :--- | :---: | :---: | :--- |
| **Major Landmarks & Facilities** | 10 | `EAST` | Main Gate, Main Building, Central Library, e-Library, LHC-A, LHC-B, Co-op Societies, Suprabha Canteens |
| **West Campus Departments** | 4 | `WEST` | CSE, ECE, EEE, IT |
| **East Campus Departments** | 10 | `EAST` | Mechanical, Civil, Chemical, MME, Mining, MACS, Physics, Chemistry, HSSM, WROE |
| **Boys Hostels** | 13 | `EAST` | Blocks 1 (Karavali), 2 (Aravali), 3 (Vindhya), 4 (Satpura), 5 (Nilgiri), 6 (Pushpagiri), 7 (Sahyadri), 8 (Trishul), Mega Towers 1–3, Brahmagiri PG, Shivalik |
| **Girls Hostels** | 6 | `EAST` | GH 1 (Ganga), GH 2 (Kaveri), GH 3 (Yamuna), GH 4 (Sharavathi), GH 5 (Netravathi), GH 6 (Godavari) |
| **Official Dining Messes** | 11 | `EAST` | GB Mess, PG-New Brahmagiri, PG-Pushpagiri, B1: Karavali, B2: Aravali, B3: Vindhya, B4: Satpura, B5: Nilgiri, B7: Sahyadri, B8: Trishul, Mega Mess |
| **Total** | **54** | — | — |

---

## 4. Official Mess Structure (2025 Mess Location Chart)

The dining mess set is modeled strictly from the **official NITK 2025 Mess Location Chart** for boys and general students:
1. **GB Mess**
2. **PG-New Brahmagiri**
3. **PG-Pushpagiri**
4. **B1: Karavali**
5. **B2: Aravali**
6. **B3: Vindhya**
7. **B4: Satpura**
8. **B5: Nilgiri**
9. **B7: Sahyadri**
10. **B8: Trishul**
11. **Mega Mess**

Generic, unverified names (such as Central Mess, Mega Mess 1/2, Brahma Mess, Campus Food Court) are deprecated and excluded from the mobility graph. Girls' messes remain strictly excluded from this prototype per specifications.

---

## 5. Excluded Locations & Phase Boundaries

Per the project specifications and phase discipline:
1. **Girls' Messes**: Strictly excluded from the dataset and routing prototype.
2. **Fabricated Geographic Coordinates**: No latitude or longitude values have been invented or added to the dataset.
3. **Fabricated Road Distances**: No synthetic road distances, travel times, or routing matrices have been hardcoded. Spatial graphs and distance matrices are deferred to subsequent verified phases.
4. **Department of Design & Entrepreneurship**: Deferred until physical campus location is verified.
5. **Non-Campus Commercial Spots**: External off-campus vendors and private transport hubs are excluded.

---

## 6. Verified Facts vs. Simulation Assumptions

To ensure complete transparency and scientific rigor, the distinction between grounded facts and simulation assumptions is maintained:

### Verified Facts
* Geographic split of NITK Surathkal across **NH-66**.
* Placement of **CSE, ECE, EEE, and IT** on the **West Campus**.
* Location of **Main Building, Central Library, e-Library, LHC-A, and LHC-B** on the **East Campus**.
* Existence and designations of NITK boys hostel blocks (Blocks 1–8 including Block 6 Pushpagiri, Mega Towers Everest/Himalaya/Kailash, Brahmagiri, Shivalik).
* Existence and designations of NITK girls hostel blocks (GH 1 to GH 6).
* 11 Official Boys/General Mess locations from the **2025 NITK Mess Location Chart**.

### Simulation Assumptions
* **Demand Weights (`peak_demand_weight`, `morning_demand_weight`, `lunch_demand_weight`, `evening_demand_weight`, `night_demand_weight`)**: Normalized weights between `0.0` and `1.0` modeled to reflect campus temporal cycles (class rush at 08:00–09:00, lunch rush at 12:00–14:00, library/canteen evening rush at 17:00–21:00). These are **not measured empirical traffic statistics** from the NITK administration.
* **Capacities (`capacity`)**: Estimated representative holding capacities for simulation modeling and batch load balancing.
* **Subzone Designations (`subzone`)**: Synthetic groupings (e.g., `East Campus - Academic Core`, `West Campus - Tech Cluster`, `East Campus - Boys Hostels`) created to facilitate discrete zone-level demand aggregation in future phases.
