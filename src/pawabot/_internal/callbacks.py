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

from __future__ import annotations

import asyncio
import random
import re
from textwrap import dedent
from typing import TYPE_CHECKING, Any

import aria2p
from loguru import logger
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.ext import ConversationHandler

from pawabot._internal.database import _User
from pawabot._internal.decorators import (
    _require_access,
    _require_admin,
    _require_privileges,
)
from pawabot._internal.privileges import _Privileges
from pawabot._internal.search import _ProviderError, _resolve_imdb_id, _search_movies, _search_torrents

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

    from pawabot._internal.search.models import _Movie, _MovieTorrent

# Conversation state is scoped to both the Telegram user and chat.
_SELECTING_RESULT, _SELECTING_TORRENT = range(2)
_SEARCH_PAGE_SIZE = 10


async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    effective_user = update.effective_user
    effective_chat = update.effective_chat
    if effective_user is None or effective_chat is None:
        return
    tg_user = effective_user
    logger.info(f"{tg_user.username} ({tg_user.id}) called /start")

    db_user = _User.get_with_id(tg_user.id)

    if not db_user:
        text = dedent(
            f"""
            Hi @{tg_user.username}

            Sorry, but you have not been granted access to my commands.
            Please contact my administrator.
            """,
        )
    else:
        text = dedent(
            f"""
            Nice to meet you, {tg_user.username}!

            I'm some kind of an assistant bot. I'll help you search and find
            torrents, select them for download and re-organize the downloaded
            files with filebot! I'll ask for confirmations and stuff, I hope
            you don't mind me sending you a few messages sometimes!

            Type the command /help to learn how to use my commands!
            """,
        )

    await context.bot.send_message(chat_id=effective_chat.id, text=text)


@_require_access
async def _help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    effective_user = update.effective_user
    effective_chat = update.effective_chat
    if effective_user is None or effective_chat is None:
        return
    user = effective_user
    logger.info(f"{user.username} ({user.id}) called /help")
    text = dedent(
        """
        /start - To get an introduction.
        /help - To print this help.
        /requestAccess - To request access to my commands.
        /myID - To show your Telegram ID.
        /myPrivileges - To show your current permissions.
        /search - To search for movies and their torrents.
        /grant - To grant a permission to a user.
        /revoke - To revoke a permission to a user.
    """,
    )

    await context.bot.send_message(chat_id=effective_chat.id, text=text, parse_mode=ParseMode.MARKDOWN)


@_require_access
async def _my_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    effective_user = update.effective_user
    effective_chat = update.effective_chat
    if effective_user is None or effective_chat is None:
        return
    user = effective_user
    logger.info(f"{user.username} ({user.id}) called /myID")
    await context.bot.send_message(chat_id=effective_chat.id, text=str(user.id))


