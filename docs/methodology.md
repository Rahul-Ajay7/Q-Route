# Methodology

## Problem Definition

Capacitated Vehicle Routing Problem with Time Windows (CVRPTW) under
traffic-dependent travel times. Minimize total weighted cost:

- distance cost
- traffic-induced travel-time cost
- vehicle operating cost
- late-delivery penalties

subject to:

- vehicle capacity
- customer time windows
- vehicle availability windows
- route continuity

## Traffic Modeling

Time-dependent congestion factors scale free-flow speeds, producing
time-varying travel-time matrices used during route evaluation.
