import datetime
import math
import threading

import requests

import configuration
import lib.recurring_task as recurring_task
from lib.simulated_values import SimulatedValue

HEADING_NOT_AVAILABLE = '---'


class StratuxStatus(object):

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
            except:
                return False

        return False

    def __init__(self, stratux_address, stratux_session, simulation_mode=False):
        """
        Builds a list of Capabilities of the stratux.
        """

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
            except:
                self.__status_json__ = {}

            self.cpu_temp = self.__get_status__('CPUTemp')
            self.satellites_locked = self.__get_status__(
                'GPS_satellites_locked')


class StratuxCapabilities(object):
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
            except:
                return False

        return False

    def __init__(self, stratux_address, stratux_session, simulation_mode=False):
        """
        Builds a list of Capabilities of the stratux.
        """

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
            except:
                self.__capabilities_json__ = {}

            self.traffic_enabled = self.__get_capability__('UAT_Enabled')
            self.gps_enabled = self.__get_capability__('GPS_Enabled')
            self.barometric_enabled = self.__get_capability__(
                'BMP_Sensor_Enabled')
            self.ahrs_enabled = self.__get_capability__('IMU_Sensor_Enabled')

    # http://192.168.10.1/getSettings - get device settings. Example output:
    # {
    # "UAT_Enabled": true,
    # "ES_Enabled": false,
    # "Ping_Enabled": false,
    # "GPS_Enabled": true,
    # "BMP_Sensor_Enabled": true,
    # "IMU_Sensor_Enabled": true,
    # "NetworkOutputs": [
    #     {
    #     "Conn": null,
    #     "Ip": "",
    #     "Port": 4000,
    #     "Capability": 5,
    #     "MessageQueueLen": 0,
    #     "LastUnreachable": "0001-01-01T00:00:00Z",
    #     "SleepFlag": false,
    #     "FFCrippled": false
    #     }
    # ],
    # "SerialOutputs": null,
    # "DisplayTrafficSource": false,
    # "DEBUG": false,
    # "ReplayLog": false,
    # "AHRSLog": false,
    # "IMUMapping": [
    #     -1,
    #     0
    # ],
    # "SensorQuaternion": [
    #     0.0068582877312501,
    #     0.0067230280142738,
    #     0.7140806859355,
    #     -0.69999752767998
    # ],
    # "C": [
    #     -0.019065523239845,
    #     -0.99225684377575,
    #     -0.019766228217414
    # ],
    # "D": [
    #     -2.7707754753258,
    #     5.544145023957,
    #     -1.890621662038
    # ],
    # "PPM": 0,
    # "OwnshipModeS": "F00000",
    # "WatchList": "",
    # "DeveloperMode": false,
    # "GLimits": "",
    # "StaticIps": [
    # ]
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

        return int(self.gps_heading)

    def get_onscreen_projection_display_heading(self):
        try:
            if self.__is_compass_heading_valid__():
                return int(self.compass_heading)
        except:
            pass

        return HEADING_NOT_AVAILABLE

    def get_heading(self):
        try:
            if self.compass_heading is None or self.compass_heading > 360 or self.compass_heading < 0 or self.compass_heading is '':
                return int(self.gps_heading)

            return int(self.compass_heading)
        except:
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


