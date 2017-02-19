# -*- coding: utf-8 -*-
import uuid

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

    def __init__(self, name=None, datetime=None, description=None, access=None):
        if name is None:
            raise ValueError("Event name must be provided.")
        if datetime is None:
            raise ValueError("Date and Time must be provided.")
        if access is None:
            pass

        self.name = name
        self.datetime = datetime
        self.description = description
        self.link = self.create_link()
        self.access = access


    def create_link(self):
        """
        Create a 6 character id that can be used to
        GET the event. Let's call it a link.
        """
        # it doesnt really matter which characters
        # we grab. Starting with 6 characters which
        # should give us 16^6 combinations to begin
        # with. In the case of collisions on
        # database commit, we keep retrying until
        # we find a combination with no collisions.
        # This is a good place to revisit if we
        # get over a million events in the db.
        link = uuid.uuid4().hex[8:14]
        return link
