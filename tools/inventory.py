"""Everything the current site shows, listed so the new site can be checked against it, item by item.

Two parts:

* the code scan: every heading, label, option, help text, explanation, table column, chart text and message
  written in the site's code (views/, ui/, app.py), page by page and part by part;
* the live crawl: every page opened on the test scorecards (tests/fixtures and tests/fixtures_2026), plus the Player
  and Match pages with a pick made and Home with no team, recording what each actually shows: headings, text, tiles,
  tables (their columns), charts (titles, axes, series), choices (with their options), tabs, expanders, buttons and
  downloads;
* what is saved on the PC: every file, everything inside a career file, every career setting and preference.

    python3 tools/inventory.py            # writes design/INVENTORY.md and design/inventory.json

Engine text (headlines, stories, alerts, explanations worked out from the numbers) comes from ccstats/, which the
new site reuses as it is; the live crawl shows where each of those appears.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

UI_CALLS = {
    # Streamlit
    "title", "header", "subheader", "markdown", "caption", "write", "info", "warning", "success", "error", "toast",
    "text", "metric", "selectbox", "multiselect", "radio", "pills", "segmented_control", "toggle", "checkbox", "slider",
    "select_slider", "number_input", "text_input", "text_area", "date_input", "button", "download_button",
    "file_uploader", "tabs", "expander", "dialog", "popover", "form_submit_button", "link_button", "page_link", "Page",
    "dataframe", "data_editor", "TextColumn", "NumberColumn", "ImageColumn", "LinkColumn", "ProgressColumn",
    "CheckboxColumn", "SelectboxColumn", "DateColumn", "Column", "LineChartColumn", "BarChartColumn", "code",
    "spinner", "status", "html",
    # the site's own helpers
    "page_header", "safe_section", "chart_note", "explain_list", "kpis", "html_table", "scoreboard", "heading",
    "my_teams_row", "tile", "counted", "named", "board", "card", "note", "section_title",
}
CHART_FILES = {"ui/charts.py"}


def _text(node) -> str | None:
    """A string literal, or an f-string with its {…} parts shown as they are written."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        out = []
        for v in node.values:
            if isinstance(v, ast.Constant):
                out.append(str(v.value))
            elif isinstance(v, ast.FormattedValue):
                out.append("{" + ast.unparse(v.value) + "}")
        return "".join(out)
    return None


def _strings(node, depth: int = 0):
    """Every string inside a call's arguments (lists, dicts, nested calls, joins and conditionals too)."""
    if depth > 8 or node is None:
        return
    t = _text(node)
    if t is not None:
        yield t
        return
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.Lambda,)):
            continue
        yield from _strings(child, depth + 1)


def _clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)  # html tags out, the words stay
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _call_name(node: ast.Call) -> str:
    f = node.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return ""


def scan_file(path: Path) -> dict:
    """{part (function or 'page'): [(kind, text)]} for one file."""
    tree = ast.parse(path.read_text())
    rel = str(path.relative_to(ROOT))
    parts: dict[str, list] = {}

    def visit(node, where: str):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visit(child, child.name)
                continue
            if isinstance(child, ast.Call):
                name = _call_name(child)
                if name in UI_CALLS or rel in CHART_FILES:
                    for a in list(child.args) + [k.value for k in child.keywords]:
                        for s in _strings(a):
                            c = _clean(s)
                            if len(c) >= 2 and re.search(r"[A-Za-z]", c) and not c.startswith(("#", "rgba", "data:")):
                                kind = name if name in UI_CALLS else "chart text"
                                for k in child.keywords:
                                    if k.arg == "help" and s in set(_strings(k.value)):
                                        kind = name + " · help"
                                parts.setdefault(where, []).append((kind, c))
            visit(child, where)

    visit(tree, "page")
    for k in list(parts):  # one line per distinct text
        seen, out = set(), []
        for kind, t in parts[k]:
            if t not in seen:
                seen.add(t)
                out.append((kind, t))
        parts[k] = out
    return parts


