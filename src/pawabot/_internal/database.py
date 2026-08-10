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

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()
session = None


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    uid = Column(Integer, unique=True, nullable=False)
    username = Column(String(255), unique=True, nullable=False)
    is_admin = Column(Boolean, default=False)

    privileges = relationship("UserPrivilege", back_populates="user")

    def __repr__(self):
        return f"<User(uid={self.uid}, username='{self.username}', is_admin={self.is_admin})>"

    @staticmethod
    def all():
        return list(session.query(User))

    @staticmethod
    def get(int_or_string):
        if isinstance(int_or_string, int):
            return User.get_with_id(int_or_string)
        try:
            uid = int(int_or_string)
        except ValueError:
            return User.get_with_username(int_or_string)
        else:
            return User.get_with_id(uid)

    @staticmethod
    def get_with_id(uid):
        return session.query(User).filter(User.uid == uid).first()

    @staticmethod
    def get_with_username(username):
        return session.query(User).filter(User.username == username).first()

    @staticmethod
    def create(uid, username=None, is_admin=False):
        user = User(uid=uid, username=username or "???", is_admin=is_admin)
        session.add(user)
        session.commit()
        return user

    def has_privilege(self, privilege):
        return privilege.name in set(up.privilege for up in self.privileges)

    def has_privileges(self, privileges):
        return set(p.name for p in privileges).issubset(set(up.privilege for up in self.privileges))

    def get_privilege(self, privilege):
        for up in self.privileges:
            if up.privilege == privilege:
                return up
        return None

    def grant(self, privilege):
        session.add(UserPrivilege(user_id=self.uid, privilege=privilege.name))
        session.commit()
        return True

    def revoke(self, privilege):
        session.delete(self.get_privilege(privilege))
        session.commit()
        return True


def save():
    session.commit()


class UserPrivilege(Base):
    __tablename__ = "privilege"
    __table_args__ = (UniqueConstraint("user_id", "privilege"), {"extend_existing": True})

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    privilege = Column(String(255), nullable=False)

    user = relationship("User", back_populates="privileges")

    def __repr__(self):
        return f"<UserPrivilege(user={self.user!r}, privilege='{self.privilege}')>"


def init(db_path="sqlite:///db.sqlite3"):
    global session

    # connection
    engine = create_engine(db_path)

    # create metadata
    Base.metadata.create_all(engine)

    # create session
    session = sessionmaker(bind=engine)()

    return session
