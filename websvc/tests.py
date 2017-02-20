# -*- coding: utf-8 -*-

import app
from database import Database, Base
import datetime
from models import Event
import mock
import unittest

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
                                'minute': '00',
                                'ampm':'am',
                                'timezone':'-5'}

    def tearDown(self):
        Base.metadata.drop_all(app.db.engine)


    def test_event_model_initialization_missing_values(self):
        """
        Assert that the Event model raises ValueError
        when required fields are None.
        """
        with self.assertRaises(ValueError):
            # missing name
            Event(name=None, datetime="not None", description="not None", access="not None")

        with self.assertRaises(ValueError):
            # missing datetime
            Event(name="not None", datetime=None, description="not None", access="not None")

    def test_event_model_initialization_link_generation(self):
        """
        Assert that the Event model creates a link during
        initialization.
        """
        event = Event(name="not None", datetime="not None", description="not None", access="not None")

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
        result = self.client.post('/event', data={
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
        result = self.client.post('/event', data=data)
        self.assertEqual(result.status_code, 400)

        data['year'] = '2017'; data['month'] = None
        result = self.client.post('/event', data=data)
        self.assertEqual(result.status_code, 400)

        data['month'] = '12'; data['day'] = None
        result = self.client.post('/event', data=data)
        self.assertEqual(result.status_code, 400)

        data['day'] = '12'; data['hour'] = None
        result = self.client.post('/event', data=data)
        self.assertEqual(result.status_code, 400)

        data['hour'] = '10'; data['minute'] = None
        result = self.client.post('/event', data=data)
        self.assertEqual(result.status_code, 400)

        data['minute'] = '00'; data['ampm'] = None
        result = self.client.post('/event', data=data)
        self.assertEqual(result.status_code, 400)

        data['ampm'] = 'am'; data['timezone'] = None
        result = self.client.post('/event', data=data)
        self.assertEqual(result.status_code, 400)


    def test_get_event_returns_event_object(self):
        """
        Assert that a GET request to /event/<link>
        returns the Event object with that link id
        """
        # create an event object and save it to the
        # database
        create = self.client.post('/event', data=self.proper_post_data)
        self.assertEqual(create.status_code, 302)

        # get the item we just created from the database
        # so we can get its link
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
        response = self.client.post('/event', data=self.proper_post_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(bytes(self.proper_post_data['name'], 'utf-8'), response.get_data())

        # get the item we just created from the database
        # so we can get its link
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
        response = self.client.post('/event', data=self.proper_post_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(bytes(self.proper_post_data['name'], 'utf-8'), response.get_data())

        # get the item we just created from the database
        # so we can get its link
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


