""" Database staff here. """
from __future__ import annotations

from io import BytesIO
from typing import Optional

import sqlalchemy as sa
from PIL.Image import Image
from sqlalchemy import MetaData, create_engine, select, insert, update
from sqlalchemy.orm import declarative_base

engine = create_engine("sqlite:///bot.db")
metadata = MetaData(bind=engine)
Base = declarative_base(bind=engine, metadata=metadata)


class User(Base):
    """ User model """

    __tablename__ = "user"

    name = sa.Column(sa.String, primary_key=True)
    messages_count = sa.Column(sa.Integer, default=1)

    @staticmethod
    def get_msg_count(name: str) -> int:
        """ Get allowed messages limit """
        st = select(User.messages_count).where(User.name == name)
        with engine.connect() as conn:
            count = conn.scalar(st)
        if count is None:
            User.create(name)
            count = User.messages_count.default.arg
        return count

    @staticmethod
    def create(name: str) -> None:
        """ Create user """
        st = insert(User).values(name=name)
        with engine.connect() as conn:
            conn.execute(st)

    @staticmethod
    def decrease_messages_count(name) -> None:
        """ Decrease messages limit """
        st = update(User).where(User.name == name).values(messages_count=User.messages_count - 1)
        with engine.connect() as conn:
            conn.execute(st)


class Message(Base):
    """ Message model """
    __tablename__ = "message"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)

    user_name = sa.Column(sa.String, sa.ForeignKey("user.name"))
    text = sa.Column(sa.String)
    img = sa.Column(sa.LargeBinary)

    @staticmethod
    def create(user_name: str, text: Optional[str], img: Optional[Image]) -> None:
        """ Create message model """
        img_bin = None
        if img is not None:
            with BytesIO() as output:
                img.save(output, "BMP")
                img_bin = output.getvalue()
        st1 = insert(Message).values(user_name=user_name, text=text, img=img_bin)
        with engine.connect() as conn:
            conn.execute(st1)


metadata.create_all()
