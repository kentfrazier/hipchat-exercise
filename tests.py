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

    def test_matches_before_normal_text(self):
        self.assertMessageEqual(
            '@foo Good to see you',
            {'mentions': ['foo']},
        )

    def test_matches_after_normal_text(self):
        self.assertMessageEqual(
            'And you as well! @bar',
            {'mentions': ['bar']},
        )

    def test_matches_in_the_middle_of_text(self):
        self.assertMessageEqual(
            'Thanks! @foo I hope you are well!',
            {'mentions': ['foo']},
        )

    def test_matches_when_on_both_sides_of_text(self):
        self.assertMessageEqual(
            '@bob can you talk to @steve about stuff?',
            {'mentions': ['bob', 'steve']},
        )


class EmoticonsTests(MessageTestCase):

    def test_simple_emoticon(self):
        self.assertMessageEqual(
            '(success)',
            {'emoticons': ['success']},
        )

    def test_empty_parens_do_not_match(self):
        self.assertMessageEqual(
            '()',
            {},
        )

    def test_1_to_15_characters_match(self):
        for count in xrange(1, 16):
            match = 'a' * count
            self.assertMessageEqual(
                '({0})'.format(match),
                {'emoticons': [match]},
            )
        self.assertMessageEqual(
            '()',
            {},
        )

    def test_16_characters_does_not_match(self):
        self.assertMessageEqual(
            '({0})'.format('a' * 16),
            {},
        )

    def test_parens_with_non_alphanumeric_chars_do_not_match(self):
        self.assertMessageEqual(
            '(foo_bar) (foo bar)',
            {},
        )

    def test_multiple_emoticons_match(self):
        self.assertMessageEqual(
            '(foo)(bar) (baz)',
            {'emoticons': ['foo', 'bar', 'baz']},
        )

    def test_matches_before_normal_text(self):
        self.assertMessageEqual(
            '(foo)Good to see you',
            {'emoticons': ['foo']},
        )

    def test_matches_after_normal_text(self):
        self.assertMessageEqual(
            'And you as well! (bar)',
            {'emoticons': ['bar']},
        )

    def test_matches_in_the_middle_of_text(self):
        self.assertMessageEqual(
            'Thanks! (happy) I hope you are well!',
            {'emoticons': ['happy']},
        )

    def test_matches_when_on_both_sides_of_text(self):
        self.assertMessageEqual(
            '(beaming) You are so kind! (hugs)',
            {'emoticons': ['beaming', 'hugs']},
        )

