import datetime
import math
import threading

import requests

from aircraft_data_cache import AircraftDataCache
import configuration
import lib.recurring_task as recurring_task
from lib.simulated_values import SimulatedValue
from logging_object import LoggingObject

HEADING_NOT_AVAILABLE = '---'


class AhrsData(object):
    """
    Class to hold the AHRS data
    """

    def __is_compass_heading_valid__(
        self
    ):
        return self.compass_heading is not None and self.compass_heading <= 360

    def get_onscreen_projection_heading(
        self
    ):
        if self.__is_compass_heading_valid__():
            return int(self.compass_heading)

        if self.gps_online:
            return int(self.gps_heading)

        return HEADING_NOT_AVAILABLE

    def get_onscreen_projection_display_heading(
        self
    ):
        try:
            if self.__is_compass_heading_valid__():
                return int(self.compass_heading)
        except:
            pass

        return HEADING_NOT_AVAILABLE

    def get_onscreen_gps_heading(
        self
    ):
        """
            Returns a safe display version of the GPS heading
        """
        return self.gps_heading if self.gps_online else HEADING_NOT_AVAILABLE

    def get_heading(
        self
    ):
        try:
            if (self.compass_heading is None
                    or self.compass_heading > 360
                    or self.compass_heading < 0
                    or self.compass_heading is '') and self.gps_online:
                return int(self.gps_heading)

            if self.__is_compass_heading_valid__():
                return int(self.compass_heading)
        except:
            return HEADING_NOT_AVAILABLE

        return HEADING_NOT_AVAILABLE

    def __init__(
        self
    ):
        self.roll = 0.0
        self.pitch = 0.0
        self.compass_heading = 0.0
        self.gps_heading = 0.0
        self.compass_heading = 0.0
        self.alt = 0.0
        self.position = (0, 0)  # lat, lon
        self.groundspeed = 0
        self.vertical_speed = 0
        self.g_load = 1.0
        self.utc_time = datetime.datetime.utcnow()
        self.gps_online = True
        self.is_avionics_source = False


class AhrsSimulation(object):
    """
    Class to simulate the AHRS data.
    """

    def simulate(
        self
    ):
        """
        Ticks the simulated data.
        """
        self.ahrs_data.pitch = self.pitch_simulator.simulate()
        self.ahrs_data.roll = self.roll_simulator.simulate()
        self.ahrs_data.compass_heading = self.yaw_simulator.simulate()
        self.ahrs_data.gps_heading = self.ahrs_data.compass_heading
        self.ahrs_data.airspeed = self.speed_simulator.simulate()
        self.ahrs_data.groundspeed = self.ahrs_data.airspeed
        self.ahrs_data.alt = self.alt_simulator.simulate()

    def update(
        self
    ):
        """
        Updates the simulation and serves as the interface for the
        the AHRS/Simulation/Other sourcing
        """

        self.simulate()

    def get_ahrs(
        self
    ):
        """
        Returns the current simulated values for the AHRS data.

        Returns:
            AhrsData -- The current simulated values.
        """
        return self.ahrs_data

    def __init__(
        self
    ):
        self.ahrs_data = AhrsData()

        self.pitch_simulator = SimulatedValue(1, 30, -1)
        self.roll_simulator = SimulatedValue(5, 60, 1)
        self.yaw_simulator = SimulatedValue(5, 60, 1, 30, 180)
        self.speed_simulator = SimulatedValue(5, 10, 1, 0, 85)
        self.alt_simulator = SimulatedValue(10, 100, -1, 0, 200)


