import json
import re
from collections import namedtuple

import requests
from bs4 import BeautifulSoup

Torrent = namedtuple("Torrent", "title magnet url seeders leechers date size uploader")


def get_torrents(pattern, page=None, proxy=None):
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

    # url/search/PATTERN/PAGE/ORDER/CATEGORY

    if not proxy:
        proxy = "https://pirateproxy.ch"

    if isinstance(page, int):
        page = "&page=" + str(page)
    else:
        page = ""

    soup = BeautifulSoup(requests.get(proxy).text, features="lxml")
    search_url = f"{proxy.rstrip('/')}/{soup.form['action'].lstrip('/')}?q={pattern}{page}"
    print(search_url)
    soup = BeautifulSoup(requests.get(search_url).text, features="lxml")

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
                url=proxy.rstrip("/") + "/" + link["href"].lstrip("/"),
                seeders=seeders,
                leechers=leechers,
                date=extra[0][len("Uploaded ") :],
                size=extra[1][len("Size ") :],
                uploader=extra[2][len("ULed by ") :],
            )
        )

    return torrents


def save_torrents(pattern, torrents, uid):
    with open(f"torrent-search-{uid}.json", "w") as fp:
        json.dump({"pattern": pattern, "torrents": torrents}, fp, indent=2)


def update_saved_torrents(pattern, new_torrents, uid):
    try:
        pattern, current_torrents = load_torrents(uid)
    except FileNotFoundError:
        current_torrents = []
    current_torrents.extend(new_torrents)
    save_torrents(pattern, current_torrents, uid)
    return current_torrents


def load_torrents(uid):
    with open(f"torrent-search-{uid}.json", "r") as fp:
        data = json.load(fp)
        return data["pattern"], [Torrent(*item) for item in data["torrents"]]
