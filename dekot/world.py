from dataclasses import dataclass, asdict

# The village map, matching the approved Phase-0 scene: river along the top,
# a ghat path down to it, paddy plots in the middle band, homes below the
# main path, the banyan by the path junction, grazing land at the bottom.
# Rows 0-1 (water) are impassable; everything else is walkable.
TERRAIN = [
    "WWWWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWWWW",
    "KKKKKKKKTTKKKKKKKK",
    "GPPPGQQQTTPPPGPPPG",
    "GPPPGQQQTTPPPGPPPG",
    "GPPPGQQQTTPPPGPPPG",
    "TTTTTTTTTTTTTTTTTT",
    "GGDDDGDDDTTGDDDGGG",
    "GGDDDGDDDTTGDDDGDD",
    "GGGGGDGGGBBGGGGGDD",
    "GGGGGGGGGGGGGGGGGG",
    "GGGGGGGGGGGGGGGGGG",
]
WATER_ROWS = 2
PLOT_SITES = [(6, 4), (2, 4), (11, 4), (15, 4), (2, 5), (12, 5)]   # plot 0 = the good plot
CLEAR_SITES = [(2, 11), (5, 11), (8, 11), (11, 11), (14, 11), (16, 11)]
HOME_SITES = [(3, 8), (7, 8), (12, 8), (16, 8), (5, 9)]
EXPANSION_HOMES = [(2, 10), (12, 10), (15, 10), (17, 9)]  # new couples build here


def free_home(agents, exclude_ids=()):
    """First unoccupied home site, base sites before expansion ground."""
    occupied = {tuple(x.home) for x in agents
                if x.alive and x.home and x.id not in exclude_ids}
    for site in HOME_SITES + EXPANSION_HOMES:
        if site not in occupied:
            return site
    return None
GRAZE = (8, 10)  # noqa: referenced by assign_roles below and the engine
BANYAN = (9, 9)
GHAT = (9, 2)    # steps down to the river: water is fetched here
SHRINE = (17, 7)  # small shrine east of the houses


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
    width: int = 18
    height: int = 12

    def good_plot(self):
        return max(self.plots, key=lambda p: p.fertility)

    def walkable(self, x, y):
        return 0 <= x < self.width and WATER_ROWS <= y < self.height

    def to_dict(self):
        return {"plots": [asdict(p) for p in self.plots], "herd_size": self.herd_size,
                "width": self.width, "height": self.height,
                "terrain": TERRAIN, "homes": [list(h) for h in HOME_SITES],
                "graze": list(GRAZE), "banyan": list(BANYAN),
                "ghat": list(GHAT), "shrine": list(SHRINE)}

    @classmethod
    def from_dict(cls, d):
        return cls(plots=[Plot(**p) for p in d["plots"]], herd_size=d["herd_size"],
                   width=d["width"], height=d["height"])


def make_world(cfg):
    assert cfg.n_plots <= len(PLOT_SITES) and cfg.max_plots <= len(PLOT_SITES) + len(CLEAR_SITES)
    plots = [Plot(id=i, x=PLOT_SITES[i][0], y=PLOT_SITES[i][1], fertility=cfg.plot_fertility)
             for i in range(cfg.n_plots)]
    plots[0].fertility = cfg.good_plot_fertility
    return World(plots=plots, herd_size=cfg.herd_size)


def clear_site(world, cfg):
    """Map position for the next plot cleared from grass, or None when land runs out."""
    nxt = len(world.plots) - cfg.n_plots
    if len(world.plots) >= cfg.max_plots or nxt >= len(CLEAR_SITES):
        return None
    return CLEAR_SITES[nxt]


def assign_roles(agents, world, cfg):
    """Trait fit: most helpful -> cowherd; farmers by ambition, most ambitious gets the good plot.
    Every founder also gets a home tile and starts there."""
    for i, a in enumerate(agents):
        a.home = list(HOME_SITES[i % len(HOME_SITES)])
        a.pos = list(a.home)
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
    # people live near their work: plot holders take the home closest to their
    # plot, cowherds the home closest to the grazing land
    for a in agents:
        if a.role == "farmer" and a.plot is not None:
            p = world.plots[a.plot]
            target = (p.x, p.y)
        elif a.role == "cowherd":
            target = GRAZE
        else:
            continue
        a.home = list(min(HOME_SITES, key=lambda h: abs(h[0]-target[0]) + abs(h[1]-target[1])))
        a.pos = list(a.home)


def owns(world, agent) -> bool:
    return agent.plot is not None and world.plots[agent.plot].holder == agent.id
