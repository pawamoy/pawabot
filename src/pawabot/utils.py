import json
import logging
import re
from collections import namedtuple
from functools import wraps
from pathlib import Path
from tempfile import mktemp

import requests
from bs4 import BeautifulSoup

from .database import Permission, User, session


def restricted_command(permissions):
    def decorator(func):
        @wraps(func)
        def wrapped(update, context, *args, **kwargs):
            user_id = update.effective_user.id
            db_user = session.query(User).filter(User.uid == user_id).first()

            if not db_user:
                deny_access(update, context)
                return

            if db_user.username != update.effective_user.username:
                db_user.username = update.effective_user.username
                session.commit()

            if not db_user.is_owner:
                db_user_perms = session.query(Permission.permission).filter(Permission.user_id == user_id)

                if not set(permissions).issubset(set(db_user_perms)):
                    deny_access(update, context, func.__name__)
                    return

            return func(update, context, *args, **kwargs)

        return wrapped

    return decorator


def deny_access(update, context, func_name):
    logging.warning(
        f"Unauthorized access denied for {update.effective_user.username} ({update.effective_user.id}) "
        f"on function {func_name}"
    )
    context.bot.send_message(
        chat_id=update.message.chat_id,
        text="Sorry, you don't have the required permissions to do that."
        "Try to contact the administrator of this bot.",
    )


Torrent = namedtuple("Torrent", "title magnet url seeders leechers date size uploader")


def get_torrents(pattern, proxy=None):
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

    soup = BeautifulSoup(requests.get(proxy).text, features="lxml")
    search_url = f"{proxy.rstrip('/')}/{soup.form['action'].lstrip('/')}?q={pattern}"
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


def save_torrents(torrents, uid):
    with open(f"torrent-search-{uid}.json", "w") as fp:
        json.dump(torrents, fp, indent=2)


def update_saved_torrents(new_torrents, uid):
    try:
        current_torrents = load_torrents(uid)
    except FileNotFoundError:
        current_torrents = []
    current_torrents.extend(new_torrents)
    save_torrents(new_torrents, uid)


def load_torrents(uid):
    with open(f"torrent-search-{uid}.json", "r") as fp:
        return [Torrent(*item) for item in json.load(fp)]
