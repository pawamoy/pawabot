from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    uid = Column(Integer, unique=True, nullable=False)
    username = Column(String(255), unique=True, nullable=False)
    is_owner = Column(Boolean, default=False)

    permissions = relationship("Permission", back_populates="user")

    def __repr__(self):
        return f"<User(uid={self.uid}, username='{self.username}', is_owner={self.is_owner})>"

    def has_perm(self, permission):
        return permission in set(p.permission for p in self.permissions)

    def get_perm(self, permission):
        for perm in self.permissions:
            if perm.permission == permission:
                return perm
        return None

    def grant(self, permission):
        if isinstance(permission, str):
            permission = Permission(permission=permission)
        permission.user_id = self.uid
        session.add(permission)
        session.commit()
        return True

    def revoke(self, permission):
        if isinstance(permission, str):
            permission = self.get_perm(permission)
        session.delete(permission)
        session.commit()
        return True


class Permission(Base):
    __tablename__ = "permission"
    __table_args__ = (UniqueConstraint("user_id", "permission"), {"useexisting": True})

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    permission = Column(String(255), nullable=False)

    user = relationship("User", back_populates="permissions")

    def __repr__(self):
        return f"<Permission(user={self.user!r}, permission='{self.permission}')>"


# connection
engine = create_engine("sqlite:///db.sqlite3")

# create metadata
Base.metadata.create_all(engine)

# create session
session = sessionmaker(bind=engine)()


def get_user(int_or_string):
    if isinstance(int_or_string, int):
        return get_user_from_id(int_or_string)
    else:
        try:
            uid = int(int_or_string)
        except ValueError:
            return get_user_from_username(int_or_string)
        else:
            return get_user_from_id(uid)


def get_user_from_id(uid):
    return session.query(User).filter(User.uid == uid).first()


def get_user_from_username(username):
    return session.query(User).filter(User.username == username).first()


def create_user(uid, username=None):
    username = username or "???"
    user = User(uid=uid, username=username)
    session.add(user)
    session.commit()
    return user
