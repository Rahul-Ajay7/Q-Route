"""Solomon VRPTW parser.

Mapping to our units (documented so results are reproducible):
  1 coordinate unit = 1 km; 1 Solomon time unit = 1 minute; speed = 60 km/h
  (so travel time in minutes == Euclidean distance, as in the original benchmark).
  Clock time = day_start + minutes/60.

Tolerant of CRLF/LF, tabs/spaces/commas, BOM, UTF-16 and non-breaking spaces.
Customer row = 7 numbers (id x y demand ready due service); vehicle row = 2 numbers.
"""
import re
import numpy as np
from ..models import Customer, Vehicle, ProblemInstance
from ..traffic import assign_grid_zones


def _read_text(path: str) -> str:
    raw = open(path, "rb").read()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in raw[:200]:
        return raw.decode("utf-16", errors="replace")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def load_solomon(path: str, day_start: float = 8.0, grid: int = 3) -> ProblemInstance:
    text = _read_text(path).replace("\u00a0", " ")
    nums, veh = [], None
    for line in text.splitlines():
        parts = [p for p in re.split(r"[\s,;]+", line.strip()) if p]
        try:
            vals = [float(p) for p in parts]
        except ValueError:
            continue                                   # header / title lines
        if len(vals) == 2 and veh is None and not nums:
            veh = (int(vals[0]), vals[1])
        elif len(vals) == 7:
            nums.append(vals)
    if not nums or veh is None:
        preview = [l for l in text.splitlines() if l.strip()][:6]
        raise ValueError(
            f"{path}: could not read Solomon data (customer rows found: {len(nums)}, "
            f"vehicle row found: {veh is not None}, file size: {len(text)} chars).\n"
            f"First non-empty lines: {preview!r}\n"
            "Expected the Solomon text format (VEHICLE / NUMBER CAPACITY / CUSTOMER ... rows of 7 numbers). "
            "If the file looks like HTML or is empty, re-download it.")
    n_veh, cap = veh
    arr = np.array(nums)
    xy = arr[:, 1:3]
    dist = np.linalg.norm(xy[:, None] - xy[None], axis=2)
    customers = {int(r[0]): Customer(int(r[0]), r[3], day_start + r[4] / 60, day_start + r[5] / 60, r[6] / 60)
                 for r in arr[1:]}
    vehicles = {v: Vehicle(v, cap, day_start) for v in range(1, n_veh + 1)}
    return ProblemInstance(customers, vehicles, dist, dist / 60.0, assign_grid_zones(xy, grid),
                           depot_due=day_start + arr[0, 5] / 60, coords=xy)