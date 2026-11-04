"""python3 -I weird_paths.py <port>: the pages to open in a browser for one save: My team (both tabs), the inbox, find a
player, a few players in every tab (the oddest names first), find a match, a few matches in every tab, settings."""
import json, sys, urllib.parse, urllib.request
base = f"http://127.0.0.1:{sys.argv[1]}"
def get(p):
    try:
        return json.load(urllib.request.urlopen(base + urllib.parse.quote(p, safe="/?=&"), timeout=600))
    except Exception:
        return {}
names = get("/api/names").get("names", [])
odd = sorted(names, key=lambda n: -sum(not c.isalnum() and c != " " for c in n))[:3] + names[:2]
ms = get("/api/matches?section=All sections").get("matches", [])[:3]
q = lambda s: urllib.parse.quote(s)
paths = ["/", "/?view=scouting", "/inbox", "/players", "/matches", "/settings"]
for n in dict.fromkeys(odd):
    paths += [f"/players/{q(n)}"] + [f"/players/{q(n)}?view={v}" for v in ("bowling", "fielding", "story")]
for m in ms:
    paths += [f"/matches/{m['id']}", f"/matches/{m['id']}?view=scorecard", f"/matches/{m['id']}?view=wickets"]
print(" ".join(paths))
