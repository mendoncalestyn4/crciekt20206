"""Every sort keeps level rows in the order they came in (27 November).

pandas sorts with a quick, unsteady method unless told otherwise, and the maths library underneath picks a different
fast method on different processors. So two rows with the same value (the same count, the same total) could swap
places between one computer and another: the frozen copy of every number found it, comparing this machine with
GitHub's Windows machines. Rather than tell each of the site's ~500 sorts separately (and miss the next one), every
sort in the engine, the site and the program is steady by default from here. Where a sort names its own method, that
choice is kept."""

from __future__ import annotations

import functools

import pandas as pd

_DONE = "_stats_pack_steady"


def _steady(f):
    if getattr(f, _DONE, False):
        return f

    @functools.wraps(f)
    def sort(self, *args, **kw):
        kw.setdefault("kind", "stable")      # (every option but `by` is named in pandas 2.3 and 3: never positional)
        return f(self, *args, **kw)
    setattr(sort, _DONE, True)
    return sort


def install() -> None:
    for cls in (pd.Series, pd.DataFrame):
        cls.sort_values = _steady(cls.sort_values)
        cls.sort_index = _steady(cls.sort_index)


install()
