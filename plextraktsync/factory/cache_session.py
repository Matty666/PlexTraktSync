from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from urllib.parse import urlsplit

from requests_cache import CachedSession as RequestsCachedSession


@dataclass
class LookupStats:
    hits: int = 0
    misses: int = 0
    empty_results: int = 0


class CachedSession(RequestsCachedSession):
    lookup_stats: LookupStats | None = None

    @contextmanager
    def collect_lookup_stats(self):
        previous = self.lookup_stats
        self.lookup_stats = LookupStats()
        try:
            yield self.lookup_stats
        finally:
            self.lookup_stats = previous

    def request(self, method, url, *args, **kwargs):
        response = super().request(method, url, *args, **kwargs)
        stats = self.lookup_stats
        if stats is None or method.upper() != "GET":
            return response

        parts = urlsplit(url)
        path = parts.path.strip("/").split("/")
        if (
            parts.hostname != "api.trakt.tv"
            or len(path) != 3
            or path[0] != "search"
            or path[1] not in {"imdb", "tmdb", "tvdb", "trakt"}
        ):
            return response

        if response.from_cache:
            stats.hits += 1
        else:
            stats.misses += 1

        if response.status_code == 200:
            try:
                empty = response.json() == []
            except ValueError:
                empty = False
            if empty:
                stats.empty_results += 1
        return response
