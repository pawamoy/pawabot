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
python3.6 -m pip install --user pipx

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
{{ command_line_help }}
```

{% if commands %}Commands:
{% for command in commands %}
- [`{{ command.name }}`](#{{ command.name }}){% endfor %}

{% for command in commands %}
### `{{ command.name }}`
```
{{ command.help }}
```

{% include "command_" + command.name.replace("-", "_") + "_extra.md" ignore missing %}
{% endfor %}{% endif %}

## Screenshots
/start | /help | /search
------ | ----- | -------
![start](img/start.jpg) | ![help](img/help.jpg) | ![search](img/search.jpg)
