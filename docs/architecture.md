# Architecture

## Overview

Q-ORBIT is organized into modular packages under `src/`:

- **data**: loading CVRPLIB and synthetic instances, preprocessing into matrices
- **models**: core entities (Customer, Vehicle, Depot, Route, ProblemInstance)
- **constraints**: capacity, time windows, vehicle availability, feasibility
- **cost**: distance, traffic, operating, late penalty, weighted objective
- **traffic**: dynamic congestion model and travel-time estimation
- **optimization**: greedy, simulated annealing, and QUBO-based solvers
- **benchmarking**: run comparisons, compute metrics, generate reports
- **visualization**: route plots, convergence curves, animations, maps
- **routing**: OSRM client and road-route matrices
- **utils**: logging, timing, helpers

## Data Flow

```
raw inputs -> preprocessing -> matrices -> ProblemInstance -> solvers -> Solution -> reports
```

## Dashboard

Streamlit app under `dashboard/` with pages for problem setup, optimization,
results, and map view.
