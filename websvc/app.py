import logging
import werkzeug

from flask import Flask, redirect, request, \
                    render_template, escape, url_for
from sqlalchemy import exc
from database import Database
#from database import db_session, init_db
from models import Event

logger = logging.getLogger(__name__)

app = Flask(__name__)

# create the database with the models specified
db = Database('postgresql://postgres:temporary@localhost:5432/skedjit', 'utf8')


@app.teardown_appcontext
def shutdown_session(exception=None):
    db.db_session.remove()

@app.errorhandler(werkzeug.exceptions.NotFound)
def not_found(description, response):
    """ Show 404 page when a resource is not found. """
    return render_template("not-found.html"), 404

@app.errorhandler(werkzeug.exceptions.InternalServerError)
def not_found(description, response):
    """ Show 500 page when an error occurs. """
    return render_template("error.html"), 500

@app.route('/')
def index():
    return 'Home Page'

@app.route('/event/<link>', methods=['GET', 'PUT', 'DELETE'])
def view_event(link):
    # if request is a GET
        # query event table using link
        # and return object in response

    # if request is a PUT
        # query event table using link
        # verify access code
        # update object with form data
        # escape all data before storing/returning it
        # return updated object in response

    # if request is a DELETE
        # query event table using link
        # verify access code
        # delete record from database
        # return status in response

    # otherwise return 400 BAD REQUEST
    # or a more appropriate message
    return 'Success', 200

@app.route('/event', methods=['POST'])
def create_event():
    # extract form data
    # all can be blank except for
    # datetime.
    if request.method != 'POST':
        abort(400)

    name = request.form.get('name')
    datetime = request.form.get('datetime')
    description = request.form.get('description')
    access = request.form.get('access')

    # If we cannot make
    # a datetime out of the data
    # POSTed in, then the event
    # is useless.Verify that.
    if datetime is None:
        abort(400)
    # deal with parsing datetime

    # try, catch exception if link is not unique, then must recreate
    # make sure to log this
    retry = True
    while retry:
        try:
            # create object
            event = Event(name=name, datetime=datetime, description=description, access=access)
            db.db_session.add(event)
            db.db_session.commit()
            retry = False
        except exc.IntegrityError as error:
            if 'duplicate key' in str(error) \
                and 'events_link_key' in str(error):
                logger.warning("Collision in link hash %s" % event.link)
                db.db_session.rollback()

    # catch ValueError
    #   return 400 BAD REQUEST
    return redirect(url_for('view_event', link=event.link))
