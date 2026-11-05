from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest
from click import ClickException
from requests import Response
from trakt.errors import RateLimitException

from plextraktsync.media.MediaFactory import MediaFactory
from plextraktsync.trakt.TraktLookup import TraktLookup


def limited_lookup(stage: str, failures: int):
    calls = []
    episode = SimpleNamespace(number=1)

    def fetch():
        calls.append(stage)
        if len(calls) <= failures:
            response = Response()
            response.status_code = 429
            response.headers["Retry-After"] = "2"
            raise RateLimitException(response)

    class Season:
        season = 1

        @property
        def episodes(self):
            if stage == "episodes":
                fetch()
            return [episode]

    class Show:
        @property
        def seasons(self):
            if stage == "seasons":
                fetch()
            return [Season()]

    return TraktLookup(Show()), episode, calls


@pytest.fixture
def retry_waits(monkeypatch):
    waits = []
    module = importlib.import_module("plextraktsync.decorators.rate_limit")
    monkeypatch.setattr(module, "sleep", waits.append)
    return waits


@pytest.mark.parametrize("stage", ["seasons", "episodes"])
def test_episode_lookup_waits_for_rate_limit_and_caches_success(stage, retry_waits):
    lookup, episode, calls = limited_lookup(stage, failures=2)

    assert lookup.from_number(1, 1) is episode
    assert len(retry_waits) == 2
    assert all(delay >= 2 for delay in retry_waits)
    assert len(calls) == 3

    for _ in range(10):
        assert lookup.from_number(1, 1) is episode
    assert len(calls) == 3


def test_exhausted_episode_rate_limit_aborts_instead_of_skipping_items(retry_waits):
    lookup, _, calls = limited_lookup("episodes", failures=100)
    trakt = SimpleNamespace(find_episode_guid=lambda guid, seasons: seasons.from_number(1, 1))
    resolver = MediaFactory(plex=None, trakt=trakt, server_config=None)
    guid = SimpleNamespace(syncable=True)
    show = SimpleNamespace(seasons=lookup)

    with pytest.raises(ClickException, match="Trakt API didn't respond properly"):
        resolver.resolve_guid(guid, show)

    assert len(calls) == 6
    assert len(retry_waits) == 5
