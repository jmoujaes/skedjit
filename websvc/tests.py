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
                                    'datetime': datetime.datetime.now(),
                                    'access': 'access'})
        # and assert that it sends redirect
        self.assertEqual(result.status_code, 302)


