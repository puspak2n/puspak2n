"""Save/load full state, including RNG state and both logs (SPEC §8)."""
import json
from .config import Config
from .engine import Simulation
from .agents import Agent
from .world import World
from .relationships import Relationships
from .log import Log
from .ledger import Ledger
from .fingerprint import engine_fingerprint


class IncompatibleCheckpoint(Exception):
    pass


def _rng_to_json(state):
    version, internal, gauss = state
    return [version, list(internal), gauss]


def _rng_from_json(s):
    version, internal, gauss = s
    return (version, tuple(internal), gauss)


def save(sim: Simulation, path):
    d = {
        "engine_fingerprint": engine_fingerprint(),
        "config": sim.cfg.to_dict(),
        "day": sim.day,
        "stopped": sim.stopped,
        "rng": _rng_to_json(sim.rng.getstate()),
        "agents": [a.to_dict() for a in sim.agents],
        "world": sim.world.to_dict(),
        "affinity": sim.rel.affinity,
        "events": sim.events.entries, "events_seq": sim.events.seq,
        "ledger": sim.ledger.entries, "ledger_seq": sim.ledger.seq,
    }
    with open(path, "w") as f:
        json.dump(d, f, sort_keys=True)


def load(path, force=False) -> Simulation:
    with open(path) as f:
        d = json.load(f)
    if not force and d.get("engine_fingerprint") != engine_fingerprint():
        raise IncompatibleCheckpoint("checkpoint written by a different engine version; pass force=True to override")
    sim = Simulation.__new__(Simulation)
    sim.cfg = Config.from_dict(d["config"])
    import random
    sim.rng = random.Random()
    sim.rng.setstate(_rng_from_json(d["rng"]))
    sim.day = d["day"]
    sim.stopped = d["stopped"]
    sim.agents = [Agent.from_dict(a) for a in d["agents"]]
    sim.world = World.from_dict(d["world"])
    sim.rel = Relationships(data=d["affinity"])
    sim.events = Log(); sim.events.entries = d["events"]; sim.events.seq = d["events_seq"]
    sim.ledger = Ledger(); sim.ledger.entries = d["ledger"]; sim.ledger.seq = d["ledger_seq"]
    return sim
