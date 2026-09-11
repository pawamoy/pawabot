# pawabot

[![ci](https://github.com/pawamoy/pawabot/workflows/ci/badge.svg)](https://github.com/pawamoy/pawabot/actions?query=workflow%3Aci)
[![documentation](https://img.shields.io/badge/docs-zensical-FF9100.svg?style=flat)](https://pawamoy.github.io/pawabot/)
[![pypi version](https://img.shields.io/pypi/v/pawabot.svg)](https://pypi.org/project/pawabot/)
[![gitter](https://img.shields.io/badge/matrix-chat-4DB798.svg?style=flat)](https://app.gitter.im/#/room/#pawabot:gitter.im)

My personal Telegram bot: aria2 management, torrent sites crawling, media organization with mvodb and Plex, etc.

This bot provides a command to search for torrents on the web, and let you select them for download.
There is a basic permission system allowing to manage multiple users for one bot.

## Installation

```bash
pip install pawabot
```

With [`uv`](https://docs.astral.sh/uv/):

```bash
uv tool install pawabot
```

## Setup

1. Create your Telegram bot account by talking to the `@botfather` bot.
2. Write your bot token in `~/.config/pawabot/bot_token.txt`,
   or set and export the environment variable `BOT_TOKEN`.
3. Register your Telegram main account as administrator in the database with:

```
pawabot create-admin -i MY_TG_ID -u MY_TG_USERNAME
```

## Usage

```
usage: pawabot [-h] [-L {TRACE,DEBUG,INFO,SUCCESS,WARNING,ERROR,CRITICAL}]
               ...

optional arguments:
  -h, --help            show this help message and exit

Commands:

    run                 Run the bot.
    create-admin        Create an administrator in the database.
    create-user         Create a user in the database.
    list-users          List registered users.

Global options:
  -L {TRACE,DEBUG,INFO,SUCCESS,WARNING,ERROR,CRITICAL}, --log-level {TRACE,DEBUG,INFO,SUCCESS,WARNING,ERROR,CRITICAL}
                        Log level to use
```

Commands:

- [`create-admin`](#create-admin)
- [`create-user`](#create-user)
- [`list-users`](#list-users)
- [`run`](#run)
- [`search`](#search)

### `create-admin`

```
usage: pawabot create-admin [-h] [-i UID] [-u USERNAME]

Create an administrator in the database.

optional arguments:
  -h, --help            Show this help message and exit.
  -i UID, --uid UID     Telegram user id.
  -u USERNAME, --username USERNAME
                        Telegram user name.
```

### `create-user`

```
usage: pawabot create-user [-h] [-i UID] [-u USERNAME] [-a]

Create a user in the database.

optional arguments:
  -h, --help            Show this help message and exit.
  -i UID, --uid UID     Telegram user id.
  -u USERNAME, --username USERNAME
                        Telegram user name.
  -a, --admin           Give admin access.
```

### `list-users`

```
usage: pawabot list-users [-h]

List registered users.

optional arguments:
  -h, --help  Show this help message and exit.
```

### `run`

```
usage: pawabot run [-h]

Run the bot.

optional arguments:
  -h, --help  Show this help message and exit.
```

### `search`

```
/search <movie name>
/search <imdb_id>            (e.g. /search tt1254207)
/cancel
```

In Telegram, search for a movie, choose its number, then choose a torrent to download with aria2. Results show release quality, seeders and size when available. Use Next/Previous to browse torrents, `/cancel` to leave, or `/search` to start again. Only movies are supported.

Title search tries OMDb when `OMDB_API_KEY` is set, then TMDB when `TMDB_API_KEY` is set, and finally Cinemeta (no API key needed). TMDB IMDb IDs are resolved only after selecting a movie. Searching by IMDb ID skips title lookup.

Torrentio uses its public Stremio JSON interface; no Stremio installation or debrid account is required. Set `TORRENTIO_BASE_URL` to override its base URL (default: `https://torrentio.strem.fun`, without `/manifest.json`). The endpoint must return raw torrent streams; HTTP/debrid-only results are not downloadable through this search flow. Provider failures are reported separately from empty results.

Searching requires the Downloader privilege. Starting a download additionally requires Verified Downloader, or administrator access. The bot preserves Torrentio's file selection for movies inside multi-file torrents. Administrator approval requests are not implemented; users without Verified Downloader must ask an administrator for access.

The implementation is grouped under `src/pawabot/_internal/search/`:

- `__init__.py`: the search entry points and metadata-provider fallback order used by the bot.
- `models.py`: shared movie and torrent data.
- `metadata.py`: OMDb, TMDB, and Cinemeta clients, including IMDb ID resolution.
- `torrentio.py`: Torrentio requests and conversion of stream responses into torrents.
- `_http.py`: shared JSON requests, response validation, and provider errors.

Telegram conversations and the aria2 download handoff live in `callbacks.py`.
