import numpy as np


def assign_grid_zones(xy: np.ndarray, grid: int = 3) -> np.ndarray:
    """Zone id = cell of a grid x grid partition of the bounding box."""
    lo, hi = xy.min(axis=0), xy.max(axis=0)
    span = np.where(hi - lo > 0, hi - lo, 1.0)
    cell = np.minimum(((xy - lo) / span * grid).astype(int), grid - 1)
    return cell[:, 0] * grid + cell[:, 1]