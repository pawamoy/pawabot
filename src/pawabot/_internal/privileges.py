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


class _Privilege:
    """A named permission with a display name and description."""

    def __init__(self, name: str, verbose_name: str, description: str) -> None:
        """Initialize the privilege's identifier and display information."""
        self.name = name
        self.verbose_name = verbose_name
        self.description = description


class _Privileges:
    """Container for privileges."""

    DOWNLOADER = _Privilege(
        "downloader",
        "Downloader",
        "This privilege allows users to request downloads, either through a search or by sending a magnet to the bot. "
        "Another privilege, 'Verified Downloader', allows users to automatically start downloads "
        "without requiring validation by administrators.",
    )
    """Downloaded privilege."""
    VERIFIED_DOWNLOADER = _Privilege(
        "verified_downloader",
        "Verified Downloader",
        "This privilege allows users to automatically start downloads without requiring validation by administrators.",
    )
    """Verified downloaded privilege."""
    MEDIA_MANAGER = _Privilege(
        "media_manager",
        "Media Manager",
        "This privilege allows users to act (accept or reject) on media-related requests.",
    )
    """Media manager privilege."""
    USER_MANAGER = _Privilege(
        "user_manager",
        "User Manager",
        "This privilege allows users to manage access of other users to the bot.",
    )
    """User manager privilege."""
    TESTER = _Privilege("tester", "Tester", "This privilege allows users to test new things.")
    """Tester privilege."""

    @classmethod
    def get(cls, privilege_name: str) -> _Privilege | None:
        """Return a privilege by its identifier, or None if it is unknown."""
        for value in vars(cls).values():
            if isinstance(value, _Privilege) and value.name == privilege_name:
                return value
        return None
