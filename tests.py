from collections import Mapping
from itertools import product
import random
import unittest

import message


class MessageTestCase(unittest.TestCase):

    """
    Base class for all message test cases.
    """

    def assertMessageEqual(self, message_text, expected,
                           retrieve_url_titles=True):
        """Parse message string and compare to expected result."""
        parsed = message.parse(message_text, retrieve_url_titles)
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


class URLExtractionTests(MessageTestCase):

    GOOD_HOSTS = (
        '192.168.20.1',
        '[0123:4567:89AB:CDEF:0123:4567:89AB:CDEF]',
        '[123:4567:AB:CDEF:3:4567:89AB:CDEF]',
        '[0123:4567:89AB:CDEF:123:4567:192.168.0.1]',
        '[123:4567:AB:CDEF:3:4567:192.168.0.1]',
        '[0123:4567:89ab:cdef:0123:4567:89ab:cdef]',
        '[::4567:89AB:CDEF:0123:4567:89AB:CDEF]',
        '[::4567:89AB:CDEF:0123:4567:253.46.234.1]',
        '[::89AB:CDEF:0123:4567:89AB:CDEF]',
        '[::89AB:CDEF:0123:4567:253.46.234.1]',
        '[::CDEF:0123:4567:89AB:CDEF]',
        '[::CDEF:0123:4567:253.46.234.1]',
        '[::0123:4567:89AB:CDEF]',
        '[::0123:4567:253.46.234.1]',
        '[::4567:89AB:CDEF]',
        '[::4567:253.46.234.1]',
        '[::89AB:CDEF]',
        '[::253.46.234.1]',
        '[::CDEF]',
        '[::]',
        '[1234::89AB:CDEF:0123:4567:89AB:CDEF]',
        '[1234::89AB:CDEF:0123:4567:253.46.234.1]',
        '[1234::CDEF:0123:4567:89AB:CDEF]',
        '[1234::CDEF:0123:4567:253.46.234.1]',
        '[1234::0123:4567:89AB:CDEF]',
        '[1234::0123:4567:253.46.234.1]',
        '[1234::4567:89AB:CDEF]',
        '[1234::4567:253.46.234.1]',
        '[1234::89AB:CDEF]',
        '[1234::253.46.234.1]',
        '[1234::CDEF]',
        '[1234::]',
        '[1234:5678::CDEF:0123:4567:89AB:CDEF]',
        '[1234:5678::CDEF:0123:4567:253.46.234.1]',
        '[1234:5678::0123:4567:89AB:CDEF]',
        '[1234:5678::0123:4567:253.46.234.1]',
        '[1234:5678::4567:89AB:CDEF]',
        '[1234:5678::4567:253.46.234.1]',
        '[1234:5678::89AB:CDEF]',
        '[1234:5678::253.46.234.1]',
        '[1234:5678::CDEF]',
        '[1234:5678::]',
        '[1234:5678:90AB::0123:4567:89AB:CDEF]',
        '[1234:5678:90AB::0123:4567:253.46.234.1]',
        '[1234:5678:90AB::4567:89AB:CDEF]',
        '[1234:5678:90AB::4567:253.46.234.1]',
        '[1234:5678:90AB::89AB:CDEF]',
        '[1234:5678:90AB::253.46.234.1]',
        '[1234:5678:90AB::CDEF]',
        '[1234:5678:90AB::]',
        '[1234:5678:90AB:CDEF::4567:89AB:CDEF]',
        '[1234:5678:90AB:CDEF::4567:253.46.234.1]',
        '[1234:5678:90AB:CDEF::89AB:CDEF]',
        '[1234:5678:90AB:CDEF::253.46.234.1]',
        '[1234:5678:90AB:CDEF::CDEF]',
        '[1234:5678:90AB:CDEF::]',
        '[1234:5678:90AB:CDEF:FEDC::89AB:CDEF]',
        '[1234:5678:90AB:CDEF:FEDC::253.46.234.1]',
        '[1234:5678:90AB:CDEF:FEDC::CDEF]',
        '[1234:5678:90AB:CDEF:FEDC::]',
        '[1234:5678:90AB:CDEF:FEDC:BA09::CDEF]',
        '[1234:5678:90AB:CDEF:FEDC:BA09::]',
        '[1234:5678:90AB:CDEF:FEDC:BA09:8765::]',
        'www.example.com',
        'example.com',
        'new-top-level.domain',
        'internationalized-punycode-domain.xn--11b5bs3a9aj6g',
        'www.' + 'a' * 63 + '.com',
        'a.com',
        'trailing-number1.com',
    )
    BAD_HOSTS = (
        '::', # IPv6 without brackets
        '255.255.255.256', # IPv4 octet out of range
        '255.255.255.265', # IPv4 octet out of range
        '255.255.255.355', # IPv4 octet out of range
        '[0123:4567:89AB:CDEF:0123:4567:89AB:CDEG]', # IPv6 piece out of range
        '[0123:4567:89AB:CDEF:0123:4567:255.255.255.256]', # IPv6 bad ls32
        '[0123:4567:89AB:CDEF:0123:4567:89AB:CDEFE]', # IPv6 malformed piece
        '[0123:4567:89AB:CDEF:0123:4567:89AB]', # IPv6 not enough pieces
        '[0123:4567:89AB:CDEF:0123:4567:89AB:CDEF:0123]', # IPv6 too many
        '[0123:4567:89AB:CDEF:0123:4567:89AB::CDEF]', # IPv6 elision with too many
        '[0123::89AB:CDEF:0123::89AB:CDEG]', # IPv6 more than one elision
        'com', # top-level domain with no subdomain
        'www.' + 'a' * 64 + '.com', # DNS label with too many characters
        'www.-leading-dash.com', # leading dash in DNS label
        'www.trailing-dash-.com', # trailing dash in DNS label
        'www.1leading-number.com', # leading number in DNS label
    )
    GOOD_SCHEMES = (
        'http',
        'https',
    )
    GOOD_USER_INFO = (
        'foo',
        'foo:',
        'foo:b%20:%af%AFar',
        '%af%20%AFfoo:bar',
    )
    GOOD_PORTS = (
        '',
        '80',
        '4096',
    )
    GOOD_PATHS = (
        '',
        'moo/goo/gai/pan',
        'with/%20percent/encoded%ba/stuff',
        'with/trailing/slash/',
        'with/(some+parentheses)/yo',
        'with/(ending+parenthesis)',
    )
    GOOD_QUERIES = (
        'foo=bar',
        'foo=bar/with/slash&baz=',
    )
    GOOD_FRAGMENTS = (
        '',
        'question%20mark?/and/slash&ampersand#hashbrown',
    )

    @classmethod
    def generate_url_parts(cls, options, template, allow_missing=True):
        if allow_missing:
            yield ''
        for option in options:
            yield template.format(option)

    @classmethod
    def generate_urls(cls, hosts):
        scheme = cls.generate_url_parts(cls.GOOD_SCHEMES, '{0}://')
        userinfo = cls.generate_url_parts(cls.GOOD_USER_INFO, '{0}@')
        path = cls.generate_url_parts(cls.GOOD_PATHS, '/{0}')
        query = cls.generate_url_parts(cls.GOOD_QUERIES, '?{0}')
        fragment = cls.generate_url_parts(cls.GOOD_FRAGMENTS, '#{0}')
        for parts in product(scheme, userinfo, hosts, path, query, fragment):
            url = ''.join(parts)
            if not message.is_likely_email(url):
                yield url

    def test_good_hosts_match(self):
        for url in self.generate_urls(self.GOOD_HOSTS):
            self.assertMessageEqual(
                url,
                {'links': [{'url': url}]},
                retrieve_url_titles=False,
            )

    def test_bad_hosts_do_not_match(self):
        for url in self.generate_urls(self.BAD_HOSTS):
            self.assertMessageEqual(
                url,
                {},
                retrieve_url_titles=False,
            )

    def test_urls_with_trailing_sentence_punctuation(self):
        for punctuation in '.!?,;':
            for url in self.generate_urls(self.GOOD_HOSTS):
                text = 'Check out: {url}{punctuation} It is good.'.format(
                    url=url,
                    punctuation=punctuation,
                )
                self.assertMessageEqual(
                    text,
                    {'links': [{'url': url}]},
                    retrieve_url_titles=False,
                )

    def test_urls_enclosed_in_brackets(self):
        for template in ('({0})', '{{{0}}}', '<{0}>', '[{0}]', '(({0}))'):
            for url in self.generate_urls(self.GOOD_HOSTS):
                text = 'Cool site {0} Check it out.'.format(
                    template.format(url)
                )
                self.assertMessageEqual(
                    text,
                    {'links': [{'url': url}]},
                    retrieve_url_titles=False,
                )

    def test_multiple_urls_in_one_message(self):
        urls = random.sample(list(self.generate_urls(self.GOOD_HOSTS)), 5)
        text = 'have you checked [{0}], ({1}), <{2}>, {{{3}}} or {4}?'.format(
            *urls
        )
        self.assertMessageEqual(
            text,
            {'links': [{'url': url} for url in urls]},
            retrieve_url_titles=False,
        )


if __name__ == '__main__':
    unittest.main()