class AhrsStratux(object):
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
            ahrs_json = self.__stratux_session__.get(
                url, timeout=self.__timeout__).json()
            self.__last_update__ = datetime.datetime.utcnow(
            ) if ahrs_json is not None else self.__last_update__

        except KeyboardInterrupt:
            raise
        except SystemExit:
            raise
        except:
            # If we are spamming the REST too quickly, then we may loose a single update.
            # Do no consider the service unavailable unless we are
            # way below the max target framerate.
            delta_time = datetime.datetime.utcnow() - self.__last_update__
            self.data_source_available = delta_time.total_seconds() < (
                self.__min_update_microseconds__ / 1000000.0)

            return

        new_ahrs_data.roll = self.__get_value__(ahrs_json, 'AHRSRoll', 0.0)
        new_ahrs_data.pitch = self.__get_value__(ahrs_json, 'AHRSPitch', 0.0)
        new_ahrs_data.compass_heading = self.__get_value__(
            ahrs_json, 'AHRSGyroHeading', 1080)  # anything above 360 indicates "not available"
        new_ahrs_data.gps_heading = self.__get_value__(
            ahrs_json, 'GPSTrueCourse', 0.0)
        new_ahrs_data.alt = self.__get_value_with_fallback__(
            ahrs_json, ['GPSAltitudeMSL', 'BaroPressureAltitude'], None)
        new_ahrs_data.position = (
            ahrs_json['GPSLatitude'], ahrs_json['GPSLongitude'])
        new_ahrs_data.vertical_speed = self.__get_value__(
            ahrs_json, 'GPSVerticalSpeed', 0.0)
        new_ahrs_data.groundspeed = self.__get_value__(
            ahrs_json, 'GPSGroundSpeed', 0.0)
        new_ahrs_data.g_load = self.__get_value__(ahrs_json, 'AHRSGLoad', 1.0)
        new_ahrs_data.utc_time = self.__get_value_with_fallback__(
            ahrs_json, 'GPSTime', str(datetime.datetime.utcnow()))
        self.data_source_available = True
        # except:
        #    self.data_source_available = False

        self.__set_ahrs_data__(new_ahrs_data)

        # SAMPLE FULL JSON
        #
        # {u'GPSAltitudeMSL': 68.041336,
        # u'GPSFixQuality': 1,
        #  u'AHRSGLoadMin': 0.3307450162084107
        #  u'GPSHorizontalAccuracy': 4.2,
        #  u'GPSLongitude': -122.36627,
        #  u'GPSGroundSpeed': 16.749273158117294,
        #  u'GPSLastFixLocalTime': u'0001-01-01T00:06:49.36Z',
        #  u'AHRSMagHeading': 3276.7,
        #  u'GPSSatellites': 7,
        #  u'GPSSatellitesTracked': 12,
        #  u'BaroPressureAltitude': -149.82413,
        #  u'GPSPositionSampleRate': 0,
        #  u'AHRSPitch': -1.6670512276023939,
        #  u'GPSSatellitesSeen': 12,
        #  u'GPSLastValidNMEAMessage': u'$PUBX,00,163529.60,4740.16729,N,12221.97653,W,1.939,G3,2.1,3.2,31.017,179.98,0.198,,1.93,2.43,1.89,7,0,0*4D',
        # u'AHRSSlipSkid': -25.030695817203796,
        #  u'GPSLastGPSTimeStratuxTime': u'0001-01-01T00:06:48.76Z',
        #  u'GPSLastFixSinceMidnightUTC': 59729.6,
        #  u'GPSLastValidNMEAMessageTime': u'0001-01-01T00:06:49.36Z',
        #  u'GPSNACp': 10,
        #  u'AHRSLastAttitudeTime': u'0001-01-01T00:06:49.4Z',
        #  u'GPSTurnRate': 0,
        #  u'AHRSTurnRate': -0.2607137769860283,
        #  u'GPSLastGroundTrackTime': u'0001-01-01T00:06:49.36Z',
        #  u'BaroVerticalSpeed': -11.46994,
        #  u'GPSTrueCourse': 179.98,
        #  u'BaroLastMeasurementTime': u'0001-01-01T00:06:49.4Z',
        #  u'GPSVerticalAccuracy': 6.4,
        #  u'AHRSGLoad': 0.8879934248943415,
        #  u'BaroTemperature': 30.09,
        #  u'AHRSGyroHeading': 184.67916154869323,
        #  u'AHRSRoll': 26.382463342051672,
        #  u'GPSGeoidSep': -61.67979,
        #  u'AHRSGLoadMax': 1.0895587458493998,
        #  u'GPSTime': u'2018-02-26T16:35:29Z',
        #  u'GPSVerticalSpeed': -0.6496063,
        #  u'GPSHeightAboveEllipsoid': 6.361549,
        #  u'GPSLatitude': 47.669456,
        #  u'AHRSStatus': 7}

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
                configuration.CONFIGURATION.stratux_address(), self.__stratux_session__)
            self.stratux_status = StratuxStatus(
                configuration.CONFIGURATION.stratux_address(), self.__stratux_session__)
        finally:
            self.__lock__.release()

    def __init__(self):
        self.__min_update_microseconds__ = int(
            1000000.0 / (configuration.MAX_FRAMERATE / 10.0))
        self.__timeout__ = 1.0 / (configuration.MAX_FRAMERATE / 8.0)
        self.__stratux_session__ = requests.Session()

        self.ahrs_data = AhrsData()
        self.data_source_available = False
        self.capabilities = StratuxCapabilities(
            configuration.CONFIGURATION.stratux_address(), self.__stratux_session__)
        recurring_task.RecurringTask(
            'UpdateCapabilities', 15, self.__update_capabilities__)

        self.__lock__ = threading.Lock()
        self.__last_update__ = datetime.datetime.utcnow()


class Aircraft(object):
    def update_orientation_in_background(self):
        print("starting")
        while True:
            try:
                self.__update_orientation__()
            except KeyboardInterrupt:
                raise
            except:
                print("error")

    def __init__(self, force_simulation=False):
        self.ahrs_source = None

        if force_simulation or configuration.CONFIGURATION.data_source() == configuration.DataSourceNames.SIMULATION:
            self.ahrs_source = AhrsSimulation()
        elif configuration.CONFIGURATION.data_source() == configuration.DataSourceNames.STRATUX:
            self.ahrs_source = AhrsStratux()

        recurring_task.RecurringTask('UpdateAhrs',
                                     1.0 / (configuration.MAX_FRAMERATE * 2.0),
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
