# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String, DateTime
from database import Base

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    name = Column(String(64))
    datetime = Column(DateTime())
    description = Column(String())
    link = Column(String(64), unique=True)
    access = Column(String(256))

    def __init__(self, name=None, datetime=None, description=None, link=None, access=None):
        if name is None:
            raise ValueError("Event name must be provided.")
        if datetime is None:
            raise ValueError("Date and Time must be provided.")
        if link is None:
            # create a link here and assign it to local variable link
            # because self.link will be assigned some lines down
            pass
        if access is None:
            pass
        self.name = name
        self.datetime = datetime
        self.description = description
        self.link = link
        self.access = access


