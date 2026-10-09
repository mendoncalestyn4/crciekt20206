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