@_require_privileges([])
async def _my_privileges(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    effective_user = update.effective_user
    effective_chat = update.effective_chat
    if effective_user is None or effective_chat is None:
        return
    user = effective_user
    logger.info(f"{user.username} ({user.id}) called /myPrivileges")
    db_user = _User.get_with_id(user.id)

    text = []
    if db_user:
        if db_user.is_admin:
            text.append("You are an administrator: you have full access to all commands.\n")
        privileges = list(db_user.privileges) if db_user else []
        if privileges:
            text.append("\n" + "\n".join(privileges))
        else:
            text.append("You have zero privileges.")
    else:
        text.append("You do not have access to my commands.")

    await context.bot.send_message(chat_id=effective_chat.id, text="".join(text))


async def _request_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    effective_user = update.effective_user
    effective_chat = update.effective_chat
    if effective_user is None or effective_chat is None:
        return
    tg_user = effective_user
    logger.info(f"{tg_user.username} ({tg_user.id}) called /requestAccess")

    user = _User.get_with_id(tg_user.id)

    if not user:
        _User.create(tg_user.id, tg_user.username)
        await context.bot.send_message(
            chat_id=effective_chat.id,
            text="I received your request. Please wait for feedback.",
        )
    else:
        await context.bot.send_message(
            chat_id=effective_chat.id,
            text=f"I already know you {tg_user.username}! No need to request access!",
        )


@_require_admin
async def _grant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    effective_user = update.effective_user
    effective_chat = update.effective_chat
    if effective_user is None or effective_chat is None:
        return
    tg_user = effective_user
    logger.info(f"{tg_user.username} ({tg_user.id}) called /grant")

    if not context.args or len(context.args) != 2:  # noqa: PLR2004
        await context.bot.send_message(
            chat_id=effective_chat.id,
            text="Usage is /grant <ID_OR_USERNAME> <PERMISSION>",
        )
        return

    permission = context.args[1]
    user = _User.get(context.args[0])

    if not user:
        try:
            uid = int(context.args[0])
        except ValueError:
            await context.bot.send_message(
                chat_id=effective_chat.id,
                text="I don't know that user, please ask them to send '/requestAccess' to me.",
            )
            return
        else:
            user = _User.create(uid)

    if user.has_perm(permission):
        await context.bot.send_message(
            chat_id=effective_chat.id,
            text=f"User {user.username} ({user.uid}) already has permission '{permission}'.",
        )
        return

    user.grant(permission)
    await context.bot.send_message(
        chat_id=effective_chat.id,
        text=f"Done! User {user.username} ({user.uid}) now has permission '{permission}'.",
    )

    if effective_user.id != user.uid:
        await context.bot.send_message(
            chat_id=user.uid,
            text=f"Hi! You've been granted the permission '{permission}' "
            f"just now by {effective_user.username} on "
            f"the bot called '{context.bot.username}'. "
            f"If you don't know what this means, just ignore this message!",
        )


@_require_admin
async def _revoke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    effective_user = update.effective_user
    effective_chat = update.effective_chat
    if effective_user is None or effective_chat is None:
        return
    if not context.args or len(context.args) != 2:  # noqa: PLR2004
        await context.bot.send_message(
            chat_id=effective_chat.id,
            text="Usage is /revoke <ID_OR_USERNAME> <PERMISSION>",
        )
        return

    permission = context.args[1]
    user = _User.get(context.args[0])

    if not user:
        try:
            uid = int(context.args[0])
        except ValueError:
            await context.bot.send_message(
                chat_id=effective_chat.id,
                text="I don't know that user, please ask them to send '/requestAccess' to me.",
            )
            return
        else:
            user = _User.create(uid)

    if not user.has_perm(permission):
        await context.bot.send_message(
            chat_id=effective_chat.id,
            text=f"User {user.username} ({user.uid}) does not have permission '{permission}'.",
        )
        return

    user.revoke(permission)
    await context.bot.send_message(
        chat_id=effective_chat.id,
        text=f"Done! User {user.username} ({user.uid}) just lost permission '{permission}'.",
    )

    if effective_user.id != user.uid:
        await context.bot.send_message(
            chat_id=user.uid,
            text=f"Hi! You've been revoked the permission '{permission}' "
            f"just now by {effective_user.username} on "
            f"the bot called '{context.bot.username}'. "
            f"If you don't know what this means, just ignore this message!",
        )


def _search_data(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> dict[str, Any]:
    if context.user_data is None:
        return {}
    return context.user_data.setdefault("search_sessions", {}).setdefault(chat_id, {})


def _clear_search(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data is not None:
        context.user_data.get("search_sessions", {}).pop(chat_id, None)


def _selection(text: str, count: int) -> int | None:
    if not re.fullmatch(r"[0-9]{1,3}", text):
        return None
    number = int(text)
    return number - 1 if 1 <= number <= count else None


def _selection_keyboard(count: int) -> ReplyKeyboardMarkup:
    numbers = [str(i) for i in range(1, count + 1)]
    return ReplyKeyboardMarkup(
        [numbers[i : i + 5] for i in range(0, count, 5)] + [["/cancel"]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )


@_require_privileges([_Privileges.DOWNLOADER])
async def _search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Find a movie by title or IMDb ID, then choose a torrent."""
    if update.effective_chat is None:
        return ConversationHandler.END
    chat_id = update.effective_chat.id
    _clear_search(chat_id, context)
    query = " ".join(context.args or []).strip()
    if not query:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Usage: /search <movie name> or /search tt1254207",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END
    if re.fullmatch(r"tt[0-9]+", query):
        return await _search_by_imdb_id(chat_id, context, query)
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Searching movies for '{query[:200]}'...",
        reply_markup=ReplyKeyboardRemove(),
    )
    try:
        movies = await _search_movies(query)
    except _ProviderError as error:
        await context.bot.send_message(chat_id=chat_id, text=str(error))
        return ConversationHandler.END
    if not movies:
        await context.bot.send_message(chat_id=chat_id, text="No movies found. Try a different title or an IMDb ID.")
        return ConversationHandler.END
    _search_data(chat_id, context)["movies"] = movies
    await _display_search_results(chat_id, context, movies)
    return _SELECTING_RESULT


async def _search_by_imdb_id(chat_id: int, context: ContextTypes.DEFAULT_TYPE, imdb_id: str) -> int:
    await context.bot.send_message(
        chat_id=chat_id,
        text="Searching torrents...",
        reply_markup=ReplyKeyboardRemove(),
    )
    try:
        torrents = await _search_torrents(imdb_id)
    except _ProviderError as error:
        _clear_search(chat_id, context)
        await context.bot.send_message(chat_id=chat_id, text=str(error))
        return ConversationHandler.END
    if not torrents:
        _clear_search(chat_id, context)
        await context.bot.send_message(chat_id=chat_id, text="No torrents found for this movie.")
        return ConversationHandler.END
    session = _search_data(chat_id, context)
    session.clear()
    session.update(torrents=torrents, page=0)
    await _display_streams(chat_id, context)
    return _SELECTING_TORRENT


async def _display_search_results(chat_id: int, context: ContextTypes.DEFAULT_TYPE, movies: list[_Movie]) -> None:
    lines = [f"{i}. {movie.title[:160]} ({movie.year})" for i, movie in enumerate(movies, 1)]
    await context.bot.send_message(
        chat_id=chat_id,
        text="Movies:\n\n" + "\n".join(lines) + "\n\nChoose a movie by number, or /cancel.",
        reply_markup=_selection_keyboard(len(movies)),
    )


@_require_privileges([_Privileges.DOWNLOADER])
async def _select_search_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Resolve the selected movie and fetch its torrents."""
    if update.effective_chat is None or update.effective_message is None:
        return ConversationHandler.END
    chat_id = update.effective_chat.id
    movies = _search_data(chat_id, context).get("movies", [])
    if not movies:
        return await _cancel(update, context)
    index = _selection((update.effective_message.text or "").strip(), len(movies))
    if index is None:
        await context.bot.send_message(chat_id=chat_id, text=f"Choose a number from 1 to {len(movies)}, or /cancel.")
        return _SELECTING_RESULT
    try:
        imdb_id = await _resolve_imdb_id(movies[index])
    except _ProviderError as error:
        await context.bot.send_message(chat_id=chat_id, text=f"{error} Choose again or /cancel.")
        return _SELECTING_RESULT
    if not imdb_id:
        await context.bot.send_message(
            chat_id=chat_id,
            text="This movie has no IMDb ID. Choose another movie or /cancel.",
        )
        return _SELECTING_RESULT
    return await _search_by_imdb_id(chat_id, context, imdb_id)


async def _display_streams(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = _search_data(chat_id, context)
    torrents = session["torrents"]
    start = session["page"] * _SEARCH_PAGE_SIZE
    page = torrents[start : start + _SEARCH_PAGE_SIZE]
    lines = []
    for i, torrent in enumerate(page, 1):
        seeders = torrent.seeders if torrent.seeders is not None else "Unknown"
        lines.append(
            f"{i}. {torrent.title[:160]}\n   {torrent.quality[:50]} | Seeders: {seeders} | Size: {torrent.size}",
        )
    numbers = [str(i) for i in range(1, len(page) + 1)]
    buttons = [numbers[i : i + 5] for i in range(0, len(numbers), 5)]
    navigation = []
    if start:
        navigation.append("Previous")
    if start + len(page) < len(torrents):
        navigation.append("Next")
    buttons.append([*navigation, "/cancel"])
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Torrents {start + 1}-{start + len(page)} of {len(torrents)}:\n\n"
        + "\n\n".join(lines)
        + "\n\nChoose a torrent number to download, or /cancel.",
        reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True),
    )


def _add_movie_torrent(torrent: _MovieTorrent) -> str:
    # Run the synchronous RPC calls in a worker; keep database access on the event loop.
    # Stremio file indices start at zero; aria2's select-file option starts at one.
    options = {} if torrent.file_index is None else {"select-file": str(torrent.file_index + 1)}
    download = aria2p.API().add_magnet(torrent.magnet, options=options)
    return f"Download added: {torrent.filename or torrent.title}\nGID: {download.gid} | Status: {download.status}"


@_require_privileges([_Privileges.DOWNLOADER])
async def _select_torrent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Download the selected torrent while retaining its file selection."""
    if update.effective_chat is None or update.effective_message is None or update.effective_user is None:
        return ConversationHandler.END
    chat_id = update.effective_chat.id
    session = _search_data(chat_id, context)
    torrents = session.get("torrents", [])
    if not torrents:
        return await _cancel(update, context)
    text = (update.effective_message.text or "").strip()
    page = session["page"]
    if text in {"Next", "Previous"}:
        page += 1 if text == "Next" else -1
        if 0 <= page * _SEARCH_PAGE_SIZE < len(torrents):
            session["page"] = page
        await _display_streams(chat_id, context)
        return _SELECTING_TORRENT
    start = page * _SEARCH_PAGE_SIZE
    index = _selection(text, min(_SEARCH_PAGE_SIZE, len(torrents) - start))
    if index is None:
        await context.bot.send_message(chat_id=chat_id, text="Choose one of the torrent numbers, or /cancel.")
        return _SELECTING_TORRENT
    db_user = _User.get_with_id(update.effective_user.id)
    if db_user is None:
        return await _cancel(update, context)
    if not (db_user.is_admin or db_user.has_privilege(_Privileges.VERIFIED_DOWNLOADER)):
        await context.bot.send_message(
            chat_id=chat_id,
            text="Starting downloads requires the Verified Downloader privilege. Ask an administrator for access.",
        )
        return _SELECTING_TORRENT
    try:
        reply = await asyncio.to_thread(_add_movie_torrent, torrents[start + index])
    except (aria2p.ClientException, OSError):
        await context.bot.send_message(
            chat_id=chat_id,
            text="Could not confirm the download with aria2. Check its queue before trying again, or /cancel.",
        )
        return _SELECTING_TORRENT
    _clear_search(chat_id, context)
    await context.bot.send_message(chat_id=chat_id, text=reply, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


_MAGNET_RE = r"\bmagnet:\?xt=urn:btih:(?:[a-fA-F0-9]{40}|[A-Za-z2-7]{32})(?=&|\s|$)(?:&[^\s<>]+)*"


@_require_privileges([_Privileges.DOWNLOADER])
async def _parse_magnet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    effective_user = update.effective_user
    effective_chat = update.effective_chat
    effective_message = update.effective_message
    if effective_user is None or effective_chat is None or effective_message is None:
        return
    tg_user = effective_user
    logger.info(f"{tg_user.username} ({tg_user.id}) sent magnet(s)")

    db_user = _User.get_with_id(tg_user.id)
    if db_user is None:
        return

    magnets = re.findall(_MAGNET_RE, effective_message.text or "")

    reply = "I got your magnet, thanks.\n" if len(magnets) == 1 else f"I got your {len(magnets)} magnets, thanks.\n"

    if db_user.is_admin or db_user.has_privilege(_Privileges.VERIFIED_DOWNLOADER):
        api = aria2p.API()
        downloads = [await asyncio.to_thread(api.add_magnet, magnet) for magnet in magnets]
        reply += "The new downloads are: \n\n"
        for d in downloads:
            reply += f"*{d.name}* (gid: {d.gid}, status: {d.status})\n\n"
    else:
        reply += "Starting downloads requires the Verified Downloader privilege. Ask an administrator for access."

    await context.bot.send_message(chat_id=effective_chat.id, text=reply, parse_mode=ParseMode.MARKDOWN)


async def _cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    effective_user = update.effective_user
    effective_message = update.effective_message
    if effective_user is None or effective_message is None:
        return ConversationHandler.END
    if update.effective_chat is not None:
        _clear_search(update.effective_chat.id, context)
    user = effective_user
    logger.info("User {} canceled the conversation.", user.first_name)
    await effective_message.reply_text("Search canceled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


@_require_privileges([_Privileges.TESTER])
async def _test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    effective_chat = update.effective_chat
    if effective_chat is None:
        return
    await context.bot.send_message(
        chat_id=effective_chat.id,
        text="testing",
        reply_markup=ReplyKeyboardMarkup([[str(i)] for i in range(20)], one_time_keyboard=True),
    )


@_require_access
async def _unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    effective_user = update.effective_user
    effective_chat = update.effective_chat
    effective_message = update.effective_message
    if effective_user is None or effective_chat is None or effective_message is None:
        return
    user = effective_user
    logger.info(f"{user.username} ({user.id}) typed unknown command: {effective_message.text}")
    await context.bot.send_message(
        chat_id=effective_chat.id,
        text="I did not understand that command. Please type /help to see the commands.",
    )


@_require_access
async def _unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    effective_user = update.effective_user
    effective_chat = update.effective_chat
    effective_message = update.effective_message
    if effective_user is None or effective_chat is None or effective_message is None:
        return
    user = effective_user
    logger.info(f"{user.username} ({user.id}) typed unknown text: {effective_message.text}")
    text = random.choice(  # noqa: S311
        [
            "yo",
            "wassup",
            "whatever",
            "yeah",
            "OK",
            "great",
            "good",
            "no.",
            "dude, get some /help",
            "stop that",
            f"toi {effective_message.text}",
        ],
    )

    await context.bot.send_message(chat_id=effective_chat.id, text=text)
