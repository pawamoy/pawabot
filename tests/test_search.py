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

"""Regression tests for movie search and torrent selection."""

from __future__ import annotations

import asyncio
import re
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, Mock
from urllib.parse import parse_qs, urlsplit

import httpx2
import pytest
from telegram.ext import ConversationHandler

from pawabot._internal import callbacks, search
from pawabot._internal.search import _http, _ProviderError, torrentio
from pawabot._internal.search.models import _Movie, _MovieTorrent

if TYPE_CHECKING:
    from collections.abc import Callable

_HASH = "a" * 40


@pytest.fixture
def mock_http(monkeypatch: pytest.MonkeyPatch) -> Callable:
    """Replace only the HTTP transport, preserving request construction."""
    client_class = httpx2.AsyncClient

    def install(handler: Callable) -> None:
        monkeypatch.setattr(
            httpx2,
            "AsyncClient",
            lambda **kwargs: client_class(transport=httpx2.MockTransport(handler), **kwargs),
        )

    monkeypatch.delenv("OMDB_API_KEY", raising=False)
    monkeypatch.delenv("TMDB_API_KEY", raising=False)
    monkeypatch.delenv("TORRENTIO_BASE_URL", raising=False)
    return install


@pytest.fixture
def conversation(monkeypatch: pytest.MonkeyPatch) -> tuple[Any, Any]:
    """Set up an authorized chat without Telegram or database connections."""
    user = SimpleNamespace(
        id=42,
        username="tester",
        first_name="Tester",
        is_admin=False,
        has_privileges=lambda privileges: True,
        has_privilege=lambda privilege: True,
    )
    monkeypatch.setattr(callbacks._User, "get_with_id", lambda uid: user)
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=100),
        effective_user=user,
        effective_message=SimpleNamespace(text="1", reply_text=AsyncMock()),
    )
    context = SimpleNamespace(args=["Bunny"], user_data={}, bot=SimpleNamespace(send_message=AsyncMock()))
    return update, context


def test_torrentio_protocol_and_parsing(mock_http: Callable) -> None:
    """Parse a real-shaped stream, including trackers and collection file index."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path == "/stream/movie/tt1254207.json"
        assert request.headers["User-Agent"] == "pawabot"
        return httpx2.Response(
            200,
            json={
                "streams": [
                    {
                        "name": "Torrentio\n1080p",
                        "title": "Movie collection\nBunny.mkv\n👤 12 💾 856.01 MB ⚙️ Provider",
                        "infoHash": _HASH,
                        "fileIdx": 3,
                        "behaviorHints": {"filename": "Bunny.mkv"},
                        "sources": [
                            "tracker:https://tracker.example/announce?a=1&b=2",
                            "tracker:https://tracker.example/announce?a=1&b=2",
                            f"dht:{_HASH}",
                        ],
                    },
                ],
            },
        )

    mock_http(handler)
    (result,) = asyncio.run(torrentio._get_streams("tt1254207"))
    assert (result.quality, result.seeders, result.size) == ("1080p", 12, "856.01 MB")
    assert result.filename == "Bunny.mkv"
    assert result.file_index == 3
    params = parse_qs(urlsplit(result.magnet).query)
    assert params == {
        "xt": [f"urn:btih:{_HASH}"],
        "dn": ["Movie collection"],
        "tr": ["https://tracker.example/announce?a=1&b=2"],
    }


@pytest.mark.parametrize("file_index", [None, 0])
def test_trackerless_torrents(file_index: int | None) -> None:
    """Missing trackers and metadata remain usable without inventing seed counts."""
    result = torrentio._parse_stream({"infoHash": _HASH, "title": "Bunny", "fileIdx": file_index})
    assert result is not None
    assert result.seeders is None
    assert result.quality == "Unknown"
    assert result.file_index == file_index
    assert re.fullmatch(callbacks._MAGNET_RE, result.magnet)
    assert re.fullmatch(callbacks._MAGNET_RE, f"magnet:?xt=urn:btih:{_HASH}")


@pytest.mark.parametrize(
    "stream",
    [
        {"url": "https://debrid.example/movie.mp4"},
        {"infoHash": "invalid"},
        {"infoHash": _HASH, "fileIdx": -1},
        {"infoHash": _HASH, "fileIdx": True},
    ],
)
def test_unsupported_streams(stream: dict) -> None:
    """Do not reinterpret HTTP URLs or invalid file selections as torrents."""
    assert torrentio._parse_stream(stream) is None


@pytest.mark.parametrize(
    "response",
    [
        httpx2.Response(403, json={}),
        httpx2.Response(429, json={}),
        httpx2.Response(502, text="upstream unavailable"),
        httpx2.Response(200, text="<html>not JSON</html>"),
        httpx2.Response(200, json=[]),
        httpx2.Response(200, json={}),
        httpx2.Response(200, json={"streams": [None]}),
        httpx2.Response(200, json={"streams": [{"url": "https://debrid.example/movie"}]}),
    ],
)
def test_provider_errors_are_not_empty_results(mock_http: Callable, response: httpx2.Response) -> None:
    """Unavailable or incompatible providers are distinguishable from no matches."""
    mock_http(lambda request: response)
    with pytest.raises(_ProviderError):
        asyncio.run(torrentio._get_streams("tt1254207"))


def test_empty_torrent_results(mock_http: Callable) -> None:
    """A successful empty search is not a provider error."""
    mock_http(lambda request: httpx2.Response(200, json={"streams": []}))
    assert asyncio.run(torrentio._get_streams("tt1254207")) == []


@pytest.mark.parametrize("imdb_id", ["tt1254207:1:2", "imdb:tt1254207", "../manifest"])
def test_only_movie_ids_are_accepted(mock_http: Callable, imdb_id: str) -> None:
    """Reject episode IDs and malformed IDs before making a request."""
    handler = Mock()
    mock_http(handler)
    with pytest.raises(ValueError, match="movie IMDb ID"):
        asyncio.run(torrentio._get_streams(imdb_id))
    handler.assert_not_called()


def test_timeout_and_credential_redaction(mock_http: Callable) -> None:
    """Network errors must not reveal API keys embedded in request URLs."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout(f"request failed: {request.url}", request=request)

    mock_http(handler)
    with pytest.raises(_ProviderError, match="Could not reach") as error:
        asyncio.run(_http._request_json("OMDb", "https://example.test", params={"apikey": "private-key"}))
    assert "private-key" not in str(error.value)


