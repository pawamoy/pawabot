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

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from telegram import Update
from telegram.ext import ContextTypes

from pawabot._internal.database import User, save

F = TypeVar("F", bound=Callable[..., Any])


def _require_access(update: Update, context: ContextTypes.DEFAULT_TYPE, func_name: str) -> User:
    db_user = User.get_with_id(update.effective_user.id)

    # user does not have access to the bot
    if not db_user:
        deny_access(update, context, func_name)
        raise PermissionError

    # update the username if it has changed
    if db_user.username != update.effective_user.username:
        db_user.username = update.effective_user.username
        save()

    return db_user


def require_access(func: F) -> F:
    @wraps(func)
    def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> Any:
        try:
            _require_access(update, context, func.__name__)
        except PermissionError:
            return None

        return func(update, context, *args, **kwargs)

    return wrapped


def require_admin(func: F) -> F:
    @wraps(func)
    def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> Any:
        try:
            db_user = _require_access(update, context, func.__name__)
        except PermissionError:
            return None

        if not db_user.is_admin:
            deny_access(update, context, func.__name__)

        return func(update, context, *args, **kwargs)

    return wrapped


def require_privileges(privileges: list) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> Any:
            try:
                db_user = _require_access(update, context, func.__name__)
            except PermissionError:
                return None

            # permissions check are for basic users only: skip for admins
            if not db_user.is_admin:
                if not db_user.has_privileges(privileges):
                    deny_access(update, context, func.__name__)
                    return None

            return func(update, context, *args, **kwargs)

        return wrapped

    return decorator


def deny_access(update: Update, context: ContextTypes.DEFAULT_TYPE, func_name: str) -> None:
    logging.warning(
        f"Unauthorized access denied for {update.effective_user.username} ({update.effective_user.id}) "
        f"on function {func_name}",
    )
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Sorry, you don't have the required permissions to do that.Try to contact the administrator of this bot.",
    )
