from collections import Mapping
from unittest import TestCase

import message


class MessageTestCase(TestCase):

    """
    Base class for all message test cases.
    """

    def assertMessageEqual(self, message_text, expected):
        """Parse message string and compare to expected result."""
        parsed = message.parse(message_text)
        self.assertMessageDictsEqual(parsed, expected)

    def assertMessageDictsEqual(self, obj1, obj2):
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
            '',
            {},
        )

    def test_no_special_tokens(self):
        self.assertMessageEqual(
            'nothing to see here.',
            {},
        )

class MentionsTests(MessageTestCase):

    def test_simple_mention(self):
        self.assertMessageEqual(
            '@foobar',
            {'mentions': ['foobar']},
        )

    def test_mention_followed_by_punctuation(self):
        self.assertMessageEqual(
            '@foobaz.',
            {'mentions': ['foobaz']},
        )

    def test_nothing_returned_for_lone_at_symbol(self):
        self.assertMessageEqual(
            '@',
            {},
        )

    def test_nothing_returned_for_at_symbol_with_non_word_character(self):
        self.assertMessageEqual(
            '@!',
            {},
        )

    def test_multiple_mentions_match(self):
        self.assertMessageEqual(
            '@foo @bar @baz',
            {'mentions': ['foo', 'bar', 'baz']},
        )

    def test_matches_with_leading_space(self):
        self.assertMessageEqual(
            ' @foo',
            {'mentions': ['foo']},
        )

    def test_does_not_match_email_address(self):
        self.assertMessageEqual(
            'test@example.com',
            {},
        )
