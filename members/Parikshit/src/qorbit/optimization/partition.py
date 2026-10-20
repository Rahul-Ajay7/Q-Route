"""Adaptive partitioning: overlapping windows of consecutive customers inside one route."""
from dataclasses import dataclass
from ..models import Solution


@dataclass(frozen=True)
class Partition:
    vehicle_id: int
    start: int          # index of first customer in the route
    end: int            # one past the last (route[start:end])
    customers: tuple

    @property
    def size(self) -> int:
        return self.end - self.start


def generate_partitions(sol: Solution, k: int = 5, stride: int | None = None, min_size: int = 3) -> list[Partition]:
    """Windows of up to k customers, moving by `stride` (default k//2 -> ~50% overlap).
    Routes shorter than min_size are skipped (nothing worth reordering)."""
    stride = stride or max(1, k // 2)
    out = []
    for vid, route in sol.routes.items():
        n = len(route)
        if n < min_size:
            continue
        if n <= k:
            out.append(Partition(vid, 0, n, tuple(route)))
            continue
        starts = list(range(0, n - k + 1, stride))
        if starts[-1] != n - k:
            starts.append(n - k)
        out += [Partition(vid, s, s + k, tuple(route[s:s + k])) for s in starts]
    return out