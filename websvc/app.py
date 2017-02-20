import bcrypt
import datetime
import logging
import werkzeug

from flask import Flask, jsonify, redirect, request, abort, \
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
    return render_template("not-found.html", 404)

@app.errorhandler(werkzeug.exceptions.InternalServerError)
def not_found(description, response):
    """ Show 500 page when an error occurs. """
    return render_template("error.html", 500)

@app.route('/')
def index():
    return 'Home Page'

@app.route('/event/<link>', methods=['GET', 'PUT', 'DELETE'])
def view_event(link):
    # if request is a GET
        # query event table using link
        # and return object in response
    if request.method=='GET':
        event = Event.query.filter(Event.link==link).first()
        if event is None: abort(404)
        to_ret = {'name': escape(event.name),
                    'description': escape(event.description),
                    'datetime': sendback_datetime(event.datetime),
                    'link': event.link}
        return render_template("view.html", data=to_ret)

    # if request is a PUT
        # query event table using link
        # verify access code
        # update object with form data
        # escape all data before storing/returning it
        # return updated object in response
    if request.method=='PUT':
        event = Event.query.filter(Event.link==link).first()
        given_access = request.form.get('access')
        if event is None: abort(404)
        if given_access is None: abort(400)

        #TODO revisit hashing and get to the bottom of why we must
        # do an encoding/decoding dance to get storage and comparison
        # of the hash to not blow up (see goo.gl/IpOfm4)
        given_access = given_access.encode('utf-8')
        hashed_access = event.access.encode('utf-8')
        if bcrypt.hashpw(given_access, hashed_access) != event.access.encode('utf-8'):
            abort(403)

        newmonth = request.form.get('month')
        newday = request.form.get('day')
        newyear = request.form.get('year')
        newhour = request.form.get('hour')
        newminute = request.form.get('minute')
        newampm = request.form.get('ampm')
        newtimezone = request.form.get('timezone')
        newname = request.form.get('name')
        newdescription = request.form.get('description')
        newdatetime_obj = create_datetime(newyear, newmonth, newday, newhour, newminute, newampm, newtimezone)
        if newdatetime_obj is None:
            abort(400)

        # update the event
        # dont have to set the access code or
        # or worry about link generation because the
        # object already exists in the database
        event.name = newname
        event.datetime=newdatetime_obj
        event.description=newdescription
        db.db_session.add(event)
        db.db_session.commit()

        return redirect(url_for('view_event', link=event.link))

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

    month = request.form.get('month')
    day = request.form.get('day')
    year = request.form.get('year')
    hour = request.form.get('hour')
    minute = request.form.get('minute')
    ampm = request.form.get('ampm')
    timezone = request.form.get('timezone')
    name = request.form.get('name')
    description = request.form.get('description')
    access = request.form.get('access')

    # deal with parsing datetime
    datetime_obj = create_datetime(year, month, day, hour, minute, ampm, timezone)
    if datetime_obj is None:
        abort(400)

    # hash the access code given
    if access is None: abort(400)

    #TODO revisit hashing and get to the bottom of why we must
    # do an encoding/decoding dance to get storage and comparison
    # of the hash to not blow up (see goo.gl/IpOfm4) 
    access = access.encode('utf-8')
    access = bcrypt.hashpw(access, bcrypt.gensalt()).decode('utf-8')

    # try, catch exception if link is not unique, then must recreate
    # make sure to log this
    retry = True
    while retry:
        try:
            # create object
            event = Event(name=name, datetime=datetime_obj, description=description, access=access)
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



def create_datetime(year, month, day, hour, minute, ampm, timezone):
    """
    Create a datetime object with timezone given the input
    parameters.
    :return: None if any parameters are missing or invalid
    :return: datetime object if successful
    """
    if year is None or month is None or day is None \
        or hour is None or minute is None \
        or ampm is None or timezone is None:
        return None

    try:
        year = int(year)
        month = int(month)
        day = int(day)
        hour = int(hour)
        minute = int(minute)
        timezone = int(timezone)
    except ValueError as error:
        logger.debug(error)
        return None

    ampm = ampm.upper()
    if ampm != 'AM' and ampm != 'PM':
        logger.debug("ampm was: %s" % ampm)
        return None

    if ampm == 'PM':
        hour = 12 + hour

    # -12 <= timezone <= 14
    if timezone < -12 or timezone > 14:
        return None

    utc_offset = datetime.timedelta(hours=timezone)
    timezone_obj = datetime.timezone(utc_offset)
    datetime_obj = datetime.datetime(year, month, day, hour, minute, tzinfo=timezone_obj)
    return datetime_obj


def sendback_datetime(sqlalchemy_timestamp):
    """
    Return a dictionary of the parts of a sqlalchemy timestamp object.
    This includes year, month, day, hour, minute, AM/PM,
    and timezone.
    :return: None if any parameters are missing or invalid
    :return: dictionary of timestamp object parts if successful
    """
    year = sqlalchemy_timestamp.year
    month = sqlalchemy_timestamp.month
    day = sqlalchemy_timestamp.day
    hour = sqlalchemy_timestamp.hour
    minute = sqlalchemy_timestamp.minute
    if hour < 12:
        ampm = "AM"
    else:
        ampm = "PM"

    # hacky way of getting the timezone offset
    # but I had to make some progress. Basically
    # get the string representation of the timestamp
    # and take the last 6 characters
    utc_offset = str(sqlalchemy_timestamp)[-6:]

    to_ret = {'year': year,
                'month': month,
                'day': day,
                'hour': hour,
                'minute': minute,
                'ampm': ampm,
                'timezone': utc_offset}
    return to_ret
