"""Pairing, births and coming of age. A post-M1 addition, still pure seeded rules.

Runs once per life-year, like the dispute. All draws come from sim.rng and all
iteration orders are sorted, so replay determinism is preserved.
"""
from .agents import Agent, TRAITS, name_for


def year_tick(sim, day):
    _pair_singles(sim, day)
    _births(sim, day)


def _fertile(a, cfg):
    return a.alive and cfg.fertile_age_min <= a.age <= cfg.fertile_age_max


def _related(a, b):
    pa, pb = set(a.parents or ()), set(b.parents or ())
    return a.id in pb or b.id in pa or bool(pa & pb)  # parent-child or siblings


def _pair_singles(sim, day):
    cfg = sim.cfg
    by_id = {a.id: a for a in sim.agents}
    singles = sorted(
        (a for a in sim.living()
         if _fertile(a, cfg) and (a.partner is None or not by_id[a.partner].alive)),
        key=lambda a: a.id)
    while singles:
        a = singles.pop(0)
        candidates = [b for b in singles if b.sex != a.sex and not _related(a, b)]
        if not candidates:
            continue
        match = max(candidates, key=lambda b: (sim.rel.get(a.id, b.id),
                                               a.traits["sociability"] + b.traits["sociability"], b.id))
        if sim.rng.random() < cfg.pair_chance:
            singles.remove(match)
            a.partner, match.partner = match.id, a.id
            match.home = list(a.home)  # the couple shares one house
            sim.rel.shift(a.id, match.id, 30)
            sim.events.add(day, 0, type="paired", a=a.id, b=match.id)


def _births(sim, day):
    cfg = sim.cfg
    by_id = {a.id: a for a in sim.agents}
    seen = set()
    for a in sorted(sim.living(), key=lambda x: x.id):
        if a.partner is None or a.id in seen:
            continue
        b = by_id[a.partner]
        if not b.alive or b.id in seen or not (_fertile(a, cfg) and _fertile(b, cfg)):
            continue
        seen.update((a.id, b.id))
        if sim.rng.random() < cfg.birth_chance:
            _born(sim, day, a, b)


def _born(sim, day, pa, pb):
    cfg = sim.cfg
    i = len(sim.agents)
    traits = {t: max(0, min(100, (pa.traits[t] + pb.traits[t]) // 2 + sim.rng.randint(-10, 10)))
              for t in TRAITS}
    sex = "f" if sim.rng.random() < 0.5 else "m"
    nth = sum(1 for x in sim.agents if x.sex == sex)
    child = Agent(id=f"a{i:02d}", name=name_for(sex, nth), traits=traits, age=0.0, sex=sex,
                  role="child", health=70.0, inventory={"rice": 0.0, "milk": 0.0},
                  parents=[pa.id, pb.id], pos=list(pa.home), home=list(pa.home))
    sim.agents.append(child)
    sim.rel.add_agent(child.id, [x.id for x in sim.agents if x.id != child.id])
    sim.rel.shift(child.id, pa.id, 60)
    sim.rel.shift(child.id, pb.id, 60)
    # the child's opening rice is a ledgered transfer from the parent with more
    give = min(cfg.child_rice_at_birth, max(pa.inventory["rice"], pb.inventory["rice"]))
    donor = pa if pa.inventory["rice"] >= pb.inventory["rice"] else pb
    if give > 0:
        sim.ledger.transfer(day, 0, donor, child, "rice", give, "birth")
    else:
        sim.ledger.apply(day, 0, child, "rice", 0.0, "opening_balance", "birth")
    sim.ledger.apply(day, 0, child, "milk", 0.0, "opening_balance", "birth")
    sim.events.add(day, 0, type="birth", child=child.id, name=child.name,
                   parents=[pa.id, pb.id])


def come_of_age(sim, a, day):
    a.role = "farmer"
    a.plot = None  # landless until a plot is vacant
    sim.events.add(day, sim.cfg.ticks_per_day - 1, type="came_of_age", agent=a.id)
