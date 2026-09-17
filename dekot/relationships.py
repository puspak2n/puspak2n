"""Pairwise affinity, -100..100, keyed by sorted id pair."""


def key(a, b):
    return "|".join(sorted((a, b)))


class Relationships:
    def __init__(self, agent_ids=None, data=None):
        self.affinity = data if data is not None else {}
        if agent_ids:
            for i, a in enumerate(agent_ids):
                for b in agent_ids[i + 1:]:
                    self.affinity.setdefault(key(a, b), 0.0)

    def get(self, a, b):
        return self.affinity[key(a, b)]

    def shift(self, a, b, amount):
        k = key(a, b)
        self.affinity[k] = max(-100.0, min(100.0, self.affinity[k] + amount))
