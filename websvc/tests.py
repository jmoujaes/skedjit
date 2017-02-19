import unittest
import models

class TestApp(unittest.TestCase):

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
