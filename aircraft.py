import datetime
import math
import threading

import requests

import configuration
import lib.recurring_task as recurring_task
from lib.simulated_values import SimulatedValue

HEADING_NOT_AVAILABLE = '---'


class LoggingObject(object):
    def log(self, text):
        """
        Logs the given text if a logger is available.

        Arguments:
            text {string} -- The text to log
        """

        if self.__logger__ is not None:
            self.__logger__.log_info_message(text)
        else:
            print(text)

    def warn(self, text):
        """
        Logs the given text if a logger is available AS A WARNING.

        Arguments:
            text {string} -- The text to log
        """

        if self.__logger__ is not None:
            self.__logger__.log_warning_message(text)
        else:
            print(text)

    def __init__(self, logger):
        self.__logger__ = logger


class StratuxStatus(LoggingObject):
    def __get_status__(self, key):
        if key is None:
            return False

        if self.__status_json__ is None:
            return False

        if key in self.__status_json__:
            try:
                return bool(self.__status_json__[key])
            except KeyboardInterrupt:
                raise
            except SystemExit:
                raise
            except Exception as ex:
                self.warn("__get_status__ EX={}".format(ex))
                return False

        return False

    def __init__(self, stratux_address, stratux_session, logger, simulation_mode=False):
        """
        Builds a list of Capabilities of the stratux.
        """

        super(StratuxStatus, self).__init__(logger)

        if stratux_address is None or simulation_mode:
            self.__status_json__ = None
            self.cpu_temp = 50.0
            self.satellites_locked = 0

        else:
            url = "http://{0}/getStatus".format(stratux_address)

            try:
                self.__status_json__ = stratux_session.get(
                    url, timeout=2).json()

            except KeyboardInterrupt:
                raise
            except SystemExit:
                raise
            except Exception as ex:
                self.warn("__get_status__ EX={}".format(ex))
                self.__status_json__ = {}

            self.cpu_temp = self.__get_status__('CPUTemp')
            self.satellites_locked = self.__get_status__(
                'GPS_satellites_locked')

            # Results of a getStatus call
            # {
            #     "Version": "v1.5b2",
            #     "Build": "8f4a52d7396c0dc20270e7644eebe5d9fc49eed9",
            #     "HardwareBuild": "",
            #     "Devices": 2,
            #     "Connected_Users": 1,
            #     "DiskBytesFree": 367050752,
            #     "UAT_messages_last_minute": 0,
            #     "UAT_messages_max": 38,
            #     "ES_messages_last_minute": 1413,
            #     "ES_messages_max": 6522,
            #     "UAT_traffic_targets_tracking": 0,
            #     "ES_traffic_targets_tracking": 5,
            #     "Ping_connected": false,
            #     "UATRadio_connected": false,
            #     "GPS_satellites_locked": 12,
            #     "GPS_satellites_seen": 13,
            #     "GPS_satellites_tracked": 19,
            #     "GPS_position_accuracy": 3,
            #     "GPS_connected": true,
            #     "GPS_solution": "GPS + SBAS (WAAS)",
            #     "GPS_detected_type": 55,
            #     "Uptime": 3261140,
            #     "UptimeClock": "0001-01-01T00:54:21.14Z",
            #     "CPUTemp": 49.925,
            #     "CPUTempMin": 44.546,
            #     "CPUTempMax": 55.843,
            #     "NetworkDataMessagesSent": 3080,
            #     "NetworkDataMessagesSentNonqueueable": 3080,
            #     "NetworkDataBytesSent": 89047,
            #     "NetworkDataBytesSentNonqueueable": 89047,
            #     "NetworkDataMessagesSentLastSec": 3,
            #     "NetworkDataMessagesSentNonqueueableLastSec": 3,
            #     "NetworkDataBytesSentLastSec": 84,
            #     "NetworkDataBytesSentNonqueueableLastSec": 84,
            #     "UAT_METAR_total": 0,
            #     "UAT_TAF_total": 0,
            #     "UAT_NEXRAD_total": 0,
            #     "UAT_SIGMET_total": 0,
            #     "UAT_PIREP_total": 0,
            #     "UAT_NOTAM_total": 0,
            #     "UAT_OTHER_total": 0,
            #     "Errors": [],
            #     "Logfile_Size": 90107,
            #     "AHRS_LogFiles_Size": 0,
            #     "BMPConnected": true,
            #     "IMUConnected": true,
            #     "NightMode": false
            # }


