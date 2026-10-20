"""Partition pressure score = estimated extra INR the traffic change causes inside a partition.

Score(P) = c_t * (extra driving hours on legs touching P)
         + fuel_price * (extra litres on those legs)
         + lambda_late * (extra lateness at P's customers)
measured by tracing the SAME route under old traffic (ev0) and new traffic (ev1).
Delay that spills onto customers after P is not counted here (it is picked up by the
full-solution evaluation when a change is accepted)."""
from dataclasses import dataclass
from ..cost import Evaluator
from ..models import Solution
from .partition import Partition, generate_partitions


@dataclass(frozen=True)
class PartitionScore:
    partition: Partition
    total: float
    time: float
    fuel: float
    late: float


def rank_partitions(sol: Solution, k: int, ev0: Evaluator, ev1: Evaluator, **gen_kw) -> list[PartitionScore]:
    p = ev1.p
    traces = {}
    for vid, route in sol.routes.items():
        veh = ev1.inst.vehicles[vid]
        traces[vid] = (ev0.trace_route(veh, route), ev1.trace_route(veh, route))
    scores = []
    for part in generate_partitions(sol, k, **gen_kw):
        t0, t1 = traces[part.vehicle_id]
        legs = range(part.start, part.end + 1)          # legs touching the window, incl. entry and exit leg
        d_time = sum(t1[l]["travel_h"] - t0[l]["travel_h"] for l in legs)
        d_fuel = sum(t1[l]["fuel_l"] - t0[l]["fuel_l"] for l in legs)
        d_late = sum(t1[l]["late_h"] - t0[l]["late_h"] for l in range(part.start, part.end))
        time_c, fuel_c, late_c = p.c_t * d_time, p.fuel_price * d_fuel, p.lambda_late_per_hour * d_late
        scores.append(PartitionScore(part, time_c + fuel_c + late_c, time_c, fuel_c, late_c))
    return sorted(scores, key=lambda s: s.total, reverse=True)