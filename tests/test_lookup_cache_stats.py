from __future__ import annotations

from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.response import HTTPResponse

from plextraktsync.factory.cache_session import CachedSession, LookupStats


def test_trakt_lookup_stats_count_cached_and_live_responses_once(monkeypatch):
    def send(adapter, request, **kwargs):
        response = Response()
        response.request = request
        response.url = request.url
        response.status_code = 429 if "/rate-limited" in request.url else 200
        response._content = b"[{}]" if "/match?" in request.url else b"[]"
        response.raw = HTTPResponse(body=response._content, request_url=request.url)
        return response

    monkeypatch.setattr(HTTPAdapter, "send", send)
    with CachedSession(backend="memory") as session:
        url = "https://api.trakt.tv/search/tmdb/"
        with session.collect_lookup_stats() as stats:
            for lookup in ("match", "empty"):
                assert not session.get(url + lookup, params={"type": "movie"}).from_cache
                assert session.get(url + lookup, params={"type": "movie"}).from_cache
            assert session.get(url + "rate-limited").status_code == 429
            session.get("https://api.trakt.tv/sync/history")
            session.get("https://plex.example/search/tmdb/empty")

        assert stats == LookupStats(hits=2, misses=3, empty_results=2)
        session.get(url + "match", params={"type": "movie"})
        assert stats == LookupStats(hits=2, misses=3, empty_results=2)
        with session.collect_lookup_stats() as next_run:
            assert next_run == LookupStats()
