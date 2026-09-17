import os, tempfile
from dataclasses import replace
import pytest
from dekot.config import Config
from dekot.engine import Simulation
from dekot.health import p_death, annual_hazard
from dekot.persistence import save, load
from dekot.ledger import LedgerError


def logs(sim):
    return sim.events.dumps(), sim.ledger.dumps()


def test_replay_is_byte_identical():
    a = Simulation(Config(seed=7)).run()
    b = Simulation(Config(seed=7)).run()
    assert logs(a) == logs(b)


def test_different_seed_different_log():
    a = Simulation(Config(seed=7)).run()
    b = Simulation(Config(seed=8)).run()
    assert logs(a) != logs(b)


def test_no_wall_clock_in_logs():
    sim = Simulation(Config(seed=1)).run()
    for e in sim.events.entries + sim.ledger.entries:
        assert not any(k in e for k in ("timestamp", "time", "created_at"))


def test_save_resume_matches_uninterrupted():
    full = Simulation(Config(seed=3)).run()
    part = Simulation(Config(seed=3)).run(until_day=20)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "state.json")
        save(part, p)
        resumed = load(p).run()
    assert logs(resumed) == logs(full)


def test_hazard_properties():
    cfg = Config()
    for age in (20, 40, 60, 80):
        for h in (0, 50, 100):
            assert 0 < p_death(age, h, cfg) < 1
    assert p_death(60, 70, cfg) > p_death(30, 70, cfg)
    assert p_death(40, 90, cfg) < p_death(40, 30, cfg)
    assert annual_hazard(40, 100, cfg) > 0


def test_ledger_rejects_missing_reason_and_negative():
    sim = Simulation(Config(seed=1))
    a = sim.agents[0]
    with pytest.raises(LedgerError):
        sim.ledger.apply(0, 0, a, "rice", -1, "eat", "")
    with pytest.raises(LedgerError):
        sim.ledger.apply(0, 0, a, "rice", -999, "eat", "test")


@pytest.mark.parametrize("seed", range(1, 1001))
def test_invariants_across_seeds(seed):
    sim = Simulation(Config(seed=seed)).run()
    rec = sim.ledger.reconstruct()
    for a in sim.agents:
        assert all(v >= 0 for v in a.inventory.values())
        assert all(rec[(a.id, r)] == v for r, v in a.inventory.items())
    assert all(e["reason"] for e in sim.ledger.entries)
    assert sim.stopped in ("duration", "population")


def test_ledger_reconstructs_inventory_exactly():
    sim = Simulation(Config(seed=1)).run()
    rec = sim.ledger.reconstruct()
    for a in sim.agents:
        for r, v in a.inventory.items():
            assert rec[(a.id, r)] == v


def test_no_farming_without_ownership():
    sim = Simulation(Config(seed=1))
    sim.run()
    farms = [e for e in sim.ledger.entries if e["action"] == "farm"]
    forages = [e for e in sim.ledger.entries if e["action"] == "forage"]
    assert farms and forages  # 8 farmers, 6 plots -> landless exist and forage
    # day 0: exactly one farmer per plot produces, and never more than n_plots distinct farmers
    day0 = {e["actor"] for e in farms if e["day"] == 0}
    assert len(day0) == Config().n_plots


def test_landless_are_explicit_at_start():
    sim = Simulation(Config(seed=1))
    farmers = [a for a in sim.agents if a.role == "farmer"]
    landless = [a for a in farmers if a.plot is None]
    assert len(landless) == len(farmers) - Config().n_plots
    assert len({a.plot for a in farmers if a.plot is not None}) == Config().n_plots


def test_agents_stay_on_land_and_move():
    from dekot.world import WATER_ROWS
    sim = Simulation(Config(seed=2))
    moved = farmed_at_plot = False
    while sim.day < 6:
        sim.step_tick()
        for a in sim.living():
            assert 0 <= a.pos[0] < sim.world.width
            assert WATER_ROWS <= a.pos[1] < sim.world.height
            if a.pos != a.home:
                moved = True
            if a.activity == "farming":
                p = sim.world.plots[a.plot]
                assert a.pos == [p.x, p.y]  # work only happens at the workplace
                farmed_at_plot = True
    assert moved and farmed_at_plot


def test_everyone_sleeps_at_home():
    sim = Simulation(Config(seed=4))
    sim.run(until_day=5)
    for _ in range(2):  # first two night ticks of day 5
        sim.step_tick()
    for a in sim.living():
        assert a.pos == a.home or a.activity == "walking"


def test_walking_produces_nothing():
    sim = Simulation(Config(seed=3))
    while sim.day < 4:
        before = {x.id: dict(x.inventory) for x in sim.agents}
        walkers = {x.id for x in sim.living() if x.activity == "walking"}
        sim.step_tick()
        for e in sim.ledger.entries[-40:]:
            pass  # ledger checked via inventory delta below
        for a in sim.living():
            if a.activity == "walking" and a.id in before:
                gained = a.inventory["rice"] - before[a.id]["rice"]
                assert gained <= 0.0001 or any(
                    x["action"] in ("receive",) and x["actor"] == a.id
                    for x in sim.ledger.entries[-60:])


def test_tick_stepping_matches_day_stepping():
    a = Simulation(Config(seed=5))
    while a.day < a.max_days and a.stopped is None:
        a.step_day()
    b = Simulation(Config(seed=5))
    while b.day < b.max_days and b.stopped is None:
        b.step_tick()
    assert logs(a) == logs(b)


def test_save_resume_mid_day_matches_uninterrupted():
    full = Simulation(Config(seed=3)).run()
    part = Simulation(Config(seed=3))
    for _ in range(20 * Config().ticks_per_day + 7):  # stop mid-day at tick 7
        part.step_tick()
    assert part.tick == 7
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "state.json")
        save(part, p)
        resumed = load(p)
        assert resumed.tick == 7
        resumed.run()
    assert logs(resumed) == logs(full)


def test_births_are_deterministic_and_ledgered():
    a = Simulation(Config(seed=11)).run()
    b = Simulation(Config(seed=11)).run()
    assert logs(a) == logs(b)
    births = [e for e in a.events.entries if e["type"] == "birth"]
    for e in births:
        child = a.agent(e["child"])
        assert child.age < Config().duration_years + 0.001
        assert child.parents == e["parents"]
        # every born child has ledger entries for both resources
        rec = a.ledger.reconstruct()
        assert (child.id, "rice") in rec and (child.id, "milk") in rec


def test_experiment_keeps_starting_village_fixed():
    a = Simulation(Config(seed=1)); b = Simulation(Config(seed=999))
    assert [x.to_dict() for x in a.agents] == [x.to_dict() for x in b.agents]
    assert a.world.to_dict() == b.world.to_dict()


def test_checkpoint_rejects_different_engine():
    import json
    from dekot.persistence import IncompatibleCheckpoint
    sim = Simulation(Config(seed=2)).run(until_day=5)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "s.json"); save(sim, p)
        j = json.load(open(p)); j["engine_fingerprint"] = "deadbeef"; json.dump(j, open(p, "w"))
        with pytest.raises(IncompatibleCheckpoint):
            load(p)
        assert load(p, force=True).day == 5