class AhrsStratux(LoggingObject):
    """
    Class to pull actual AHRS data from a Stratux (or Stratus)
    """

    def __get_value__(
        self,
        ahrs_json,
        key,
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
        ahrs_json,
        keys,
        default
    ):
        if keys is None:
            return default

        values = [self.__get_value__(ahrs_json, key, default) for key in keys]
        values = filter(lambda x: x != default, values)

        return values[0] if values is not None and len(values) > 0 else default

    def __get_situation__(
        self,
        service_address
    ):
        """
        Grabs the AHRS (if available).

        Arguments:
            service_address {str} -- The address that contains the getSituation service. May be avionics or Stratux

        Returns:
            dict -- The resulting AHRS data if contact could be made, otherwise None
        """

        if service_address is None or len(service_address) < 1:
            return None

        url = "http://{0}/getSituation".format(
            service_address)

        try:
            ahrs_json = self.__stratux_session__.get(
                url,
                timeout=configuration.AHRS_TIMEOUT).json()

        except KeyboardInterrupt:
            raise
        except SystemExit:
            raise
        except Exception as ex:
            self.warn('AHRS.update() ex={}'.format(ex))

            return None

        return ahrs_json

    def __decode_situation__(
        self,
        ahrs_json
    ):
        """
        Decodes AHRS results from getSituation into a package that is
        usable by the HUD.

        The package may be from a single source, or from combined sources.

        Arguments:
            ahrs_json {dict} -- The AHRS package to decode

        Returns:
            AhrsData -- The decoded value (if it could be decoded), or otherwise a safe package.
        """
        new_ahrs_data = AhrsData()

        system_utc_time = str(datetime.datetime.utcnow())

        new_ahrs_data.is_avionics_source = "Service" in ahrs_json\
            and "ToHud" in ahrs_json["Service"]

        new_ahrs_data.gps_online = self.__get_value__(
            ahrs_json,
            'GPSFixQuality',
            0) > 0

        is_reliable = new_ahrs_data.gps_online or new_ahrs_data.is_avionics_source

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
            0.0) if new_ahrs_data.gps_online else HEADING_NOT_AVAILABLE
        new_ahrs_data.alt = self.__get_value_with_fallback__(
            ahrs_json,
            ['BaroPressureAltitude', 'GPSAltitudeMSL'],
            None) if is_reliable else HEADING_NOT_AVAILABLE
        new_ahrs_data.position = (self.__get_value__(ahrs_json, 'GPSLatitude', None),
                                  self.__get_value__(ahrs_json, 'GPSLongitude', None)) if new_ahrs_data.gps_online else (None, None)
        new_ahrs_data.vertical_speed = self.__get_value_with_fallback__(
            ahrs_json,
            ["BaroVerticalSpeed",
             'GPSVerticalSpeed'],
            0.0) if is_reliable else HEADING_NOT_AVAILABLE
        new_ahrs_data.groundspeed = self.__get_value_with_fallback__(
            ahrs_json,
            ['AHRSAirspeed', 'GPSGroundSpeed'],
            0.0) if is_reliable else HEADING_NOT_AVAILABLE
        new_ahrs_data.g_load = self.__get_value__(
            ahrs_json,
            'AHRSGLoad',
            1.0)
        new_ahrs_data.utc_time = self.__get_value_with_fallback__(
            ahrs_json,
            'GPSTime',
            system_utc_time) if new_ahrs_data.gps_online else system_utc_time

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
        new_ahrs_data = self.__get_situation__(
            configuration.CONFIGURATION.stratux_address())

        if new_ahrs_data is not None:
            self.__stratux_ahrs_cache__.update(new_ahrs_data)

    def update_avionics(
        self
    ):
        """
        Attempts to get the AHRS data from the avionics source.
        """
        new_ahrs_data = self.__get_situation__(
            configuration.CONFIGURATION.avionics_address())

        if new_ahrs_data is not None:
            self.__avionics_cache__.update(new_ahrs_data)

    def is_data_source_available(
        self
    ):
        """
        Checks if any AHRS source is available and recent.

        Returns:
            bool -- True if data is available and recent.
        """
        is_stratux_available = self.__stratux_ahrs_cache__ is not None and self.__stratux_ahrs_cache__.is_available()
        is_avionics_available = self.__avionics_cache__ is not None and self.__avionics_cache__.is_available()

        return is_stratux_available or is_avionics_available

    def get_ahrs(
        self
    ):
        """
        Returns a decoded AHRS object back. Attempts to combine ALL available
        AHRS data source.
        Avionics sourced data is prioritized over Stratux AHRS sourced data.

        Returns:
            AhrsData -- Any available AHRS data.
        """
        package = {}
        stratux_ahrs = self.__stratux_ahrs_cache__.get()
        avionics_ahrs = self.__avionics_cache__.get()

        if stratux_ahrs is not None:
            package.update(stratux_ahrs)

        if avionics_ahrs is not None:
            package.update(avionics_ahrs)

        return self.__decode_situation__(package)

    def __init__(
        self,
        logger
    ):
        super(AhrsStratux, self).__init__(logger)

        self.__stratux_session__ = requests.Session()

        self.__stratux_ahrs_cache__ = AircraftDataCache(0.3)
        self.__avionics_cache__ = AircraftDataCache(0.3)


class Aircraft(LoggingObject):
    def update_orientation_in_background(
        self
    ):
        print("starting")
        while True:
            try:
                self.__update_orientation__()
            except KeyboardInterrupt:
                raise
            except Exception as ex:
                self.warn("update_orientation_in_background ex={}".format(ex))

    def __init__(
        self,
        logger=None,
        force_simulation=False
    ):
        super(Aircraft, self).__init__(logger)

        self.ahrs_source = AhrsStratux(logger)

        recurring_task.RecurringTask(
            'UpdateStratuxAhrs',
            1.0 / configuration.TARGET_AHRS_FRAMERATE,
            self.__update_orientation__)

        recurring_task.RecurringTask(
            'UpdateAvionics',
            1.0 / configuration.TARGET_AHRS_FRAMERATE,
            self.__update_avionics_orientation__)

    def is_ahrs_available(
        self
    ):
        """
        Returns True if the AHRS data is available
        """

        return self.ahrs_source is not None and self.ahrs_source.is_data_source_available()

    def get_orientation(
        self
    ):
        return self.ahrs_source.get_ahrs()

    def __update_orientation__(
        self
    ):
        if self.ahrs_source is not None:
            self.ahrs_source.update()

    def __update_avionics_orientation__(
        self
    ):
        if self.ahrs_source is not None:
            self.ahrs_source.update_avionics()


if __name__ == '__main__':
    import time
    plane = Aircraft()

    while True:
        print(str(plane.get_orientation().roll))
        time.sleep(1.0 / 60.0)
