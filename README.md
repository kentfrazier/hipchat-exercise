# hipchat-exercise

A tool to extract mentions, emoticons and links from free-form chat messages.

## Using the `message` module

From the `message` module, import `parse` or `parse_to_json`. The former will
give you a nested Python structure of dictionaries and lists. `parse_to_json`
is a convenience wrapper that will dump the result of calling `parse` to a
JSON string.

This module does not have any external dependencies beyond Python 2.7 and
the Python standard library.

## Testing

You can run the full test suite by `cd`ing into the project directory and
running
    
    python tests.py

Since this runs through many thousands of message patterns, it takes
quite a while.

If you'd prefer to run the tests of only a particular `TestCase` subclass,
you can do so by running this from the project directory:

    python -m unittest tests.URLTitleLiveTests tests.MentionsTests

where you substitute the test classes you want to run for those in the example.
