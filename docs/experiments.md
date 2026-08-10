# Experiments

## Configuration

Experiments are driven by YAML files in `experiments/configs/`:

- `small.yaml` — 15 customers
- `medium.yaml` — 50 customers
- `large.yaml` — 120 customers

## Running

```bash
python experiments/run_greedy.py
python experiments/run_sa.py
python experiments/run_qubo.py
python experiments/run_all.py
```

## Outputs

Results are written to `results/` (raw, processed, tables, figures).
