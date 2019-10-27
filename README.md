<!--
IMPORTANT:
  This file is generated from the template at 'scripts/templates/README.md'.
  Please update the template instead of this file.
-->

# pawabot
<!--
[![pipeline status](https://gitlab.com/pawamoy/pawabot/badges/master/pipeline.svg)](https://gitlab.com/pawamoy/pawabot/pipelines)
[![coverage report](https://gitlab.com/pawamoy/pawabot/badges/master/coverage.svg)](https://gitlab.com/pawamoy/pawabot/commits/master)
[![documentation](https://img.shields.io/readthedocs/pawabot.svg?style=flat)](https://pawabot.readthedocs.io/en/latest/index.html)
[![pypi version](https://img.shields.io/pypi/v/pawabot.svg)](https://pypi.org/project/pawabot/)
-->

A bot for many things: aria2 management, torrent sites crawling, media organization with filebot and plex.

This bot provides a command to search for torrents on the web, and let you select them for download.
There is a basic permission system allowing to manage multiple users for one bot.

## Requirements
pawabot requires Python 3.6 or above.

<details>
<summary>To install Python 3.6, I recommend using <a href="https://github.com/pyenv/pyenv"><code>pyenv</code></a>.</summary>

```bash
# install pyenv
git clone https://github.com/pyenv/pyenv ~/.pyenv

# setup pyenv (you should also put these three lines in .bashrc or similar)
export PATH="${HOME}/.pyenv/bin:${PATH}"
export PYENV_ROOT="${HOME}/.pyenv"
eval "$(pyenv init -)"

# install Python 3.6
pyenv install 3.6.8

# make it available globally
pyenv global system 3.6.8
```
</details>

## Installation
With `pip`:
```bash
python3.6 -m pip install pawabot
```

With [`pipx`](https://github.com/cs01/pipx):
```bash
# install pipx with the recommended method
curl https://raw.githubusercontent.com/cs01/pipx/master/get-pipx.py | python3

pipx install --python python3.6 pawabot
```

## Setup
1. Create your Telegram bot account by talking to the `@godfather` bot.
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




## Screenshots
/start | /help | /search
------ | ----- | -------
![start](img/start.jpg) | ![help](img/help.jpg) | ![search](img/search.jpg)
