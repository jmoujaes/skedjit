import app
from database import Database, Base
import datetime
import models
import mock
import unittest

class TestApp(unittest.TestCase):

    def setUp(self):
        app.db = Database('postgresql://postgres:temporary@localhost:5432/test_skedjit', 'utf8')
        Base.metadata.create_all(app.db.engine)
        app.app.config['TESTING'] = True
        self.client = app.app.test_client()

    def tearDown(self):
        Base.metadata.drop_all(app.db.engine)


    def test_event_model_initialization_missing_values(self):
        """
        Assert that the Event model raises ValueError
        when required fields are None.
        """
        with self.assertRaises(ValueError):
            # missing name
            models.Event(name=None, datetime="not None", description="not None", access="not None")

        with self.assertRaises(ValueError):
            # missing datetime
            models.Event(name="not None", datetime=None, description="not None", access="not None")

    def test_event_model_initialization_link_generation(self):
        """
        Assert that the Event model creates a link during
        initialization.
        """
        event = models.Event(name="not None", datetime="not None", description="not None", access="not None")

        self.assertIsNotNone(event.link)

    @mock.patch('models.Event.create_link')
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
        data={'name':'name', 'description': 'desc',
                'access': 'access',
                'year': None,
                'month': '12',
                'day': '12',
                'hour':'10',
                'minute': '00',
                'ampm':'am',
                'timezone':'EST'}

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