def code_scan() -> dict:
    files = sorted((ROOT / "views").glob("*.py")) + sorted((ROOT / "ui").glob("*.py")) + [ROOT / "app.py"]
    return {str(f.relative_to(ROOT)): scan_file(f) for f in files}


# --------------------------------------------------------------------------- the live crawl
def _walk(node, out: list, depth=0):
    kids = getattr(node, "children", None)
    rec = _describe(node)
    if rec:
        out.append(rec)
    if kids:
        for c in (kids.values() if isinstance(kids, dict) else kids):
            _walk(c, out, depth + 1)


def _describe(node):
    t = getattr(node, "type", "")
    p = getattr(node, "proto", None)
    try:
        if t in ("markdown", "caption", "title", "header", "subheader", "text", "code", "latex"):
            body = _clean(getattr(node, "value", "") or "")
            return (t, body[:400]) if body and re.search(r"[A-Za-z0-9]", body) else None
        if t in ("alert", "exception", "toast", "error", "warning", "info", "success"):
            return (t, _clean(str(getattr(node, "value", "") or getattr(p, "body", "") or getattr(p, "message", ""))))
        if t == "metric":
            return ("metric", f"{getattr(node, 'label', '')}: {getattr(node, 'value', '')}")
        if t in ("selectbox", "multiselect", "radio", "button_group", "select_slider"):
            opts = [str(o) for o in (getattr(node, "options", []) or [])]
            return (t, f"{getattr(node, 'label', '')} [{len(opts)} options: {', '.join(opts[:8])}{'…' if len(opts) > 8 else ''}]")
        if t in ("checkbox", "toggle", "text_input", "text_area", "number_input", "slider", "date_input", "button",
                 "download_button", "file_uploader", "color_picker", "time_input"):
            return (t, str(getattr(node, "label", "") or getattr(p, "label", "")))
        if t == "tab":
            return ("tab", str(getattr(node, "label", "")))
        if t in ("expander", "expandable", "status"):
            return ("expander", _clean(str(getattr(node, "label", "") or getattr(p, "label", ""))))
        if t in ("arrow_data_frame", "dataframe", "table", "arrow_table"):
            df = node.value
            return ("table", f"{len(df)} rows · columns: {', '.join(map(str, df.columns))}")
        if t == "plotly_chart":
            spec = json.loads(p.spec)
            lay = spec.get("layout", {})
            names = [d.get("name") for d in spec.get("data", []) if d.get("name")]
            def ttl(x):
                v = (x or {}).get("title")
                return (v.get("text") if isinstance(v, dict) else v) or ""
            bits = [f"{len(spec.get('data', []))} series"]
            bits += [f"{k}: {_clean(v)}" for k, v in (("title", ttl(lay)), ("x", ttl(lay.get("xaxis"))),
                                                      ("y", ttl(lay.get("yaxis")))) if v]
            bits += [f"series: {', '.join(map(str, names[:6]))}"] if names else []
            return ("chart", " · ".join(bits))
        if t in ("pills", "segmented_control"):
            return (t, str(getattr(node, "label", "")))
    except Exception as e:  # noqa: BLE001 - an element that can't be read is listed as such
        return (t or "element", f"(couldn't read: {type(e).__name__})")
    if t and t not in ("root", "block", "vertical", "horizontal", "column", "main", "sidebar", "event", "tab_container",
                       "empty", "unknown", "flex_container", "form", "dialog", "popover"):
        return (t, "")
    return None


