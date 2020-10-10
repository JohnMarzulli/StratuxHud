"""
Holds code relevant to collecting and traffic information.
"""

import datetime
import math
import random
import threading
import time

import requests
from common_utils import simulated_values, tasks
from configuration import configuration


class Traffic(object):
    """
    Holds data about traffic that the ADSB has received.
    """

    TAIL_NUMBER_KEY = 'displayName'
    LATITUDE_KEY = 'Lat'
    LONGITUDE_KEY = 'Lng'
    DISTANCE_KEY = 'Distance'
    BEARING_KEY = 'Bearing'
    ALTITUDE_KEY = 'Alt'
    # We need to key off the ICAO address due to 'Anonymous Mode'...
    ICAO_ADDR_KEY = 'Icao_addr'

    """
    Holds an instance of a traffic callout.

    EXAMPLE:
    {
        "Icao_addr": 11268767,
        "Reg": "N8690A",
        "Tail": "SWA483",
        "Emitter_category": 0,
        "OnGround": false,
        "Addr_type": 0,
        "TargetType": 1,
        "SignalLevel": -18.53716886840413,
        "Squawk": 1001,
        "Position_valid": true,
        "Lat": 47.557755,
        "Lng": -122.200584,
        "Alt": 7550,
        "GnssDiffFromBaroAlt": -175,
        "AltIsGNSS": false,
        "NIC": 8,
        "NACp": 8,
        "Track": 358,
        "Speed": 245,
        "Speed_valid": true,
        "Vvel": -576,
        "Timestamp": "2018-02-22T08:43:34.492Z",
        "PriorityStatus": 0,
        "Age": 0.29000000000000004,
        "AgeLastAlt": 0.030000000000000002,
        "Last_seen": "0001-01-01T01:21:00.39Z",
        "Last_alt": "0001-01-01T01:21:00.39Z",
        "Last_GnssDiff": "0001-01-01T01:21:00.28Z",
        "Last_GnssDiffAlt": 7550,
        "Last_speed": "0001-01-01T01:21:00.28Z",
        "Last_source": 1,
        "ExtrapolatedPosition": false,
        "BearingDist_valid": true,
        "Bearing": 139.81876501328543,
        "Distance": 19427.035251983383
    }
    """

    def is_on_ground(
        self
    ) -> bool:
        """
        Is this aircraft on the ground?

        Returns:
            bool -- True if the plane is on the ground.
        """

        try:
            if 'OnGround' in self.__json__:
                return bool(self.__json__['OnGround'])
        except:
            pass

        return False

    def get_age(
        self
    ) -> float:
        """
        Returns the age of this report in total seconds.
        """
        delta = datetime.datetime.utcnow() - self.time_decoded
        return delta.total_seconds()

    def get_display_name(
        self
    ) -> str:
        """
        Returns the identifier to use of the traffic
        """

        if self.display_name is not None and len(self.display_name) > 1:
            return self.display_name

        return self.icao_address

    def get_bearing(
        self,
        starting_lat: float,
        starting_lon: float
    ) -> float:
        """
        Returns the bearing to the traffic from the
        given point.
        """

        lat2 = float(self.__json__[Traffic.LATITUDE_KEY])
        lon2 = float(self.__json__[Traffic.LONGITUDE_KEY])

        bearing = math.atan2(math.sin(lon2 - starting_lon) * math.cos(lat2), math.cos(starting_lat)
                             * math.sin(lat2) - math.sin(starting_lat) * math.cos(lat2) * math.cos(lon2 - starting_lon))
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360

        return bearing

    def get_distance(
        self,
        starting_lat: float,
        starting_lon: float
    ) -> float:
        """
        Returns the distance to the traffic from the
        given point.
        """

        if self.latitude is None or self.longitude is None:
            return None

        lon1 = starting_lon
        lat1 = starting_lat
        lat2 = float(self.latitude)
        lon2 = float(self.longitude)

        # convert decimal degrees to radians
        lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

        # haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * \
            math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.asin(math.sqrt(a))
        # Radius of earth. Can change with units
        r = configuration.EARTH_RADIUS_STATUTE_MILES
        return c * r

    def update(
        self,
        json_report: dict
    ):
        """
        Applies the new data to the existing traffic.
        """

        try:
            self.__json__.update(json_report)
            self.__update_from_json__()
        except:
            print("Issue in update()")

    def __init__(
        self,
        icao_address: str,
        json_from_stratux: dict
    ):
        """
        Initializes the traffic from the JSON response.
        """

        # Create all of the possible data
        self.icao_address = icao_address
        self.display_name = None
        self.time_decoded = datetime.datetime.utcnow()
        self.latitude = None
        self.longitude = None
        self.distance = None
        self.bearing = None
        self.altitude = None

        self.__json__ = json_from_stratux
        self.__update_from_json__()

    def __update_from_json__(
        self
    ):
        """
        Updates the report from the most recently received report.
        (Deserialized from the JSON)
        """

        # Position report with full GPS
        # {u'TargetType': 1,
        # u'Vvel': -1152,
        # u'Speed_valid': True,
        # u'Emitter_category': 3,
        # u'Tail': u'SKW4677',
        # u'GnssDiffFromBaroAlt': -300,
        # u'Reg': u'N256SY',
        # u'Last_seen': u'0001-01-01T03:20:11.93Z',
        # u'Squawk': 0,
        # u'Track': 181,
        # u'Timestamp': u'2018-02-25T22:04:00.122Z',
        # u'Icao_addr': 10645359,
        # u'ExtrapolatedPosition': False,
        # u'Addr_type': 0,
        # u'Last_alt': u'0001-01-01T03:20:12.2Z',
        # u'Lat': 47.642025,
        # u'Position_valid': True,
        # u'Distance': 6686.765716909548,
        # u'Age': 0.15000000000000002,
        # u'Last_GnssDiffAlt': 4000,
        # u'Last_speed': u'0001-01-01T03:20:12.26Z',
        # u'AgeLastAlt': 0.15000000000000002,
        # u'Last_GnssDiff': u'0001-01-01T03:20:12.26Z',
        # u'BearingDist_valid': True,
        # u'Lng': -122.31614,
        # u'Bearing': 144.92257263398366,
        # u'OnGround': False,
        # u'NIC': 8,
        # u'Last_source': 1,
        # u'PriorityStatus': 0,
        # u'NACp': 10,
        # u'SignalLevel': -5.054252345140135,
        # u'AltIsGNSS': False,
        # u'Alt': 4000,
        # u'Speed': 177}

        try:
            self.display_name = self.__json__[Traffic.TAIL_NUMBER_KEY]
            self.time_decoded = datetime.datetime.utcnow()

            if Traffic.LATITUDE_KEY in self.__json__:
                self.latitude = self.__json__[Traffic.LATITUDE_KEY]
            else:
                self.latitude = None

            if Traffic.LONGITUDE_KEY in self.__json__:
                self.longitude = self.__json__[Traffic.LONGITUDE_KEY]
            else:
                self.longitude = None

            if Traffic.DISTANCE_KEY in self.__json__:
                self.distance = float(self.__json__[Traffic.DISTANCE_KEY])
            else:
                self.distance = None

            if Traffic.BEARING_KEY in self.__json__:
                self.bearing = float(self.__json__[Traffic.BEARING_KEY])
            else:
                self.bearing = None

            if Traffic.ALTITUDE_KEY in self.__json__:
                self.altitude = float(self.__json__[Traffic.ALTITUDE_KEY])
            else:
                self.altitude = None
        except Exception as ex:
            print("Exception while updating:{}".format(ex))


