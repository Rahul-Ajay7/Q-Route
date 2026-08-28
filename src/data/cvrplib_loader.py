"""
src/data/cvrplib_loader.py

Parses CVRPLIB .vrp instance files (Set A/B format) into the same plain-dict
structure produced by SyntheticGenerator, so both feed solvers identically.

CVRPLIB format reference: sections NODE_COORD_SECTION, DEMAND_SECTION,
DEPOT_SECTION, CAPACITY. Standard CVRPLIB Set A/B files do NOT include
time windows -- if absent, default wide windows covering full horizon
are assigned so the same CVRPTW pipeline still works.
"""

import re
from typing import Dict, Tuple


class CVRPLibLoader:

    def load(self, filepath: str, default_time_horizon_min: float = 480.0,
              default_service_time_min: float = 10.0,
              vehicles_override: int = None) -> Dict:
        with open(filepath, "r") as f:
            content = f.read()

        capacity = self._parse_capacity(content)
        num_vehicles = vehicles_override or self._parse_num_vehicles(content)
        coords = self._parse_section(content, "NODE_COORD_SECTION")
        demands = self._parse_section(content, "DEMAND_SECTION")
        depot_id = self._parse_depot_id(content)

        customers = []
        depot_coord = None
        for node_id, (x, y) in coords.items():
            if node_id == depot_id:
                depot_coord = (x, y)
                continue
            demand = demands.get(node_id, 0.0)
            customers.append({
                "id": node_id,
                "coord": (x, y),
                "demand": demand,
                "ready_time": 0.0,
                "due_time": default_time_horizon_min,
                "service_time": default_service_time_min,
            })

        if depot_coord is None:
            raise ValueError(f"Depot node {depot_id} not found in NODE_COORD_SECTION")

        vehicles = [
            {
                "id": vid,
                "capacity": capacity,
                "shift_window": (0.0, default_time_horizon_min),
            }
            for vid in range(1, num_vehicles + 1)
        ]

        return {
            "depot": {"coord": depot_coord},
            "customers": customers,
            "vehicles": vehicles,
        }

    def _parse_capacity(self, content: str) -> float:
        match = re.search(r"CAPACITY\s*:\s*(\d+)", content)
        if not match:
            raise ValueError("CAPACITY field not found in .vrp file")
        return float(match.group(1))

    def _parse_num_vehicles(self, content: str) -> int:
        """
        CVRPLIB filenames often encode vehicle count e.g. A-n32-k5.vrp = k5
        means 5 vehicles. Try COMMENT field first, else default to 1
        (caller should override via vehicles_override if known from filename).
        """
        match = re.search(r"No of trucks:\s*(\d+)", content)
        if match:
            return int(match.group(1))
        return 1

    def _parse_depot_id(self, content: str) -> int:
        section = content.split("DEPOT_SECTION")[1] if "DEPOT_SECTION" in content else ""
        for line in section.strip().splitlines():
            line = line.strip()
            if line and line != "-1":
                return int(line)
        return 1  # CVRPLIB convention: node 1 is usually depot

    def _parse_section(self, content: str, section_name: str) -> Dict[int, Tuple]:
        result = {}
        if section_name not in content:
            return result
        section = content.split(section_name)[1]
        # stop at next SECTION keyword or EOF marker
        for stop_kw in ["_SECTION", "DEPOT_SECTION", "EOF"]:
            if stop_kw in section and stop_kw != section_name:
                idx = section.find(stop_kw)
                if idx > 0:
                    section = section[:idx]
                    break

        for line in section.strip().splitlines():
            parts = line.split()
            if not parts or not parts[0].lstrip("-").isdigit():
                continue
            node_id = int(parts[0])
            if section_name == "NODE_COORD_SECTION" and len(parts) >= 3:
                result[node_id] = (float(parts[1]), float(parts[2]))
            elif section_name == "DEMAND_SECTION" and len(parts) >= 2:
                result[node_id] = float(parts[1])
        return result
