import re


MENTION_REGEX = re.compile(r'(?:^|\s)@(\w+)')


def parse(msg_string):
    mentions = MENTION_REGEX.findall(msg_string)
    parsed = {
        key: value
        for key, value in (('mentions', mentions),)
        if value
    }
    return parsed
