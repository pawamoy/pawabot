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

import random
import re
from textwrap import dedent

import aria2p
from loguru import logger
from telegram import (
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)

from pawabot._internal.database import User
from pawabot._internal.decorators import require_access, require_admin, require_privileges
from pawabot._internal.privileges import Privileges
from pawabot._internal.torrents import TPB, Search


class STATE:
    class SEARCH:
        PATTERN, SELECT = range(2)


def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    logger.info(f"{tg_user.username} ({tg_user.id}) called /start")

    db_user = User.get_with_id(tg_user.id)

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

    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


@require_access
def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"{user.username} ({user.id}) called /help")
    text = dedent(
        """
        /start - To get an introduction.
        /help - To print this help.
        /requestAccess - To request access to my commands.
        /myID - To show your Telegram ID.
        /myPrivileges - To show your current permissions.
        /search - To search on The Pirate Bay.
        /grant - To grant a permission to a user.
        /revoke - To revoke a permission to a user.
    """,
    )

    context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode=ParseMode.MARKDOWN)


@require_access
def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"{user.username} ({user.id}) called /myID")
    context.bot.send_message(chat_id=update.effective_chat.id, text=user.id)


@require_privileges([])
def my_privileges(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"{user.username} ({user.id}) called /myPrivileges")
    db_user = User.get_with_id(user.id)

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

    context.bot.send_message(chat_id=update.effective_chat.id, text="".join(text))


def request_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    logger.info(f"{tg_user.username} ({tg_user.id}) called /requestAccess")

    user = User.get_with_id(tg_user.id)

    if not user:
        User.create(tg_user.id, tg_user.username)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="I received your request. Please wait for feedback.",
        )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"I already know you {tg_user.username}! No need to request access!",
        )


@require_admin
def grant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    logger.info(f"{tg_user.username} ({tg_user.id}) called /grant")

    if not context.args or len(context.args) != 2:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Usage is /grant <ID_OR_USERNAME> <PERMISSION>",
        )
        return

    permission = context.args[1]
    user = User.get(context.args[0])

    if not user:
        try:
            uid = int(context.args[0])
        except ValueError:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="I don't know that user, please ask them to send '/requestAccess' to me.",
            )
            return
        else:
            user = User.create(uid)

    if user.has_perm(permission):
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"User {user.username} ({user.uid}) already has permission '{permission}'.",
        )
        return

    user.grant(permission)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Done! User {user.username} ({user.uid}) now has permission '{permission}'.",
    )

    if update.effective_user.id != user.uid:
        context.bot.send_message(
            chat_id=user.uid,
            text=f"Hi! You've been granted the permission '{permission}' "
            f"just now by {update.effective_user.username} on "
            f"the bot called '{context.bot.username}'. "
            f"If you don't know what this means, just ignore this message!",
        )


@require_admin
def revoke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or len(context.args) != 2:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Usage is /revoke <ID_OR_USERNAME> <PERMISSION>",
        )
        return

    permission = context.args[1]
    user = User.get(context.args[0])

    if not user:
        try:
            uid = int(context.args[0])
        except ValueError:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="I don't know that user, please ask them to send '/requestAccess' to me.",
            )
            return
        else:
            user = User.create(uid)

    if not user.has_perm(permission):
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"User {user.username} ({user.uid}) does not have permission '{permission}'.",
        )
        return

    user.revoke(permission)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Done! User {user.username} ({user.uid}) just lost permission '{permission}'.",
    )

    if update.effective_user.id != user.uid:
        context.bot.send_message(
            chat_id=user.uid,
            text=f"Hi! You've been revoked the permission '{permission}' "
            f"just now by {update.effective_user.username} on "
            f"the bot called '{context.bot.username}'. "
            f"If you don't know what this means, just ignore this message!",
        )


@require_privileges([Privileges.DOWNLOADER])
def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    user = update.effective_user
    logger.info(f"{user.username} ({user.id}) called /search with args={context.args}")

    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    if not context.args:
        context.bot.send_message(chat_id=update.effective_chat.id, text="What do you want to search?")
        return STATE.SEARCH.PATTERN

    pattern = " ".join(context.args)
    s = TPB.search(user.id, pattern)

    if not s.results:
        context.bot.send_message(chat_id=update.effective_chat.id, text="No results")
        return ConversationHandler.END

    s.save(user.id)
    reply_torrents(update, context, s.results)

    return STATE.SEARCH.SELECT


def search_pattern(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    pattern = update.effective_message.text
    logger.info(f"{user.username} ({user.id}) sent pattern '{pattern}' during /search conversation")
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING, timeout=25)

    logger.info(f"Searching '{pattern}' on TPB proxies")
    try:
        s = TPB.search(user.id, pattern)
    except LookupError:
        logger.info(f"No results for '{pattern}' on TPB proxies")
        context.bot.send_message(chat_id=update.effective_chat.id, text="No results")
        return ConversationHandler.END

    logger.info(f"Saving results for '{pattern}'")
    s.save()
    reply_torrents(update, context, s.results)

    return STATE.SEARCH.SELECT


