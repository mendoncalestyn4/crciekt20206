import pandas as pd
import streamlit as st

from ccstats import extras as E
from ccstats import records as RC
from ui.charts import CONFIG, bars
from ccstats.stats import Scope
from ui import state
from ui.theme import chart_note, page_header

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

# ---------------------------------------------------------------- on pace for
pace = E.on_pace(career, section)
info = E.season_in_progress(career, section)
if info is not None and len(pace):
    cur, now, full = info
    with st.container(border=True):
        st.markdown(f"**On pace for** · {section} {cur} is under way ({now} of about {full} matches played)")
        cols = st.columns(2, gap="medium")
        for box, what in zip(cols, ("runs", "wickets")):
            p = pace[pace.what == what].head(8)
            with box:
                if p.empty:
                    st.caption(f"Nobody has played enough yet to project {what}.")
                    continue
                st.plotly_chart(bars([pl + (" 🔥" if b else "") for pl, b in zip(p.player, p.beats_record)],
                                     p.projected, f"Projected season {what}", 0,
                                     texts=[f"{pr} (now {s} in {mt})" for pr, s, mt in zip(p.projected, p.so_far, p.matches)],
                                     reference=p.record.iloc[0] or None, reference_label="season record",
                                     x_range=[0, max(p.projected.max(), p.record.iloc[0]) * 1.75],
                                     notes=[f"{t} · record: {h or '–'}" for t, h in zip(p.team, p.record_holder)]),
                                width="stretch", config=CONFIG, key=f"rc_pace_{what}")
                p0 = p.iloc[0]
                rec_ = p0.record
                chart_note(f"{p0.player} is on course for {p0.projected} {what} (now {p0.so_far} in {p0.matches} matches)"
                           + (f", {(p0.projected - rec_) / rec_ * 100:+.0f}% against the season record of {int(rec_)}."
                              if pd.notna(rec_) and rec_ else "."),
                           f"Who could break the season {what} record (the dashed line) if they keep this up.")
        st.caption("Projected = what they have so far, per match, times the number of matches their team played last "
                   "season. 🔥 = on course to break the season record (the dashed line).")
fresh = set(RC.recent_sources(career))

GROUPS = [("Team", ["Highest team totals", "Lowest completed totals", "Biggest wins by runs", "Innings wins"]),
          ("Batting", ["Highest individual scores", "Most runs in a season", "Most sixes in an innings", "Highest partnerships"]),
          ("Bowling", ["Best bowling in an innings", "Best bowling in a match", "Most wickets in a season"])]
def record_table(name: str) -> None:
    t = recs[name]
    with st.container(border=True):
        st.markdown(f"**{name}**")
        show = pd.DataFrame({
            "#": [str(r) for r in t["rank"]],
            "Who": [f"{h} 🆕" if s in fresh else h for h, s in zip(t.holder, t.source)], "Record": t.value,
            "Against": [a if a else "" for a in t.against], "Date": t.date.dt.strftime("%d %b %Y")})
        if "season" in name:
            show = show.drop(columns=["Against", "Date"])
        st.dataframe(show, hide_index=True, width="stretch", column_config={"#": st.column_config.TextColumn(width=40)})


for group, names in GROUPS:
    names = [n for n in names if n in recs]
    if not names:
        continue
    st.subheader(group, anchor=False)
    # tables with an opponent and a date get the full width, so nothing is cut off on a smaller screen;
    # the short season tables sit side by side
    wide = [n for n in names if "season" not in n]
    short = [n for n in names if "season" in n]
    for name in wide:
        record_table(name)
    for i in range(0, len(short), 2):
        cols = st.columns(2, gap="medium")
        for col, name in zip(cols, short[i:i + 2]):
            with col:
                record_table(name)
st.caption("Equal records share a place. Partnerships come from the fall of wickets; * means unbroken at the end of "
           "the innings. The fastest fifties and hundreds can't be worked out because scorecards don't record when "
           "each run was scored.")
