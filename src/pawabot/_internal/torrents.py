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

import json
import re
from typing import Any

import httpx2
from bs4 import BeautifulSoup
from loguru import logger

from pawabot._internal.utils import get_cache_dir

CACHE_DIR = get_cache_dir()


class Torrent:
    def __init__(
        self,
        *,
        title: str,
        magnet: str,
        url: str,
        seeders: int,
        leechers: int,
        date: str,
        size: str,
        uploader: str,
    ) -> None:
        self.title = title
        self.magnet = magnet
        self.url = url
        self.seeders = seeders
        self.leechers = leechers
        self.date = date
        self.size = size
        self.uploader = uploader

    def as_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "magnet": self.magnet,
            "url": self.url,
            "seeders": self.seeders,
            "leechers": self.leechers,
            "date": self.date,
            "size": self.size,
            "uploader": self.uploader,
        }


class Search:
    def __init__(self, user_id: int, proxy: str, pattern: str, results: list[Torrent], pages: list[int]) -> None:
        self.user_id = user_id
        self.proxy = proxy
        self.pattern = pattern
        self.results = results
        self.pages = pages

    def save(self) -> None:
        with CACHE_DIR.joinpath(f"torrent-search-{self.user_id}.json").open("w") as fp:
            json.dump(
                {
                    "user_id": self.user_id,
                    "proxy": self.proxy,
                    "pattern": self.pattern,
                    "results": [t.as_dict() for t in self.results],
                    "pages": self.pages,
                },
                fp,
            )

    def update(self, search: Search) -> None:
        if self.proxy != search.proxy or self.pattern != search.pattern or self.user_id != search.user_id:
            raise ValueError
        self.results.extend(search.results)
        self.pages = sorted(set(self.pages + search.pages))
        self.save()

    @staticmethod
    def load(user_id: int) -> Search:
        with CACHE_DIR.joinpath(f"torrent-search-{user_id}.json").open() as fp:
            data = json.load(fp)
        return Search(
            data["user_id"],
            data["proxy"],
            data["pattern"],
            [Torrent(**item) for item in data["results"]],
            data["pages"],
        )


class ThePirateBay:
    MIRROR_LIST_PAGES = ("https://proxybay.lat", "https://proxybay.github.io")

    def __init__(self, mirrors: list[str] | None = None, limit: int = 5) -> None:
        if not mirrors:
            # logging.info("No mirrors provided")
            mirrors = self.get_mirror_list()[:limit]
        self.mirrors = [m.rstrip("/") for m in mirrors]
        self.search_urls = [""] * len(mirrors)

    def get_mirror_list(self) -> list[str]:
        html_page = None

        for mirror_list_page in self.MIRROR_LIST_PAGES:
            try:
                # logging.info("Fetching mirrors from " + mirror_list_page)
                html_page = httpx2.get(mirror_list_page)
            except httpx2.ConnectTimeout:  # noqa: PERF203
                # logging.info("Timeout")
                continue
            else:
                break

        if html_page is None:
            raise LookupError

        soup = BeautifulSoup(html_page.text, features="html.parser")
        rows = soup.find(id="proxyList").find_all("tr")[1:]  # ty:ignore

        return [row.find("a")["href"] for row in rows]  # ty:ignore

    @staticmethod
    def get_search_url(mirror: str) -> str:
        # url/search/PATTERN/PAGE/ORDER/CATEGORY
        soup = BeautifulSoup(httpx2.get(mirror, timeout=5).text, features="html.parser")
        form = soup.form
        if form is None:
            return mirror
        action = form.get("action", "")
        if isinstance(action, str):
            return f"{mirror}/{action.lstrip('/')}"
        return mirror

    def search(self, user_id: int, pattern: str, page: int = 1) -> Search:
        for i, mirror in enumerate(self.mirrors):
            logger.info("Fetching torrents from " + mirror)
            if not self.search_urls[i]:
                try:
                    self.search_urls[i] = self.get_search_url(mirror)
                except (httpx2.ConnectError, TypeError) as error:
                    logger.error(f"Error when requesting home page of {mirror}")
                    logger.opt(exception=True).trace(error)
                    continue
                except (httpx2.ConnectTimeout, httpx2.ReadTimeout):
                    logger.info("Timeout")
                    continue
            search_url = self.search_urls[i]

            page_param = "&page=" + str(page - 1)
            try:
                html_page = httpx2.get(search_url + f"?q={pattern}{page_param}", timeout=5)
            except (httpx2.ConnectTimeout, httpx2.ReadTimeout):
                logger.info("Timeout")
                continue

            soup = BeautifulSoup(html_page.text, features="html.parser")

            torrents = []
            rows = soup.find_all("tr")[1:]

            for row in rows:
                link = row.find("a", class_="detLink")
                seeders, leechers = [int(td.text) for td in row.find_all("td")[2:]]
                extra = row.font.text.split(", ")  # ty:ignore

                torrents.append(
                    Torrent(
                        title=link.text,  # ty:ignore
                        magnet=row.find("a", href=re.compile(r"^magnet:\?"))["href"],  # ty:ignore
                        url=mirror + "/" + link["href"].lstrip("/"),  # ty:ignore
                        seeders=seeders,
                        leechers=leechers,
                        date=extra[0][len("Uploaded ") :],
                        size=extra[1][len("Size ") :],
                        uploader=extra[2][len("ULed by ") :],
                    ),
                )

            if torrents:
                return Search(user_id, mirror, pattern, torrents, [page])
            logger.info("No results")

        raise LookupError


TPB = ThePirateBay()
