"""Legacy experiment paths must resolve after workspace organization."""
import json
from pathlib import Path

from team_benchmark import layout


def test_recorded_paths_resolve_with_most_specific_mapping(tmp_path, monkeypatch):
    monkeypatch.setattr(layout, "ROOT", tmp_path)
    (tmp_path / "docs").mkdir()
    mapping = {"comparison_results": "results/comparison",
               "comparison_results/pilot": "results/comparison/archive/pilot",
               "SB+QUBO": "members/Rahul"}
    (tmp_path / "docs/PATH_MIGRATION.json").write_text(json.dumps(mapping))
    assert layout.resolve_recorded_path("SB+QUBO/test_cases/TC03.json") == tmp_path / "members/Rahul/test_cases/TC03.json"
    assert layout.resolve_recorded_path(tmp_path / "comparison_results/pilot/runs.json") == tmp_path / "results/comparison/archive/pilot/runs.json"
    assert layout.resolve_recorded_path("team_benchmark/run.py") == tmp_path / "team_benchmark/run.py"


def test_external_paths_are_not_rewritten(tmp_path, monkeypatch):
    monkeypatch.setattr(layout, "ROOT", tmp_path / "project")
    external = tmp_path / "unrelated/instance.json"
    assert layout.resolve_recorded_path(external) == external
