"""Every resource creation, consumption or transfer goes through here (SPEC §4)."""
from .log import Log


PRECISION = 4


class LedgerError(Exception):
    pass


class OwnershipError(Exception):
    pass


class Ledger(Log):
    def apply(self, day, tick, agent, resource, delta, action, reason, counterparty=None):
        if not reason:
            raise LedgerError("ledger entry without reason")
        delta = round(delta, PRECISION)  # accounting precision == logged precision
        new = round(agent.inventory[resource] + delta, PRECISION)
        if new < 0:
            raise LedgerError(f"negative inventory: {agent.id} {resource} {new}")
        agent.inventory[resource] = new
        self.add(day, tick, actor=agent.id, resource=resource, delta=delta,
                 action=action, reason=reason, counterparty=counterparty)

    def open(self, agents):
        for a in sorted(agents, key=lambda x: x.id):
            for r in sorted(a.inventory):
                self.add(0, 0, actor=a.id, resource=r, delta=a.inventory[r], action="opening_balance",
                         reason="founding", counterparty=None)

    def reconstruct(self):
        inv = {}
        for e in self.entries:
            k = (e["actor"], e["resource"])
            inv[k] = round(inv.get(k, 0.0) + e["delta"], PRECISION)
        return inv

    def transfer(self, day, tick, giver, taker, resource, amount, reason):
        self.apply(day, tick, giver, resource, -amount, "give", reason, counterparty=taker.id)
        self.apply(day, tick, taker, resource, amount, "receive", reason, counterparty=giver.id)
