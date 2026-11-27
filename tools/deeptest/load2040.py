import sys, os, pickle
sys.path.insert(0, "/home/user/crciekt20206")
from pathlib import Path
from ccstats.loader import Career
root = Path(sys.argv[1]) / "Scorecards"
files = [(p.name, p.read_bytes(), os.path.getmtime(p)) for p in sorted(root.glob("*.txt"))]
c = Career.build("Save 2040", files)
pickle.dump(c, open(Path(sys.argv[1]) / "career.pickle", "wb"))
print(len(c.matches), "matches", len(c.problems), "problems", len(c.guesses), "guesses", len(c.auto_splits), "splits")
