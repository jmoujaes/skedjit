from flask import Flask
from database import db_session, init_db

app = Flask(__name__)

# create the database with the models specified
init_db()


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


@app.route('/')
def index():
    return 'Hello'
