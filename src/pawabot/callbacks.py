import logging
import random
import re
import subprocess
from textwrap import dedent

import aria2p
from telegram import (
    ChatAction,
    InlineQueryResultArticle,
    InputTextMessageContent,
    ParseMode,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import ConversationHandler

from .database import create_user, get_user
from .utils import get_torrents, load_torrents, restricted_command, save_torrents, update_saved_torrents


class STATE:
    class SEARCH:
        PATTERN, SELECT = range(2)


def start(update, context):
    tg_user = update.effective_user
    db_user = get_user(tg_user.id)
    logging.info(f"{tg_user.username} ({tg_user.id}) called start")

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


@restricted_command(["can_request_help"])
def help(update, context):
    user = update.message.from_user
    logging.info(f"{user.username} ({user.id}) called help")
    text = dedent(
        """
        /start - To get an introduction.
        /help - To print this help.
        /requestAccess - To request access to my commands.
        /myID - To show your Telegram ID.
        /myPermissions - To show your current permissions.
        /search - To search on The Pirate Bay.
        /grant - To grant a permission to a user.
        /revoke - To revoke a permission to a user.
    """
    )

    context.bot.send_message(chat_id=update.message.chat_id, text=text, parse_mode=ParseMode.MARKDOWN)


@restricted_command([])
def my_id(update, context):
    user = update.message.from_user
    logging.info(f"{user.username} ({user.id}) called myID")
    context.bot.send_message(chat_id=update.message.chat_id, text=update.effective_user.id)


@restricted_command([])
def my_permissions(update, context):
    user = update.message.from_user
    logging.info(f"{user.username} ({user.id}) called myPermissions")
    db_user = get_user(user.id)

    text = []
    if db_user:
        if db_user.is_owner:
            text.append("You are an administrator: you have full access to all commands.\n")
        permissions = list(db_user.permissions) if db_user else []
        if permissions:
            text.append("\n" + "\n".join(permissions))
        else:
            text.append("You have zero permissions.")
    else:
        text.append("You do not have access to my commands.")

    context.bot.send_message(chat_id=update.message.chat_id, text="".join(text))


@restricted_command(["can_search"])
def search(update, context):
    user = update.message.from_user
    logging.info(f"{user.username} ({user.id}) called search with {context.args}")

    context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)

    if not context.args:
        context.bot.send_message(chat_id=update.message.chat_id, text="What do you want to search?")
        return STATE.SEARCH.PATTERN

    torrents = get_torrents(" ".join(context.args))

    if not torrents:
        context.bot.send_message(chat_id=update.message.chat_id, text="No results")
        return

    update_saved_torrents(torrents, update.effective_user.id)
    reply_torrents(update, context, torrents)

    return STATE.SEARCH.SELECT


def search_pattern(update, context):
    torrents = get_torrents(update.message.text)

    if not torrents:
        context.bot.send_message(chat_id=update.message.chat_id, text="No results")
        return ConversationHandler.END

    update_saved_torrents(torrents, update.effective_user.id)
    reply_torrents(update, context, torrents)

    return STATE.SEARCH.SELECT


def search_select(update, context):
    if update.message.text == "Cancel":
        return ConversationHandler.END

    context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)

    torrents = load_torrents(update.effective_user.id)

    if update.message.text.endswith("+"):
        page = int(update.message.text[:-1]) // 10
        reply_torrents(update, context, torrents, page=page + 1)
        return STATE.SEARCH.SELECT

    choice = int(update.message.text)
    torrent = torrents[choice - 1]

    context.bot.send_message(chat_id=update.message.chat_id, text=f"You chose torrent {torrent.title}")

    return ConversationHandler.END


def reply_torrents(update, context, torrents, page=1):
    x = (page - 1) * 10
    y = x + 10

    reply_text = []
    keyboard_buttons = [[], []]

    for i, torrent in enumerate(torrents[x:y], 1):
        keyboard_buttons[0 if i <= 5 else 1].append(str(i + x))
        reply_text.append(
            f"*#{i} - {torrent.title}*\n" f"  {torrent.seeders}/{torrent.leechers}  {torrent.size}  {torrent.date}\n\n"
        )

    keyboard_buttons.append([str(int(keyboard_buttons[1][-1])) + "+", "Cancel"])

    context.bot.send_message(
        chat_id=update.message.chat_id,
        text="".join(reply_text),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardMarkup(keyboard_buttons, one_time_keyboard=True),
    )


