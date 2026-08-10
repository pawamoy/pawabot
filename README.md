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
