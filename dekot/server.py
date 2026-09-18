"""Live server: one authoritative simulation, paced by wall clock, served over HTTP.

Stdlib only. A pacing thread advances the simulation one tick at a time
(default: 1 real hour = 1 Dekot day, i.e. 3600 / ticks_per_day seconds per
tick) and checkpoints after every tick. On start, an existing checkpoint is
resumed, so restarts and reboots lose at most the current tick. The server
also serves the viewer page, so a phone browser just opens http://host:port/.

Not simulation-affecting: excluded from the engine fingerprint.
"""
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import Config
from .engine import Simulation
from .fingerprint import engine_fingerprint
from .persistence import save, load
from .state import SCHEMA, frame, last_tick_id, meta

FEED_TYPES = ("founded", "dispute", "plot_claimed", "plot_assigned", "gift",
              "refused_food", "hungry", "death", "stopped", "paired", "birth", "came_of_age")
SPEEDS = {  # label -> real seconds per Dekot day
    "1h/day": 3600.0, "10m/day": 600.0, "1m/day": 60.0, "5s/day": 5.0,
}


class LiveVillage:
    def __init__(self, cfg: Config, state_path: str, force=False):
        self.state_path = state_path
        self.lock = threading.Lock()
        self.paused = False
        self.seconds_per_day = SPEEDS["1h/day"]
        if os.path.exists(state_path):
            self.sim = load(state_path, force=force)
            ctl = self._load_control()
            self.paused = ctl.get("paused", False)
            self.seconds_per_day = ctl.get("seconds_per_day", self.seconds_per_day)
            self.resumed = True
        else:
            os.makedirs(os.path.dirname(state_path) or ".", exist_ok=True)
            self.sim = Simulation(cfg)
            save(self.sim, state_path)
            self.resumed = False
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._pace, daemon=True)

    # control state (pause, speed) lives beside the checkpoint, not inside it:
    # it is operator preference, not simulation state.
    def _control_path(self):
        return self.state_path + ".control"

    def _load_control(self):
        try:
            with open(self._control_path()) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _save_control(self):
        with open(self._control_path(), "w") as f:
            json.dump({"paused": self.paused, "seconds_per_day": self.seconds_per_day}, f)

    def seconds_per_tick(self):
        return self.seconds_per_day / self.sim.cfg.ticks_per_day

    def start(self):
        self.thread.start()

    def stop(self):
        self._stop.set()

    def _pace(self):
        elapsed = 0.0
        while not self._stop.is_set():
            # sleep in <=1s slices so pause, speed changes and shutdown apply quickly
            if self._stop.wait(min(max(self.seconds_per_tick() - elapsed, 0.0), 1.0)):
                return
            elapsed = min(elapsed + 1.0, self.seconds_per_tick() + 1.0)
            if elapsed < self.seconds_per_tick():
                continue
            with self.lock:
                if self.paused or self.sim.stopped is not None:
                    continue
                elapsed = 0.0
                self.sim.step_tick()
                save(self.sim, self.state_path)

    def control(self, action, value=None):
        with self.lock:
            if action == "pause":
                self.paused = True
            elif action == "resume":
                self.paused = False
            elif action == "speed" and value in SPEEDS:
                self.seconds_per_day = SPEEDS[value]
            self._slept = 0.0
            self._save_control()
            return self.snapshot()

    def snapshot(self, since=None):
        """Live state. `frame` and `meta` use the shared tick-level schema
        (dekot/state.py) — identical shape to a recording's frames — plus
        control/UI extras. `since` (a tick_id) bounds the recap feed."""
        sim = self.sim
        agents = []
        for a in sim.agents:
            agents.append({"id": a.id, "name": a.name, "role": a.role, "alive": a.alive,
                           "death_day": a.death_day, "age": round(a.age, 2),
                           "health": round(a.health, 1), "mood": round(a.mood, 1),
                           "rice": round(a.inventory["rice"], 2), "milk": round(a.inventory["milk"], 2),
                           "meals": a.meals_eaten, "parents": a.parents, "partner": a.partner})
        speed = next((k for k, v in SPEEDS.items() if v == self.seconds_per_day), "custom")
        tid = last_tick_id(sim)
        if since is not None:
            tpd = sim.cfg.ticks_per_day
            recap = [e for e in sim.events.entries if e["type"] in FEED_TYPES
                     and e["day"] * tpd + e["tick"] > since][-200:]
        else:
            recap = None
        return {"schema": SCHEMA, "tick_id": tid,
                "frame": frame(sim, tid, []) if tid >= 0 else None,
                "meta": meta(sim),
                "recap": recap,
                "day": sim.day, "tick": sim.tick, "stopped": sim.stopped,
                "paused": self.paused, "speed": speed, "speeds": list(SPEEDS),
                "seconds_per_tick": self.seconds_per_tick(),
                "max_days": sim.max_days, "days_per_year": sim.cfg.days_per_year,
                "seed": sim.cfg.seed, "population": len(sim.living()),
                "plots": [{"id": p.id, "fertility": p.fertility, "holder": p.holder}
                          for p in sim.world.plots],
                "agents": agents,
                "feed": [e for e in sim.events.entries if e["type"] in FEED_TYPES][-80:]}


def make_handler(village: LiveVillage, page_html: bytes):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _json(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/" or self.path.startswith("/index"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(page_html)))
                self.end_headers()
                self.wfile.write(page_html)
            elif self.path.startswith("/state"):
                since = None
                if "since=" in self.path:
                    try:
                        since = int(self.path.split("since=")[1].split("&")[0])
                    except ValueError:
                        pass
                with village.lock:
                    self._json(village.snapshot(since=since))
            else:
                self._json({"error": "not found"}, 404)

        def do_POST(self):
            if self.path != "/control":
                self._json({"error": "not found"}, 404)
                return
            n = int(self.headers.get("Content-Length", 0))
            try:
                req = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                self._json({"error": "bad json"}, 400)
                return
            self._json(village.control(req.get("action"), req.get("value")))

    return Handler


def serve(cfg: Config, state_path: str, host="0.0.0.0", port=8080, force=False):
    with open(os.path.join(os.path.dirname(__file__), "viewer.html"), "rb") as f:
        page = f.read()
    village = LiveVillage(cfg, state_path, force=force)
    httpd = ThreadingHTTPServer((host, port), make_handler(village, page))
    village.start()
    mode = "resumed" if village.resumed else "new village"
    print(f"dekot live: {mode}, day {village.sim.day} tick {village.sim.tick}, "
          f"{village.seconds_per_day:.0f}s per Dekot day")
    print(f"open http://{host}:{port}/ (checkpoint: {state_path}, fingerprint {engine_fingerprint()[:12]})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        village.stop()
        with village.lock:
            save(village.sim, state_path)
