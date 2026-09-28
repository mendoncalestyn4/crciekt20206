import pandas as pd
import streamlit as st

from ccstats import records as RC
from ccstats.stats import Scope
from ui import state
from ui.theme import page_header

career = state.current()
if career is None:
    st.info("Load a career on the Home page first.")
    st.stop()

m = career.matches
page_header("Records", "The record books",
            "The best (and worst) ever in each competition. Anything set in your 10 most recent matches is marked 🆕.")
c1, c2, c3 = st.columns([2, 1, 1])
sections = m.section.value_counts()
section = c1.selectbox("Section", list(sections.index), key="rc_section", format_func=lambda s: f"{s} · {sections[s]} matches")
seasons = sorted(m[m.section == section].season.unique(), reverse=True)
season = c2.selectbox("Season", ["All seasons"] + seasons, key="rc_season")
top = c3.selectbox("Show", [5, 10, 20], index=1, key="rc_top", format_func=lambda n: f"Top {n}")
ids = Scope(sections=[section], seasons=[] if season == "All seasons" else [season]).match_ids(m)
recs = RC.records(career, ids, top=top)
fresh = set(RC.recent_sources(career))

GROUPS = [("Team", ["Highest team totals", "Lowest completed totals", "Biggest wins by runs", "Innings wins"]),
          ("Batting", ["Highest individual scores", "Most runs in a season", "Most sixes in an innings", "Highest partnerships"]),
          ("Bowling", ["Best bowling in an innings", "Best bowling in a match", "Most wickets in a season"])]
for group, names in GROUPS:
    names = [n for n in names if n in recs]
    if not names:
        continue
    st.subheader(group, anchor=False)
    cols = st.columns(2, gap="medium")
    for i, name in enumerate(names):
        t = recs[name]
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"**{name}**")
                show = pd.DataFrame({
                    "#": [str(r) for r in t["rank"]],
                    "Who": [f"{h} 🆕" if s in fresh else h for h, s in zip(t.holder, t.source)], "Record": t.value,
                    "Against": [a if a else "" for a in t.against], "Date": t.date.dt.strftime("%d %b %Y")})
                if "season" in name:
                    show = show.drop(columns=["Against", "Date"])
                st.dataframe(show, hide_index=True, width="stretch",
                             column_config={"#": st.column_config.TextColumn(width=36)})
st.caption("Equal records share a place. Partnerships come from the fall of wickets; * means unbroken at the end of "
           "the innings. The fastest fifties and hundreds can't be worked out because scorecards don't record when "
           "each run was scored.")
