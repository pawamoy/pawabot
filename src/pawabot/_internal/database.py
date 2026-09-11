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

from typing import Any

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

_Base = declarative_base()
_session = None


class _User(_Base):
    __tablename__ = "user"

    id: int = Column(Integer, primary_key=True)  # ty:ignore[invalid-assignment]
    uid: int = Column(Integer, unique=True, nullable=False)  # ty:ignore[invalid-assignment]
    username: str = Column(String(255), unique=True, nullable=False)  # ty:ignore[invalid-assignment]
    is_admin: bool = Column(Boolean, default=False)  # ty:ignore[invalid-assignment]

    privileges = relationship("_UserPrivilege", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(uid={self.uid}, username='{self.username}', is_admin={self.is_admin})>"

    @staticmethod
    def all() -> list[_User]:
        if _session is None:
            return []
        return list(_session.query(_User))

    @staticmethod
    def get(int_or_string: int | str) -> _User | None:
        if isinstance(int_or_string, int):
            return _User.get_with_id(int_or_string)
        try:
            uid = int(int_or_string)
        except ValueError:
            return _User.get_with_username(int_or_string)
        else:
            return _User.get_with_id(uid)

    @staticmethod
    def get_with_id(uid: int) -> _User | None:
        if _session is None:
            return None
        return _session.query(_User).filter(_User.uid == uid).first()  # ty:ignore[invalid-argument-type]

    @staticmethod
    def get_with_username(username: str) -> _User | None:
        if _session is None:
            return None
        return _session.query(_User).filter(_User.username == username).first()  # ty:ignore[invalid-argument-type]

    @staticmethod
    def create(uid: int, username: str | None = None, *, is_admin: bool = False) -> _User:
        if _session is None:
            raise RuntimeError("Database not initialized")
        user = _User(uid=uid, username=username or "?", is_admin=is_admin)
        _session.add(user)
        _session.commit()
        return user

    def has_privilege(self, privilege: Any) -> bool:
        return privilege.name in {up.privilege for up in self.privileges}

    def has_privileges(self, privileges: list) -> bool:
        return {p.name for p in privileges}.issubset({up.privilege for up in self.privileges})

    def get_privilege(self, privilege: Any) -> Any | None:
        for up in self.privileges:
            if up.privilege == privilege:
                return up
        return None

    def grant(self, privilege: Any) -> bool:
        if _session is None:
            raise RuntimeError("Database not initialized")
        _session.add(_UserPrivilege(user_id=self.uid, privilege=privilege.name))
        _session.commit()
        return True

    def revoke(self, privilege: Any) -> bool:
        if _session is None:
            raise RuntimeError("Database not initialized")
        _session.delete(self.get_privilege(privilege))
        _session.commit()
        return True


def _save() -> None:
    if _session is None:
        raise RuntimeError("Database not initialized")
    _session.commit()


class _UserPrivilege(_Base):
    __tablename__ = "privilege"
    __table_args__ = (UniqueConstraint("user_id", "privilege"), {"extend_existing": True})

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    privilege = Column(String(255), nullable=False)

    user = relationship("_User", back_populates="privileges")

    def __repr__(self) -> str:
        return rf"<UserPrivilege(user={self.user!r}, privilege='{self.privilege}')\>"


def _init(db_path: str = "sqlite:///db.sqlite3") -> Any:
    global _session  # noqa: PLW0603

    # connection
    engine = create_engine(db_path)

    # create metadata
    _Base.metadata.create_all(engine)

    # create session
    _session = sessionmaker(bind=engine)()

    return _session
