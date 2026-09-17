"""N-seed experiments (SPEC §8, §10).

Starting village is fixed by cfg.founder_seed; only cfg.seed (simulation randomness) varies.
"""
from collections import Counter, defaultdict
from dataclasses import replace
from .engine import Simulation

COHORTS = ((18, 30), (31, 45))


def cohort(age0):
    for lo, hi in COHORTS:
        if lo <= age0 <= hi:
            return f"{lo}-{hi}"
    return "other"


def km_survival(obs, cfg):
    """Kaplan-Meier survival at each whole life-year. obs = [(time_years, event)]; event=1 death, 0 censored."""
    times = sorted(set(t for t, _ in obs))
    at_risk, surv, out = len(obs), 1.0, {}
    for t in times:
        d = sum(1 for tt, e in obs if tt == t and e == 1)
        c = sum(1 for tt, e in obs if tt == t and e == 0)
        if at_risk > 0:
            surv *= (1 - d / at_risk)
        at_risk -= d + c
        out[round(t, 3)] = round(surv, 4)
    return {y: min((v for t, v in out.items() if t <= y), default=1.0) for y in range(cfg.duration_years + 1)}


def run_experiment(cfg, runs, base_seed=1000):
    obs = defaultdict(list); counts = defaultdict(Counter)
    hungry_meals = []; hungry_agent_days = []; hungry_village_days = []
    pop_by_year = defaultdict(list); balances = Counter(); disputes = Counter(); stops = Counter()
    for i in range(runs):
        sim = Simulation(replace(cfg, seed=base_seed + i))
        start = {a.id: a.age for a in sim.agents}
        sim.run()
        stops[sim.stopped] += 1
        for a in sim.agents:
            if a.id not in start:
                continue  # born mid-run; founder cohorts only
            c = cohort(start[a.id])
            t = ((a.death_day + 1) if not a.alive else sim.day) / cfg.days_per_year
            obs[c].append((t, 0 if a.alive else 1))
            counts[c]["n"] += 1; counts[c]["censored" if a.alive else "died"] += 1
        hungry = [(e["day"], e["agent"]) for e in sim.events.entries if e["type"] == "hungry"]
        hungry_meals.append(len(hungry))
        hungry_agent_days.append(len(set(hungry)))
        hungry_village_days.append(len({d for d, _ in hungry}))
        for e in sim.events.entries:
            if e["type"] == "dispute":
                disputes[e["outcome"]] += 1
        for y in range(cfg.duration_years + 1):
            d = y * cfg.days_per_year
            if d > sim.day:
                pop_by_year[y].append(None)  # unobserved after early stop
            else:
                pop_by_year[y].append(sum(1 for a in sim.agents if a.alive or a.death_day >= d))
        for a in sim.agents:
            for r, v in a.inventory.items():
                balances[r] += v

    def mean(xs):
        xs = [x for x in xs if x is not None]
        return round(sum(xs) / len(xs), 2) if xs else None

    return {"runs": runs, "founder_seed": cfg.founder_seed, "stop_reasons": dict(stops),
            "survival_by_cohort": {c: {**counts[c], "km_survival_by_year": km_survival(obs[c], cfg)} for c in sorted(obs)},
            "hungry_meals_mean": mean(hungry_meals),
            "hungry_agent_days_mean": mean(hungry_agent_days),
            "hungry_village_days_mean": mean(hungry_village_days),
            "population_by_year": {y: {"mean": mean(v), "observed_runs": sum(x is not None for x in v)} for y, v in sorted(pop_by_year.items())},
            "end_balances_mean": {r: round(v / runs, 2) for r, v in balances.items()},
            "dispute_outcomes": dict(disputes)}