def live_crawl(team: str = "England") -> dict:
    """Open every page on the test scorecards (tests/fixtures: every kind of competition; tests/fixtures_2026: an IPL
    season), with careers kept in a throwaway folder so the real Stats Pack folder is never touched."""
    import os
    import tempfile
    import zipfile
    os.environ["STATS_PACK_HOME"] = tempfile.mkdtemp(prefix="inventory_home_")
    from streamlit.testing.v1 import AppTest
    from ccstats.loader import Career
    files = [(p.name, p.read_bytes()) for p in sorted((ROOT / "tests" / "fixtures").glob("*.txt"))]
    with zipfile.ZipFile(ROOT / "tests" / "fixtures_2026" / "new_playthrough.zip") as z:
        files += [(n, z.read(n)) for n in z.namelist() if n.lower().endswith(".txt")]
    career = Career.build("My career", files)

    def visit(page: Path, teams: list[str], query: dict | None = None) -> dict:
        at = AppTest.from_file(str(page), default_timeout=300)
        at.session_state["career_obj"] = career
        at.session_state[f"my_teams::{career.name}"] = teams
        for k, v in (query or {}).items():
            at.query_params[k] = v
        try:
            at.run()
            items: list = []
            _walk(at._tree, items)
            return {"items": items, "errors": [str(e.value)[:200] for e in at.exception]}
        except Exception as e:  # noqa: BLE001
            return {"items": [], "errors": [f"{type(e).__name__}: {e}"[:300]]}

    out = {}
    for page in sorted((ROOT / "views").glob("*.py")):
        out[page.name] = visit(page, [team])
        print(page.name, len(out[page.name]["items"]), "items", "· errors:", len(out[page.name]["errors"]), flush=True)
    # the pages that show little until something is picked, opened again with a pick (and Home with no team picked)
    m, bat, bowl = career.matches, career.batting, career.bowling
    multi_day = m[m.section.str.contains("Test|County|Ranji", regex=True)]
    finals = m[m.stage.fillna("").str.contains("Final")]
    extra = [("player.py", f"player {p}", {"player": p}) for p in
             [bat.groupby("player").runs.sum().idxmax(), bowl.groupby("player").wickets.sum().idxmax()]]
    extra += [("match.py", f"match {r.home} v {r.away}, {r.section}", {"match": r.match_id}) for r in
              list(finals.head(1).itertuples()) + list(multi_day.head(1).itertuples())]
    for name, label, query in extra:
        out[f"{name} · {label}"] = visit(ROOT / "views" / name, [team], query)
    out["home.py · no team picked"] = visit(ROOT / "views" / "home.py", [])
    for k in list(out)[len(list((ROOT / 'views').glob('*.py'))):]:
        print(k, len(out[k]["items"]), "items", "· errors:", len(out[k]["errors"]), flush=True)
    return {"career": f"{career.name}: {len(career.matches)} matches (tests/fixtures and tests/fixtures_2026), "
                      f"my team {team}", "pages": out}


# --------------------------------------------------------------------------- what is saved on the PC
def saved_data() -> list[str]:
    """Every file the site keeps in Documents\\Cricket Captain Stats Pack, and every setting saved with a career."""
    src = (ROOT / "ccstats" / "local.py").read_text()
    files = sorted(set(re.findall(r'"([\w.-]+\.(?:json|zip))"', src)))
    body = src[src.index("class CareerSettings"):]
    body = body[:body.index("\n\n\n")]
    fields = re.findall(r"^    (\w+): [^=\n]+(?:= [^#\n]+)?(?:#\s*(.+))?$", body, re.M)
    prefs = sorted(set(re.findall(r'save_preference\("(\w+)"', "".join(
        p.read_text() for p in list((ROOT / "ui").glob("*.py")) + list((ROOT / "views").glob("*.py"))))))
    out = [f"*file* `{f}`" for f in files] + ["*file* the backups folder (one `.stats-pack.zip` per backup)"]
    loader = (ROOT / "ccstats" / "loader.py").read_text()
    out += [f"*inside the career file* `{v}`" + (f": {c.strip()}" if c else "")
            for v, c in re.findall(r'^PACK_\w+ = "([^"]+)"(?:\s*#\s*(.+))?$', loader, re.M)]
    fixes = loader[loader.index("class Fixes"):]
    fixes = fixes[:fixes.index("def ")]
    out += [f"*your fixes (data check)* `{n}`" + (f": {c.strip()}" if c else "")
            for n, c in re.findall(r"^    (\w+): [^=\n]+= field\([^)]*\)(?:\s*#\s*(.+))?$", fixes, re.M)]
    out += [f"*career setting* `{n}`" + (f": {c.strip()}" if c else "") for n, c in fields]
    out += [f"*preference* `{p}`" for p in prefs]
    return out


