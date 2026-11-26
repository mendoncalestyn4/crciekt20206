"""Every test run keeps its careers in a folder of its own, never in Documents\\Cricket Captain Stats Pack: a test
that saves a career can't change what another test (or a second run at the same time) reads back."""
import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def _private_stats_pack_home(tmp_path_factory):
    home = tmp_path_factory.mktemp("stats_pack_home")
    before = os.environ.get("STATS_PACK_HOME")
    os.environ["STATS_PACK_HOME"] = str(home)
    yield home
    if before is None:
        os.environ.pop("STATS_PACK_HOME", None)
    else:
        os.environ["STATS_PACK_HOME"] = before


@pytest.fixture(autouse=True, scope="session")
def _no_helper_processes():
    """The many test servers get their pages ready on their own core only (tests/test_speed.py turns the helpers on
    to check them): three extra processes for each test server would only slow the run down."""
    before = os.environ.get("STATS_PACK_HELPERS")
    os.environ["STATS_PACK_HELPERS"] = "0"
    yield
    if before is None:
        os.environ.pop("STATS_PACK_HELPERS", None)
    else:
        os.environ["STATS_PACK_HELPERS"] = before


def pytest_configure(config):
    config.addinivalue_line("markers", "weekly: a heavy accuracy check run by the weekly run on GitHub (WEEKLY=1), so a "
                                       "normal test run takes no longer than before")


def pytest_collection_modifyitems(config, items):
    """The heavy accuracy checks (marked weekly) run only when WEEKLY=1 (the weekly run on GitHub, or by hand).

    TEST_SHARD="k/n" (the Windows run on GitHub, split over n machines at once): this machine runs every n-th test,
    starting at the k-th, so the n parts together are exactly every test, each once."""
    import os
    if os.environ.get("WEEKLY") != "1":
        heavy = [it for it in items if it.get_closest_marker("weekly")]
        if heavy:
            config.hook.pytest_deselected(items=heavy)
            items[:] = [it for it in items if not it.get_closest_marker("weekly")]
    shard = os.environ.get("TEST_SHARD", "")
    if not shard:
        return
    k, n = (int(x) for x in shard.split("/"))
    keep = [it for i, it in enumerate(items) if i % n == k - 1]
    config.hook.pytest_deselected(items=[it for i, it in enumerate(items) if i % n != k - 1])
    items[:] = keep
