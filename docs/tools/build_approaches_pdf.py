"""Render the four-method report using the existing matplotlib dependency."""
from pathlib import Path
import os
import tempfile
import textwrap

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "qorbit-mpl"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

DOCS = Path(__file__).resolve().parents[1]
SOURCE = DOCS / "FOUR_APPROACHES.md"
TARGET = DOCS / "FOUR_APPROACHES.pdf"


def blocks(text):
    """Yield paragraphs, headings and preformatted blocks without a Markdown dependency."""
    paragraph = []
    code = None
    for line in text.splitlines() + [""]:
        if line.startswith("```"):
            if paragraph:
                yield "body", " ".join(paragraph)
                paragraph = []
            if code is None:
                code = []
            else:
                yield "code", "\n".join(code)
                code = None
        elif code is not None:
            code.append(line)
        elif line.startswith("#"):
            if paragraph:
                yield "body", " ".join(paragraph)
                paragraph = []
            yield ("title" if line.startswith("# ") else "section"), line.lstrip("# ")
        elif not line.strip():
            if paragraph:
                yield "body", " ".join(paragraph)
                paragraph = []
        else:
            paragraph.append(line.strip())


def build():
    page = 0
    fig = None
    y = 0
    with PdfPages(TARGET, metadata={
        "Title": "Q-ORBIT: Four Optimization Approaches",
        "Author": "Q-ORBIT team",
        "Subject": "Classical SA, tunnelling SA, QUBO+SB and adaptive hybrid v2",
    }) as pdf:
        def new_page():
            nonlocal fig, y, page
            if fig is not None:
                pdf.savefig(fig)
                plt.close(fig)
            page += 1
            fig = plt.figure(figsize=(8.27, 11.69), facecolor="white")
            fig.text(0.085, 0.96, "Q-ORBIT  /  METHODS & EVIDENCE", fontsize=8,
                     color="#256c80", weight="bold")
            fig.add_artist(plt.Line2D([0.085, 0.915], [0.944, 0.944],
                                     transform=fig.transFigure, color="#c9dce1", lw=1))
            fig.text(0.085, 0.035, "21 October 2026 • Shared benchmark / hybrid v2",
                     fontsize=7.5, color="#637580")
            fig.text(0.915, 0.035, str(page), fontsize=8, ha="right", color="#637580")
            y = 0.91

        new_page()
        for kind, value in blocks(SOURCE.read_text(encoding="utf-8")):
            if kind == "section":
                new_page()
            size = {"title": 27, "section": 20, "body": 10.5, "code": 8.2}[kind]
            width = {"title": 32, "section": 40, "body": 82, "code": 82}[kind]
            lines = value.splitlines() if kind == "code" else textwrap.wrap(value, width)
            line_height = size * (1.5 if kind in ("title", "section") else 1.45) / (11.69 * 72)
            # All current code blocks fit; keep them together if a page is nearly full.
            if kind == "code" and y - len(lines) * line_height < 0.085:
                new_page()
            for line in lines:
                if y - line_height < 0.085:
                    new_page()
                fig.text(0.085 if kind != "code" else 0.10, y, line, fontsize=size,
                         va="top", family="DejaVu Sans Mono" if kind == "code" else "DejaVu Sans",
                         weight="bold" if kind in ("title", "section") else "normal",
                         color="#173549" if kind in ("title", "section") else "#263640")
                y -= line_height
            y -= 0.018 if kind in ("title", "section") else 0.013
        pdf.savefig(fig)
        plt.close(fig)
    print(f"Created {TARGET}: {page} pages, {TARGET.stat().st_size:,} bytes")


if __name__ == "__main__":
    build()
