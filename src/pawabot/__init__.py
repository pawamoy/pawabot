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

"""pawabot package.

My personal Telegram bot: aria2 management, torrent sites crawling, media organization with mvodb and Plex, etc.
"""

from pawabot._internal.callbacks import STATE
from pawabot._internal.cli import get_parser, main
from pawabot._internal.privileges import Privileges
from pawabot._internal.torrents import TPB, Search, ThePirateBay, Torrent
from pawabot._internal.utils import get_cache_dir, get_config_dir, get_data_dir, get_runtime_dir

__all__ = [
    "STATE",
    "TPB",
    "Privileges",
    "Search",
    "ThePirateBay",
    "Torrent",
    "get_cache_dir",
    "get_config_dir",
    "get_data_dir",
    "get_parser",
    "get_runtime_dir",
    "main",
]
