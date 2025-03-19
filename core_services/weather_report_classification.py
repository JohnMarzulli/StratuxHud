"""
Handles fetching and decoding weather.
"""

import re
from datetime import datetime, timedelta, timezone

INVALID = "INVALID"
INOP = "INOP"
VFR = "VFR"
MVFR = "M" + VFR
IFR = "IFR"
LIFR = "L" + IFR
NIGHT = "NIGHT"
NIGHT_DARK = "DARK"
SMOKE = "SMOKE"

DRIZZLE = "DRIZZLE"
RAIN = "RAIN"
HEAVY_RAIN = "HEAVY {}".format(RAIN)
SNOW = "SNOW"
ICE = "ICE"
UNKNOWN = "UNKNOWN"


def get_visibility(metar):
    """
    Returns the flight rules classification based on visibility from a RAW metar.

    Arguments:
        metar {string} -- The RAW weather report in METAR format.

    Returns:
        string -- The flight rules classification, or INVALID in case of an error.

    >>> get_visibility('KRNT 132053Z 33010KT 10SM SCT034 SCT041 23/14 A3001 RMK AO2 SLP165')
    'VFR'
    >>> get_visibility('KRNT 132053Z 33010KT 4SM SCT034 SCT041 23/14 A3001 RMK AO2 SLP165')
    'MVFR'
    >>> get_visibility('KRNT 132053Z 33010KT 3SM SCT034 SCT041 23/14 A3001 RMK AO2 SLP165')
    'MVFR'
    >>> get_visibility('KRNT 132053Z 33010KT 2 1/2SM SCT034 SCT041 23/14 A3001 RMK AO2 SLP165')
    'IFR'
    >>> get_visibility('KRNT 132053Z 33010KT 2SM SCT034 SCT041 23/14 A3001 RMK AO2 SLP165')
    'IFR'
    >>> get_visibility('KRNT 132053Z 33010KT 1SM SCT034 SCT041 23/14 A3001 RMK AO2 SLP165')
    'IFR'
    >>> get_visibility('KRNT 132053Z 33010KT 1/2SM SCT034 SCT041 23/14 A3001 RMK AO2 SLP165')
    'LIFR'
    >>> get_visibility('KGCC 231853Z AUTO 28011KT 20/12 A2991 RMK AO2 LTG DSNT SE RAB41RAEMM SLP085 P0000 T02000117 PWINO $')
    'VFR'
    >>> get_visibility('KVOK 251453Z 34004KT 10SM SCT008 OVC019 21/21 A2988 RMK AO2A SCT V BKN SLP119 53012')
    'VFR'
    """

    match = re.search("( [0-9] )?([0-9]/?[0-9]?SM)", metar)
    is_smoke = re.search(".* FU .*", metar) is not None
    # Not returning a visibility indicates UNLIMITED
    if match == None:
        return VFR
    (g1, g2) = match.groups()
    if g2 == None:
        return INVALID
    if g1 != None:
        if is_smoke:
            return SMOKE
        return IFR
    if "/" in g2:
        if is_smoke:
            return SMOKE
        return LIFR
    vis = int(re.sub("SM", "", g2))
    if vis < 3:
        if is_smoke:
            return SMOKE
        return IFR
    if vis <= 5:
        if is_smoke:
            return SMOKE

        return MVFR
    return VFR


def get_ceiling(metar):
    """
    Returns the flight rules classification based on ceiling from a RAW metar.

    Arguments:
        metar {string} -- The RAW weather report in METAR format.

    Returns:
        string -- The flight rules classification, or INVALID in case of an error.

    >>> get_ceiling('KRNT 132053Z 33010KT 10SM SCT034 SCT041 23/14 A3001 RMK AO2 SLP165')
    10000
    >>> get_ceiling('KRNT 132053Z 33010KT 4SM BKN041 SCT030 23/14 A3001 RMK AO2 SLP165')
    4100
    >>> get_ceiling('KRNT 132053Z 33010KT 4SM BKN041 OVC030 23/14 A3001 RMK AO2 SLP165')
    3000
    >>> get_ceiling('KRNT 132053Z 33010KT 4SM SCT041 OVC030 23/14 A3001 RMK AO2 SLP165')
    3000
    >>> get_ceiling('KRNT 132053Z 33010KT 3SM SCT041 BKN025 23/14 A3001 RMK AO2 SLP165')
    2500
    >>> get_ceiling('KRNT 132053Z 33010KT 2 1/2SM SCT041 BKN009 23/14 A3001 RMK AO2 SLP165')
    900
    >>> get_ceiling('KRNT 132053Z 33010KT 2 1/2SM SCT041 OVC009 23/14 A3001 RMK AO2 SLP165')
    900
    >>> get_ceiling('KRNT 132053Z 33010KT 2SM OVC004 23/14 A3001 RMK AO2 SLP165')
    400
    >>> get_ceiling('KRNT 132053Z 33010KT 2SM SCT010 OVC004 23/14 A3001 RMK AO2 SLP165')
    400
    >>> get_ceiling('KGCC 231853Z AUTO 28011KT 20/12 A2991 RMK AO2 LTG DSNT SE RAB41RAEMM SLP085 P0000 T02000117 PWINO $')
    10000
    >>> get_ceiling('KVOK 251453Z 34004KT 10SM SCT008 OVC019 21/21 A2988 RMK AO2A SCT V BKN SLP119 53012')
    1900
    """

    # Exclude the remarks from being parsed as the current
    # condition as they normally are for events that
    # are in the past.
    components = __get_main_metar_components__(metar)
    minimum_ceiling = 10000
    for component in components:
        if "BKN" in component or "OVC" in component:
            try:
                ceiling = int("".join(filter(str.isdigit, component))) * 100

                if ceiling < minimum_ceiling:
                    minimum_ceiling = ceiling
            except Exception as ex:
                pass
    return minimum_ceiling


