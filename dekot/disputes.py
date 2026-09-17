"""One dispute type: the good plot (SPEC §7). Runs once per life-year."""


def contest_good_plot(sim, day):
    world, cfg = sim.world, sim.cfg
    plot = world.good_plot()
    holder = sim.agent(plot.holder) if plot.holder else None
    if holder is None or not holder.alive:
        # vacancy: most ambitious living farmer simply takes it
        farmers = [a for a in sim.living() if a.role == "farmer"]
        if not farmers:
            return
        taker = max(farmers, key=lambda a: (a.traits["ambition"], a.id))
        _move_to(sim, taker, plot)
        sim.events.add(day, 0, type="plot_claimed", plot=plot.id, agent=taker.id, reason="vacant")
        return
    challengers = sorted((a for a in sim.living() if a.role == "farmer" and a.id != holder.id),
                         key=lambda a: (-a.traits["ambition"], a.id))[:2]
    for c in challengers:
        # weight: stubbornness and health favour each side; affinity with holder softens the challenge
        c_w = c.traits["stubbornness"] + c.health - max(sim.rel.get(c.id, holder.id), 0) * 0.5
        h_w = holder.traits["stubbornness"] + holder.health + 20  # incumbency
        c_wins = sim.rng.random() < c_w / (c_w + h_w)
        if c_wins:
            sim.rel.shift(c.id, holder.id, -20)
            sim.events.add(day, 0, type="dispute", plot=plot.id, challenger=c.id, holder=holder.id, outcome="challenger_wins")
            _move_to(sim, c, plot)
            holder.mood = max(holder.mood - 15, 0)
            holder = c
        else:
            sim.rel.shift(c.id, holder.id, -10)
            c.mood = max(c.mood - 10, 0)
            sim.events.add(day, 0, type="dispute", plot=plot.id, challenger=c.id, holder=holder.id, outcome="holder_keeps")


def _move_to(sim, agent, plot):
    if agent.plot is not None:
        old = sim.world.plots[agent.plot]
        if old.holder == agent.id:
            old.holder = None
    if plot.holder is not None:
        prev = sim.agent(plot.holder)
        prev.plot = None
    plot.holder = agent.id
    agent.plot = plot.id
