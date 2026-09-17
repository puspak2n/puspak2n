from dataclasses import dataclass, field, asdict

TRAITS = ("stubbornness", "helpfulness", "temper", "piety", "ambition", "sociability")


@dataclass
class Agent:
    id: str
    name: str
    traits: dict
    age: float                 # life clock, years
    sex: str = "m"             # "m" or "f"; pairing is opposite-sex in this stylized model
    role: str = "farmer"
    plot: int | None = None
    health: float = 80.0
    fatigue: float = 0.0
    mood: float = 60.0
    alive: bool = True
    death_day: int | None = None
    partner: str | None = None
    parents: list | None = None
    # space (SPEC map tiles): where they are, where they live, what they're doing
    pos: list | None = None
    home: list | None = None
    activity: str = "idle"
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


MALE_NAMES = ["Bhima", "Dasarathi", "Hari", "Nrusingha", "Purna", "Trilochan",
              "Raghu", "Banamali", "Gopal", "Kanhu", "Dhruba", "Shyam"]
FEMALE_NAMES = ["Sukanti", "Laxmi", "Kausalya", "Subhadra", "Jamuna", "Sabitri",
                "Malati", "Kuni", "Basanti", "Nirmala", "Puspa", "Gita"]


def name_for(sex, nth):
    """nth same-sex villager gets the nth name; repeats gain a numeral."""
    pool = FEMALE_NAMES if sex == "f" else MALE_NAMES
    name = pool[nth % len(pool)]
    return name if nth < len(pool) else f"{name} {nth // len(pool) + 1}"


def make_founders(cfg, rng):
    agents = []
    for i in range(cfg.n_agents):
        frac = i / max(cfg.n_agents - 1, 1)
        age = cfg.founder_age_min + frac * (cfg.founder_age_max - cfg.founder_age_min)
        traits = {t: rng.randint(10, 90) for t in TRAITS}
        sex = "m" if i % 2 == 0 else "f"
        agents.append(Agent(id=f"a{i:02d}", name=name_for(sex, i // 2), traits=traits,
                            age=age, sex=sex))
    return agents
