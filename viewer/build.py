"""Assemble the recorded animated viewer: a recording JSON between head and tail.

    python -m dekot record --seed 34 --years 20 --out runs/rec.json
    python viewer/build.py runs/rec.json dekot_alive.html
"""
import sys

def build(rec_path, out_path):
    here = __file__.rsplit("/", 1)[0]
    data = open(rec_path).read()
    assert "</script" not in data
    head = open(f"{here}/alive_head.html").read()
    tail = open(f"{here}/alive_tail.html").read()
    with open(out_path, "w") as f:
        f.write(head + data + "\n" + tail)

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
    print("built", sys.argv[2])
