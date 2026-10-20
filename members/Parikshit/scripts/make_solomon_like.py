"""Write a Solomon-FORMAT file (R1-like: uniform customers, capacity 200, horizon 230).
NOT the real benchmark -- it only lets you exercise `--solomon` before downloading R101.

usage: python scripts/make_solomon_like.py [n_customers] [seed] [out_path]
"""
import sys
import numpy as np

n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
out = sys.argv[3] if len(sys.argv) > 3 else f"data/solomon/RLIKE{n}_s{seed}.txt"

rng = np.random.default_rng(seed)
H, SERVICE, CAP = 230, 10, 200
depot = (35, 35)
rows = [(0, *depot, 0, 0, H, 0)]
for i in range(1, n + 1):
    x, y = (int(v) for v in rng.integers(0, 101, 2))
    d = int(np.hypot(x - depot[0], y - depot[1]))
    hi = max(d + 1, H - d - SERVICE)
    c = rng.uniform(d, hi)
    hw = rng.uniform(5, 30)
    ready = int(max(0, c - hw))
    due = int(min(c + hw, hi))
    rows.append((i, x, y, int(rng.choice([10, 20, 30, 40, 50])), ready, max(due, ready + 1), SERVICE))

with open(out, "w") as f:
    f.write(f"RLIKE{n}\n\nVEHICLE\nNUMBER     CAPACITY\n  {max(5, n // 4)}         {CAP}\n\nCUSTOMER\n")
    f.write("CUST NO.  XCOORD.   YCOORD.    DEMAND   READY TIME   DUE DATE   SERVICE   TIME\n\n")
    for r in rows:
        f.write("  ".join(f"{v:>5}" for v in r) + "\n")
print("wrote", out)