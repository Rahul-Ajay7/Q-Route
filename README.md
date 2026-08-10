# Q-ORBIT

Quantum-Optimized Route-Based Intelligent Transportation for capacity-constrained vehicle routing with traffic-aware travel times.

## Overview

Q-ORBIT solves the Capacitated Vehicle Routing Problem with Time Windows (CVRPTW) under dynamic traffic conditions, combining classical heuristics (greedy, simulated annealing) with quantum-inspired QUBO formulations.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Run experiments:

```bash
python experiments/run_all.py
```

Launch the dashboard:

```bash
streamlit run dashboard/app.py
```

## Project Layout

```
Q-ORBIT/
├── config/         # YAML configuration files
├── data/           # raw, processed, and synthetic datasets
├── src/            # core source code
├── dashboard/      # Streamlit dashboard
├── experiments/    # experiment entry points
├── tests/          # unit and integration tests
├── results/        # outputs (tables, figures)
└── docs/           # documentation
```

## License

See the LICENSE file.
