"""The shared tick-level state format (plan Phase 2).

One schema, used identically by the live server's /state endpoint and by
recorded playback files, so the same viewer code parses both:

- ``tick_id`` is monotonic: ``day * ticks_per_day + tick``.
- A *frame* is the state after that tick ran: every agent's position,
  destination (null when stationary), and activity, plus the events that
  occurred during the tick.
- A *recording* is ``{schema, meta, frames}`` with contiguous tick_ids.
- ``meta`` carries everything static a renderer needs: the terrain, plot,
  home and landmark geometry, and each agent's identity.

Renderer contract (enforced in the viewer, stated here): interpolate by
easing toward a frame's positions, and snap on any discontinuity greater
than one tile — pause, speed changes and timeline scrubbing never slide a
character across the map.
"""

SCHEMA = "dekot-state/1"


def tick_id(day, tick, cfg):
    return day * cfg.ticks_per_day + tick


def last_tick_id(sim):
    """tick_id of the most recently completed tick, -1 before any ran."""
    return sim.day * sim.cfg.ticks_per_day + sim.tick - 1


def agent_state(a):
    return {"id": a.id, "x": a.pos[0], "y": a.pos[1],
            "dx": a.dest[0] if a.dest else None, "dy": a.dest[1] if a.dest else None,
            "act": a.activity, "alive": a.alive}


def frame(sim, tid, events):
    return {"t": tid,
            "agents": [agent_state(a) for a in sim.agents if a.alive or a.death_day is not None],
            "events": list(events)}


def meta(sim):
    from .world import TERRAIN, GRAZE, BANYAN, HOME_SITES
    cfg = sim.cfg
    return {"schema": SCHEMA,
            "seed": cfg.seed, "founder_seed": cfg.founder_seed,
            "ticks_per_day": cfg.ticks_per_day, "days_per_year": cfg.days_per_year,
            "duration_years": cfg.duration_years, "night_ticks": cfg.night_ticks,
            "meal_ticks": list(cfg.meal_ticks),
            "terrain": TERRAIN, "homes": [list(h) for h in HOME_SITES],
            "graze": list(GRAZE), "banyan": list(BANYAN),
            "plots": [{"id": p.id, "x": p.x, "y": p.y, "fertility": p.fertility}
                      for p in sim.world.plots],
            "agents": [{"id": a.id, "name": a.name, "sex": a.sex,
                        "parents": a.parents, "home": a.home, "role": a.role,
                        "death_day": a.death_day}
                       for a in sim.agents]}


def record(cfg, progress=None):
    """Run a fresh simulation, capturing a frame after every tick."""
    from .engine import Simulation
    sim = Simulation(cfg)
    frames = []
    seen = 0
    while (sim.day < sim.max_days or sim.tick != 0) and sim.stopped is None:
        tid = tick_id(sim.day, sim.tick, cfg)
        sim.step_tick()
        frames.append(frame(sim, tid, sim.events.entries[seen:]))
        seen = len(sim.events.entries)
        if progress and sim.tick == 0:
            progress(sim.day)
    if sim.stopped is None:
        sim.stopped = "duration"
        sim.events.add(sim.day, 0, type="stopped", reason="duration",
                       population=len(sim.living()))
    if len(sim.events.entries) > seen and frames:
        frames[-1]["events"].extend(sim.events.entries[seen:])
    return {"schema": SCHEMA, "meta": meta(sim), "frames": frames,
            "stopped": sim.stopped, "n_days": sim.day}