class SimulatedTraffic(object):
    """
    Class to simulated ADSB received traffic.
    """

    def __init__(
        self
    ):
        """
        Creates a new traffic simulation object.
        """

        target_center_position = (48.160464, -122.166409)
        runway_number_position = (48.155973, -122.157582)
        starting_points = (target_center_position, runway_number_position)

        self.icao_address = random.randint(10000, 100000)
        self.tail_number = "N{0}{1}{2}".format(
            random.randint(1, 9),
            random.randint(0, 9),
            random.randint(0, 9))
        self.time_decoded = datetime.datetime.utcnow()
        self.latitude = simulated_values.SimulatedValue(
            0.1,
            10,
            1,
            random.randint(0, 9),
            starting_points[random.randint(0, 1)][0])
        self.longitude = simulated_values.SimulatedValue(
            0.1,
            10,
            1,
            random.randint(0, 9),
            starting_points[random.randint(0, 1)][1])
        self.distance = simulated_values.SimulatedValue(
            10,
            1000,
            -1,
            random.randint(0, 1000),
            1000)
        self.bearing = simulated_values.SimulatedValue(
            0,
            180,
            -1,
            random.randint(0, 180),
            180)
        self.altitude = simulated_values.SimulatedValue(
            10,
            100,
            -1,
            0,
            500)
        self.speed = simulated_values.SimulatedValue(
            5,
            10,
            1,
            85)

    def simulate(
        self
    ):
        """
        Simulates the traffic for a 'tick'.
        """

        self.time_decoded = datetime.datetime.utcnow()
        self.latitude.simulate()
        self.longitude.simulate()
        self.distance.simulate()
        self.bearing.simulate()
        self.altitude.simulate()
        self.speed.simulate()

    def to_json(
        self
    ):
        """
        Returns this object back as a dictionary (deserialized json)

        Returns:
            dictionary -- The dictionary representing a traffic report.
        """

        return {
            'TargetType': 1,
            'Vvel': -1152,
            'Speed_valid': True,
            'Emitter_category': 3,
            'Tail': self.tail_number,
            'displayName': self.tail_number,
            'GnssDiffFromBaroAlt': -300,
            'Reg': self.tail_number,
            'Last_seen': str(self.time_decoded),
            'Squawk': 0,
            'Track': 181,
            'Timestamp': str(self.time_decoded),
            'Icao_addr': self.icao_address,
            'ExtrapolatedPosition': False,
            'Addr_type': 0,
            'Last_alt': str(self.time_decoded),
            'Lat': self.latitude.value,
            'Distance': self.distance.value,
            'Age': 0.15000000000000002,
            'Last_GnssDiffAlt': 4000,
            'Last_speed': str(self.time_decoded),
            'AgeLastAlt': 0.15000000000000002,
            'Last_GnssDiff': str(self.time_decoded),
            'BearingDist_valid': True,
            'Lng': self.longitude.value,
            'Lon': self.longitude.value,
            'Bearing': self.bearing.value,
            'OnGround': False,
            'NIC': 8,
            'Last_source': 1,
            'PriorityStatus': 0,
            'NACp': 10,
            'SignalLevel': -5.054252345140135,
            'AltIsGNSS': False,
            'Alt': self.altitude.value,
            'Speed': self.speed.value
        }


