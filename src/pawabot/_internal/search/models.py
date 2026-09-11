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

from dataclasses import dataclass


@dataclass(frozen=True)
class _Movie:
    """A movie candidate, with IMDb resolution deferred when necessary."""

    title: str
    year: str = "Unknown year"
    imdb_id: str | None = None
    tmdb_id: int | None = None


@dataclass(frozen=True)
class _MovieTorrent:
    """A downloadable movie, independent of the search provider."""

    title: str
    magnet: str
    quality: str = "Unknown"
    seeders: int | None = None
    size: str = "Unknown"
    file_index: int | None = None
    filename: str | None = None
