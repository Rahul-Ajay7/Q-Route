#!/usr/bin/env bash
# Runs ONLY the experiments needed for the Q-ORBIT (greedy + QUBO + SA) results, then the statistics.
# usage:  bash run_experiments.sh            (full study, ~35-45 min)
#         nohup bash run_experiments.sh > all.log 2>&1 &      (recommended; then: tail -f all.log)
# Skip the parameter sweeps:  SKIP_SWEEPS=1 bash run_experiments.sh
# Quick smoke test:  SEEDS=1 SOLVES=3 SWEEP_SEEDS=1 bash run_experiments.sh
set -e
cd "$(dirname "$0")"
PY=python
[ -x .venv/bin/python ] && PY=.venv/bin/python        # uses the project's venv even if it is not activated
SEEDS=${SEEDS:-30}; SOLVES=${SOLVES:-30}; SWEEP_SEEDS=${SWEEP_SEEDS:-6}
mkdir -p results/figures
run() { echo; echo "=== $* ==="; "$PY" -u "$@"; }

# E1 main comparison on R101 (all five methods)
run experiments/run_dynamic.py --solomon data/solomon/R101.txt  --seeds $SEEDS --solves $SOLVES --k ${K:-5} \
    --methods do_nothing,direct_sa,qorbit_swap,qorbit_random --out results/final_r101.csv
# E2 other Solomon families (swap variant: identical answers to flip, about 5x faster)
run experiments/run_dynamic.py --solomon data/solomon/C101.txt  --seeds $SEEDS --solves $SOLVES --k ${K:-5} \
    --methods do_nothing,direct_sa,qorbit_swap,qorbit_random --out results/final_c101.csv
run experiments/run_dynamic.py --solomon data/solomon/RC101.txt --seeds $SEEDS --solves $SOLVES --k ${K:-5} \
    --methods do_nothing,direct_sa,qorbit_swap,qorbit_random --out results/final_rc101.csv
# E3 parameter studies (skip with SKIP_SWEEPS=1)
if [ -z "$SKIP_SWEEPS" ]; then
  run experiments/run_sweeps.py --sweep k      --solomon data/solomon/R101.txt --seeds $SWEEP_SEEDS --solves 15
  run experiments/run_sweeps.py --sweep lambda --solomon data/solomon/R101.txt --seeds $SWEEP_SEEDS --solves 15
fi
# statistics and figures
run experiments/analyze_results.py results/final_r101.csv
cp results/stats.md results/stats_r101.md
run experiments/analyze_results.py results/final_r101.csv results/final_c101.csv results/final_rc101.csv --ref qorbit_swap
cp results/stats.md results/stats_all_instances.md
run experiments/plot_recovery.py results/final_r101.csv results/figures/recovery_r101.png
run experiments/plot_recovery.py results/final_c101.csv results/figures/recovery_c101.png
run experiments/plot_recovery.py results/final_rc101.csv results/figures/recovery_rc101.png
echo; echo "ALL DONE. Results in results/ (stats_r101.md, stats_all_instances.md, sweep_*.csv, figures/)"
