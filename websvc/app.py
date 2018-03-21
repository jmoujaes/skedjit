import bcrypt
import datetime
import logging
import werkzeug

from flask import Flask, jsonify, redirect, request, abort, \
                    render_template, escape, url_for
from sqlalchemy import exc
from database import Database
from models import Event

# create instance of app
app = Flask(__name__)

# set up logging
fh = logging.FileHandler("webapp.log")
fh.setFormatter(logging.Formatter(
    '%(asctime)s %(filename)s:%(lineno)d %(levelname)s: %(message)s'))
fh.setLevel(logging.DEBUG)
app.logger.addHandler(fh)

# create the database with the models specified
db = Database('postgresql://postgres:temporary@localhost:5432/skedjit', 'utf8')


@app.teardown_appcontext
def shutdown_session(exception=None):
    db.db_session.remove()

@app.errorhandler(werkzeug.exceptions.NotFound)
def not_found(response):
    """ Show 404 page when a resource is not found. """
    return render_template("not-found.html")

@app.errorhandler(werkzeug.exceptions.InternalServerError)
def error(response):
    """ Show 500 page when an error occurs. """
    return render_template("error.html")

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/event/<link>', methods=['GET', 'PUT', 'DELETE'])
def view_event(link):
    # if request is a GET
        # query event table using link
        # and return object in response
    if request.method=='GET':
        app.logger.info("Retrieving event %s" % link)
        event = Event.query.filter(Event.link==link).first()
        if event is None:
            app.logger.debug("event not found")
            abort(404)

        to_ret = {'name': escape(event.name),
                    'description': escape(event.description),
                    'datetime': sendback_datetime(event.datetime, event.tz_offset),
                    'link': event.link}
        return render_template("view.html", data=to_ret)

    # if request is a PUT
        # query event table using link
        # verify access code
        # update object with form data
        # escape all data before storing/returning it
        # return updated object in response
    if request.method=='PUT':
        app.logger.info("Updating event %s" % link)
        event = Event.query.filter(Event.link==link).first()
        given_access = request.form.get('access')
        if event is None:
            app.logger.debug("event not found.")
            abort(404)
        if given_access is None:
            app.logger.debug("user did not supply access code.")
            abort(400)

        if check_access(event, given_access) is False:
            abort(403)

        newmonth = request.form.get('month')
        newday = request.form.get('day')
        newyear = request.form.get('year')
        newhour = request.form.get('hour')
        newminute = request.form.get('minute')
        newampm = request.form.get('ampm')
        newtz_offset = request.form.get('timezone')
        newname = request.form.get('name')
        newdescription = request.form.get('description')
        newdatetime_obj, newtz_offset = create_datetime(newyear, newmonth, newday, newhour, newminute, newampm, newtz_offset)
        if newdatetime_obj is None:
            app.logger.debug("newdatetime_obj is None")
            abort(400)

        # update the event
        # dont have to set the access code or
        # or worry about link generation because the
        # object already exists in the database
        event.name = newname
        event.datetime = newdatetime_obj
        event.tz_offset = newtz_offset
        event.description = newdescription
        db.db_session.add(event)
        db.db_session.commit()

        return redirect(url_for('view_event', link=event.link))

    # if request is a DELETE
        # query event table using link
        # verify access code
        # delete record from database
        # return status in response
    if request.method=='DELETE':
        app.logger.info("Deleting event %s" % link)
        event = Event.query.filter(Event.link==link).first()
        given_access = request.form.get('access')
        if event is None:
            app.logger.debug("event not found.")
            abort(404)
        if given_access is None:
            app.logger.debug("user did not supply access code.")
            abort(400)

        if check_access(event, given_access) is True:
            Event.query.filter(Event.link==link).delete()
            db.db_session.commit()
            return "Success", 200

        else: abort(403)

    # otherwise return 400 BAD REQUEST
    # or a more appropriate message
    return 400