def get_ceiling_category(ceiling):
    """
    Returns the flight rules classification based on the cloud ceiling.

    Arguments:
        ceiling {int} -- Number of feet the clouds are above the ground.

    Returns:
        string -- The flight rules classification.

    >>> get_ceiling_category(get_ceiling('KRNT 132053Z 33010KT 10SM SCT034 SCT041 23/14 A3001 RMK AO2 SLP165'))
    'VFR'
    >>> get_ceiling_category(get_ceiling('KRNT 132053Z 33010KT 4SM SCT041 OVC030 23/14 A3001 RMK AO2 SLP165'))
    'MVFR'
    >>> get_ceiling_category(get_ceiling('KRNT 132053Z 33010KT 3SM SCT041 BKN025 23/14 A3001 RMK AO2 SLP165'))
    'MVFR'
    >>> get_ceiling_category(get_ceiling('KRNT 132053Z 33010KT 2 1/2SM SCT041 BKN009 23/14 A3001 RMK AO2 SLP165'))
    'IFR'
    >>> get_ceiling_category(get_ceiling('KRNT 132053Z 33010KT 2 1/2SM SCT041 OVC009 23/14 A3001 RMK AO2 SLP165'))
    'IFR'
    >>> get_ceiling_category(get_ceiling('KRNT 132053Z 33010KT 2SM OVC004 23/14 A3001 RMK AO2 SLP165'))
    'LIFR'
    >>> get_ceiling_category(get_ceiling('KRNT 132053Z 33010KT 2SM SCT010 OVC004 23/14 A3001 RMK AO2 SLP165'))
    'LIFR'
    >>> get_ceiling_category(get_ceiling('KGCC 231853Z AUTO 28011KT 20/12 A2991 RMK AO2 LTG DSNT SE RAB41RAEMM SLP085 P0000 T02000117 PWINO $'))
    'VFR'
    >>> get_ceiling_category(get_ceiling('KVOK 251453Z 34004KT 10SM SCT008 OVC019 21/21 A2988 RMK AO2A SCT V BKN SLP119 53012'))
    'MVFR'
    """

    if ceiling <= 500:
        return LIFR
    if ceiling <= 1000:
        return IFR
    if ceiling <= 3000:
        return MVFR
    return VFR


def get_category(metar: str) -> str:
    """
    Returns the flight rules classification based on the entire RAW metar.

    Arguments:
        metar {string} -- The RAW weather report in METAR format.

    Returns:
        string -- The flight rules classification, or INVALID in case of an error.

    >>> get_category('KRNT 132053Z 33010KT 10SM SCT034 SCT041 23/14 A3001 RMK AO2 SLP165')
    'VFR'
    >>> get_category('KRNT 132053Z 33010KT 4SM SCT041 OVC030 23/14 A3001 RMK AO2 SLP165')
    'MVFR'
    >>> get_category('KRNT 132053Z 33010KT 3SM SCT041 BKN025 23/14 A3001 RMK AO2 SLP165')
    'MVFR'
    >>> get_category('KRNT 132053Z 33010KT 2 1/2SM SCT041 BKN009 23/14 A3001 RMK AO2 SLP165')
    'IFR'
    >>> get_category('KRNT 132053Z 33010KT 2 1/2SM SCT041 OVC009 23/14 A3001 RMK AO2 SLP165')
    'IFR'
    >>> get_category('KRNT 132053Z 33010KT 2SM OVC004 23/14 A3001 RMK AO2 SLP165')
    'LIFR'
    >>> get_category('KRNT 132053Z 33010KT 2SM SCT010 OVC004 23/14 A3001 RMK AO2 SLP165')
    'LIFR'
    >>> get_category('KGCC 231853Z AUTO 28011KT 20/12 A2991 RMK AO2 LTG DSNT SE RAB41RAEMM SLP085 P0000 T02000117 PWINO $')
    'VFR'
    >>> get_category('KVOK 251453Z 34004KT 10SM SCT008 OVC019 21/21 A2988 RMK AO2A SCT V BKN SLP119 53012')
    'MVFR'
    """
    if metar is None or metar == INVALID:
        return INVALID

    if len(metar) < 4:
        return INVALID

    vis = get_visibility(metar)
    ceiling = get_ceiling_category(get_ceiling(metar))
    if ceiling == INVALID or vis == INVALID:
        return INVALID
    if vis == SMOKE:
        return SMOKE
    if vis == LIFR or ceiling == LIFR:
        return LIFR
    if vis == IFR or ceiling == IFR:
        return IFR
    if vis == MVFR or ceiling == MVFR:
        return MVFR

    return VFR


def __get_main_metar_components__(metar: str) -> list:
    if metar is None:
        return None

    return metar.split("RMK")[0].split(" ")[1:]


if __name__ == "__main__":
    import doctest

    print("Starting Weather Report Classification tests.")

    doctest.testmod()

    print("Tests Weather Report Classification finished")
