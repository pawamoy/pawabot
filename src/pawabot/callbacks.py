import random
import re
from textwrap import dedent

import aria2p
from loguru import logger
from privibot import User, require_access, require_privileges
from telegram import (  # InlineQueryResultArticle, InputTextMessageContent,
    ChatAction,
    ParseMode,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import ConversationHandler

from .privileges import Privileges
from .torrents import TPB, Search


class STATE:
    class SEARCH:
        PATTERN, SELECT = range(2)


def start(update, context):
    tg_user = update.effective_user
    logger.info(f"{tg_user.username} ({tg_user.id}) called /start")

    db_user = User.get_with_id(tg_user.id)

    if not db_user:
        text = dedent(
            f"""
            Hi @{tg_user.username}

            Sorry, but you have not been granted access to my commands.
            Please contact my administrator.
            """
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
            """
        )

    context.bot.send_message(chat_id=update.message.chat_id, text=text)


@require_access
def help(update, context):
    user = update.message.from_user
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
    """
    )

    context.bot.send_message(chat_id=update.message.chat_id, text=text, parse_mode=ParseMode.MARKDOWN)


@require_access
def my_id(update, context):
    user = update.message.from_user
    logger.info(f"{user.username} ({user.id}) called /myID")
    context.bot.send_message(chat_id=update.message.chat_id, text=update.effective_user.id)


@require_privileges([Privileges.DOWNLOADER])
def search(update, context):
    user = update.message.from_user
    logger.info(f"{user.username} ({user.id}) called /search with args={context.args}")

    context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)

    if not context.args:
        context.bot.send_message(chat_id=update.message.chat_id, text="What do you want to search?")
        return STATE.SEARCH.PATTERN

    pattern = " ".join(context.args)
    s = TPB.search(user.id, pattern)

    if not s.results:
        context.bot.send_message(chat_id=update.message.chat_id, text="No results")
        return ConversationHandler.END

    s.save(user.id)
    reply_torrents(update, context, s.results)

    return STATE.SEARCH.SELECT


def search_pattern(update, context):
    user = update.effective_user
    pattern = update.message.text
    logger.info(f"{user.username} ({user.id}) sent pattern '{pattern}' during /search conversation")
    context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING, timeout=25)

    logger.info(f"Searching '{pattern}' on TPB proxies")
    try:
        s = TPB.search(user.id, pattern)
    except LookupError:
        logger.info(f"No results for '{pattern}' on TPB proxies")
        context.bot.send_message(chat_id=update.message.chat_id, text="No results")
        return ConversationHandler.END

    logger.info(f"Saving results for '{pattern}'")
    s.save()
    reply_torrents(update, context, s.results)

    return STATE.SEARCH.SELECT


def search_select(update, context):
    user = update.effective_user
    message = update.message.text

    if message == "Cancel":
        logger.info(f"{user.username} ({user.id}) canceled /search conversation")
        return ConversationHandler.END

    context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)

    s = Search.load(user.id)

    if message.endswith("+"):
        last = int(message[:-1])
        page = last // 10
        logger.info(f"{user.username} ({user.id}) asked to see page {page+1} during /search conversation")

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
            f"A download request has been sent to an administrator. "
            f"You will get a notification when they processed it."
        )

    context.bot.send_message(
        chat_id=update.message.chat_id, text=reply, reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.MARKDOWN
    )

    return ConversationHandler.END


def reply_torrents(update, context, torrents, page=1):
    x = (page - 1) * 10
    y = x + 10

    reply_text = []
    keyboard_buttons = [[], []]

    for i, torrent in enumerate(torrents[x:y], 1):
        keyboard_buttons[0 if i <= 5 else 1].append(str(i + x))
        reply_text.append(
            f"*#{i+x} - {torrent.title}*\n"
            f"  {torrent.seeders}/{torrent.leechers}  {torrent.size}  {torrent.date}\n\n"
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
        chat_id=update.message.chat_id,
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
def parse_magnet(update, context):
    tg_user = update.effective_user
    logger.info(f"{tg_user.username} ({tg_user.id}) sent magnet(s)")

    db_user = User.get_with_id(tg_user.id)

    magnets = re.findall(MAGNET_RE, update.message.text)

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
            "You must now wait for the administrator to accept them.\n"
            "You will receive a notification when it's done!"
        )

    context.bot.send_message(chat_id=update.message.chat_id, text=reply, parse_mode=ParseMode.MARKDOWN)


def cancel(update, context):
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text("Bye! I hope we can talk again some day.", reply_markup=ReplyKeyboardRemove())


@require_privileges([Privileges.TESTER])
def test(update, context):
    context.bot.send_message(
        chat_id=update.message.chat_id,
        text="testing",
        reply_markup=ReplyKeyboardMarkup([[str(i)] for i in range(20)], one_time_keyboard=True),
    )


@require_access
def unknown_command(update, context):
    user = update.message.from_user
    logger.info(f"{user.username} ({user.id}) typed unknown command: {update.message.text}")
    context.bot.send_message(
        chat_id=update.message.chat_id, text="I did not understand that command. Please type /help to see the commands."
    )


@require_access
def unknown(update, context):
    user = update.message.from_user
    logger.info(f"{user.username} ({user.id}) typed unknown text: {update.message.text}")
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
            f"toi {update.message.text}",
        ]
    )

    context.bot.send_message(chat_id=update.message.chat_id, text=text)
