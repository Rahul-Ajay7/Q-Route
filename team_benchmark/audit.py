"""Independent final-route accounting; deliberately does not call Problem methods."""
from collections import Counter
import math


def audit(problem, routes):
    data, p = problem.data, problem.costs
    nodes = {n["id"]: n for n in [data["depot"]] + data["customers"]}
    index = {n: i for i, n in enumerate(nodes)}
    depot = data["depot"]["id"]
    expected = Counter(c["id"] for c in data["customers"])
    assert len(routes) == len(data["vehicles"]), "Wrong fleet length"
    assert Counter(c for r in routes for c in r) == expected, "Missing/duplicate/unknown customer"
    distance = travel = duration = liters = late = total = 0.0
    for vehicle, route in zip(data["vehicles"], routes):
        if not route:
            continue
        load = sum(nodes[c].get("demand", 0) for c in route)
        assert load <= vehicle["capacity"] + 1e-9, "Over capacity"
        begin = max(data.get("simulation", {}).get("start_time", 0), data["depot"].get("ready_time", 0))
        clock, prev = begin, depot
        rd = rt = rf = rl = 0.0
        for node in route + [depot]:
            events = sorted((e for e in data.get("traffic_events", [])
                             if (e["from"], e["to"]) == (prev, node)), key=lambda e: e["time"])
            trials = sorted({clock} | {float(t) for e in events for t in (e["time"], e.get("end_time"))
                                      if t is not None and t > clock})
            for depart in trials:
                active = [e for e in events if e["time"] <= depart and
                          (e.get("end_time") is None or depart < e["end_time"])]
                mult = active[-1].get("multiplier") if active else 1.0
                if mult is not None:
                    break
            assert mult is not None, "Permanently closed edge"
            tt = float(data["_matrix"][index[prev], index[node]]) * mult
            d = math.hypot(nodes[prev]["x"]-nodes[node]["x"], nodes[prev]["y"]-nodes[node]["y"])
            rf += d * p.liters_per_km * (1+p.load_premium*load/max(vehicle["capacity"], 1e-9)) * (
                1+p.congestion_premium*max(0, mult-1))
            rd += d
            rt += tt
            clock = depart + tt
            customer = nodes[node]
            if node != depot:
                releases = [e["time"] for e in data.get("order_events", [])
                            if e.get("type") == "new_order" and e["customer_id"] == node]
                clock = max([clock, customer.get("ready_time", 0), customer.get("release_time", 0)] + releases)
            excess = max(0, clock-customer.get("due_time", math.inf))
            rl += excess
            assert not problem.hard_windows or excess <= 1e-9, "Late service/depot return"
            if node != depot:
                clock += customer.get("service_time", 0)
                load -= customer.get("demand", 0)
            prev = node
        assert not any(e.get("type") == "breakdown" and e.get("vehicle_id") == vehicle["id"]
                       and clock > e["time"] for e in data.get("vehicle_events", [])), "Breakdown"
        distance += rd
        travel += rt
        duration += clock-begin
        liters += rf
        late += rl
        total += rd*p.distance_per_km + (clock-begin)*p.driver_per_minute + rf*p.fuel_per_liter + (
            rl*p.late_per_minute) + p.vehicle_fixed
    return dict(cost=total, distance=distance, travel_minutes=travel, duration_minutes=duration,
                fuel_liters=liters, lateness_minutes=late)
