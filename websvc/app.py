import werzeug
from flask import Flask, request, render_template, escape
from database import db_session, init_db

app = Flask(__name__)

# create the database with the models specified
init_db()


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

@app.errorhandler(werzeug.exceptions.NotFound)
def not_found(description, response):
    """ Show 404 page when a resource is not found. """
    return render_template("not-found.html"), 404

@app.errorhandler(werzeug.exceptions.InternalServerError)
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


@app.route('/event', methods=['POST'])
def create_event():
    # extract form data
    # all can be blank except for
    # datetime. If we cannot make
    # a datetime out of the data
    # POSTed in, then the event
    # is useless.
    # verify that 

    # try creating object
    # catch ValueError
    #   return 400 BAD REQUEST

