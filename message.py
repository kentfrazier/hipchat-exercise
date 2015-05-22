from HTMLParser import HTMLParser
import json
from urlparse import urlsplit
from urllib2 import urlopen, URLError
import re


def _build_url_and_email_patterns():
    """
    Encapsulate the ugly details of building the URL regex.

    We are doing all this in a utility function to avoid polluting the module
    namespace with all the intermediate variables that are needed to create
    the very complicated final regular expressions. Everything is built in
    intermediate steps to increase the clarity and make it easier to modify
    and debug the various components of these regular expressions in the future.

    Most of the patterns and terminology here come from the URI specification:
        https://tools.ietf.org/html/rfc3986
    """

    # encoding lists from https://url.spec.whatwg.org/#percent-encoded-bytes
    simple_whitelist = {chr(code) for code in xrange(0x20, 0x7f)}
    default_whitelist = simple_whitelist - {' ', '"', '#', '<', '>', '?', '`'}
    password_whitelist = default_whitelist - {'/', '@', '\\'}
    username_whitelist = password_whitelist - {':'}
    query_whitelist = default_whitelist | {'?'}
    fragment_whitelist = query_whitelist | {'#'}

    char_class_template = r'(?:[{0}]|%[A-Fa-f0-9]{{2}})'

    url_chars = {
        key: char_class_template.format(re.escape(''.join(sorted(whitelist))))
        for key, whitelist in (
            ('default', default_whitelist),
            ('password', password_whitelist),
            ('username', username_whitelist),
            ('query', query_whitelist),
            ('fragment', fragment_whitelist),
        )
    }

    # Only supporting http and https URLs for now (if a schema is provided).
    scheme = r'https?'

    user_information = r'{username}*(?::{password}*)?'.format(**url_chars)

    ipv4_octet = r'(?:\b(?:1\d\d|2[0-4]\d|25[0-5]|[1-9]\d|\d)\b)'
    ipv4 = r'(?:{octet}(?:\.{octet}){{3}})'.format(octet=ipv4_octet)
    ipv6_piece = r'[A-Fa-f0-9]{1,4}'
    ipv6_last_32_bits = r'(?:{piece}:{piece}|{ipv4})'.format(
        piece=ipv6_piece,
        ipv4=ipv4,
    )
    ipv6 = r'''
    (?:
     (?:{piece}:){{6}}{ls32}
     |
     ::(?:{piece}:){{5}}{ls32}
     |
     (?:{piece})?::(?:{piece}:){{4}}{ls32}
     |
     (?:(?:{piece}:)?{piece})?::(?:{piece}:){{3}}{ls32}
     |
     (?:(?:{piece}:){{,2}}{piece})?::(?:{piece}:){{2}}{ls32}
     |
     (?:(?:{piece}:){{,3}}{piece})?::{piece}:{ls32}
     |
     (?:(?:{piece}:){{,4}}{piece})?::{ls32}
     |
     (?:(?:{piece}:){{,5}}{piece})?::{piece}
     |
     (?:(?:{piece}:){{,6}}{piece})?::
    )
    '''.format(
        piece=ipv6_piece,
        ls32=ipv6_last_32_bits,
    )

    # as defined by the DNS spec at http://tools.ietf.org/html/rfc1035
    dns_label = r'''
    (?<![A-Za-z0-9-])
    [A-Za-z](?:[A-Za-z0-9-]{,61}[A-Za-z0-9])?
    (?![A-Za-z0-9-])
    '''
    # while a top-level domain alone would be a valid URL, we choose to ignore
    # as a rare case that would generate a lot of false positives.
    registered_domain = r'{label}(?:\.{label})+'.format(label=dns_label)

    # at this time, we are supporting IPv4 and IPv6, but not IPvFuture
    # as defined in rfc3986
    host = r'(?:{ipv4}|\[{ipv6}\]|{registered_domain})'.format(
        ipv4=ipv4,
        ipv6=ipv6,
        registered_domain=registered_domain,
    )

    port = r'\d*'

    authority = r'(?:{user_information}@)?{host}(?:\:{port})?'.format(
        user_information=user_information,
        host=host,
        port=port,
    )

    path = r'{default}*'.format(**url_chars)
    query = r'{query}*'.format(**url_chars)
    fragment = r'{fragment}*'.format(**url_chars)

    # The authority is the only portion of the pattern that is mandatory. It
    # is assumed that relative URLs wouldn't make much sense for this
    # application, so a host is required.
    url_pattern = r'''
    (?:{scheme}://)?
    (?:{authority})
    (?:/{path})?
    (?:\?{query})?
    (?:\#{fragment})?
    '''.format(
        scheme=scheme,
        authority=authority,
        path=path,
        query=query,
        fragment=fragment,
    )

    url_regex = re.compile(url_pattern, re.VERBOSE)

    # -- EMAIL PATTERN --

    # ignores many complicated aspects of RFC5322, such as comments in local
    # parts, quoted-string form, and addresses containing Unicode above \u007f
    # Given the context, is should be acceptable to have the occasional false
    # negative from the resulting regex
    email_local_part = r'{char}+(?:\.{char}+)*'.format(
        char=r'''(?:[A-Za-z0-9#\-_~!\$&'\(\)\*\+,;=:]|%[A-Fa-f0-9]{2})'''
    )
    email_host = r'(?:\[(?:{ipv4}|{ipv6})\]|{registered_domain})'.format(
        ipv4=ipv4,
        ipv6=ipv6,
        registered_domain=registered_domain,
    )
    email_pattern = r'^{local}@{host}$'.format(
        local=email_local_part,
        host=email_host,
    )

    email_regex = re.compile(email_pattern, re.VERBOSE)

    # -- IPv6 HOST --
    ipv6_host_regex = re.compile(r'^\[{0}\]'.format(ipv6), re.VERBOSE)

    return url_regex, email_regex, ipv6_host_regex


