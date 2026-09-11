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
from typing import Any
from urllib.parse import urlencode

from pawabot._internal.search._http import _ProviderError, _request_json, _result_list
from pawabot._internal.search.models import _MovieTorrent


async def _get_streams(imdb_id: str) -> list[_MovieTorrent]:
    """Look up raw movie torrents using the Stremio stream protocol."""
    if not re.fullmatch(r"tt[0-9]+", imdb_id):
        raise ValueError("Expected a movie IMDb ID such as tt1254207.")
    base = os.getenv("TORRENTIO_BASE_URL", "https://torrentio.strem.fun").rstrip("/")
    data = await _request_json("Torrentio", f"{base}/stream/movie/{imdb_id}.json")
    streams = _result_list(data, "streams", "Torrentio")
    torrents = [torrent for stream in streams if (torrent := _parse_stream(stream)) is not None]
    if streams and not torrents:
        raise _ProviderError("Torrentio returned no usable torrent links. Check the provider configuration.")
    return torrents


def _parse_stream(stream: dict[str, Any]) -> _MovieTorrent | None:
    """Convert a raw torrent stream; HTTP/debrid streams are not magnets."""
    info_hash = stream.get("infoHash")
    if not isinstance(info_hash, str) or not re.fullmatch(r"[a-fA-F0-9]{40}", info_hash):
        return None
    title = stream.get("title") or "Unknown release"
    name = stream.get("name") or ""
    hints = stream.get("behaviorHints") or {}
    if not isinstance(title, str) or not isinstance(name, str) or not isinstance(hints, dict):
        return None
    filename = hints.get("filename")
    file_index = stream.get("fileIdx")
    if file_index is not None and (type(file_index) is not int or file_index < 0):
        return None
    sources = stream.get("sources") or []
    if not isinstance(sources, list):
        return None
    trackers = list(
        dict.fromkeys(
            source.removeprefix("tracker:")
            for source in sources
            if isinstance(source, str) and source.startswith(("tracker:udp://", "tracker:http://", "tracker:https://"))
        ),
    )
    release = title.splitlines()[0]
    parameters = [("dn", release), *(("tr", tracker) for tracker in trackers)]
    magnet = f"magnet:?xt=urn:btih:{info_hash.lower()}&{urlencode(parameters)}"
    seeders = re.search(r"👤\s*([0-9]+)", title)
    size = re.search(r"💾\s*([0-9.,]+\s*[KMGT]?B)", title, re.IGNORECASE)
    quality = name.partition("\n")[2].strip() or "Unknown"
    return _MovieTorrent(
        title=release,
        magnet=magnet,
        quality=quality,
        seeders=int(seeders[1]) if seeders else None,
        size=size[1] if size else "Unknown",
        file_index=file_index,
        filename=filename if isinstance(filename, str) else None,
    )
