"""Deep test step 5b: every check in the test suite that takes a whole career, run on the owner's save."""
import sys, pickle, time, traceback, inspect, importlib
from pathlib import Path
sys.path[:0] = ["/home/user/crciekt20206", "/home/user/crciekt20206/tests"]
import pytest
c = pickle.load(open(Path(sys.argv[1]) / "career.pickle", "rb")); c.count_fielding = False
skip = {"test_long_career", "test_same_number", "test_second_counter", "test_web", "test_web_stage5", "test_web_program"}
results = []
for f in sorted(Path("/home/user/crciekt20206/tests").glob("test_*.py")):
    if f.stem in skip: continue
    try:
        mod = importlib.import_module(f.stem)
    except Exception as e:
        print(f"IMPORT {f.stem}: {e}"); continue
    for n, fn in vars(mod).items():
        if not n.startswith("test_") or not callable(fn): continue
        try:
            sig = list(inspect.signature(fn).parameters)
        except (TypeError, ValueError):
            continue
        if sig != ["career"]: continue
        t = time.time()
        try:
            fn(c); r = "ok"; e = ""
        except pytest.skip.Exception as x:
            r = "skip"; e = str(x)[:200]
        except Exception as x:
            r = "FAIL"; e = f"{type(x).__name__}: {str(x)[:500]} @ " + " | ".join(l.strip() for l in traceback.format_exc().splitlines()[-4:-1])
        results.append((r, f.stem, n, round(time.time() - t, 1), e))
        print(f"{r:4} {time.time() - t:6.1f}s {f.stem}.{n} {e[:300]}", flush=True)
print(f"\n{len(results)} checks: {sum(r[0]=='ok' for r in results)} ok, {sum(r[0]=='FAIL' for r in results)} failed, {sum(r[0]=='skip' for r in results)} skipped")
