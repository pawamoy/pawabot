import json
import re

import requests
from bs4 import BeautifulSoup


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
        with open(f"torrent-search-{self.user_id}.json", "w") as fp:
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
        with open(f"torrent-search-{user_id}.json", "r") as fp:
            data = json.load(fp)
        return Search(
            data["user_id"],
            data["proxy"],
            data["pattern"],
            [Torrent(**item) for item in data["results"]],
            data["pages"],
        )


class ThePirateBay:
    def __init__(self, proxy=None):
        # https://pirateproxy.ch
        # https://tpb6.ukpass.co
        # https://tpbprox.com
        # https://thepiratebay.unblockthe.net
        # https://piratebayblocked.com
        # https://cruzing.xyz
        # https://ikwilthepiratebay.org
        # https://thepiratebay-org.prox3.info
        # https://uj3wazyk5u4hnvtk.onion.pet
        # https://uj3wazyk5u4hnvtk.onion.ly/
        # https://thepiratebay.vip
        # https://tpb.cloud.louifox.house
        if not proxy:
            proxy = "https://pirateproxy.ch"
        self.proxy = proxy

        self.search_url = None

    def get_search_url(self):
        # url/search/PATTERN/PAGE/ORDER/CATEGORY
        soup = BeautifulSoup(requests.get(self.proxy).text, features="lxml")
        return f"{self.proxy.rstrip('/')}/{soup.form['action'].lstrip('/')}"

    def search(self, user_id, pattern, page=1):
        if not self.search_url:
            self.search_url = self.get_search_url()

        page_param = "&page=" + str(page - 1)
        soup = BeautifulSoup(requests.get(self.search_url + f"?q={pattern}{page_param}").text, features="lxml")

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
                    url=self.proxy.rstrip("/") + "/" + link["href"].lstrip("/"),
                    seeders=seeders,
                    leechers=leechers,
                    date=extra[0][len("Uploaded ") :],
                    size=extra[1][len("Size ") :],
                    uploader=extra[2][len("ULed by ") :],
                )
            )

        return Search(user_id, self.proxy, pattern, torrents, [page])


TPB = ThePirateBay()
