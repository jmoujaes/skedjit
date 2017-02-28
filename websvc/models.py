# -*- coding: utf-8 -*-
import uuid

#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from database import Base

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    name = Column(String(64))
    dtstamp = Column(DateTime())
    dtstamp_tz = Column(Integer)
    dtstart = Column(DateTime())
    dtstart_tz = Column(Integer)
    dtend = Column(DateTime())
    dtend_tz = Column(Integer)
    description = Column(String())
    link = Column(String(64), unique=True)
    access = Column(String(256))
    ics_data = Column(String())

    def __init__(self, name=None, description=None, access=None, dtstart=None, dtstart_tz=None, dtend=None, dtend_tz=None):
        if (dtstart is None) or (dtstart_tz is None) or (dtend is None) \
            or (dtend_tz is None):
            raise ValueError("Start and End dates and times must be provided.")

        self.name = name
        self.description = description
        self.access = access
        self.dtstamp = ""
        self.dtstamp_tz = ""
        self.dtstart = dtstart
        self.dtstart_tz = dtstart_tz
        self.dtend = dtend
        self.dtend_tz = dtend_tz
        self.link = self.create_link()


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