def test_tmdb_resolves_only_selected_movie(mock_http: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    """Movie search does one request; selection adds one external-ID lookup."""
    monkeypatch.setenv("TMDB_API_KEY", "test-key")
    paths = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        paths.append(request.url.path)
        assert request.url.params["api_key"] == "test-key"
        if request.url.path == "/3/search/movie":
            return httpx2.Response(
                200,
                json={"results": [{"id": i, "title": f"Movie {i}", "release_date": "2008-01-01"} for i in range(20)]},
            )
        assert request.url.path == "/3/movie/1/external_ids"
        return httpx2.Response(200, json={"imdb_id": "tt1254207"})

    mock_http(handler)
    movies = asyncio.run(search._search_movies("Bunny"))
    assert len(movies) == 10
    assert paths == ["/3/search/movie"]
    assert movies[1].imdb_id is None
    assert asyncio.run(search._resolve_imdb_id(movies[1])) == "tt1254207"
    assert paths == ["/3/search/movie", "/3/movie/1/external_ids"]


def test_key_free_cinemeta_movie_search(mock_http: Callable) -> None:
    """Search escaped movie titles without requesting TV catalogs or credentials."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.host == "v3-cinemeta.strem.io"
        assert request.url.raw_path == b"/catalog/movie/top/search=A%2FB%20%26%20C.json"
        return httpx2.Response(
            200,
            json={
                "metas": [
                    {"type": "series", "id": "tt1234", "name": "TV"},
                    {"type": "movie", "id": "tt1254207", "name": "Bunny", "releaseInfo": "2008"},
                ],
            },
        )

    mock_http(handler)
    assert asyncio.run(search._search_movies("A/B & C")) == [_Movie("Bunny", "2008", "tt1254207")]


def test_omdb_failure_falls_back(mock_http: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    """An invalid configured key does not prevent key-free title lookup."""
    monkeypatch.setenv("OMDB_API_KEY", "test-key")
    hosts = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        hosts.append(request.url.host)
        if request.url.host == "www.omdbapi.com":
            assert request.url.params["type"] == "movie"
            return httpx2.Response(200, json={"Response": "False", "Error": "Invalid API key!"})
        return httpx2.Response(200, json={"metas": [{"type": "movie", "name": "Bunny", "id": "tt1254207"}]})

    mock_http(handler)
    assert asyncio.run(search._search_movies("Bunny"))[0].imdb_id == "tt1254207"
    assert hosts == ["www.omdbapi.com", "v3-cinemeta.strem.io"]


def test_metadata_no_results_vs_failure(mock_http: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    """Only successful empty responses produce 'no movies found'."""
    mock_http(lambda request: httpx2.Response(200, json={"metas": []}))
    assert asyncio.run(search._search_movies("missing")) == []
    monkeypatch.setenv("OMDB_API_KEY", "test-key")

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.host == "www.omdbapi.com":
            return httpx2.Response(401, json={})
        return httpx2.Response(200, json={"metas": []})

    mock_http(handler)
    with pytest.raises(_ProviderError, match="incomplete"):
        asyncio.run(search._search_movies("missing"))


@pytest.mark.parametrize("file_index", [None, 0, 3])
def test_movie_to_selected_torrent(
    conversation: tuple[Any, Any],
    monkeypatch: pytest.MonkeyPatch,
    file_index: int | None,
) -> None:
    """The chosen release reaches aria2 with its collection file selection."""
    update, context = conversation
    movies = AsyncMock(return_value=[_Movie("Bunny", "2008", "tt1254207")])
    torrents = [
        _MovieTorrent("First", f"magnet:?xt=urn:btih:{_HASH}", file_index=0),
        _MovieTorrent("Collection", f"magnet:?xt=urn:btih:{_HASH}", file_index=file_index, filename="Bunny.mkv"),
    ]
    streams = AsyncMock(return_value=torrents)
    monkeypatch.setattr(callbacks, "_search_movies", movies)
    monkeypatch.setattr(callbacks, "_search_torrents", streams)
    add = Mock(return_value=SimpleNamespace(gid="1234", status="active"))
    monkeypatch.setattr(callbacks.aria2p, "API", lambda: SimpleNamespace(add_magnet=add))
    assert asyncio.run(callbacks._search(update, context)) == callbacks._SELECTING_RESULT
    assert asyncio.run(callbacks._select_search_result(update, context)) == callbacks._SELECTING_TORRENT
    streams.assert_awaited_once_with("tt1254207")
    update.effective_message.text = "2"
    assert asyncio.run(callbacks._select_torrent(update, context)) == ConversationHandler.END
    add.assert_called_once_with(
        torrents[1].magnet,
        options={} if file_index is None else {"select-file": str(file_index + 1)},
    )
    assert not context.user_data["search_sessions"]
    assert "Bunny.mkv" in context.bot.send_message.call_args.kwargs["text"]


def test_restart_cancel_and_chat_isolation(conversation: tuple[Any, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """Failed searches and cancellation clear only this user's current chat."""
    update, context = conversation
    other_session = {"movies": [_Movie("Other")]}
    context.user_data["search_sessions"] = {100: {"movies": [_Movie("Old")]}, 200: other_session}
    monkeypatch.setattr(callbacks, "_search_movies", AsyncMock(side_effect=_ProviderError("Service unavailable")))
    assert asyncio.run(callbacks._search(update, context)) == ConversationHandler.END
    assert context.user_data["search_sessions"] == {200: other_session}
    context.user_data["search_sessions"][100] = {"torrents": [_MovieTorrent("Bunny", "magnet")]}
    assert asyncio.run(callbacks._cancel(update, context)) == ConversationHandler.END
    assert context.user_data["search_sessions"] == {200: other_session}


def test_direct_id_and_paging(conversation: tuple[Any, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """Direct movie IDs skip metadata and later pages download the displayed entry."""
    update, context = conversation
    context.args = ["tt1254207"]
    torrents = [_MovieTorrent(f"Movie {i}", f"magnet:{i}") for i in range(12)]
    monkeypatch.setattr(callbacks, "_search_torrents", AsyncMock(return_value=torrents))
    metadata = AsyncMock()
    monkeypatch.setattr(callbacks, "_search_movies", metadata)
    assert asyncio.run(callbacks._search(update, context)) == callbacks._SELECTING_TORRENT
    metadata.assert_not_awaited()
    update.effective_message.text = "Next"
    assert asyncio.run(callbacks._select_torrent(update, context)) == callbacks._SELECTING_TORRENT
    assert "Torrents 11-12 of 12" in context.bot.send_message.call_args.kwargs["text"]
    update.effective_message.text = "3"
    assert asyncio.run(callbacks._select_torrent(update, context)) == callbacks._SELECTING_TORRENT
    add = Mock(return_value="Added")
    monkeypatch.setattr(callbacks, "_add_movie_torrent", add)
    update.effective_message.text = "1"
    assert asyncio.run(callbacks._select_torrent(update, context)) == ConversationHandler.END
    add.assert_called_once_with(torrents[10])


def test_download_privilege_and_rpc_failure(conversation: tuple[Any, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """Unverified users cannot start downloads; RPC failures preserve the choice."""
    update, context = conversation
    torrent = _MovieTorrent("Bunny", "magnet")
    callbacks._search_data(100, context).update(torrents=[torrent], page=0)
    add = Mock(side_effect=OSError("connection lost"))
    monkeypatch.setattr(callbacks, "_add_movie_torrent", add)
    update.effective_user.has_privilege = lambda privilege: False
    assert asyncio.run(callbacks._select_torrent(update, context)) == callbacks._SELECTING_TORRENT
    add.assert_not_called()
    assert "Verified Downloader" in context.bot.send_message.call_args.kwargs["text"]
    update.effective_user.has_privilege = lambda privilege: True
    assert asyncio.run(callbacks._select_torrent(update, context)) == callbacks._SELECTING_TORRENT
    assert "Check its queue" in context.bot.send_message.call_args.kwargs["text"]
    assert callbacks._search_data(100, context)["torrents"] == [torrent]


def test_no_access_no_search(conversation: tuple[Any, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """The search entry point still enforces Downloader access."""
    update, context = conversation
    update.effective_user.has_privileges = lambda privileges: False
    _search_movies = AsyncMock()
    monkeypatch.setattr(callbacks, "_search_movies", _search_movies)
    asyncio.run(callbacks._search(update, context))
    _search_movies.assert_not_awaited()
    assert "required permissions" in context.bot.send_message.call_args.kwargs["text"]
