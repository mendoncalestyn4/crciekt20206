"""A picked XI shown as a team sheet."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ccstats import seasonal as SN

from .theme import html_table, player_link


def team_sheet(xi: pd.DataFrame, title: str, show_team: bool = True) -> None:
    """The XI in team-sheet order, with the reason for each pick."""
    with st.container(border=True):
        st.markdown(f"**{title}**")
        if xi.empty:
            st.caption("Not enough games yet to pick an XI.")
            return
        rows = [[i + 1, r.slot, player_link(r.player)] + ([r.team] if show_team else []) + [r.why]
                for i, r in enumerate(xi.itertuples())]
        html_table(rows, ["", "Role", "Player"] + (["Team"] if show_team else []) + ["Why"], numeric={0}, raw={2})
        kind = xi.attrs.get("kind", "t20")
        how = {"t20": "Batters on average × strike rate, a finisher (batting 5–7) on runs per innings × strike rate, "
                      "bowlers on wickets (each worth the section's runs per wicket) plus runs kept below the "
                      "section's economy.",
               "one": "Batters on average × strike rate; bowlers on wickets (each worth the section's runs per "
                      "wicket) plus runs kept below the section's economy.",
               "multi": "Batters on average; bowlers on wickets, worth more the lower their average and strike "
                        "rate against the section's, plus 2 for each five-for."}[kind]
        st.caption(f"Picked by role: 2 openers, the middle order, a keeper (made a stumping), an all-rounder (bats in "
                   f"the top 8; runs per innings × bowling) and 4 bowlers. {how} Needs {xi.attrs.get('need', 2)}+ "
                   "games here. 'Best available': not enough players in that role, so the best of the rest.")


def best_xi_cached(career, ids, team: str = "") -> pd.DataFrame:
    from . import state
    return state.memo(SN.best_xi, career, ids, team)
