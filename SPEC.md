# Dekot Village Simulation — Milestone 1 Spec

Status: settled. No further design rounds before build.

## 1. Purpose

A deterministic, rules-based village simulation of Dekot (Kalahandi, Odisha).
Milestone 1 proves the engine: ten villagers eat, work, rest, form relationships,
fight over one scarce plot, and age under a hazard model. No LLM. The question
milestone 1 answers is whether the villagers' tomorrow is worth watching.

Later milestones (not in scope here): bounded LLM intentions, families and births,
lifestyle-driven health, institutions, dashboard.

## 2. Time

- `ticks_per_day = 12`, `days_per_year = 8` (config). Live mode: 1 real hour = 1 Dekot day.
- Two clocks, one compression:
  - **Routine clock** (ticks, days): meals, work, rest, conversations, disputes, memory recency.
  - **Life clock** (years): aging, mortality, chronic health.
- The compression is stylized and accepted: a 7-day dispute spans 0.875 life-years.
  The two durations are **not independent**; routine days = life-years × `days_per_year`.
- Routine behaviour **does** feed biology. Every conversion from routine quantities
  (meals, rest ticks) to biological updates is explicit in `health.py` and stated in
  routine units → per-day biological delta. Mixing units without an explicit
  conversion is a defect.

## 3. Agents

- Traits (fixed, 0–100): stubbornness, helpfulness, temper, piety, ambition, sociability.
- State: age (years, float), health (0–100), fatigue (0–100), mood (0–100), inventory.
- Roles: farmer, cowherd. Assigned by trait fit (helpfulness → cowherd; farmers by ambition, most ambitious gets the good plot). Farmers beyond the plot count are **landless**: they forage at a low fixed yield until a plot is vacant. Farming requires ownership; the engine raises on violation.
- Founders start aged 18–45, spread evenly. No births, no immigration.

## 4. World and economy

- Grid map with paddy plots (one high-fertility "good plot") and grazing land.
- Resources: rice, milk. Per-agent inventories. Village has no shared granary in M1.
- Opening balances are ledger entries. Every creation, consumption, or transfer is a ledger entry (fixed 4-decimal precision, applied and logged identically):
  `(day, tick, seq, actor, action, resource, delta, reason)`.
- Invariants: no inventory is ever negative; replaying the ledger reconstructs every inventory exactly; no farm entry from a non-owner.

## 5. Daily routine (rules)

- Night ticks: rest. Day ticks: work at assigned plot / herd. Two meal ticks.
- A meal consumes 1 rice. Shortfall triggers a request to the most helpful neighbour
  with surplus; transfer is a ledger entry and raises affinity. Unmet meal = hungry.
- Work produces rice (plot fertility × effort) or milk (herd size × effort). Milk is
  consumed as a diet supplement when present.

## 6. Health and mortality

Applied once per day at end of day:

- `health += food_gain × meals_eaten/2 − hunger_loss × (2 − meals_eaten) + rest_gain × (rest_ticks/rest_needed) − fatigue_loss × overwork_ticks − age_decay(age)`
- `annual_hazard = base × exp(k × age) × exp(β × (50 − health) / 50)`
- `delta_years = 1 / days_per_year`
- `p_death = 1 − exp(−annual_hazard × delta_years)` (constant hazard within step, documented).
- Death is a seeded roll against `p_death`. `health = 100` does **not** eliminate age mortality.
- Target distributions are fictional calibration choices, tuned over experiments, not facts.

## 7. Relationships and dispute

- Affinity graph (−100..100) between every pair. Food gifts raise it; dispute losses lower it.
- One dispute type: claim on the good plot. Each year the two highest-ambition farmers
  not currently holding it contest the holder. Resolution is a seeded draw weighted by
  stubbornness, affinity with the holder, and current health. Outcome is an event and
  moves affinity.

## 8. Determinism, replay, experiments

- Two seeds: `founder_seed` builds the starting village (traits, roles, plots); `seed` drives simulation randomness. RNG state is part of saved state.
- **Replay**: same seed + starting state + config + engine fingerprint → byte-identical
  canonical event log. Canonical means: stable ordering (day, tick, seq), stable IDs,
  sorted-key JSON, no wall-clock timestamps in compared output.
- **Fingerprint**: SHA-256 over all simulation-affecting source files, Python version,
  and dependency list. Written to the run manifest.
- **Experiments**: same `founder_seed` and config, N distinct `seed` values.
- Checkpoints store the engine fingerprint; resuming under a different fingerprint is rejected unless forced.
- Saved state mid-run + resume reproduces the uninterrupted log.

## 9. Stopping condition

Run for `duration_years = 5` (40 Dekot days) or until population < 2, whichever first.
Five years measures **short-term survival**, not lifespan. Extinction is possible,
not expected.

## 10. Experiment metrics (headless, N seeds)

- Survival by **starting-age cohort** (18–30, 31–45): observation time in life-years and event flag per agent; Kaplan–Meier survival by year. Agents alive at stop are **censored**.
- Hunger reported three ways: missed meals, hungry agent-days, hungry village-days. Population by year with unobserved years (after early stop) marked missing. End-of-run balances, dispute outcomes.
- Invariant checks fail the run: negative inventory; ledger delta without reason.
- For the later LLM comparison: matched starting conditions; measure invalid-action rate,
  tokens and cost per Dekot day, behavioural divergence (action and dispute-outcome
  distributions) against the deterministic baseline.

## 11. Acceptance criteria

1. `dekot run --seed 1` completes a 5-year run headless and writes `events.jsonl`, `ledger.jsonl`, `manifest.json`.
2. Two runs with the same seed and config produce byte-identical event and ledger logs; a different seed produces a different log.
3. Save at day 20, resume, and the combined log is byte-identical to the uninterrupted run.
4. Invariants hold across 1,000 seeds: no negative inventory, every ledger entry has a reason, ledger replay reconstructs inventories exactly, no non-owner farm entries.
5. `p_death` is in (0, 1), increases with age, decreases with health, and is non-zero at health = 100.
6. `dekot experiment --runs 1000` keeps the starting village fixed and reports KM survival by cohort with censoring, hunger (meals / agent-days / village-days), population by observed year, balances, dispute outcomes.
9. A checkpoint from a different engine fingerprint is rejected on resume.
7. Headless throughput: **performance target** ≤ 2 s per 5-year run on a laptop, to be measured — not a claim.
8. Event feed is readable as a text stream; map state is serialisable for a later viewer.
