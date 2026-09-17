import argparse, json, os, sys, time
from .config import Config
from .engine import Simulation
from .experiments import run_experiment
from .fingerprint import engine_fingerprint
from .persistence import save, load


def write_run(sim, out):
    os.makedirs(out, exist_ok=True)
    sim.events.write(os.path.join(out, "events.jsonl"))
    sim.ledger.write(os.path.join(out, "ledger.jsonl"))
    with open(os.path.join(out, "manifest.json"), "w") as f:
        json.dump({"config": sim.cfg.to_dict(), "engine_fingerprint": engine_fingerprint(),
                   "days": sim.day, "stopped": sim.stopped, "population": len(sim.living())}, f, sort_keys=True, indent=1)


def feed(sim, kinds=("founded", "dispute", "plot_claimed", "gift", "refused_food", "death", "stopped")):
    names = {a.id: a.name for a in sim.agents}
    for e in sim.events.entries:
        if e["type"] in kinds:
            rest = {k: names.get(v, v) for k, v in e.items() if k not in ("day", "tick", "seq", "type")}
            print(f"day {e['day']:>3} t{e['tick']:>2}  {e['type']:<13} {rest}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="dekot")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("--seed", type=int, default=1); r.add_argument("--out", default="runs/run"); r.add_argument("--save-at", type=int); r.add_argument("--quiet", action="store_true")
    s = sub.add_parser("resume"); s.add_argument("state"); s.add_argument("--out", default="runs/resumed"); s.add_argument("--force", action="store_true")
    e = sub.add_parser("experiment"); e.add_argument("--runs", type=int, default=100); e.add_argument("--out", default="runs/experiment.json")
    v = sub.add_parser("serve"); v.add_argument("--seed", type=int, default=1); v.add_argument("--state", default="runs/live/state.json"); v.add_argument("--host", default="0.0.0.0"); v.add_argument("--port", type=int, default=8080); v.add_argument("--force", action="store_true")
    a = p.parse_args(argv)
    if a.cmd == "run":
        sim = Simulation(Config(seed=a.seed))
        t0 = time.perf_counter()
        if a.save_at:
            sim.run(until_day=a.save_at); save(sim, os.path.join(a.out, "state.json")) if os.makedirs(a.out, exist_ok=True) is None else None
        sim.run()
        dt = time.perf_counter() - t0
        write_run(sim, a.out)
        if not a.quiet:
            feed(sim)
        print(f"stopped={sim.stopped} days={sim.day} alive={len(sim.living())} wall={dt:.3f}s -> {a.out}", file=sys.stderr)
    elif a.cmd == "resume":
        sim = load(a.state, force=a.force); sim.run(); write_run(sim, a.out)
        print(f"stopped={sim.stopped} days={sim.day} alive={len(sim.living())} -> {a.out}", file=sys.stderr)
    elif a.cmd == "serve":
        from .server import serve
        serve(Config(seed=a.seed), a.state, host=a.host, port=a.port, force=a.force)
    elif a.cmd == "experiment":
        t0 = time.perf_counter()
        res = run_experiment(Config(), a.runs)
        res["wall_seconds"] = round(time.perf_counter() - t0, 2); res["engine_fingerprint"] = engine_fingerprint()
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1)
        print(json.dumps(res, indent=1))