def search_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    message = update.effective_message.text

    if message == "Cancel":
        logger.info(f"{user.username} ({user.id}) canceled /search conversation")
        return ConversationHandler.END

    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    s = Search.load(user.id)

    if message.endswith("+"):
        last = int(message[:-1])
        page = last // 10
        logger.info(f"{user.username} ({user.id}) asked to see page {page + 1} during /search conversation")

        if last >= len(s.results):
            s.update(TPB.search(s.user_id, s.pattern, s.pages[-1] + 1))

        reply_torrents(update, context, s.results, page=page + 1)
        return STATE.SEARCH.SELECT

    torrent = s.results[int(message) - 1]
    logger.info(f"{user.username} ({user.id}) chose torrent '{torrent.title}' during /search conversation")

    db_user = User.get_with_id(user.id)
    if db_user.is_admin or db_user.has_perm("can_auto_download"):
        api = aria2p.API()
        download = api.add_magnet(torrent.magnet)
        reply = f"The new download is *{download.name}* (gid: {download.gid}, status: {download.status})"
        logger.info(f"torrent '{download.name}' (gid: {download.gid}) was added to aria2")
    else:
        reply = (
            "A download request has been sent to an administrator. You will get a notification when they processed it."
        )

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=reply,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )

    return ConversationHandler.END


def reply_torrents(
    update: Update, context: ContextTypes.DEFAULT_TYPE, torrents: list | None = None, page: int = 1
) -> None:
    x = (page - 1) * 10
    y = x + 10

    reply_text = []
    keyboard_buttons = [[], []]

    for i, torrent in enumerate(torrents[x:y], 1):
        keyboard_buttons[0 if i <= 5 else 1].append(str(i + x))
        reply_text.append(
            f"*#{i + x} - {torrent.title}*\n  {torrent.seeders}/{torrent.leechers}  {torrent.size}  {torrent.date}\n\n",
        )

    third_row = ["Cancel"]
    if keyboard_buttons[1]:
        last = keyboard_buttons[1][-1]
    else:
        last = keyboard_buttons[0][-1]
    if len(torrents) > y or len(torrents) % 30 == 0:
        third_row.insert(0, last + "+")

    keyboard_buttons.append(third_row)

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="".join(reply_text),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardMarkup(keyboard_buttons, one_time_keyboard=True, resize_keyboard=True),
    )


# @require_privileges([Privileges.DOWNLOADER])
# def inline_search(update, context):
#     query = update.inline_query.query
#     user = update.inline_query.from_user
#     logger.info(f"{user.username} ({user.id}) called inline search with {query}")
#
#     if not query:
#         logger.info("inline search: query is empty, aborting")
#         return
#
#     output = None
#     retries = 2
#
#     while not output and retries > 0:
#         logger.info(f"running pirate-bay-search")
#         try:
#             output = (
#                 subprocess.check_output(["pirate-bay-search", query], timeout=5).decode(encoding="utf-8").rstrip("\n")
#             )
#         except subprocess.TimeoutExpired:
#             retries -= 1
#             logger.warn(f"pirate-bay-search timeout, retries left: {retries}")
#
#     if retries == 0:
#         context.bot.answer_inline_query(
#             update.inline_query.id,
#             [
#                 InlineQueryResultArticle(
#                     id=query,
#                     title="Connection timeout",
#                     input_message_content=InputTextMessageContent("Connection timeout"),
#                 )
#             ],
#         )
#         return
#
#     logger.debug("pirate-bay-search results:\n\n" + output)
#
#     results = []
#     for i, torrent in enumerate(output.split("\n\n")):
#         lines = torrent.split("\n")
#         results.append(
#             InlineQueryResultArticle(
#                 id=query + str(i),
#                 title=lines[0].replace(".", " "),
#                 description=lines[1],
#                 input_message_content=InputTextMessageContent(torrent),
#                 hide_url=True,
#             )
#         )
#
#     context.bot.answer_inline_query(update.inline_query.id, results)


MAGNET_RE = r"\bmagnet:\?xt=urn:[A-Za-z0-9]+:[A-Za-z0-9]{32,40}(?:&(?:amp;)?dn=.+)?(?:&(?:amp;)?tr=.+)+\b"


@require_privileges([Privileges.DOWNLOADER])
def parse_magnet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    logger.info(f"{tg_user.username} ({tg_user.id}) sent magnet(s)")

    db_user = User.get_with_id(tg_user.id)

    magnets = re.findall(MAGNET_RE, update.effective_message.text)

    if len(magnets) == 1:
        reply = "I got your magnet, thanks.\n"
    else:
        reply = f"I got your {len(magnets)} magnets, thanks.\n"

    if db_user.is_admin or db_user.has_perm("can_auto_download"):
        api = aria2p.API()
        downloads = []
        for magnet in magnets:
            downloads.append(api.add_magnet(magnet))
        reply += "The new downloads are: \n\n"
        for d in downloads:
            reply += f"*{d.name}* (gid: {d.gid}, status: {d.status})\n\n"
    else:
        reply += (
            "You must now wait for the administrator to accept them.\nYou will receive a notification when it's done!"
        )

    context.bot.send_message(chat_id=update.effective_chat.id, text=reply, parse_mode=ParseMode.MARKDOWN)


def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.effective_message.reply_text("Bye! I hope we can talk again some day.", reply_markup=ReplyKeyboardRemove())


@require_privileges([Privileges.TESTER])
def test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="testing",
        reply_markup=ReplyKeyboardMarkup([[str(i)] for i in range(20)], one_time_keyboard=True),
    )


@require_access
def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"{user.username} ({user.id}) typed unknown command: {update.effective_message.text}")
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="I did not understand that command. Please type /help to see the commands.",
    )


@require_access
def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"{user.username} ({user.id}) typed unknown text: {update.effective_message.text}")
    text = random.choice(  # nosec
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
            f"toi {update.effective_message.text}",
        ],
    )

    context.bot.send_message(chat_id=update.effective_chat.id, text=text)