@restricted_command(["can_search_inline"])
def inline_search(update, context):
    query = update.inline_query.query
    user = update.inline_query.from_user
    logging.info(f"{user.username} ({user.id}) called inline search with {query}")

    if not query:
        logging.info("inline search: query is empty, aborting")
        return

    output = None
    retries = 2

    while not output and retries > 0:
        logging.info(f"running pirate-bay-search")
        try:
            output = (
                subprocess.check_output(["pirate-bay-search", query], timeout=5).decode(encoding="utf-8").rstrip("\n")
            )
        except subprocess.TimeoutExpired:
            retries -= 1
            logging.warn(f"pirate-bay-search timeout, retries left: {retries}")

    if retries == 0:
        context.bot.answer_inline_query(
            update.inline_query.id,
            [
                InlineQueryResultArticle(
                    id=query,
                    title="Connection timeout",
                    input_message_content=InputTextMessageContent("Connection timeout"),
                )
            ],
        )
        return

    logging.debug("pirate-bay-search results:\n\n" + output)

    results = []
    for i, torrent in enumerate(output.split("\n\n")):
        lines = torrent.split("\n")
        results.append(
            InlineQueryResultArticle(
                id=query + str(i),
                title=lines[0].replace(".", " "),
                description=lines[1],
                input_message_content=InputTextMessageContent(torrent),
                hide_url=True,
            )
        )

    context.bot.answer_inline_query(update.inline_query.id, results)


MAGNET_RE = r"\bmagnet:\?xt=urn:[A-Za-z0-9]+:[A-Za-z0-9]{32,40}(?:&(?:amp;)?dn=.+)?(?:&(?:amp;)?tr=.+)+\b"


@restricted_command(["can_request_download"])
def parse_magnet(update, context):
    tg_user = update.effective_user
    db_user = get_user(tg_user.id)

    user = update.message.from_user
    logging.info(f"{user.username} ({user.id}) sent magnet(s)")
    magnets = re.findall(MAGNET_RE, update.message.text)

    if len(magnets) == 1:
        reply = "I got your magnet, thanks.\n"
    else:
        reply = f"I got your {len(magnets)} magnets, thanks.\n"

    if db_user.is_owner or db_user.has_perm("can_auto_download"):
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


@restricted_command([])
def request_access(update, context):
    tg_user = update.effective_user
    user = get_user(tg_user.id)

    if not user:
        create_user(tg_user.id, tg_user.username)
        context.bot.send_message(
            chat_id=update.message.chat_id, text="I received your request. Please wait for feedback."
        )
    else:
        context.bot.send_message(
            chat_id=update.message.chat_id, text=f"I already know you {tg_user.username}! No need to request access!"
        )


@restricted_command(["can_grant_permissions"])
def grant(update, context):
    if (not context.args) or len(context.args) != 2:
        context.bot.send_message(chat_id=update.message.chat_id, text="Usage is /grant <ID_OR_USERNAME> <PERMISSION>")
        return

    permission = context.args[1]
    user = get_user(context.args[0])

    if not user:
        try:
            uid = int(context.args[0])
        except ValueError:
            context.bot.send_message(
                chat_id=update.message.chat_id,
                text="I don't know that user, please ask them to send '/requestAccess' to me.",
            )
            return
        else:
            user = create_user(uid)

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


@restricted_command(["can_revoke_permissions"])
def revoke(update, context):
    if not context.args or len(context.args) != 2:
        context.bot.send_message(chat_id=update.message.chat_id, text="Usage is /revoke <ID_OR_USERNAME> <PERMISSION>")
        return

    permission = context.args[1]
    user = get_user(context.args[0])

    if not user:
        try:
            uid = int(context.args[0])
        except ValueError:
            context.bot.send_message(
                chat_id=update.message.chat_id,
                text="I don't know that user, please ask them to send '/requestAccess' to me.",
            )
            return
        else:
            user = create_user(uid)

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


def cancel(update, context):
    user = update.message.from_user
    logging.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text("Bye! I hope we can talk again some day.", reply_markup=ReplyKeyboardRemove())


@restricted_command([])
def unknown_command(update, context):
    user = update.message.from_user
    logging.info(f"{user.username} ({user.id}) typed unknown command: {update.message.text}")
    context.bot.send_message(
        chat_id=update.message.chat_id, text="I did not understand that command. Please type /help to see the commands."
    )


@restricted_command([])
def unknown(update, context):
    user = update.message.from_user
    logging.info(f"{user.username} ({user.id}) type unknown text: {update.message.text}")
    text = random.choice(
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