class StratuxCapabilities(LoggingObject):
    """
    Get the capabilities of the Stratux, so we know what can be used
    in the HUD.
    """

    def __get_capability__(self, key):
        if key is None:
            return False

        if self.__capabilities_json__ is None:
            return False

        if key in self.__capabilities_json__:
            try:
                return bool(self.__capabilities_json__[key])
            except KeyboardInterrupt:
                raise
            except SystemExit:
                raise
            except Exception as ex:
                self.warn("__get_capability__ EX={}".format(ex))
                return False

        return False

    def __init__(self, stratux_address, stratux_session, logger=None, simulation_mode=False):
        """
        Builds a list of Capabilities of the stratux.
        """

        super(StratuxCapabilities, self).__init__(logger)

        if stratux_address is None or simulation_mode:
            self.__capabilities_json__ = None
            self.traffic_enabled = False
            self.gps_enabled = False
            self.barometric_enabled = True
            self.ahrs_enabled = True
        else:
            url = "http://{0}/getSettings".format(stratux_address)

            try:
                self.__capabilities_json__ = stratux_session.get(
                    url, timeout=2).json()

            except KeyboardInterrupt:
                raise
            except SystemExit:
                raise
            except Exception as ex:
                self.__capabilities_json__ = {}
                self.warn("EX in __init__ ex={}".format(ex))

            self.traffic_enabled = self.__get_capability__('UAT_Enabled')
            self.gps_enabled = self.__get_capability__('GPS_Enabled')
            self.barometric_enabled = self.__get_capability__(
                'BMP_Sensor_Enabled')
            self.ahrs_enabled = self.__get_capability__('IMU_Sensor_Enabled')

            # http://192.168.10.1/getSettings - get device settings. Example output:
            #
            # {
            #     "UAT_Enabled": true,
            #     "ES_Enabled": true,
            #     "Ping_Enabled": false,
            #     "GPS_Enabled": true,
            #     "BMP_Sensor_Enabled": true,
            #     "IMU_Sensor_Enabled": true,
            #     "NetworkOutputs": [
            #         {
            #             "Conn": null,
            #             "Ip": "",
            #             "Port": 4000,
            #             "Capability": 5,
            #             "MessageQueueLen": 0,
            #             "LastUnreachable": "0001-01-01T00:00:00Z",
            #             "SleepFlag": false,
            #             "FFCrippled": false
            #         }
            #     ],
            #     "SerialOutputs": null,
            #     "DisplayTrafficSource": false,
            #     "DEBUG": false,
            #     "ReplayLog": false,
            #     "AHRSLog": false,
            #     "IMUMapping": [
            #         2,
            #         0
            #     ],
            #     "SensorQuaternion": [
            #         0.017336041263077348,
            #         0.7071029888451218,
            #         0.7068942365539764,
            #         -0.0023158510746434354
            #     ],
            #     "C": [
            #         -0.02794518875698111,
            #         0.021365398113956116,
            #         -1.0051649525437176
            #     ],
            #     "D": [
            #         -0.43015839106418047,
            #         -0.0019837031159398175,
            #         -1.2866603595080415
            #     ],
            #     "PPM": 0,
            #     "OwnshipModeS": "F00000",
            #     "WatchList": "",
            #     "DeveloperMode": false,
            #     "GLimits": "",
            #     "StaticIps": [],
            #     "WiFiSSID": "stratux",
            #     "WiFiChannel": 1,
            #     "WiFiSecurityEnabled": false,
            #     "WiFiPassphrase": ""
            # }


