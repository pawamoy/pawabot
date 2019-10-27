import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from loguru import logger

from .utils import get_cache_dir

CACHE_DIR = get_cache_dir()


class Torrent:
    def __init__(self, title, magnet, url, seeders, leechers, date, size, uploader):
        self.title = title
        self.magnet = magnet
        self.url = url
        self.seeders = seeders
        self.leechers = leechers
        self.date = date
        self.size = size
        self.uploader = uploader

    def as_dict(self):
        return dict(
            title=self.title,
            magnet=self.magnet,
            url=self.url,
            seeders=self.seeders,
            leechers=self.leechers,
            date=self.date,
            size=self.size,
            uploader=self.uploader,
        )


class Search:
    def __init__(self, user_id, proxy, pattern, results, pages):
        self.user_id = user_id
        self.proxy = proxy
        self.pattern = pattern
        self.results = results
        self.pages = pages

    def save(self):
        with open(CACHE_DIR / f"torrent-search-{self.user_id}.json", "w") as fp:
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

    def update(self, search):
        if self.proxy != search.proxy or self.pattern != search.pattern or self.user_id != search.user_id:
            raise ValueError
        self.results.extend(search.results)
        self.pages = list(sorted(set(self.pages + search.pages)))
        self.save()

    @staticmethod
    def load(user_id):
        with open(CACHE_DIR / f"torrent-search-{user_id}.json", "r") as fp:
            data = json.load(fp)
        return Search(
            data["user_id"],
            data["proxy"],
            data["pattern"],
            [Torrent(**item) for item in data["results"]],
            data["pages"],
        )


class ThePirateBay:
    MIRROR_LIST_PAGES = ["https://proxybay.lat", "https://proxybay.github.io"]

    def __init__(self, mirrors=None, limit=5):
        if not mirrors:
            # logging.info("No mirrors provided")
            mirrors = self.get_mirror_list()[:limit]
        self.mirrors = [m.rstrip("/") for m in mirrors]
        self.search_urls = [""] * len(mirrors)

    def get_mirror_list(self):
        html_page = None

        for mirror_list_page in self.MIRROR_LIST_PAGES:
            try:
                # logging.info("Fetching mirrors from " + mirror_list_page)
                html_page = requests.get(mirror_list_page)
            except requests.ConnectTimeout:
                # logging.info("Timeout")
                continue
            else:
                break

        if html_page is None:
            raise LookupError

        soup = BeautifulSoup(html_page.text, features="html.parser")
        rows = soup.find(id="proxyList").find_all("tr")[1:]

        return [row.find("a")["href"] for row in rows]

    @staticmethod
    def get_search_url(mirror):
        # url/search/PATTERN/PAGE/ORDER/CATEGORY
        soup = BeautifulSoup(requests.get(mirror, timeout=5).text, features="html.parser")
        return f"{mirror}/{soup.form['action'].lstrip('/')}"

    def search(self, user_id, pattern, page=1):
        for i, mirror in enumerate(self.mirrors):
            logger.info("Fetching torrents from " + mirror)
            if not self.search_urls[i]:
                try:
                    self.search_urls[i] = self.get_search_url(mirror)
                except (requests.exceptions.SSLError, TypeError) as error:
                    logger.error(f"Error when requesting home page of {mirror}")
                    logger.opt(exception=True).trace(error)
                    continue
                except (requests.ConnectTimeout, requests.ReadTimeout):
                    logger.info("Timeout")
                    continue
            search_url = self.search_urls[i]

            page_param = "&page=" + str(page - 1)
            try:
                html_page = requests.get(search_url + f"?q={pattern}{page_param}", timeout=5)
            except (requests.ConnectTimeout, requests.ReadTimeout):
                logger.info("Timeout")
                continue

            soup = BeautifulSoup(html_page.text, features="html.parser")

            torrents = []
            rows = soup.find_all("tr")[1:]

            for row in rows:
                link = row.find("a", class_="detLink")
                seeders, leechers = [int(td.text) for td in row.find_all("td")[2:]]
                extra = row.font.text.split(", ")

                torrents.append(
                    Torrent(
                        title=link.text,
                        magnet=row.find("a", href=re.compile(r"^magnet:\?"))["href"],
                        url=mirror + "/" + link["href"].lstrip("/"),
                        seeders=seeders,
                        leechers=leechers,
                        date=extra[0][len("Uploaded ") :],
                        size=extra[1][len("Size ") :],
                        uploader=extra[2][len("ULed by ") :],
                    )
                )

            if torrents:
                return Search(user_id, mirror, pattern, torrents, [page])
            else:
                logger.info("No results")
                pass

        raise LookupError


TPB = ThePirateBay()
