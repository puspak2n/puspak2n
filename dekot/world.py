from dataclasses import dataclass, field, asdict


@dataclass
class Plot:
    id: int
    x: int
    y: int
    fertility: float
    holder: str | None = None


@dataclass
class World:
    plots: list
    herd_size: int
    width: int = 8
    height: int = 6

    def good_plot(self):
        return max(self.plots, key=lambda p: p.fertility)

    def to_dict(self):
        return {"plots": [asdict(p) for p in self.plots], "herd_size": self.herd_size,
                "width": self.width, "height": self.height}

    @classmethod
    def from_dict(cls, d):
        return cls(plots=[Plot(**p) for p in d["plots"]], herd_size=d["herd_size"],
                   width=d["width"], height=d["height"])


def make_world(cfg):
    # plots along the river (y=0); plot 0 is the good plot by the water
    plots = [Plot(id=i, x=i + 1, y=1, fertility=cfg.plot_fertility) for i in range(cfg.n_plots)]
    plots[0].fertility = cfg.good_plot_fertility
    return World(plots=plots, herd_size=cfg.herd_size)


def assign_roles(agents, world, cfg):
    """Trait fit: most helpful -> cowherd; farmers by ambition, most ambitious gets the good plot."""
    by_help = sorted(agents, key=lambda a: (-a.traits["helpfulness"], a.id))
    cowherds = by_help[:2]
    for a in cowherds:
        a.role = "cowherd"
    farmers = sorted((a for a in agents if a not in cowherds), key=lambda a: (-a.traits["ambition"], a.id))
    for i, a in enumerate(farmers):
        a.role = "farmer"
        if i < len(world.plots):
            a.plot = world.plots[i].id
            world.plots[i].holder = a.id
        else:
            a.plot = None  # landless: forages until a plot is vacant


def owns(world, agent) -> bool:
    return agent.plot is not None and world.plots[agent.plot].holder == agent.id
