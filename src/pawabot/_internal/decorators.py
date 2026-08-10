"""Decorators for access control."""

import logging
from functools import wraps

from pawabot._internal.database import User, save


def _require_access(update, context, func_name):
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


def require_access(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        try:
            _require_access(update, context, func.__name__)
        except PermissionError:
            return None

        return func(update, context, *args, **kwargs)

    return wrapped


def require_admin(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        try:
            db_user = _require_access(update, context, func.__name__)
        except PermissionError:
            return None

        if not db_user.is_admin:
            deny_access(update, context, func.__name__)

        return func(update, context, *args, **kwargs)

    return wrapped


def require_privileges(privileges):
    def decorator(func):
        @wraps(func)
        def wrapped(update, context, *args, **kwargs):
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


def deny_access(update, context, func_name):
    logging.warning(
        f"Unauthorized access denied for {update.effective_user.username} ({update.effective_user.id}) "
        f"on function {func_name}",
    )
    context.bot.send_message(
        chat_id=update.message.chat_id,
        text="Sorry, you don't have the required permissions to do that.Try to contact the administrator of this bot.",
    )
