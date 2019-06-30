"""
Module to hold common utilities.
"""

import subprocess

import local_debug

DEFAULT_POWER_CYCLE_DELAY = 2  # Time to allow for responses to be sent


def get_singular_or_plural(value, unit):
    """
    Returns the value with a singuar
    or plural form.

    Arguments:
        value {number} -- The number to determine the plurality.
        unit {string} -- The representation of the units.

    Returns:
        string -- The value with the unit in singular or plural form.
    """

    as_int = int(value)

    # Get rid of the decimal in
    # values like 1.0
    if as_int == value:
        value = as_int

    result = str(value) + " " + unit

    if value != 1:
        result += "s"

    return result


def get_time_text(number_of_seconds):
    """
    Returns the amount of time in the appropriate unit.
    >>> get_time_text(-1)
    'No time'
    >>> get_time_text(0)
    'No time'
    >>> get_time_text(1)
    '1 second'
    >>> get_time_text(30)
    '30 seconds'
    >>> get_time_text(59)
    '59 seconds'
    >>> get_time_text(60)
    '1 minute'
    >>> get_time_text(90)
    '1 minute'
    >>> get_time_text(120)
    '2 minutes'
    >>> get_time_text(600)
    '10 minutes'
    >>> get_time_text((60 * 60) - 1)
    '59 minutes'
    >>> get_time_text(60 * 60)
    '1 hour'
    >>> get_time_text((60 * 60) + 1)
    '1 hour'
    >>> get_time_text((60 * 60) * 1.5)
    '1.5 hours'
    >>> get_time_text((60 * 60) * 2)
    '2 hours'
    >>> get_time_text((60 * 60) * 23)
    '23 hours'
    >>> get_time_text((60 * 60) * 24)
    '1 day'
    >>> get_time_text((60 * 60) * 36)
    '1.5 days'
    >>> get_time_text((60 * 60) * 36.1234)
    '1.5 days'
    >>> get_time_text((60 * 60) * 48)
    '2 days'
    """

    if number_of_seconds <= 0:
        return "No time"

    if number_of_seconds < 60:
        return get_singular_or_plural(int(number_of_seconds), "second")

    number_of_minutes = number_of_seconds / 60

    if number_of_minutes < 60:
        return get_singular_or_plural(int(number_of_minutes), "minute")

    number_of_hours = round(number_of_minutes / 60.0, 1)

    if number_of_hours < 24:
        return get_singular_or_plural(number_of_hours, "hour")

    number_of_days = round(number_of_hours / 24.0, 1)

    return get_singular_or_plural(number_of_days, "day")


def escape(text):
    """
    Replaces escape sequences do they can be printed.

    Funny story. PyDoc can't unit test strings with a CR or LF...
    It gives a white space error.

    >>> escape("text")
    'text'
    >>> escape("")
    ''
    """

    return str(text).replace('\r', '\\r').replace('\n', '\\n').replace('\x1a', '\\x1a')


def get_cleaned_phone_number(dirty_number):
    """
    Removes any text from the phone number that
    could cause the command to not work.

    >>> get_cleaned_phone_number('"2061234567"')
    '2061234567'
    >>> get_cleaned_phone_number('+2061234567')
    '2061234567'
    >>> get_cleaned_phone_number('""+2061234567')
    '2061234567'
    >>> get_cleaned_phone_number('2061234567')
    '2061234567'
    >>> get_cleaned_phone_number('(206) 123-4567')
    '2061234567'
    >>> get_cleaned_phone_number(None)
    """
    if dirty_number is not None:
        return dirty_number.replace('+',
                                    '').replace('(',
                                                '').replace(')',
                                                            '').replace('-',
                                                                        '').replace(' ',
                                                                                    '').replace('"',
                                                                                                '')
    return None


def restart():
    """
    Restarts down the Pi.
    """

    if local_debug.IS_PI:
        subprocess.Popen(["sudo shutdown -r 30"],
                         shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)


def shutdown(seconds=30):
    """
    Shuts down the Pi.
    """

    if local_debug.IS_PI:
        subprocess.Popen(["sudo shutdown -h {0}".format(int(seconds))],
                         shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)


if __name__ == '__main__':
    import doctest

    print("Starting tests.")

    doctest.testmod()

    print("Tests finished")
