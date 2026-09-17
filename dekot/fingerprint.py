"""Engine fingerprint: all simulation-affecting source, Python version, dependencies."""
import hashlib
import os
import sys

EXCLUDE = {"cli.py", "__main__.py", "fingerprint.py"}


def engine_fingerprint() -> str:
    h = hashlib.sha256()
    pkg = os.path.dirname(__file__)
    for name in sorted(os.listdir(pkg)):
        if name.endswith(".py") and name not in EXCLUDE:
            with open(os.path.join(pkg, name), "rb") as f:
                h.update(name.encode()); h.update(f.read())
    h.update(sys.version.split()[0].encode())
    h.update(b"deps:stdlib-only")
    return h.hexdigest()