class TrafficManager(object):
    """
    Manager class that handles all of the position reports.
    """

    def heartbeat(
        self
    ):
        """
        Record a heartbeat / response from the traffic manager.
        """
        self.__last_report_time__ = datetime.datetime.utcnow()

    def is_traffic_available(
        self
    ):
        """
        Do we believe the traffic manager is available and responding?

        Returns:
            bool -- True if the traffic manager is online.
        """
        if self.__last_report_time__ is None:
            return False

        return (datetime.datetime.utcnow() - self.__last_report_time__).total_seconds() < 10

    def clear(
        self
    ):
        """
        Resets the traffic reports.
        """

        self.traffic = {}

    def get_traffic_with_position(
        self
    ) -> list:
        """
        Returns the subset of traffic with actionable
        traffic data.
        """

        actionable_traffic = []
        ownship = configuration.CONFIGURATION.capabilities.ownship_icao

        self.__lock__.acquire()
        try:
            traffic_with_position = {
                k: v for k, v in self.traffic.items()
                if v is not None and ownship != int(v.icao_address)
            }
        except Exception:
            traffic_with_position = []
        finally:
            self.__lock__.release()

        actionable_traffic = [self.traffic[identifier]
                              for identifier in traffic_with_position]

        sorted_traffic = sorted(
            actionable_traffic, key=lambda traffic: traffic.distance)

        return sorted_traffic

    def handle_traffic_report(
        self,
        icao_address: str,
        json_report: dict
    ) -> str:
        """
        Updates or sets a traffic report.
        """
        self.__lock__.acquire()
        try:
            traffic_report = Traffic(icao_address, json_report)
            identifier = str(traffic_report.icao_address)
            if traffic_report.icao_address in self.traffic:
                self.traffic[identifier].update(json_report)
            else:
                self.traffic[identifier] = traffic_report
        finally:
            self.__lock__.release()

        if traffic_report is not None:
            return traffic_report.get_display_name()

        return None

    def prune_traffic_reports(
        self
    ):
        """
        Removes traffic reports that are too old.
        """

        self.__lock__.acquire()
        try:
            traffic_to_remove = []
            for identifier in self.traffic:
                traffic_age = self.traffic[identifier].get_age()

                if traffic_age > (configuration.CONFIGURATION.max_minutes_before_removal * 60):
                    traffic_to_remove.append(identifier)

            for identifier_to_remove in traffic_to_remove:
                del self.traffic[identifier_to_remove]
        except:
            print("Issue on prune")
        finally:
            self.__lock__.release()

    def __init__(
        self
    ):
        # Traffic held by tail number
        self.traffic = {}
        self.__last_report_time__ = None
        self.__lock__ = threading.Lock()
        self.__prune_task__ = tasks.RecurringTask(
            'PruneTraffic',
            10,
            self.prune_traffic_reports)


