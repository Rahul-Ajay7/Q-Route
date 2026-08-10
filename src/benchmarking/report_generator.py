"""Generate result reports and tables."""

from __future__ import annotations

from typing import Dict


class ReportGenerator:
    """Export comparison results to CSV / Markdown / LaTeX."""

    def to_csv(self, results: Dict, path: str) -> None:
        raise NotImplementedError

    def to_markdown(self, results: Dict, path: str) -> None:
        raise NotImplementedError

    def to_latex(self, results: Dict, path: str) -> None:
        raise NotImplementedError