# --------------------------------------------------------------------------- the checklist
PAGE_NAMES = {"home.py": "My team / Home", "player.py": "Players", "compare.py": "Compare players", "stories.py": "Player stories",
              "match.py": "Matches", "teams.py": "Teams", "team_vs_team.py": "Team vs team", "opponent.py": "Opponent preview",
              "planner.py": "Team planner", "rivalries.py": "Rivalries", "competitions.py": "Competitions", "season.py": "Season",
              "review.py": "Season review", "honours.py": "Honours board", "fixtures.py": "Fixtures", "stat_by_stat.py": "Stat by stat",
              "records.py": "Records", "hall_of_fame.py": "Hall of fame", "rankings.py": "Rankings", "insights.py": "Insights",
              "analytics.py": "Analytics", "data_check.py": "Data check"}


def write(code: dict, live: dict | None) -> None:
    lines = ["# Everything the current site shows: the checklist for the new site", "",
             "Made by `tools/inventory.py` from the site's own code and from opening every page on a real career. "
             "**The new site is not finished until every line here has a place on it.** Each item gets ticked when "
             "its page is rebuilt, and the live crawl is run again on the new site at the end to compare.", ""]
    n_code = sum(len(v) for f in code.values() for v in f.values())
    n_live = sum(len(p["items"]) for p in live["pages"].values()) if live else 0
    lines += [f"- From the code: **{n_code}** headings, labels, options, help texts, explanations, columns and messages "
              f"in {len(code)} files.", f"- From the live crawl: **{n_live}** things shown across {len(live['pages']) if live else 0} pages"
              + (f" ({live['career']})." if live else "."), ""]
    saved = saved_data()
    lines += ["## Saved on your PC · `ccstats/local.py`", "",
              "Everything kept in `Documents\\Cricket Captain Stats Pack`. The new site reads and writes the same files "
              "with the same code.", ""] + [f"- [ ] {s}" for s in saved] + [""]
    for f, parts in code.items():
        title = PAGE_NAMES.get(Path(f).name, f)
        lines += [f"## {title} · `{f}`", ""]
        visits = [k for k in (live["pages"] if live else {}) if k == Path(f).name or k.startswith(Path(f).name + " · ")]
        for key in visits:
            pg = live["pages"][key]
            how = "as it opens" if key == Path(f).name else "with " + key.split(" · ", 1)[1]
            lines += [f"**Shown on the page {how}** ({len(pg['items'])} things"
                      + (f"; ⚠️ errors: {'; '.join(pg['errors'])}" if pg["errors"] else "") + ")", ""]
            for kind, txt in pg["items"]:
                lines.append(f"- [ ] *{kind}* {txt}".rstrip())
            lines.append("")
        lines += ["**In the code** (every part of the page, including what shows only for some choices)", ""]
        for part, items in parts.items():
            lines.append(f"- **{part}**")
            for kind, txt in items:
                lines.append(f"  - [ ] *{kind}* {txt[:500]}")
        lines.append("")
    (ROOT / "design").mkdir(exist_ok=True)
    (ROOT / "design" / "INVENTORY.md").write_text("\n".join(lines))
    (ROOT / "design" / "inventory.json").write_text(json.dumps({"code": code, "live": live, "saved": saved}, indent=1,
                                                               default=str))
    print("code items:", n_code, "· live items:", n_live, "· saved:", len(saved))


if __name__ == "__main__":
    code = code_scan()
    live = None if "--code-only" in sys.argv else live_crawl()
    write(code, live)