@app.route('/create', methods=['GET', 'POST'])
def create_event():
    if request.method == 'GET':
        return render_template("create.html")

    elif request.method == 'POST':
        app.logger.info("Creating event.")
        # extract form data
        # all can be blank except for
        # datetime.
        month = request.form.get('month')
        day = request.form.get('day')
        year = request.form.get('year')
        hour = request.form.get('hour')
        minute = request.form.get('minute')
        ampm = request.form.get('ampm')
        tz_offset = request.form.get('timezone')
        name = request.form.get('name')
        description = request.form.get('description')
        access = request.form.get('access')
        app.logger.debug("name: %s description: %s" % (name, description))

        # deal with parsing datetime
        datetime_obj, tz_offset = create_datetime(year, month, day, hour, minute, ampm, tz_offset)
        if datetime_obj is None:
            app.logger.debug("datetime_obj is None")
            abort(400)

        # hash the access code given
        #TODO revisit hashing and get to the bottom of why we must
        # do an encoding/decoding dance to get storage and comparison
        # of the hash to not blow up (see goo.gl/IpOfm4) 
        if access is None:
            app.logger.debug("access is None")
            abort(400)

        access = access.encode('utf-8')
        access = bcrypt.hashpw(access, bcrypt.gensalt()).decode('utf-8')

        # try, catch exception if link is not unique, then must recreate
        # make sure to log this
        retry = True
        while retry:
            try:
                # create object
                event = Event(name=name, datetime=datetime_obj, tz_offset=tz_offset, description=description, access=access)
                db.db_session.add(event)
                db.db_session.commit()
                retry = False
            except exc.IntegrityError as error:
                if 'duplicate key' in str(error) \
                    and 'events_link_key' in str(error):
                    app.logger.warning("Collision in link hash %s" % event.link)
                    db.db_session.rollback()

        return redirect(url_for('view_event', link=event.link))

    # request.method is neither GET nor POST
    else: abort(400)


def create_datetime(year, month, day, hour, minute, ampm, tz_offset):
    """
    Create a datetime object given the input parameters.
    :return: None if any parameters are missing or invalid
    :return: (datetime_object, tz_info) if successful
    """
    app.logger.debug("year: %s month: %s day: %s " \
        "hour: %s minute: %s ampm: %s tz_offset: %s" \
        % (year, month, day, hour, minute, ampm, tz_offset))
    if year is None or month is None or day is None \
        or hour is None or minute is None \
        or ampm is None or tz_offset is None:
        return (None, None)

    try:
        year = int(year)
        month = int(month)
        day = int(day)
        hour = int(hour)
        minute = int(minute)
        tz_offset = int(tz_offset)
    except ValueError as error:
        app.logger.error(error)
        return (None, None)

    ampm = ampm.upper()
    if ampm != 'AM' and ampm != 'PM':
        app.logger.debug("ampm was: %s" % ampm)
        return (None, None)

    if ampm == 'PM':
        hour = 12 + hour

    # -12 <= timezone <= 14
    if tz_offset < -12 or tz_offset > 14:
        app.logger.debug("timezone offset was not within -12 to 14 range")
        return (None, None)

    datetime_obj = datetime.datetime(year, month, day, hour, minute)
    return (datetime_obj, tz_offset)


def sendback_datetime(sqlalchemy_timestamp, tz_offset):
    """
    Return a dictionary of the parts of a sqlalchemy timestamp object.
    This includes year, month, day, hour, minute, AM/PM,
    and timezone offset.
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

    to_ret = {'year': str(year),
                'month': str(month),
                'day': str(day),
                'hour': str(hour),
                'minute': str(minute),
                'ampm': ampm,
                'timezone': str(tz_offset)}
    return to_ret


def check_access(event_object, given_access_code):
    """
    Return True if the given access code matches
    that of the event.
    Return False otherwise.
    """
    #TODO revisit hashing and get to the bottom of why we must
    # do an encoding/decoding dance to get storage and comparison
    # of the hash to not blow up (see goo.gl/IpOfm4)
    app.logger.debug("verifiying access code.")
    if isinstance(given_access_code, str):
        given_access_code = given_access_code.encode('utf-8')
    if isinstance(event_object.access, str):
        event_object.access = event_object.access.encode('utf-8')

    if bcrypt.hashpw(given_access_code, event_object.access) == event_object.access:
        app.logger.debug("access granted")
        return True
    else:
        app.logger.debug("access denied")
        return False
