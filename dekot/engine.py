"""Tick loop. The engine owns resources, health, movement, relationships and deaths."""
import random
from .agents import make_founders
from .clock import is_night, age_after_day
from .config import Config
from .disputes import contest_good_plot
from .family import year_tick, come_of_age
from .health import daily_health_delta, p_death
from .ledger import Ledger, OwnershipError
from .log import Log
from .relationships import Relationships
from .world import make_world, assign_roles, owns


class Simulation:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.rng = random.Random(cfg.seed)
        self.world = make_world(cfg)
        self.agents = make_founders(cfg, random.Random(cfg.founder_seed))
        assign_roles(self.agents, self.world, cfg)
        self.rel = Relationships([a.id for a in self.agents])
        self.events = Log()
        self.ledger = Ledger()
        self.day = 0
        self.tick = 0
        self.stopped = None
        self.events.add(0, 0, type="founded", village="Dekot", population=len(self.agents))
        self.ledger.open(self.agents)

    # ---- queries
    def agent(self, aid):
        return next(a for a in self.agents if a.id == aid)

    def living(self):
        return [a for a in self.agents if a.alive]

    @property
    def max_days(self):
        return self.cfg.duration_years * self.cfg.days_per_year

    # ---- main loop
    def run(self, until_day=None):
        stop = self.max_days if until_day is None else min(until_day, self.max_days)
        while (self.day < stop or self.tick != 0) and self.stopped is None:
            self.step_tick()
        if self.stopped is None and self.day >= self.max_days:
            self.stopped = "duration"
            self.events.add(self.day, 0, type="stopped", reason="duration", population=len(self.living()))
        return self

    def step_day(self):
        self.step_tick()
        while self.tick != 0 and self.stopped is None:
            self.step_tick()

    def step_tick(self):
        """Advance one routine tick. Day boundaries (reset, plots, year events,
        end-of-day biology) happen inside the first and last tick of the day,
        so tick-paced and day-paced runs produce identical logs."""
        if self.stopped is not None:
            return
        cfg, day, tick = self.cfg, self.day, self.tick
        if tick == 0:
            for a in self.living():
                a.reset_day()
            self._assign_vacant_plots(day)
            if day % cfg.days_per_year == 0 and day > 0:
                contest_good_plot(self, day)
                year_tick(self, day)
                self._clear_new_land(day)
        for a in self.living():
            self._act(a, day, tick)
        self.tick += 1
        if self.tick >= cfg.ticks_per_day:
            for a in self.living():
                self._end_of_day(a, day)
            self.tick = 0
            self.day += 1
            if len(self.living()) < cfg.min_population:
                self.stopped = "population"
                self.events.add(self.day, 0, type="stopped", reason="population", population=len(self.living()))

    # ---- per-tick behaviour (rules only)
    def _act(self, a, day, tick):
        cfg = self.cfg
        if is_night(tick, cfg):
            a.rest_ticks += 1
            a.fatigue = max(a.fatigue - 4, 0)
            return
        if tick in cfg.meal_ticks:
            self._eat(a, day, tick)
            return
        if a.role == "child":
            return  # children neither work nor tire
        self._work(a, day, tick)

    def _eat(self, a, day, tick):
        cfg = self.cfg
        if a.role == "child":
            need = cfg.infant_rice_per_meal if a.age < 7 else cfg.child_rice_per_meal
        else:
            need = cfg.rice_per_meal
        if a.inventory["rice"] < need:
            self._ask_for_food(a, day, tick, need)
        if a.inventory["rice"] >= need:
            self.ledger.apply(day, tick, a, "rice", -need, "eat", "meal")
            a.meals_eaten += 1
        else:
            self.events.add(day, tick, type="hungry", agent=a.id)
            a.mood = max(a.mood - 3, 0)
        if a.inventory["milk"] >= 1.0:
            self.ledger.apply(day, tick, a, "milk", -1.0, "drink", "meal")
            a.milk_drunk += 1.0

    def _ask_for_food(self, a, day, tick, need=None):
        cfg = self.cfg
        need = cfg.rice_per_meal if need is None else need
        # family shares food first — spouse, then parents, then own children —
        # with no helpfulness gate and no self-reserve: a household eats or
        # goes hungry together
        by_id = {x.id: x for x in self.agents}
        family = ([a.partner] if a.partner else []) + list(a.parents or []) + \
                 [x.id for x in self.agents if x.parents and a.id in x.parents]
        for fid in family:
            f = by_id[fid]
            if f.alive and f.inventory["rice"] >= need:
                self.ledger.transfer(day, tick, f, a, "rice", need, "share_family")
                self.rel.shift(a.id, f.id, 1)
                return
        donors = [d for d in self.living() if d.id != a.id and d.inventory["rice"] >= cfg.surplus_threshold + need]
        if not donors:
            return
        donor = max(donors, key=lambda d: (d.traits["helpfulness"] + self.rel.get(a.id, d.id), d.id))
        if donor.traits["helpfulness"] + self.rel.get(a.id, donor.id) < 40:
            self.events.add(day, tick, type="refused_food", agent=a.id, asked=donor.id)
            self.rel.shift(a.id, donor.id, -3)
            return
        self.ledger.transfer(day, tick, donor, a, "rice", need, "gift_to_hungry")
        self.rel.shift(a.id, donor.id, 5)
        self.events.add(day, tick, type="gift", giver=donor.id, taker=a.id, resource="rice")

    def _work(self, a, day, tick):
        cfg = self.cfg
        effort = 0.5 + 0.5 * (a.health / 100) * (1 - a.fatigue / 200)
        a.work_ticks += 1
        a.fatigue = min(a.fatigue + 3, 100)
        if a.role == "farmer":
            if a.plot is None:
                self.ledger.apply(day, tick, a, "rice", cfg.forage_yield * effort, "forage", "landless")
            elif owns(self.world, a):
                self.ledger.apply(day, tick, a, "rice", self.world.plots[a.plot].fertility * effort, "farm", f"plot_{a.plot}")
            else:
                raise OwnershipError(f"{a.id} farming plot {a.plot} held by {self.world.plots[a.plot].holder}")
        elif a.role == "cowherd":
            cowherds = [c for c in self.living() if c.role == "cowherd"]
            milk = self.world.herd_size * cfg.milk_per_cow_tick * effort / len(cowherds)
            self.ledger.apply(day, tick, a, "milk", milk, "herd", "village_herd")
            # cowherds sell milk for rice at 1:1 with the farmer holding the most rice
            farmers = [f for f in self.living() if f.role == "farmer" and f.inventory["rice"] >= cfg.surplus_threshold + 1]
            if farmers and a.inventory["milk"] >= 2.0:
                buyer = max(farmers, key=lambda f: (f.inventory["rice"], f.id))
                self.ledger.transfer(day, tick, a, buyer, "milk", 1.0, "trade")
                self.ledger.transfer(day, tick, buyer, a, "rice", 1.0, "trade")

    def _clear_new_land(self, day):
        """Once a year, each landless farmer clears a fresh plot while land remains."""
        from .world import Plot
        cfg = self.cfg
        landless = sorted((a for a in self.living() if a.role == "farmer" and a.plot is None),
                          key=lambda x: (-x.traits["ambition"], x.id))
        for a in landless:
            if len(self.world.plots) >= cfg.max_plots:
                return
            p = Plot(id=len(self.world.plots), x=len(self.world.plots) + 1, y=2,
                     fertility=cfg.cleared_plot_fertility, holder=a.id)
            self.world.plots.append(p)
            a.plot = p.id
            self.events.add(day, 0, type="plot_cleared", agent=a.id, plot=p.id)

    def _assign_vacant_plots(self, day):
        free = [p for p in self.world.plots if p.holder is None]
        for a in sorted(self.living(), key=lambda x: (-x.traits["ambition"], x.id)):
            if a.role == "farmer" and not owns(self.world, a) and free:
                p = free.pop(0)
                p.holder = a.id
                a.plot = p.id
                self.events.add(day, 0, type="plot_assigned", agent=a.id, plot=p.id)

    # ---- end of day: biology and mortality
    def _end_of_day(self, a, day):
        cfg = self.cfg
        a.health = max(0.0, min(100.0, a.health + daily_health_delta(a, cfg)))
        a.mood = max(0.0, min(100.0, a.mood + (2 if a.meals_eaten == 2 else -2)))
        a.age = age_after_day(a.age, cfg)
        if a.role == "child" and a.age >= cfg.adult_age:
            come_of_age(self, a, day)
        p = p_death(a.age, a.health, cfg)
        if self.rng.random() < p or a.health <= 0:
            a.alive = False
            a.death_day = day
            if a.plot is not None and self.world.plots[a.plot].holder == a.id:
                self.world.plots[a.plot].holder = None
            cause = "starvation" if a.health <= 0 else "illness"
            self.events.add(day, cfg.ticks_per_day - 1, type="death", agent=a.id, age=round(a.age, 2),
                            health=round(a.health, 1), cause=cause, p=round(p, 5))
            for b in self.living():
                b.mood = max(b.mood - 5, 0)
        self.events.add(day, cfg.ticks_per_day - 1, type="day_end", agent=a.id, health=round(a.health, 1),
                        mood=round(a.mood, 1), age=round(a.age, 2), rice=round(a.inventory["rice"], 2),
                        milk=round(a.inventory["milk"], 2), meals=a.meals_eaten)
