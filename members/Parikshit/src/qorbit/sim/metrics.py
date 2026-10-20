"""Plain-language metrics of a plan under a given traffic state: not only total cost."""
from ..cost import Evaluator
from ..models import Solution


def solution_metrics(ev: Evaluator, sol: Solution) -> dict:
    res = ev.evaluate(sol)
    routes = [r for r in res.routes.values() if r.used]
    b = res.breakdown
    return dict(
        cost=res.total_cost,
        distance_km=sum(r.distance_km for r in routes),
        route_hours=sum(r.duration_h for r in routes),        # includes service and waiting
        fuel_l=sum(r.fuel_l for r in routes),
        late_min=60 * sum(r.late_h for r in routes),
        vehicles=len(routes),
        cost_vehicle=b["vehicle"], cost_distance=b["distance"], cost_time=b["time"],
        cost_fuel=b["fuel"], cost_late=b["late"],
    )
