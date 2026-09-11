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
from typing import TYPE_CHECKING, Any, TypeVar

from pawabot._internal.database import _save, _User

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

_F = TypeVar("_F", bound=Callable[..., Any])

_logger = logging.getLogger("pawabot")


async def _check_access(update: Update, context: ContextTypes.DEFAULT_TYPE, func_name: str) -> _User:
    effective_user = update.effective_user
    if effective_user is None:
        raise PermissionError
    db_user = _User.get_with_id(effective_user.id)

    # user does not have access to the bot
    if not db_user:
        await _deny_access(update, context, func_name)
        raise PermissionError

    # update the username if it has changed
    if db_user.username != effective_user.username:
        db_user.username = effective_user.username  # ty:ignore
        _save()

    return db_user


def _require_access(func: _F) -> _F:
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> Any:
        try:
            await _check_access(update, context, func.__name__)  # ty:ignore[unresolved-attribute]
        except PermissionError:
            return None

        return await func(update, context, *args, **kwargs)

    return wrapped  # ty:ignore[invalid-return-type]


def _require_admin(func: _F) -> _F:
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> Any:
        try:
            db_user = await _check_access(update, context, func.__name__)  # ty:ignore[unresolved-attribute]
        except PermissionError:
            return None

        if not db_user.is_admin:
            await _deny_access(update, context, func.__name__)  # ty:ignore[unresolved-attribute]

        return await func(update, context, *args, **kwargs)

    return wrapped  # ty:ignore[invalid-return-type]


def _require_privileges(privileges: list) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        @wraps(func)
        async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> Any:
            try:
                db_user = await _check_access(update, context, func.__name__)  # ty:ignore[unresolved-attribute]
            except PermissionError:
                return None

            # permissions check are for basic users only: skip for admins
            if not db_user.is_admin and not db_user.has_privileges(privileges):
                await _deny_access(update, context, func.__name__)  # ty:ignore[unresolved-attribute]
                return None

            return await func(update, context, *args, **kwargs)

        return wrapped  # ty:ignore[invalid-return-type]

    return decorator


async def _deny_access(update: Update, context: ContextTypes.DEFAULT_TYPE, func_name: str) -> None:
    effective_user = update.effective_user
    effective_chat = update.effective_chat
    if effective_user is None or effective_chat is None:
        return
    _logger.warning(
        f"Unauthorized access denied for {effective_user.username} ({effective_user.id}) on function {func_name}",
    )
    await context.bot.send_message(
        chat_id=effective_chat.id,
        text="Sorry, you don't have the required permissions to do that.Try to contact the administrator of this bot.",
    )