class AhrsData(object):
    """
    Class to hold the AHRS data
    """

    def __is_compass_heading_valid__(self):
        return self.compass_heading is not None and self.compass_heading <= 360

    def get_onscreen_projection_heading(self):
        if self.__is_compass_heading_valid__():
            return int(self.compass_heading)

        if self.gps_online:
            return int(self.gps_heading)

        return HEADING_NOT_AVAILABLE

    def get_onscreen_projection_display_heading(self):
        try:
            if self.__is_compass_heading_valid__():
                return int(self.compass_heading)
        except:
            pass

        return HEADING_NOT_AVAILABLE

    def get_onscreen_gps_heading(self):
        """
            Returns a safe display version of the GPS heading
        """
        return self.gps_heading if self.gps_online else HEADING_NOT_AVAILABLE

    def get_heading(self):
        try:
            if (self.compass_heading is None
                    or self.compass_heading > 360
                    or self.compass_heading < 0
                    or self.compass_heading is '') and self.gps_online:
                return int(self.gps_heading)

            if __is_compass_heading_valid__():
                return int(self.compass_heading)
        except:
            return HEADING_NOT_AVAILABLE

        return HEADING_NOT_AVAILABLE

    def __init__(self):
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


class AhrsSimulation(object):
    """
    Class to simulate the AHRS data.
    """

    def simulate(self):
        """
        Ticks the simulated data.
        """
        self.ahrs_data.pitch = self.pitch_simulator.simulate()
        self.ahrs_data.roll = self.roll_simulator.simulate()
        self.ahrs_data.compass_heading = self.yaw_simulator.simulate()
        self.ahrs_data.gps_heading = self.ahrs_data.compass_heading
        self.ahrs_data.airspeed = self.speed_simulator.simulate()
        self.ahrs_data.alt = self.alt_simulator.simulate()

    def update(self):
        """
        Updates the simulation and serves as the interface for the
        the AHRS/Simulation/Other sourcing
        """

        self.simulate()

    def __init__(self):
        self.ahrs_data = AhrsData()
        self.data_source_available = True

        self.pitch_simulator = SimulatedValue(1, 30, -1)
        self.roll_simulator = SimulatedValue(5, 60, 1)
        self.yaw_simulator = SimulatedValue(5, 60, 1, 30, 180)
        self.speed_simulator = SimulatedValue(5, 10, 1, 85)
        self.alt_simulator = SimulatedValue(10, 100, -1, 0, 200)

        self.capabilities = StratuxCapabilities(None, None, True)


