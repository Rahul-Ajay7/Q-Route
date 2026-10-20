from ..models import Solution
from .partition import Partition


def splice(sol: Solution, part: Partition, new_order) -> Solution:
    """Return a copy of sol with route[part.start:part.end] replaced by new_order."""
    assert sorted(new_order) == sorted(part.customers), "new order must be a permutation of the partition"
    new = sol.copy()
    new.routes[part.vehicle_id][part.start:part.end] = list(new_order)
    return new
