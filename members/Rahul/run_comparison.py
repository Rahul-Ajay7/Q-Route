"""Existing ballistic SB backend under the shared team objective/constraints."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from team_benchmark.member_cli import main

if __name__ == "__main__":
    main("qubo_sb")
