# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# notes on configuring psql
# to connect manually to the database, you must sudo su - postgres
# then you can do psql
# at that point you can change the password of the default user account
# by doing "ALTER USER postgres WITH PASSWORD 'temporary';"
# finally exit psql using \q and log out of the postgres account using exit
# then sudo vi /etc/postgresql/9.5/main/pg_hba.conf and change line 92
# to 'trust'
#
# TODO lock this down when releasing to production, and adjust users/passwords
# as necessary
engine = create_engine('postgresql://postgres:temporary@localhost:5432/skedjit', client_encoding='utf8')
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata. Otherwise
    # you will have to import them first bifore calling init__db()
    import models
    Base.metadata.create_all(bind=engine)
 
