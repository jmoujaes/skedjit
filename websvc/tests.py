# -*- coding: utf-8 -*-

import app
import datetime
import logging
import mock
import unittest
from database import Database, Base
from models import Event
from flask import template_rendered, escape
from contextlib import contextmanager
from werkzeug.exceptions import InternalServerError

class TestApp(unittest.TestCase):

    def setUp(self):
        app.db = Database('postgresql://postgres:temporary@localhost:5432/test_skedjit', 'utf8')
        Base.metadata.create_all(app.db.engine)
        app.app.config['TESTING'] = True
        self.client = app.app.test_client()
        self.proper_post_data = {'name':'My Wonderful Event',
                                'description': 'This event will change the world!',
                                'access': 'access',
                                'year': '2017',
                                'month': '12',
                                'day': '12',
                                'hour':'10',
                                'minute': '0',
                                'ampm':'AM',
                                'timezone':'-5'}

    def tearDown(self):
        # close all connections before dropping all tables
        app.db.db_session.close_all()
        Base.metadata.drop_all(app.db.engine)


    def test_event_model_initialization_missing_values(self):
        """
        Assert that the Event model raises ValueError
        when required fields are None.
        """
        with self.assertRaises(ValueError):
            # missing name
            Event(name=None, datetime="not None", tz_offset=0, description="not None", access="not None")

        with self.assertRaises(ValueError):
            # missing datetime
            Event(name="not None", datetime=None, tz_offset=0, description="not None", access="not None")

        with self.assertRaises(ValueError):
            # missing tz_offset
            Event(name="not None", datetime="not None", tz_offset=None, description="not None", access="not None")

    def test_event_model_initialization_link_generation(self):
        """
        Assert that the Event model creates a link during
        initialization.
        """
        event = Event(name="not None", datetime="not None", tz_offset=0, description="not None", access="not None")

        self.assertIsNotNone(event.link)

    @mock.patch('tests.Event.create_link')
    def test_create_event_link_collision(self, mock_createlink):
        """
        Assert that we recreate links for an event
        if there is a link collision with an
        existing event in the database.
        """
        # mock create_link to create a unique link
        # the first time, then create the same
        # link a few times before finally
        # returning a unique link and
        # saving it to the database
        mock_createlink.side_effect = ['abcd', 'abcd', \
            'abcd', 'dcba']

        # send create request
        data = self.proper_post_data
        result = self.client.post('/create', data=data)
        self.assertEqual(result.status_code, 302)

        # create a new event, there will be a link collission
        # but we retry until there isn't
        result = self.client.post('/create', data=data)
        self.assertEqual(result.status_code, 302)

    def test_create_event_missing_date_info(self):
        """
        Assert that we send back a 400 BAD REQUEST
        if the date and time info POSTed in is
        missing.
        """
        data=self.proper_post_data

        data['year'] = None
        result = self.client.post('/create', data=data)
        self.assertEqual(result.status_code, 400)

        data['year'] = '2017'; data['month'] = None
        result = self.client.post('/create', data=data)
        self.assertEqual(result.status_code, 400)

        data['month'] = '12'; data['day'] = None
        result = self.client.post('/create', data=data)
        self.assertEqual(result.status_code, 400)

        data['day'] = '12'; data['hour'] = None
        result = self.client.post('/create', data=data)
        self.assertEqual(result.status_code, 400)

        data['hour'] = '10'; data['minute'] = None
        result = self.client.post('/create', data=data)
        self.assertEqual(result.status_code, 400)

        data['minute'] = '00'; data['timezone'] = None
        result = self.client.post('/create', data=data)
        self.assertEqual(result.status_code, 400)

        data['timezone'] = '0'; data['ampm'] = None
        result = self.client.post('/create', data=data)
        self.assertEqual(result.status_code, 400)

    def test_create_event_no_access(self):
        """
        Assert that we return a 400 BAD REQUEST
        when a user tries to create an event
        without providing an access code.
        """
        data = self.proper_post_data
        data.pop("access")
        response = self.client.post("/create", data=data)
        self.assertEqual(response.status_code, 400)

    def test_get_event_returns_event_object(self):
        """
        Assert that a GET request to /event/<link>
        returns the Event object with that link id
        """
        # create an event object and save it to the
        # database
        create = self.client.post('/create', data=self.proper_post_data)
        self.assertEqual(create.status_code, 302)

        # get the item we just created from the database
        event_obj = Event.query.filter(
                        Event.name==self.proper_post_data['name'],
                        Event.description==self.proper_post_data['description']).first()

        # send a GET request with the link, and assert that the
        # html template rendered has the object we created
        response = self.client.get('/event/%s' % event_obj.link)
        self.assertEqual(response.status_code, 200)
        self.assertIn(bytes(event_obj.name,'utf-8'), response.get_data())
        self.assertIn(bytes(event_obj.description,'utf-8'), response.get_data())

    def test_get_event_not_found(self):
        """
        Assert that a GET request to /event/<link>
        redirects to the 404 page when the
        object does not exist.
        """
        with captured_templates(app.app) as templates:
            self.client.get("/event/nonexistent")
            template, _ = templates[0]
            self.assertEqual(template.name, "not-found.html")

    def test_update_event(self):
        """
        Assert that we can successfuly update an event
        when we provide the correct access code.
        """
        # create event and follow redirect to view page
        response = self.client.post('/create', data=self.proper_post_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(bytes(self.proper_post_data['name'], 'utf-8'), response.get_data())

        # get the item we just created from the database
        event_obj = Event.query.filter(
                        Event.name==self.proper_post_data['name'],
                        Event.description==self.proper_post_data['description']).first()

        # update the event
        data = self.proper_post_data
        data['name'] = "Updated Event Name"
        data['description'] = "New description for this event."
        # note that we dont change the access code so it should
        # match what's in the database and allow us to update
        response = self.client.put('/event/%s' % event_obj.link, data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(bytes(data['name'], 'utf-8'), response.get_data())
        self.assertIn(bytes(data['description'], 'utf-8'), response.get_data())

    def test_update_event_not_found(self):
        """
        Assert that we show the 404 page when a
        user tries to update an event that does
        not exist.
        """
        data = self.proper_post_data
        with captured_templates(app.app) as templates:
            self.client.put("/event/nonexistent")
            template, _ = templates[0]
            self.assertEqual(template.name, "not-found.html")

    def test_update_event_no_access_code(self):
        """
        Assert that we return a 400 BAD REQUEST
        when a user tries to update an event
        without providing an access code.
        """
        # create an event
        data = self.proper_post_data
        self.client.post('/create', data=data, follow_redirects=True)
        event_obj = Event.query.filter(Event.name==data['name']).first()

        # try to update event without providing access code
        data.pop("access")
        response = self.client.put("/event/%s" % event_obj.link,
                                   data=data)
        self.assertEqual(response.status_code, 400)

    def test_update_event_invalid_access_code(self):
        """
        Assert that we can get return a 403 during update
        if the user provides an incorrect access code.
        """
        # create event and follow redirect to view page
        response = self.client.post('/create', data=self.proper_post_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(bytes(self.proper_post_data['name'], 'utf-8'), response.get_data())

        # get the item we just created from the database
        event_obj = Event.query.filter(
                        Event.name==self.proper_post_data['name'],
                        Event.description==self.proper_post_data['description']).first()

        # update the event
        data = self.proper_post_data
        data['name'] = "Updated Event Name"
        data['description'] = "New description for this event."
        data['access'] = "WRONG CODE"

        response = self.client.put('/event/%s' % event_obj.link, data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 403)

    def test_delete_event(self):
        """
        Assert that an event is removed from the database
        when the access code provided is correct.
        """
        # create event and follow redirect to view page
        response = self.client.post('/create', data=self.proper_post_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(bytes(self.proper_post_data['name'], 'utf-8'), response.get_data())

        # get the item we just created from the database
        event_obj = Event.query.filter(
                        Event.name==self.proper_post_data['name'],
                        Event.description==self.proper_post_data['description']).first()

        # send a delete request
        response = self.client.delete('/event/%s' % event_obj.link, data={'access':self.proper_post_data['access']}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_delete_nonexistent_event(self):
        """
        Assert that we show the 404 page when a
        user tries to delete an event that does
        not exist.
        """
        data = self.proper_post_data
        with captured_templates(app.app) as templates:
            self.client.delete("/event/nonexistent")
            template, _ = templates[0]
            self.assertEqual(template.name, "not-found.html")

    def test_delete_event_no_access_code(self):
        """
        Assert that we return a 400 BAD REQUEST
        when a user tries to delete an event
        without providing an access code.
        """
        # create an event
        data = self.proper_post_data
        self.client.post('/create', data=data, follow_redirects=True)
        event_obj = Event.query.filter(Event.name==data['name']).first()

        # try to delete event without providing access code
        data.pop("access")
        response = self.client.delete("/event/%s" % event_obj.link,
                                   data=data)
        self.assertEqual(response.status_code, 400)

    def test_delete_event_invalid_access_code(self):
        """
        Assert that we return 403 to requests that
        provide an incorrect access code.
        """
        # create event and follow redirect to view page
        response = self.client.post('/create', data=self.proper_post_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(bytes(self.proper_post_data['name'], 'utf-8'), response.get_data())

        # get the item we just created from the database
        event_obj = Event.query.filter(
                        Event.name==self.proper_post_data['name'],
                        Event.description==self.proper_post_data['description']).first()

        # send a delete request
        response = self.client.delete('/event/%s' % event_obj.link, data={'access':'WRONG ACCESS CODE'}, follow_redirects=True)
        self.assertEqual(response.status_code, 403)

    def test_objects_are_same_on_post_and_get(self):
        """
        Assert that the name/description/timestamp/
        timezone combination retrieved on GET is the 
        same as entered on POST.
        """
        # create event and follow redirect to view page
        response = self.client.post('/create', data=self.proper_post_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # get the item we just created from the database
        event_obj = Event.query.filter(
                        Event.name==self.proper_post_data['name'],
                        Event.description==self.proper_post_data['description']).first()

        # assert the data was stored in the database properly
        self.assertEqual(event_obj.tz_offset, int(self.proper_post_data['timezone']))
        self.assertEqual(event_obj.datetime.year, int(self.proper_post_data['year']))
        self.assertEqual(event_obj.datetime.month, int(self.proper_post_data['month']))
        self.assertEqual(event_obj.datetime.day, int(self.proper_post_data['day']))
        self.assertEqual(event_obj.datetime.minute, int(self.proper_post_data['minute']))

        # do a GET on the event and assert that the data
        # we send the template as context is the same as
        # what was POSTed in and the same as whats in the db
        with captured_templates(app.app) as templates:
            response = self.client.get('/event/%s' % event_obj.link)
            self.assertEqual(len(templates), 1)
            template, context = templates[0]
            data = context['data']
            self.assertEqual(data['datetime']['timezone'], self.proper_post_data['timezone'])
            self.assertEqual(data['datetime']['year'], self.proper_post_data['year'])
            self.assertEqual(data['datetime']['month'], self.proper_post_data['month'])
            self.assertEqual(data['datetime']['day'], self.proper_post_data['day'])
            self.assertEqual(data['datetime']['hour'], self.proper_post_data['hour'])
            self.assertEqual(data['datetime']['minute'], self.proper_post_data['minute'])
            self.assertEqual(data['datetime']['ampm'], self.proper_post_data['ampm'])

            self.assertEqual(data['name'], escape(self.proper_post_data['name']))
            self.assertEqual(data['description'], escape(self.proper_post_data['description']))

    def test_get_index(self):
        """
        Assert that a GET request to /
        returns the index.html page.
        """
        with captured_templates(app.app) as templates:
            # make a request to /
            response = self.client.get('/')
            template, _ = templates[0]
            self.assertEqual(template.name, "index.html")

    def test_not_found(self):
        """
        Assert that a GET request to /nonexistent
        returns the not-found.html page.
        """
        with captured_templates(app.app) as templates:
            # make a request to /nonexistent
            response = self.client.get('/nonexistent')
            template, _ = templates[0]
            self.assertEqual(template.name, "not-found.html")

    @mock.patch("app.escape")
    def test_error_page(self, mock_escape):
        """
        Assert that a 500 INTERNAL SERVER ERROR
        shows the error.html page.
        """
        mock_escape.side_effect = InternalServerError

        # create an event
        data = self.proper_post_data
        self.client.post('/create', data=data)

        # fetch the item we just created from the database
        event_obj = Event.query.filter(
                        Event.name==data['name'],
                        Event.description==data['description']).first()

        # assert the error.html page is shown on InternalServerError
        with captured_templates(app.app) as templates:
            self.client.get("/event/%s" % event_obj.link)
            template, _ = templates[0]
            self.assertEqual(template.name, "error.html")

    def test_get_create_page(self):
        """
        Assert that a GET request to /create
        returns the create.html page.
        """
        with captured_templates(app.app) as templates:
            # make a request to /create
            response = self.client.get('/create')
            template, _ = templates[0]
            self.assertEqual(template.name, "create.html")


# we use this to capture the template objects that are created by the views
@contextmanager
def captured_templates(app):
    recorded = []
    def record(sender, template, context, **extra):
        recorded.append((template, context))
    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)
