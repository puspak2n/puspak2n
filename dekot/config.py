from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Config:
    seed: int = 1            # simulation randomness (disputes, mortality)
    founder_seed: int = 42   # starting village (traits, roles, plots); fixed across experiments
    # time
    ticks_per_day: int = 12
    days_per_year: int = 8
    duration_years: int = 5
    # population
    n_agents: int = 10
    min_population: int = 2
    founder_age_min: float = 18.0
    founder_age_max: float = 45.0
    # world
    n_plots: int = 6
    max_plots: int = 12               # landless farmers clear new land up to this
    cleared_plot_fertility: float = 1.05  # fresh-cleared land yields less than old paddy
    plot_fertility: float = 1.5      # rice per work tick, ordinary plot
    good_plot_fertility: float = 2.6  # rice per work tick, the good plot
    herd_size: int = 4
    forage_yield: float = 0.75         # rice per work tick for landless farmers
    milk_per_cow_tick: float = 0.4
    # seasons and weather (year = days_per_year days; index = day % days_per_year)
    # sowing -> growing -> harvest; multipliers average 1.0 so annual output is calibrated
    season_yield: tuple = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.9, 1.6)
    rain_prob: tuple = (0.6, 0.6, 0.5, 0.25, 0.15, 0.1, 0.05, 0.05)  # monsoon early in the year
    # village life
    social_min: int = 50              # sociability needed to spend the evening at the banyan
    piety_min: int = 65               # piety that sends someone to the shrine instead
    feast_rice: float = 0.5           # extra rice eaten at the festival meal, if held
    # movement (a tick spent walking produces nothing)
    move_speed: int = 4               # tiles per tick
    walk_fatigue: float = 1.0         # fatigue per walking tick
    # routine
    night_ticks: int = 4              # ticks 0..3 are rest
    meal_ticks: tuple = (4, 9)        # two meals per day
    rice_per_meal: float = 1.0
    surplus_threshold: float = 3.0    # rice kept before gifting to non-family
    trade_reserve: float = 2.0        # rice kept before buying milk
    milk_per_meal: float = 2.0        # milk that substitutes one rice meal (less filling)
    # family (pairing and births, checked once per life-year)
    fertile_age_min: float = 18.0
    fertile_age_max: float = 45.0
    adult_age: float = 14.0           # children start working (landless) at this age
    pair_chance: float = 0.6
    birth_chance: float = 0.25
    child_rice_at_birth: float = 1.0
    child_rice_per_meal: float = 0.5   # rice per meal, age 7 to adult
    infant_rice_per_meal: float = 0.25  # rice per meal under age 7
    # health (routine -> biological conversions, applied once per day)
    food_gain: float = 0.6            # health per day when both meals eaten
    hunger_loss: float = 3.0          # health per missed meal
    rest_gain: float = 0.4            # health per day at full rest
    fatigue_loss: float = 0.5         # health per overwork tick
    milk_gain: float = 0.3            # health per day when >=1 milk consumed
    age_decay_k: float = 0.03         # health per day per year of age above 30
    recovery_taper: float = 25.0      # recovery runs at full speed below (100 - this), 0 at 100
    # mortality (annual hazard)
    hazard_base: float = 0.0002
    hazard_k: float = 0.09
    hazard_beta: float = 1.5

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        d["meal_ticks"] = tuple(d["meal_ticks"])
        return cls(**d)
