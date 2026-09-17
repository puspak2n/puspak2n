from dataclasses import dataclass, field, asdict

TRAITS = ("stubbornness", "helpfulness", "temper", "piety", "ambition", "sociability")


@dataclass
class Agent:
    id: str
    name: str
    traits: dict
    age: float                 # life clock, years
    role: str = "farmer"
    plot: int | None = None
    health: float = 80.0
    fatigue: float = 0.0
    mood: float = 60.0
    alive: bool = True
    death_day: int | None = None
    inventory: dict = field(default_factory=lambda: {"rice": 4.0, "milk": 0.0})
    # per-day routine tallies, reset at day start
    meals_eaten: int = 0
    rest_ticks: int = 0
    work_ticks: int = 0
    milk_drunk: float = 0.0

    def reset_day(self):
        self.meals_eaten = self.rest_ticks = self.work_ticks = 0
        self.milk_drunk = 0.0

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


NAMES = ["Bhima", "Sukanti", "Dasarathi", "Laxmi", "Hari", "Kausalya",
         "Nrusingha", "Subhadra", "Purna", "Jamuna", "Trilochan", "Sabitri"]


def make_founders(cfg, rng):
    agents = []
    for i in range(cfg.n_agents):
        frac = i / max(cfg.n_agents - 1, 1)
        age = cfg.founder_age_min + frac * (cfg.founder_age_max - cfg.founder_age_min)
        traits = {t: rng.randint(10, 90) for t in TRAITS}
        agents.append(Agent(id=f"a{i:02d}", name=NAMES[i % len(NAMES)], traits=traits, age=age))
    return agents
