"""Canonical event and ledger logs: sorted keys, stable ordering, no wall-clock time."""
import json


class Log:
    def __init__(self):
        self.entries = []
        self.seq = 0

    def add(self, day, tick, **fields):
        self.seq += 1
        self.entries.append({"day": day, "tick": tick, "seq": self.seq, **fields})

    def dumps(self) -> str:
        return "".join(json.dumps(e, sort_keys=True, separators=(",", ":")) + "\n" for e in self.entries)

    def write(self, path):
        with open(path, "w") as f:
            f.write(self.dumps())
