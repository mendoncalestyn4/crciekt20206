from ccstats.competitions import classify
from ccstats.demo_league import SQUADS, generate
from ccstats.parser import parse_scorecard, validate_match


def test_generated_league_parses_cleanly():
    files = generate(seasons=(2026,), seed=7)
    assert len(files) == 90 + 4  # double round robin + playoffs
    teams = set()
    for name, text in files:
        m = parse_scorecard(text, name)
        assert validate_match(m) == [], name
        c = classify(m)
        assert (c.competition, c.format, c.level) == ("Indian Premier League", "T20", "Franchise")
        teams |= {m.team1, m.team2}
        for inn in m.innings:
            assert len(inn.batting) == 11
    assert teams == set(SQUADS)


def test_generation_is_repeatable():
    assert generate(seasons=(2026,), seed=3)[:5] == generate(seasons=(2026,), seed=3)[:5]