# Mentions are assumed to be an at symbol (@) followed by any number of
# word characters (numbers, letters or underscores). To avoid false positives
# on things like email addresses and the credentials section of a URL, the @
# must either occur at the beginning of the string, or immediately preceded
# by whitespace.
MENTION_REGEX = re.compile(r'(?:^|\s)@(\w+)')


# Emoticons are assumed to be a string of 1-15 letters and numbers surrounded
# by a pair of parentheses. Any non-alphanumeric characters in the parentheses,
# or a sequence of more than 15 characters should not be considered an emoticon
# match.
# TODO: prevent emoticon matches within URLs
EMOTICON_REGEX = re.compile(r'\(([A-Za-z0-9]{1,15})\)')


# This pattern will only match well-formed HTTP and HTTPS URLs. Since
# the exercise is defined to need to retrieve the title from the URL, it
# doesn't make much sense to match schemes that are unlikely to point at
# an HTML document. Extracting URLs from text is a pretty tricky thing to do
# correctly since the spec is very permissive and allows things like
# whitespace and parentheses, and people may do things like leaving off the
# schema or following the URL with punctuation that could or could not
# legally be a part of the URL. A robust system will need to handle the
# huge number of new top-level domains, as well as internationalized
# domain names which might be in Unicode or in Punycode ASCII transcriptions.
#
# In a real system, I would try to find a library which has already
# adequately solved the problem and use it, but for the conceit of the
# interview, I will provide a solution that works for most simpler cases and
# doesn't concern itself with internationalized domains (unless they have
# already been converted to Punycode). I will try to be smart about things like
# trailing punctuation, while assuming that whitespace and some types of
# characters, while actually valid in URLs, are encoded if present.
URL_REGEX, EMAIL_REGEX, IPV6_HOST_REGEX = _build_url_and_email_patterns()


_ENDING_PUNCTUATION_REGEX = re.compile(r'[\.!\?,;]$')
_LEADING_BRACKET_REGEX = re.compile(r'^[\(\[\{]')
_ENDING_BRACKET_REGEX = re.compile(r'[\)\]\}]$')
_OPEN_BRACKET_MAP = {
    '[': ']',
    '(': ')',
    '{': '}',
    '<': '>',
}
_CLOSE_BRACKET_MAP = {v: k for k, v in _OPEN_BRACKET_MAP.iteritems()}


def is_likely_email(url):
    """
    Return whether the url passed in is likely to be an email address.
    """
    return EMAIL_REGEX.match(url) is not None


