"""
Module that contains the command line application.

Why does this file exist, and why not put this in __main__?

You might be tempted to import things from __main__ later,
but that will cause problems: the code will get executed twice:

- When you run `python -m pawabot` python will execute
  ``__main__.py`` as a script. That means there won't be any
  ``pawabot.__main__`` in ``sys.modules``.
- When you import __main__ it will get executed again (as a module) because
  there's no ``pawabot.__main__`` in ``sys.modules``.

Also see http://click.pocoo.org/5/setuptools/#setuptools-integration.
"""

import argparse
import logging

from privibot import callbacks as privcallbacks
from privibot import User
from telegram.ext import CommandHandler, ConversationHandler, Filters, MessageHandler, Updater

from . import callbacks


def main(args=None):
    """The main function, which is executed when you type ``pawabot`` or ``python -m pawabot``."""
    parser = get_parser()
    args = parser.parse_args(args=args)

    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

    # with open("owner_id.txt") as stream:
    #     OWNER_ID = stream.read().rstrip("\n")

    if args.subcommand == "create-admin":
        User.create(uid=args.uid, username=args.username, is_admin=True)
        return 0
    elif args.subcommand == "create-user":
        User.create(uid=args.uid, username=args.username, is_admin=args.admin)
        return 0
    elif args.subcommand == "list-users":
        print(f"{'ID':>10}  {'USERNAME':<20}  ADMIN")
        print("---------------------------------------")
        for user in User.all():
            print(f"{user.uid:>10}  {user.username:<20}  {user.is_admin}")
            # TODO: also show privileges
        return 0
    elif args.subcommand == "delete-users":
        for uid in args.uids:
            User

    with open("token.txt") as stream:
        BOT_TOKEN = stream.read().rstrip("\n")

    updater = Updater(token=BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", callbacks.start))
    dispatcher.add_handler(CommandHandler("help", callbacks.help))
    dispatcher.add_handler(CommandHandler("myID", callbacks.my_id))
    dispatcher.add_handler(CommandHandler("myPrivileges", privcallbacks.my_privileges))
    dispatcher.add_handler(CommandHandler("requestAccess", privcallbacks.request_access))
    dispatcher.add_handler(CommandHandler("grant", privcallbacks.grant, pass_args=True))
    dispatcher.add_handler(CommandHandler("revoke", privcallbacks.revoke, pass_args=True))

    handler_search = CommandHandler("search", callbacks.search, pass_args=True)
    handler_search_pattern = MessageHandler(Filters.text, callbacks.search_pattern)
    handler_search_select = MessageHandler(Filters.regex(r"^([1-9][0-9]*\+?|Cancel)$"), callbacks.search_select)

    dispatcher.add_handler(
        ConversationHandler(
            entry_points=[handler_search],
            states={
                callbacks.STATE.SEARCH.PATTERN: [handler_search_pattern],
                callbacks.STATE.SEARCH.SELECT: [handler_search_select],
            },
            fallbacks=[CommandHandler("cancel", callbacks.cancel)],
        )
    )

    dispatcher.add_handler(handler_search)

    # dispatcher.add_handler(InlineQueryHandler(callbacks.inline_search))

    dispatcher.add_handler(MessageHandler(Filters.regex(callbacks.MAGNET_RE), callbacks.parse_magnet))

    dispatcher.add_handler(CommandHandler("test", callbacks.test))

    dispatcher.add_handler(MessageHandler(Filters.command, callbacks.unknown_command))
    dispatcher.add_handler(MessageHandler(Filters.text, callbacks.unknown))

    logging.info("Starting Bot")
    updater.start_polling()

    logging.info("Putting Bot in idle mode")
    updater.idle()

    return 0


def get_parser():
    parser = argparse.ArgumentParser(prog="pawabot")
    subparsers = parser.add_subparsers(dest="subcommand", title="Commands", metavar="", prog="pawabot")
    subcommand_help = "Show this help message and exit."

    def subparser(command, text, **kwargs):
        sub = subparsers.add_parser(command, add_help=False, help=text, description=text, **kwargs)
        sub.add_argument("-h", "--help", action="help", help=subcommand_help)
        return sub

    create_admin = subparser("create-admin", "Create an administrator user in the database.")
    create_admin.add_argument("-i", "--uid", dest="uid", help="Telegram user id.")
    create_admin.add_argument("-u", "--username", dest="username", help="Telegram user name.")

    create_user = subparser("create-user", "Create an administrator user in the database.")
    create_user.add_argument("-i", "--uid", dest="uid", help="Telegram user id.")
    create_user.add_argument("-u", "--username", dest="username", help="Telegram user name.")
    create_user.add_argument("-a", "--admin", action="store_true", dest="admin", help="Give admin access.")

    list_users = subparser("list-users", "List registered users.")

    # delete_users = subparser("delete-users", "Delete users by ID.")
    # delete_users.add_argument("uids", nargs="+", dest="uids", help="IDs of the users to delete.")

    # TODO: list-privileges
    # TODO: grant
    # TODO: revoke

    return parser
