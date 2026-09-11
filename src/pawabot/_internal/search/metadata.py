# Copyright (c) 2020, Timothée Mazzucotelli and contributors
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from __future__ import annotations

import os
import re
from urllib.parse import quote

from pawabot._internal.search._http import _ProviderError, _request_json, _result_list
from pawabot._internal.search.models import _Movie


async def _search_omdb(query: str) -> list[_Movie]:
    """Search only movies through OMDb."""
    data = await _request_json(
        "OMDb",
        "https://www.omdbapi.com/",
        params={"apikey": os.environ["OMDB_API_KEY"], "s": query, "type": "movie"},
    )
    if data.get("Response") == "False":
        if data.get("Error") == "Movie not found!":
            return []
        raise _ProviderError("OMDb could not complete the search. Check its API key and quota, or narrow the title.")
    return [
        _Movie(title=item["Title"], year=item.get("Year") or "Unknown year", imdb_id=item["imdbID"])
        for item in _result_list(data, "Search", "OMDb")
        if item.get("Type") == "movie"
        and isinstance(item.get("Title"), str)
        and re.fullmatch(r"tt[0-9]+", str(item.get("imdbID", "")))
    ][:10]


async def _search_tmdb(query: str) -> list[_Movie]:
    """Search movies without resolving every result's external IDs."""
    data = await _request_json(
        "TMDB",
        "https://api.themoviedb.org/3/search/movie",
        params={"api_key": os.environ["TMDB_API_KEY"], "query": query},
    )
    return [
        _Movie(title=item["title"], year=(item.get("release_date") or "")[:4] or "Unknown year", tmdb_id=item["id"])
        for item in _result_list(data, "results", "TMDB")
        if isinstance(item.get("title"), str) and type(item.get("id")) is int
    ][:10]


async def _search_cinemeta(query: str) -> list[_Movie]:
    """Search Cinemeta's movie catalog without credentials."""
    data = await _request_json(
        "Cinemeta",
        f"https://v3-cinemeta.strem.io/catalog/movie/top/search={quote(query, safe='')}.json",
    )
    return [
        _Movie(title=item["name"], year=item.get("releaseInfo") or "Unknown year", imdb_id=item["id"])
        for item in _result_list(data, "metas", "Cinemeta")
        if item.get("type") == "movie"
        and isinstance(item.get("name"), str)
        and re.fullmatch(r"tt[0-9]+", str(item.get("id", "")))
    ][:10]


async def _get_tmdb_imdb_id(tmdb_id: int) -> str | None:
    """Fetch a movie's IMDb ID from TMDB."""
    key = os.getenv("TMDB_API_KEY")
    if not key:
        raise _ProviderError("TMDB is no longer configured. Please start a new search.")
    data = await _request_json(
        "TMDB",
        f"https://api.themoviedb.org/3/movie/{tmdb_id}/external_ids",
        params={"api_key": key},
    )
    imdb_id = data.get("imdb_id")
    return imdb_id if isinstance(imdb_id, str) and re.fullmatch(r"tt[0-9]+", imdb_id) else None
