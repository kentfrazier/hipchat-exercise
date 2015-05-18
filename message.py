import re


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
EMOTICON_REGEX = re.compile(r'\(([A-Za-z0-9]{1,15})\)')


def parse(message_text):
    mentions = MENTION_REGEX.findall(message_text)
    emoticons = EMOTICON_REGEX.findall(message_text)
    parsed = {
        key: value
        for key, value in (('mentions', mentions),
                           ('emoticons', emoticons))
        if value
    }
    return parsed
