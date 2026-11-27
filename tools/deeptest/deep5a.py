"""Deep test step 5a: every same-number check (tests/test_same_number.py) on the owner's save; every failure listed."""
import sys, pickle, time, traceback
from pathlib import Path
sys.path[:0] = ["/home/user/crciekt20206", "/home/user/crciekt20206/tests"]
import test_same_number as SN
c = pickle.load(open(Path(sys.argv[1]) / "career.pickle", "rb")); c.count_fielding = False
names = [n for n in dir(SN) if n.startswith("test_")]
fails = []
for n in names:
    t = time.time()
    try:
        getattr(SN, n)(c); ok = "ok"
    except Exception as e:
        ok = "FAIL"; fails.append((n, f"{type(e).__name__}: {str(e)[:600]}", traceback.format_exc().splitlines()[-6:]))
    print(f"{ok:4} {time.time() - t:6.1f}s {n}", flush=True)
print(f"\n{len(names)} checks, {len(fails)} failed")
for n, e, tb in fails:
    print("\n==", n, "\n", e, "\n", "\n".join(tb))
