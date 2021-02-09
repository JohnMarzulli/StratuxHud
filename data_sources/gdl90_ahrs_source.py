from datetime import datetime

import requests
from common_utils import data_cache, logging_object
from common_utils.logger import HudLogger
from configuration import configuration

from data_sources import ahrs_data

MAX_AVIONICS_AGE = 0.3
MAX_STRATUX_AHRS_AGE = 2.0
AVIONICS_TIMEOUT = 0.2


class AhrsStratux(logging_object.LoggingObject):
    """
    Class to pull actual AHRS data from a Stratux (or Stratus)
    """

    def __get_value__(
        self,
        ahrs_json: dict,
        key: str,
        default
    ):
        """
        Safely return the value from the AHRS blob

        Arguments:
            ahrs_json {[type]} -- [description]
            key {[type]} -- [description]
            default {[type]} -- [description]

        Returns:
            [type] -- [description]
        """

        if key in ahrs_json:
            try:
                return ahrs_json[key]

            except KeyboardInterrupt:
                raise
            except SystemExit:
                raise
            except:
                return default

        return default

    def __get_value_with_fallback__(
        self,
        ahrs_json: dict,
        keys: list,
        default
    ):
        if keys is None:
            return default

        values = [self.__get_value__(ahrs_json, key, default) for key in keys]
        values = list(filter(lambda x: x != default, values))

        return values[0] if values is not None and len(values) > 0 else default

    def __decode_situation__(
        self,
        ahrs_json: str
    ) -> dict:
        """
        Decodes AHRS results from getSituation into a package that is
        usable by the HUD.

        The package may be from a single source, or from combined sources.

        Arguments:
            ahrs_json {dict} -- The AHRS package to decode

        Returns:
            AhrsData -- The decoded value (if it could be decoded), or otherwise a safe package.
        """
        new_ahrs_data = ahrs_data.AhrsData()

        system_utc_time = str(datetime.utcnow())

        new_ahrs_data.is_avionics_source = "Service" in ahrs_json\
            and "ToHud" in ahrs_json["Service"]

        new_ahrs_data.gps_online = self.__get_value__(
            ahrs_json,
            'GPSFixQuality',
            0) > 0

        new_ahrs_data.roll = self.__get_value__(
            ahrs_json,
            'AHRSRoll',
            0.0)
        new_ahrs_data.pitch = self.__get_value__(
            ahrs_json,
            'AHRSPitch',
            0.0)
        new_ahrs_data.compass_heading = self.__get_value__(
            ahrs_json,
            'AHRSGyroHeading',
            1080)  # anything above 360 indicates "not available"
        new_ahrs_data.gps_heading = self.__get_value__(
            ahrs_json,
            'GPSTrueCourse',
            ahrs_data.NOT_AVAILABLE)
        new_ahrs_data.alt = self.__get_value_with_fallback__(
            ahrs_json,
            ['Altitude', 'GPSAltitudeMSL', 'BaroPressureAltitude'],
            ahrs_data.NOT_AVAILABLE)
        new_ahrs_data.position = (self.__get_value__(ahrs_json, 'GPSLatitude', None),
                                  self.__get_value__(ahrs_json, 'GPSLongitude', None)) if new_ahrs_data.gps_online else (None, None)
        new_ahrs_data.vertical_speed = self.__get_value_with_fallback__(
            ahrs_json,
            ["BaroVerticalSpeed",
             'GPSVerticalSpeed'],
            ahrs_data.NOT_AVAILABLE)
        new_ahrs_data.airspeed = self.__get_value__(
            ahrs_json,
            'AHRSAirspeed',
            ahrs_data.NOT_AVAILABLE)
        new_ahrs_data.groundspeed = self.__get_value__(
            ahrs_json,
            'GPSGroundSpeed',
            ahrs_data.NOT_AVAILABLE) if new_ahrs_data.gps_online else ahrs_data.NOT_AVAILABLE
        new_ahrs_data.g_load = self.__get_value__(
            ahrs_json,
            'AHRSGLoad',
            ahrs_data.NOT_AVAILABLE)
        new_ahrs_data.utc_time = self.__get_value__(
            ahrs_json,
            'GPSTime',
            system_utc_time)

        if new_ahrs_data.g_load > self.__max_gs__:
            self.__max_gs__ = new_ahrs_data.g_load

        if new_ahrs_data.g_load < self.__min_gs__:
            self.__min_gs__ = new_ahrs_data.g_load

        new_ahrs_data.min_g = self.__min_gs__
        new_ahrs_data.max_g = self.__max_gs__

        return new_ahrs_data

        # SAMPLE FULL JSON
        #
        # {
        #     "GPSLastFixSinceMidnightUTC": 26705.5,
        #     "GPSLatitude": 47.69124,
        #     "GPSLongitude": -122.36745,
        #     "GPSFixQuality": 2,
        #     "GPSHeightAboveEllipsoid": 239.07481,
        #     "GPSGeoidSep": -61.35171,
        #     "GPSSatellites": 11,
        #     "GPSSatellitesTracked": 18,
        #     "GPSSatellitesSeen": 14,
        #     "GPSHorizontalAccuracy": 2.2,
        #     "GPSNACp": 11,
        #     "GPSAltitudeMSL": 300.4265,
        #     "GPSVerticalAccuracy": 4.4,
        #     "GPSVerticalSpeed": -0.39041996,
        #     "GPSLastFixLocalTime": "0001-01-01T00:59:50.37Z",
        #     "GPSTrueCourse": 0,
        #     "GPSTurnRate": 0,
        #     "GPSGroundSpeed": 0.09990055628746748,
        #     "GPSLastGroundTrackTime": "0001-01-01T00:59:50.37Z",
        #     "GPSTime": "2019-06-03T07:25:04.6Z",
        #     "GPSLastGPSTimeStratuxTime": "0001-01-01T00:59:49.47Z",
        #     "GPSLastValidNMEAMessageTime": "0001-01-01T00:59:50.37Z",
        #     "GPSLastValidNMEAMessage": "$PUBX,00,072505.50,4741.47430,N,12222.04701,W,72.870,D3,1.1,2.2,0.185,289.03,0.119,,1.07,1.64,1.20,11,0,0*79",
        #     "GPSPositionSampleRate": 0,
        #     "BaroTemperature": 36.12,
        #     "BaroPressureAltitude": 243.29552,
        #     "BaroVerticalSpeed": 1.0008061,
        #     "BaroLastMeasurementTime": "0001-01-01T00:59:50.36Z",
        #     "AHRSPitch": -0.04836615637379224,
        #     "AHRSRoll": -0.36678574817765497,
        #     "AHRSGyroHeading": 3276.7,
        #     "AHRSMagHeading": 3276.7,
        #     "AHRSSlipSkid": -0.05914792289016943,
        #     "AHRSTurnRate": 3276.7,
        #     "AHRSGLoad": 0.9988800063331206,
        #     "AHRSGLoadMin": -0.0006306474610048851,
        #     "AHRSGLoadMax": 1.0107446345882283,
        #     "AHRSLastAttitudeTime": "0001-01-01T00:59:50.43Z",
        #     "AHRSStatus": 7
        # }

    def update(
        self
    ):
        """
        Attempts to get the AHRS data from the Stratux source.
        """
        self.__stratux_ahrs_cache__.update()

    def update_avionics(
        self
    ):
        """
        Attempts to get the AHRS data from the avionics source.
        """
        self.__avionics_cache__.update()

    def is_data_source_available(
        self
    ) -> bool:
        """
        Checks if any AHRS source is available and recent.

        Returns:
            bool -- True if data is available and recent.
        """
        is_stratux_available = self.__stratux_ahrs_cache__.is_available()
        is_avionics_available = self.__avionics_cache__.is_available() \
            and self.__avionics_cache__.get_item_count() > 1

        return is_stratux_available or is_avionics_available

    def get_ahrs(
        self
    ) -> dict:
        """
        Returns a decoded AHRS object back. Attempts to combine ALL available
        AHRS data source.
        Avionics sourced data is prioritized over Stratux AHRS sourced data.

        Returns:
            AhrsData -- Any available AHRS data.
        """
        package = {}

        self.__stratux_ahrs_cache__.garbage_collect()
        self.__avionics_cache__.garbage_collect()

        stratux_ahrs = self.__stratux_ahrs_cache__.get()
        avionics_ahrs = self.__avionics_cache__.get()

        if stratux_ahrs is not None:
            package.update(stratux_ahrs)

        if avionics_ahrs is not None:
            package.update(avionics_ahrs)

        return self.__decode_situation__(package)

    def __init__(
        self,
        logger: HudLogger
    ):
        super(AhrsStratux, self).__init__(logger)

        self.__stratux_session__ = requests.Session()

        self.__stratux_ahrs_cache__ = data_cache.RestfulDataCache(
            "StratuxAhrsCache",
            self.__stratux_session__,
            "http://{0}/getSituation".format(
                configuration.CONFIGURATION.stratux_address()),
            MAX_STRATUX_AHRS_AGE,
            configuration.AHRS_TIMEOUT)
        self.__avionics_cache__ = data_cache.RestfulDataCache(
            "AvionicsCache",
            self.__stratux_session__,
            "http://{0}/getSituation".format(
                configuration.CONFIGURATION.avionics_address()),
            MAX_AVIONICS_AGE,
            AVIONICS_TIMEOUT)

        self.__max_gs__ = 1.0
        self.__min_gs__ = 1.0