class AdsbTrafficClient:
    """
    Class to handle the REST calls to the traffic manager
    for data and then handling the incoming data.
    """

    TRAFFIC_MANAGER = TrafficManager()
    INSTANCE = None
    TIME_SINCE_LAST_REPORT_KEY = "socketTimeSinceLastTraffic"

    def __init__(
        self,
        rest_address: str
    ):
        self.__traffic_session__ = requests.Session()
        self.rest_address = rest_address
        self.__update_traffic_task__ = tasks.RecurringTask(
            'UpdateTraffic',
            0.1,
            self.update_reliable_traffic)
        self.__update_service_health_task__ = tasks.RecurringTask(
            'UpdateTrafficManagerHealth',
            0.5,
            self.get_traffic_manager_service_status)
        AdsbTrafficClient.INSTANCE = self

    def get_traffic_manager_service_status(
        self
    ):
        try:
            status_json = self.__traffic_session__.get(
                "http://{}/Service/Status".format(self.rest_address),
                timeout=configuration.AHRS_TIMEOUT).json()

            if status_json is not None and AdsbTrafficClient.TIME_SINCE_LAST_REPORT_KEY in status_json:
                time_since_last_report = float(
                    status_json[AdsbTrafficClient.TIME_SINCE_LAST_REPORT_KEY])

                if time_since_last_report < 60.0:
                    AdsbTrafficClient.TRAFFIC_MANAGER.heartbeat()
        except:
            pass

    def reset_traffic_manager(
        self
    ):
        """
        Sends a reset signal (if able) to the traffic manager.
        """

        try:
            self.__traffic_session__.get(
                "http://{}/Service/Reset".format(self.rest_address),
                timeout=configuration.AHRS_TIMEOUT).json()
        except:
            pass

    def update_reliable_traffic(
        self
    ):
        """
        Calls the traffic manager and gets a list of traffic that is trustable
        for position data.
        """
        try:
            traffic_json = self.__traffic_session__.get(
                "http://{}/Traffic/Reliable".format(self.rest_address),
                timeout=configuration.AHRS_TIMEOUT).json()

            # Report each traffic based on the keys
            for icao_identifier in traffic_json.keys():
                self.received_message(
                    icao_identifier, traffic_json[icao_identifier])

            return True

        except KeyboardInterrupt:
            raise
        except SystemExit:
            raise
        except Exception:
            # If we are spamming the REST too quickly, then we may loose a single update.
            # Do no consider the service unavailable unless we are
            # way below the max target framerate.
            return False

    def received_message(
        self,
        icao_identifier: str,
        adsb_traffic: dict
    ):
        """
        Handler for receiving a message.

        Arguments:
            adsb_traffic {map} -- The json message containing the traffic update
        """

        try:
            AdsbTrafficClient.TRAFFIC_MANAGER.handle_traffic_report(
                icao_identifier,
                adsb_traffic)
        except:
            print("Issue decoding JSON")

    def __dump_traffic_diag__(
        self
    ):
        """
        Prints our current traffic understanding.
        """

        diag_traffic = AdsbTrafficClient.TRAFFIC_MANAGER.get_traffic_with_position()

        if diag_traffic is not None:
            for traffic in diag_traffic:
                print("{0} - {1} - {2}".format(
                    traffic.get_display_name(),
                    traffic.bearing,
                    traffic.distance))


if __name__ == '__main__':
    import time

    trafficClient = AdsbTrafficClient(
        configuration.CONFIGURATION.get_traffic_manager_address())

    while True:
        time.sleep(5)
        print("position_valid:")
        reports = AdsbTrafficClient.TRAFFIC_MANAGER.get_traffic_with_position()
        for traffic_report in reports:
            print("    {0} {1} {2}".format(
                traffic_report.get_display_name(),
                traffic_report.bearing,
                traffic_report.distance))
