# Project review checklist

Last updated: 21 October 2026. Check tasks off after recording their evidence
or review outcome. This is the remaining-work list, not a list of implemented
features. Hybrid v2 remains the active method.

## Immediate

- [ ] Commit and push the latest documentation, this checklist, and the archived
  adaptive-removal experiment to `Rahul-Ajay7/Q-Route` on `main`. Record the
  successful commit in the [development record](PROJECT_MASTER_RECORD.md).
- [ ] Have Alphonsa review the classical-SA baseline implemented for her role.
  Record whether she approves it or supplies a replacement; preserve provenance.

## Input and construction reliability

- [ ] Investigate shared construction failures on TC15, TC16 and TC25.
- [ ] Investigate construction failure on `R101_traffic.json`.
- [ ] Review TC14, which contains CSV despite its JSON extension. Preserve the
  original and document any correction or intentional exclusion separately.
- [ ] If initialization changes, apply it equally to every compared method and
  rerun under a new protocol/output folder. Never replace historical failure
  records or treat construction failure as a proof of infeasibility.

## Stronger evaluation and research

- [ ] Add a mature external VRP solver baseline with comparable costs,
  constraints, initialization policy and recorded runtime.
- [ ] Select genuinely independent test instances before tuning, then freeze
  settings and evaluate multiple seeds and longer budgets.
- [ ] Test whether QUBO adds value beyond classical repair using matched
  no-QUBO controls and equal budgets. Include direct permutation enumeration
  as a local-window control: five customers have 120 possible visit orders.
- [ ] Preserve feasibility counts, ties, losses, timing overruns, raw routes,
  source/input hashes and independent audits for every new experiment.

The adaptive-removal experiment is already archived; it does not need to be
reintroduced. See its [findings and restoration guide](history/ADAPTIVE_REMOVAL_PILOT.md)
before revisiting the same idea.

## Final presentation and submission

- [ ] Prepare the final presentation and report with the current method,
  member attribution, experimental protocol, graphs and limitations.
- [ ] Clearly distinguish the earlier frozen validation from the latest complete
  rerun. Use the [latest summary](../results/comparison/four_approaches_20261021/SUMMARY.md)
  and [graph index](../results/comparison/four_approaches_20261021/plots/README.md).
- [ ] Review the [method PDF](FOUR_APPROACHES.pdf) for the intended submission:
  its numerical section describes the earlier evaluation. If the submission
  needs the latest rerun, update its editable source and regenerate the PDF.
- [ ] Verify the demo, documented commands and production tests on the machine
  used for the presentation.

## Claims to retain during review

Supported scope: hybrid v2 achieved lower average cost than the three implemented
baselines on the stated supplied suite and runtime budget.

Not established: universal superiority, quantum advantage, a QUBO-specific
benefit, or validated live dispatch. Synthetic costs are not measured operational
savings. Broader research tasks above strengthen the evidence; the current
implementation can already support a working demonstration.
