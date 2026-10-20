# Team routing code review and implementation update

Historical v1 writeup. Current implementation and results are documented in
[hybrid v2](../HYBRID_V2.md). Older evidence links open the containing ZIP;
see [archive instructions](../../results/archive/README.md). Statements about
placeholder modules and tests describe the project before cleanup.

Date: 21 October 2026. Scope: routing, costs, constraints, QUBO/SB/SA solvers,
experiment entry points, tests, and existing reports relevant to the four-way
comparison. This is not a claim of a line-by-line audit of every dashboard,
network client, generated artifact, or bundled archive migration script.

## Findings and resulting changes

| Area | Finding | Action |
|---|---|---|
| Alphonsa | Folder empty; no classical SA submission available | Implemented `members/Alphonsa/classical_sa.py` with shared global SA; member review pending |
| Angel | Submitted implementation is tunnelling-inspired route SA, not QUBO+SA | Preserved source unchanged; added common-evaluator adapter and explicit attribution |
| Angel standalone | Unsound direct-edge infeasibility precheck, raw mixed objective units, ID-index assumption, approximate move width | Bypassed precheck/objective/index handling in comparison; retain heuristic move width and document it |
| Rahul SB | Working independently tested ballistic SB and QUBO encoding, but fixed vehicle membership and different raw-unit objective | Reused SB backend with shared monetary evaluator and common window QUBO; preserved historical runs |
| Parikshit original | Local traffic repair; no global SA plateau/refinement/recombination cycle or customer tabu mechanism | Added `run_hybrid.py` and complete shared hybrid implementation; preserved original experiment framework |
| Parikshit original objective | Soft windows by default; cannot compare directly to hard-window SB results | Shared hard-window main experiment and separately selectable soft-window sensitivity |
| Parikshit original QUBO | Comment claims normalized coefficients alone guarantee penalty adequacy; that is not generally sufficient | New shared encoding bounds the entire valid surrogate cost before setting assignment penalty |
| Root SA neighbourhood | Could not relocate a customer into an unused vehicle | Fixed target selection, including the one-customer/empty-vehicle case |
| Root greedy/SA conversion | Routes for unused earlier vehicle slots could shift to the wrong vehicle | Greedy emits `vehicle_index`; conversion preserves and validates slots |
| Root evaluator | Duplicate/unknown IDs and wrong fleet length could receive misleading scores | Reject structural violations with infinity; existing soft penalties for other violations retained |
| Root test suite | Nine original tests were `assert True` placeholders | Replaced SA placeholder with substantive regressions; added shared mathematical/constraint tests. Other eight placeholders are still not validation |
| Root scaffolding | QUBO solver, decoder, benchmarking, traffic-model and some visualization modules contain `NotImplementedError` | New member entry points use the working shared pipeline. These unrelated scaffold APIs remain incomplete and are not cited as working evidence |
| Inputs | `TC14.json` contains CSV; several file names differ from internal IDs | Log invalid input, continue valid suite, preserve names/data, return exit 1 |
| Feasibility | Construction failure is not proof that no solution exists | Explicit NO_FEASIBLE_INITIAL_SOLUTION, no finite score for partial routes |
| Evaluation | Different cost units, fuel assumptions, traffic and initialization prevented attribution | Shared INR model, identical initialization, matched wall time, separate final-route accounting audit |
| Selection | Repeated selection of a single expensive block can starve other QUBO windows | Track attempted windows for all methods and cycle through eligible alternatives |
| Claims | Original package's traffic-damage report shows direct SA stronger than QUBO repair and random selection competitive | Preserve that report as historical evidence; do not describe it as proof of hybrid superiority |

## What remains outside this implementation

The common experiments are offline plans with known synthetic traffic. They do
not replay a live event stream, freeze already travelled route prefixes, fetch
traffic APIs, rescue a broken-down vehicle, or implement online insertion. Input
breakdown events conservatively invalidate a vehicle's whole route if completion
occurs after failure. These cases need a separate online simulator before claims
about operational real-time dispatch.

There is no general proof of superiority for any heuristic. Tiny exhaustive
enumeration proves optimum only for those tiny instances. Equal wall time and
paired statistics support scoped empirical claims. They do not prove quantum
advantage, universal optimality, or a benefit from QUBO when an SA-only ablation
matches or beats it.

The shared evaluator is a new comparison contract; it does not silently replace
each member's historical result files. New member scripts call the shared code
so fixes apply equally. Source/input hashes accompany results for traceability.

## Reproducible evidence

Use [the shared protocol](../../team_benchmark/README.md) for commands. The complete
new-suite report lives in `results/comparison/full_suite/REPORT.md`, with raw
per-run routes, histories, counters, and paired statistics alongside it.
`results/comparison/archive/pilot` is an earlier development smoke run and must not be
pooled with the final suite: algorithm source hashes differ. The interrupted
early full-suite attempt was restarted after correcting window exploration.

See `results/comparison/full_suite/manifest.json` for the exact source hashes,
inputs, seeds, settings, Python, and NumPy versions for the completed experiment.
