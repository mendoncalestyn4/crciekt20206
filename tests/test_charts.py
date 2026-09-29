"""The charts must show exactly what the tables say, and the shaded 'better'
side of every dot chart must agree with the ranking."""

from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from ccstats.loader import Career
from ccstats.stats import Scope, player_tables, rank, stat_definitions
from ui.charts import dot_chart, ranked_bars

ROOT = Path(__file__).parent.parent
FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.txt"))


@pytest.fixture(scope="module")
def career():
    return Career.build("charts", [(p.name, p.read_bytes()) for p in FIXTURES])


def tables_for(career, section):
    bat, bowl, fld, base = player_tables(career, Scope(sections=[section]))
    return {"bat": bat, "bowl": bowl, "field": fld}, stat_definitions(base), base


SECTIONS = ["T20 Blast", "Indian Premier League", "Tests", "ODIs", "T20Is",
            "The Hundred", "County Championship · Division 1"]


@pytest.mark.parametrize("section", SECTIONS)
def test_bars_show_exactly_the_ranked_numbers(career, section):
    tables, defs, _ = tables_for(career, section)
    for disc, stats in defs.items():
        for stat in stats:
            for best in (True, False):
                ranked = rank(tables[disc], stat, best=best).head(10)
                if ranked.empty:
                    continue
                fig = ranked_bars(ranked, stat, best)
                bar = fig.data[0]
                assert list(bar.y) == list(ranked.player)[::-1], (section, stat.id)
                assert np.allclose(np.array(bar.x, float), ranked[stat.column].to_numpy(float)[::-1]), (section, stat.id)
                values = ranked[stat.column].to_numpy(float)
                if stat.better == "high":
                    assert (np.diff(values) <= 1e-9).all() if best else (np.diff(values) >= -1e-9).all()
                else:
                    assert (np.diff(values) >= -1e-9).all() if best else (np.diff(values) <= 1e-9).all()


@pytest.mark.parametrize("section", SECTIONS)
def test_dot_charts_plot_the_right_players_and_numbers(career, section):
    tables, defs, _ = tables_for(career, section)
    for disc, stats in defs.items():
        for stat in stats:
            pool = tables[disc][tables[disc][stat.column].notna()]
            if stat.keepers_only:
                pool = pool[pool.stumpings > 0]
            if pool.empty:
                continue
            ranked = rank(pool, stat).head(10)
            fig = dot_chart(pool, ranked, stat, best=True)
            grey, coloured = fig.data[0], fig.data[1]
            assert len(grey.x) + len(coloured.x) == len(pool)
            top = pool[pool.player.isin(ranked.player)]
            assert sorted(zip(np.array(coloured.x, float), np.array(coloured.y, float))) == \
                sorted(zip(top[stat.dot.x].astype(float), top[stat.dot.y].astype(float)))


# stat -> the reference value the shaded side is measured against
REFERENCE = {
    ("bat", "average"): lambda b: b.average, ("bat", "strike_rate"): lambda b: b.strike_rate,
    ("bat", "boundary_pct"): lambda b: b.boundary_share * 100, ("bat", "runs_above_average"): lambda b: 0.0,
    ("bowl", "economy"): lambda b: b.economy, ("bowl", "strike_rate"): lambda b: b.bowl_strike_rate,
    ("bowl", "average"): lambda b: b.bowl_average, ("bowl", "dot_pct"): lambda b: (b.dot_rate or 0) * 100,
    ("bowl", "runs_saved"): lambda b: 0.0,
}


@pytest.mark.parametrize("section", SECTIONS)
def test_shaded_side_agrees_with_the_ranking(career, section):
    """A player in the shaded area of the dot chart must be better than average on that stat."""
    tables, defs, base = tables_for(career, section)
    checked = 0
    for disc, stats in defs.items():
        for stat in stats:
            ref = REFERENCE.get((disc, stat.id))
            if ref is None:
                continue
            d = stat.dot
            for _, p in tables[disc][tables[disc][stat.column].notna()].iterrows():
                x, y, v = float(p[d.x]), float(p[d.y]), float(p[stat.column])
                line_y = d.value if d.line == "flat" else d.value * x
                if abs(y - line_y) < 1e-9 or (d.line == "slope" and x == 0):
                    continue  # exactly on the line
                shaded = (y < line_y) if d.better_below else (y > line_y)
                better = v > ref(base) if stat.better == "high" else v < ref(base)
                assert shaded == better, (section, stat.id, p.player)
                checked += 1
    assert checked > 0


def test_stat_page_runs_for_every_choice(career):
    """Open the Stat by stat page for every section, discipline, stat and best/worst."""
    sections = career.matches.section.unique()
    runs = 0
    for section in sections:
        _, defs, _ = tables_for(career, section)
        for disc_label, disc in (("Batting", "bat"), ("Bowling", "bowl"), ("Fielding", "field")):
            for stat in defs[disc]:
                for view in (("Best", "Worst") if disc != "field" else ("Best",)):
                    at = AppTest.from_file(str(ROOT / "views" / "stat_by_stat.py"), default_timeout=30)
                    at.session_state["career_obj"] = career
                    at.session_state["sbs_section"] = section
                    at.session_state["sbs_disc"] = disc_label
                    at.session_state["sbs_view"] = view
                    at.session_state[f"sbs_stat_{disc_label}"] = stat.label
                    at.run()
                    assert not at.exception, (section, disc_label, stat.label, view, at.exception)
                    runs += 1
    assert runs > 100


def test_stat_page_runs_for_every_batting_position(career):
    from ccstats.stats import POSITION_GROUPS
    for section in career.matches.section.unique():
        _, defs, _ = tables_for(career, section)
        for pos in POSITION_GROUPS:
            for stat in defs["bat"]:
                at = AppTest.from_file(str(ROOT / "views" / "stat_by_stat.py"), default_timeout=30)
                at.session_state["career_obj"] = career
                at.session_state["sbs_section"] = section
                at.session_state["sbs_pos"] = pos
                at.session_state["sbs_stat_Batting"] = stat.label
                at.run()
                assert not at.exception, (section, pos, stat.label, at.exception)


def test_wicket_timeline_plots_the_fall_of_wickets(career):
    from ui.charts import wicket_timeline
    mid = career.matches.set_index("source").loc["18_jul_2026-som_v_nht_blast_-_f.txt"].match_id
    data = []
    for r in career.innings[career.innings.match_id == mid].sort_values("innings_no").itertuples():
        f = career.fow[(career.fow.match_id == mid) & (career.fow.innings_no == r.innings_no)].sort_values("wicket")
        data.append(dict(label=r.team, fow=list(zip(f.wicket, f.score)), total=int(r.runs), all_out=bool(r.all_out)))
    fig = wicket_timeline(data)
    assert list(fig.data[0].y) == [0, 6, 16, 16, 17, 25, 102, 137, 137, 163]  # Somerset 163/8, unbroken at the end
    assert list(fig.data[1].y) == [0, 15, 23, 32, 46, 46, 51, 70, 87, 87, 96]  # Northants all out 96
