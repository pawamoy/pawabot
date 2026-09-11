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
from typing import TYPE_CHECKING

from pawabot._internal.search._http import _ProviderError
from pawabot._internal.search.metadata import _get_tmdb_imdb_id, _search_cinemeta, _search_omdb, _search_tmdb
from pawabot._internal.search.torrentio import (
    _get_streams as _search_torrents,  # noqa: F401 - internal search entry point
)

if TYPE_CHECKING:
    from pawabot._internal.search.models import _Movie


async def _search_movies(query: str) -> list[_Movie]:
    """Search configured metadata providers, then the key-free Cinemeta catalog."""
    providers = []
    if os.getenv("OMDB_API_KEY"):
        providers.append(_search_omdb)
    if os.getenv("TMDB_API_KEY"):
        providers.append(_search_tmdb)
    providers.append(_search_cinemeta)
    errors = []
    for provider in providers:
        try:
            movies = await provider(query)
        except _ProviderError as error:  # noqa: PERF203 - each provider must be able to fail independently
            errors.append(str(error))
        else:
            if movies:
                return movies[:10]
    if errors:
        raise _ProviderError("Movie search was incomplete. " + " ".join(errors))
    return []


async def _resolve_imdb_id(movie: _Movie) -> str | None:
    """Resolve only the movie selected by the user."""
    if movie.imdb_id:
        return movie.imdb_id
    if movie.tmdb_id is None:
        return None
    return await _get_tmdb_imdb_id(movie.tmdb_id)
