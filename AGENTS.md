# NITK Campus Mobility — AI Development Rules

## Project

Smart India Hackathon 2026 prototype:

**Intelligent Campus Mobility & Ride-Sharing System**

The prototype models campus transportation at NITK Surathkal.

## Core technology

Backend:

* Python
* FastAPI
* Pandas
* NumPy
* Google OR-Tools

Frontend:

* React
* Vite
* Tailwind CSS
* React-Leaflet
* Recharts

Prototype data:

* CSV
* SQLite where necessary

## Important development rules

1. Work in small phases.
2. Never build multiple major phases without verification.
3. Do not rewrite working code unnecessarily.
4. Do not invent geographic coordinates.
5. Do not invent road distances.
6. Do not claim simulated demand values are real NITK statistics.
7. Clearly distinguish verified NITK information from simulation assumptions.
8. Do not replace Google OR-Tools with fake or hard-coded optimization.
9. Do not hard-code final performance metrics.
10. All performance metrics must be calculated from actual simulation results.
11. Preserve the project's mathematical formulation.
12. Keep the prototype compatible with the SIH technical specification.
13. Prefer simple, explainable algorithms for the prototype.
14. Do not implement LSTM, reinforcement learning, payments, real GPS or native mobile applications unless explicitly requested.
15. Every new feature should include validation or tests where practical.

## Current project scope

The NITK prototype should model:

* Main Gate
* Main Building
* Central Library
* e-Library
* Boys Cooperative Society
* Girls Cooperative Society
* Suprabha Boys branch
* Suprabha Girls branch
* LHC-A
* LHC-B
* NITK departments
* Boys hostels
* Girls hostels
* Boys/PG/general messes

Girls' messes must be excluded.

## Campus division

For the prototype, classify these departments as WEST:

* Computer Science & Engineering
* Electronics & Communication Engineering
* Electrical & Electronics Engineering
* Information Technology

The remaining departments and major hostel/facility areas should initially be classified EAST unless verified information says otherwise.

Do not fabricate the precise geographic coordinates or road distances.

## Phase discipline

Only implement the phase explicitly requested by the user.

After completing a phase:

1. Run tests.
2. Report what was created.
3. Report any assumptions.
4. Report any unresolved issues.
5. Stop and wait for the next phase.

Do not automatically continue to the next phase.