def extract_urls(message_text):
    """
    Extract and clean up URLs from the message text.
    """

    def scrub_brackets(url):
        """
        Intelligently remove leading and trailing brackets that are unlikely to
        be part of the actual URL, while leaving brackets that are inside the
        URL or are paired with an opening brace earlier in the URL.
        """
        # Strip any leading brackets unless it is an IPv6 host, which must be
        # surrounded by a single pair of square brackets.
        while (
            _LEADING_BRACKET_REGEX.match(url)
            and
            not IPV6_HOST_REGEX.match(url)
        ):
            url = url[1:]

        # if there are no trailing brackets, we are done
        if not _ENDING_BRACKET_REGEX.search(url):
            return url

        # otherwise, we need to figure out whether the trailing brackets are
        # matched with an open bracket of the correct type from earlier in
        # the URL
        expected_stack = []
        for c in reversed(url):
            if expected_stack and expected_stack[-1] == c:
                expected_stack.pop()
            else:
                open_bracket = _CLOSE_BRACKET_MAP.get(c)
                if open_bracket is not None:
                    expected_stack.append(open_bracket)
        return url[:len(url) - len(expected_stack)]

    def clean(url):
        """
        Clean up a URL.

        Args:
            url [str]: the unsanitized URL

        Returns:
            a sanitized URL, scrubbed of extraneous surrounding characters,
            or None if the URL should be suppressed because it doesn't appear
            to actually be one.
        """
        cleaned = scrub_brackets(
            _ENDING_PUNCTUATION_REGEX.sub('', url)
        )
        if is_likely_email(cleaned):
            return None
        return cleaned

    unfiltered = URL_REGEX.findall(message_text)
    return filter(None, map(clean, unfiltered))


class TitleExtractor(HTMLParser):

    """
    Parser to find and extract HTML titles from documents
    """

    def __init__(self):
        HTMLParser.__init__(self) # grumble grumble old-style class
        self.title = ''
        self.in_title_tag = False

    def handle_starttag(self, tag, attrs):
        if not self.title and tag.lower() == 'title':
            self.in_title_tag = True

    def handle_endtag(self, tag):
        if tag.lower() == 'title':
            self.in_title_tag = False

    def handle_data(self, data):
        if self.in_title_tag:
            self.title += data


def parse(message_text, retrieve_url_titles=True, url_timeout=0.2):
    """
    Parse message and extract mentions, emoticons and links.

    Args:
        message_text [str]: A string of text to be parsed
        retrieve_url_titles [bool]: whether or not to try to retrieve titles
            for detected links
        url_timeout [float]: timeout in seconds when trying to retrieve links

    Returns:
        a dict with up to three keys, depending on what is present in the
        message:
            mentions -> list of mentions (e.g. @steve yields 'steve')
            emoticons -> list of detected emoticons (e.g. (happy) yields 'happy')
            links -> a list of dicts, each of which contain the key 'url',
                and may contain 'title' as well if retrieve_url_titles is True
    """

    def get_title(url):
        """
        Retrieve resource at URL and extract title from HTML if present.

        Since this is non-critical functionality and not every URL will be
        valid or point at an HTML document, the function will return a blank
        title if it is unable to find one.

        Args:
            url [str]: the url to retrieve

        Returns:
            a 2-tuple where the first element is the input URL,
            and the second is the retrieved title, or an empty string if
            we were unable to retrieve it. Alternately, this function can
            return None to signify that the URL should be removed from the
            list.
        """
        # If no schema was provided in the URL, we'll assume it is http
        if urlsplit(url).scheme:
            schematized_url = url
        else:
            schematized_url = 'http://' + url

        try:
            response = urlopen(schematized_url, timeout=url_timeout)
            response_data = response.read()
        except:
            return (url, '')

        try:
            encoding = response.headers.getparam('charset')
            if encoding:
                response_data = response_data.decode(encoding)
        except:
            pass # shouldn't be an issue if we can't get encoding

        parser = TitleExtractor()

        try:
            parser.feed(response_data)
        except:
            return (url, '')

        return (url, parser.title)

    mentions = MENTION_REGEX.findall(message_text)
    emoticons = EMOTICON_REGEX.findall(message_text)
    urls = extract_urls(message_text)
    if retrieve_url_titles:
        # TODO: parallelize calls to get_title using threading or
        # multiprocessing
        links = [
            {'url': url, 'title': title}
            for url, title in filter(None, map(get_title, urls))
        ]
    else:
        links = [{'url': url} for url in urls]
    parsed = {
        key: value
        for key, value in (('mentions', mentions),
                           ('emoticons', emoticons),
                           ('links', links))
        if value
    }
    return parsed


def parse_to_json(message_text, retrieve_url_titles=True, url_timeout=0.2):
    """
    Parse message and return extracted values as a JSON string.
    """
    result = parse(message_text, retrieve_url_titles, url_timeout)
    return json.dumps(result)
