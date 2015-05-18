from collections import Mapping
from unittest import TestCase

import message


class MessageTestCase(TestCase):

    """
    Base class for all message test cases.
    """

    def assertMessageEqual(self, obj1, obj2, msg=None):
        """Compare two parsed messages for equality and conformance."""
        for obj in (obj1, obj2):
            self.assertIsInstance(obj1, Mapping)
            self.assertTrue(
                set(obj.keys()) <= {'mentions', 'emoticons', 'links'},
                'extraneous keys in message dict'
            )
        for key in ('mentions', 'emoticons'):
            self.assertItemsEqual(obj1.get(key, []), obj2.get(key, []))
        self.assertItemsEqual(obj1.get('links', []), obj2.get('links', []))


class SimpleMessageTests(MessageTestCase):

    def test_empty_message(self):
        self.assertMessageEqual(
            message.parse(''),
            {},
        )

    def test_no_special_tokens(self):
        self.assertMessageEqual(
            message.parse('nothing to see here.'),
            {},
        )
