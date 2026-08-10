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
