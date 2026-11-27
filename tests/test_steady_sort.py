"""Every sort keeps level rows in the order they came in (ccstats/stablesort.py), so the order is the same on every
computer: the quick, unsteady sort pandas uses by default gave level rows a different order on GitHub's Windows
machines than on this one (found by the frozen copy of the 20-season career, 27 November). Here, long lists full of
level values, where an unsteady sort all but surely shuffles them."""

import numpy as np
import pandas as pd

import ccstats  # noqa: F401  (switches it on, as every part of the site does by importing the engine)


def _kept_order(index, values, k) -> bool:
    return bool((np.diff(np.asarray(index)[np.asarray(values) == k]) > 0).all())


def test_series_and_tables_keep_level_rows_in_order():
    s = pd.Series(np.arange(20000) % 5)
    for asc in (True, False):
        r = s.sort_values(ascending=asc)
        assert all(_kept_order(r.index, r.values, k) for k in range(5))
    d = pd.DataFrame({"n": np.arange(20000) % 5, "x": np.arange(20000)})
    for asc in (True, False):
        r = d.sort_values("n", ascending=asc)
        assert all(_kept_order(r.x, r.n, k) for k in range(5))
    r = pd.Series(np.arange(20000), index=np.arange(20000) % 5).sort_index()
    assert all(_kept_order(r.values, r.index, k) for k in range(5))


def test_counts_with_the_same_number_keep_the_order_first_seen():
    names = [f"name {i}" for i in np.random.default_rng(1).permutation(4000)]
    counted = pd.Series(names * 3).value_counts()
    assert list(counted.index) == names


def test_a_sort_that_names_its_own_method_keeps_it():
    s = pd.Series([3, 1, 2])
    assert list(s.sort_values(kind="mergesort")) == [1, 2, 3]