class AhrsStratux(LoggingObject):
    """
    Class to pull actual AHRS data from a Stratux (or Stratus)
    """

    def __get_value__(self, ahrs_json, key, default):
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

    def __get_value_with_fallback__(self, ahrs_json, keys, default):
        if keys is None:
            return default

        values = [self.__get_value__(ahrs_json, key, default) for key in keys]
        values = filter(lambda x: x != default, values)

        return values[0] if values is not None and len(values) > 0 else default

    def update(self):
        """
        Grabs the AHRS (if available)
        """

        new_ahrs_data = AhrsData()

        url = "http://{0}/getSituation".format(
            configuration.CONFIGURATION.stratux_address())

        try:
            ahrs_json = self.__stratux_session__.get(url,
                                                     timeout=self.__timeout__).json()

            if ahrs_json is not None:
                self.__last_update__ = datetime.datetime.utcnow()

        except KeyboardInterrupt:
            raise
        except SystemExit:
            raise
        except Exception as ex:
            # If we are spamming the REST too quickly, then we may loose a single update.
            # Do no consider the service unavailable unless we are
            # way below the max target framerate.
            delta_time = datetime.datetime.utcnow() - self.__last_update__
            self.data_source_available = delta_time.total_seconds() < self.__min_update_seconds__

            self.warn('AHRS.update() ex={}'.format(ex))

            return

        system_utc_time = str(datetime.datetime.utcnow())

        new_ahrs_data.roll = self.__get_value__(ahrs_json, 'AHRSRoll', 0.0)
        new_ahrs_data.pitch = self.__get_value__(ahrs_json, 'AHRSPitch', 0.0)
        new_ahrs_data.compass_heading = self.__get_value__(
            ahrs_json, 'AHRSGyroHeading', 1080)  # anything above 360 indicates "not available"
        new_ahrs_data.gps_online = self.__get_value__(
            ahrs_json, 'GPSFixQuality', 0) > 0
        new_ahrs_data.gps_heading = self.__get_value__(
            ahrs_json, 'GPSTrueCourse', 0.0) if new_ahrs_data.gps_online else HEADING_NOT_AVAILABLE
        new_ahrs_data.alt = self.__get_value_with_fallback__(
            ahrs_json, ['GPSAltitudeMSL', 'BaroPressureAltitude'], None) if new_ahrs_data.gps_online else HEADING_NOT_AVAILABLE
        new_ahrs_data.position = (self.__get_value__(ahrs_json, 'GPSLatitude', None),
                                  self.__get_value__(ahrs_json, 'GPSLongitude', None))
        new_ahrs_data.vertical_speed = self.__get_value__(
            ahrs_json, 'GPSVerticalSpeed', 0.0) if new_ahrs_data.gps_online else HEADING_NOT_AVAILABLE
        new_ahrs_data.groundspeed = self.__get_value__(
            ahrs_json, 'GPSGroundSpeed', 0.0) if new_ahrs_data.gps_online else HEADING_NOT_AVAILABLE
        new_ahrs_data.g_load = self.__get_value__(ahrs_json, 'AHRSGLoad', 1.0)
        new_ahrs_data.utc_time = self.__get_value_with_fallback__(
            ahrs_json, 'GPSTime', system_utc_time) if new_ahrs_data.gps_online else system_utc_time

        self.data_source_available = True
        # except:
        #    self.data_source_available = False

        self.__set_ahrs_data__(new_ahrs_data)

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

    def __set_ahrs_data__(self, new_ahrs_data):
        """
        Atomically sets the AHRS data.
        """
        self.__lock__.acquire()
        self.ahrs_data = new_ahrs_data
        self.__lock__.release()

    def __update_capabilities__(self):
        """
        Check occasionally to see if the settings
        for the Stratux have been changed that would
        affect what we should show and what is actually
        available.
        """
        self.__lock__.acquire()
        try:
            self.capabilities = StratuxCapabilities(
                configuration.CONFIGURATION.stratux_address(), self.__stratux_session__, self.__logger__)
            self.stratux_status = StratuxStatus(
                configuration.CONFIGURATION.stratux_address(), self.__stratux_session__, self.__logger__)
        finally:
            self.__lock__.release()

    def __init__(self, logger):
        super(AhrsStratux, self).__init__(logger)

        # If an update to the AHRS takes longer than this,
        # then the AHRS should be considered not available.
        self.__min_update_seconds__ = 0.3
        # Make the timeout a reasonable time.
        self.__timeout__ = configuration.AHRS_TIMEOUT
        self.__stratux_session__ = requests.Session()

        self.ahrs_data = AhrsData()
        self.data_source_available = False
        self.capabilities = StratuxCapabilities(
            configuration.CONFIGURATION.stratux_address(), self.__stratux_session__)
        recurring_task.RecurringTask(
            'UpdateCapabilities', 15, self.__update_capabilities__)

        self.__lock__ = threading.Lock()
        self.__last_update__ = datetime.datetime.utcnow()


class Aircraft(LoggingObject):
    def update_orientation_in_background(self):
        print("starting")
        while True:
            try:
                self.__update_orientation__()
            except KeyboardInterrupt:
                raise
            except Exception as ex:
                self.warn("update_orientation_in_background ex={}".format(ex))

    def __init__(self, logger=None, force_simulation=False):
        super(Aircraft, self).__init__(logger)

        self.ahrs_source = None

        if force_simulation or configuration.CONFIGURATION.data_source() == configuration.DataSourceNames.SIMULATION:
            self.ahrs_source = AhrsSimulation()
        elif configuration.CONFIGURATION.data_source() == configuration.DataSourceNames.STRATUX:
            self.ahrs_source = AhrsStratux(logger)

        recurring_task.RecurringTask('UpdateAhrs',
                                     1.0 / configuration.TARGET_AHRS_FRAMERATE,
                                     self.__update_orientation__)

    def is_ahrs_available(self):
        """
        Returns True if the AHRS data is available
        """

        return self.ahrs_source is not None and self.ahrs_source.data_source_available

    def get_orientation(self):
        return self.ahrs_source.ahrs_data

    def __update_orientation__(self):
        if self.ahrs_source is not None:
            self.ahrs_source.update()


if __name__ == '__main__':
    import time
    plane = Aircraft()

    while True:
        print(str(plane.get_orientation().roll))
        time.sleep(1.0 / 60.0)
