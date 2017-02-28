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
        result = self.client.post('/create', data={
                                    'name': 'name',
                                    'description': 'desc',
                                    'year': '2017',
                                    'month': '12',
                                    'day': '12',
                                    'hour': '10',
                                    'minute': '00',
                                    'ampm':'am',
                                    'timezone': '-5',
                                    'access': 'access'})
        # and assert that it sends redirect
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


    def test_ics_creation_format(self):
        """
        Assert that the create_ics helper function creates
        a proper icalendar file based on the ical spec.
        """
        # initialize event object
        datetime_obj = datetime.datetime(year=2017, month=1,
                        day=20, hour=18, minute=30)
        event_obj = Event(name="My Wonderful Event", 
                        datetime=datetime_obj, tz_offset=-5, 
                        description="Groundbreaking!", access="not None")

        # call create_ics function
        ics_data = event_obj.create_ics()
        # assert that each line contains data we expect
        lines = ics_data.split('\n')
        self.assertEqual(lines[0], 'BEGIN:VCALENDAR')
        self.assertEqual(lines[1], 'PRODID:-//SKEDJIT LLC//SKEDJ.IT')
        self.assertEqual(lines[2], 'VERSION:2.0')
        self.assertEqual(lines[3], 'BEGIN:VEVENT')
        self.assertEqual(lines[4], 'UID:{0}-{1}@skedj.it'
                                    .format(event_obj.dtstamp,
                                            event_obj.link))
        self.assertEqual(lines[5], 'DTSTAMP:{0}'
                                    .format(event_obj.dtstamp))
        self.assertEqual(lines[6], 'DTSTART:{0}'
                                    .format(event_obj.dtstart))
        self.assertEqual(lines[7], 'DTEND:{0}'
                                    .format(event_obj.dtend))
        self.assertEqual(lines[8], 'SUMMARY:{0}'
                                    .format(event_obj.name))
        self.assertEqual(lines[9], 'DESCRIPTION:{0}'
                                    .format(event_obj.description))
        self.assertEqual(lines[10], 'END:VEVENT')
        self.assertEqual(lines[11], 'END:VCALENDAR')


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
