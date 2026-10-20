"""Current project locations and resolution of paths in historical manifests."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEMBERS = ROOT / "members"
COMPARISON_DATA = ROOT / "data/comparison"
COMPARISON_RESULTS = ROOT / "results/comparison"


def resolve_recorded_path(value):
    """Resolve a recorded project path without rewriting historical evidence."""
    path = Path(value)
    if path.is_absolute():
        try:
            relative = path.relative_to(ROOT)
        except ValueError:
            return path
    else:
        relative = path
    mappings = json.loads((ROOT / "docs/PATH_MIGRATION.json").read_text(encoding="utf-8"))
    for old, new in sorted(mappings.items(), key=lambda item: len(item[0]), reverse=True):
        try:
            suffix = relative.relative_to(old)
        except ValueError:
            continue
        return ROOT / new / suffix
    return ROOT / relative
