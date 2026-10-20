# Methodology

## Problem

Urban delivery planning assigns customers to a capacity-constrained fleet and
orders each vehicle's visits. Customers have service durations and delivery time
windows; road travel times may vary with departure time and known congestion
events. The objective is to minimize an explicit operating cost while visiting
every customer exactly once and returning every used vehicle to its depot.
This is a traffic-dependent capacitated vehicle-routing problem with time windows.

CVRPTW is NP-hard. Exact methods remain useful for small instances and for some
larger structured instances, but do not provide a general practical runtime
guarantee as instance size increases. Existing fleet-routing software, including
[Google OR-Tools](https://developers.google.com/optimization/routing/vrptw) and
the [Google Maps Route Optimization API](https://developers.google.com/maps/documentation/route-optimization/reference/rpc/google.maps.routeoptimization.v1),
already addresses multi-vehicle assignments and scheduling. This project's aim
is to study a particular hybrid heuristic and its quality/latency tradeoffs.

## Optimization model used in the comparison

Every customer appears in exactly one route. Loads cannot exceed the assigned
vehicle's capacity. Vehicles start at the supplied planning time and make one
depot-returning trip. Service can begin only after the customer's ready time,
release time, and any new-order event time. In the main experiment, service must
start by the due time and depot return must meet the depot deadline.

All costs are expressed in INR, with explicitly synthetic coefficients:

\[
C(R)=c_v N_{used}+c_d D(R)+c_t H(R)+c_f F(R)+c_l L(R).
\]

Here D is distance in synthetic km, H is complete route duration in minutes
(driving, waiting, service), F is estimated fuel in litres, and L is total lateness
in minutes. Fuel depends on remaining load and congestion. Under hard windows,
L must be zero. A separate soft-window experiment permits lateness at a monetary
penalty; it is a different optimization problem and is reported separately.

Traffic events affect directed edges at departure. A vehicle can wait through
a closure until an event boundary reopens the edge. This is an offline model:
the full traffic/event information is known during optimization. It is not a live
dispatch simulation, and the reported distances and fuel are model estimates.

## Hybrid algorithm

A nearest-feasible-neighbour construction produces initial routes; feasible
insertion restarts are attempted if construction leaves customers unassigned.
Global simulated annealing then explores customer relocation across vehicles,
swaps, and route reversals. It retains the best complete feasible solution.

The current [v2 implementation](HYBRID_V2.md) waits for sustained stagnation,
then attempts bounded regret-based removal and reinsertion of customers across
vehicles, including attempts to eliminate a short route. It chooses eligible
QUBO windows by avoidable detour rather than total route cost, and backs off
after unsuccessful refinements. Windows contain at most five customers by
default, so the customer-position QUBO has at most 25 binary variables.

Binary variable x(i,p) assigns customer i to position p. The QUBO contains entry,
exit, adjacency, and approximate waiting/lateness costs, plus one-customer-per-slot
and one-slot-per-customer penalties. A penalty bound exceeds the full maximum
valid surrogate cost. Departure times and load are approximated from the current
route; exact dynamic propagation and hard feasibility are checked after decoding.

Classical binary simulated annealing samples the local QUBO by default; the
optional SB backend uses the existing ballistic simulated bifurcation solver.
Invalid assignment
matrices are projected to a one-to-one assignment using maximum-score matching.
Each decoded candidate is reinserted and evaluated against the full operating
cost. Only feasible improvements are retained. Selected customer IDs are excluded
for a fixed number of subsequent refinement cycles to encourage exploration.
Global SA then resumes, allowing assignments and route boundaries to change.

The computation is classical; SB is a quantum-inspired mechanical optimization
algorithm, and a QUBO formulation alone does not demonstrate quantum computation.
No method executes on quantum hardware. The other methods are
classical global SA, Angel's tunnelling-inspired SA adapted from
[La Cour et al.](https://doi.org/10.1007/s10955-016-1570-4), and QUBO solved by the
existing ballistic SB implementation inspired by
[Goto et al.](https://doi.org/10.1126/sciadv.abe7953).

## Research question and acceptable conclusion

The research question is whether plateau-triggered QUBO refinement with temporary
customer exclusion improves feasible operating cost at a given time budget,
compared with classical SA, tunnelling-inspired SA, and QUBO+SB.

Identical initial solutions, one evaluator, paired cases/search seeds, recorded
wall time, and independent final-route audits support this comparison. Removing
QUBO, exclusion, or ranking in separate ablations tests the proposed mechanism.
An external mature solver and independently held-out instances are necessary
before making broader performance claims.

An acceptable positive claim is: "On the stated test suite, objective, constraints,
and time budget, the hybrid reduced mean cost by X relative to Y, with the reported
interval and paired results." Fill X only from the recorded data. Negative or
mixed results require a scoped tradeoff statement. Exhaustive tiny-instance
optimality checks do not prove superiority on larger instances or quantum advantage.
