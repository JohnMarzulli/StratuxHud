"""
Holds code relevant to collecting and traffic information.
"""

import datetime
import json
import math
import random
import socket
import threading
import time
import ping

import ws4py
from ws4py.client.threadedclient import WebSocketClient
from ws4py.streaming import Stream

import configuration
import lib.recurring_task as recurring_task
from lib.simulated_values import SimulatedValue


# TODO - More work around making this a BG


class Traffic(object):
    """
    Holds data about traffic that the ADSB has received.
    """

    TAIL_NUMBER_KEY = 'Tail'
    LATITUDE_KEY = 'Lat'
    LONGITUDE_KEY = 'Lon'
    DISTANCE_KEY = 'Distance'
    BEARING_KEY = 'Bearing'
    ALTITUDE_KEY = 'Alt'
    # We need to key off the ICAO address due to 'Anonymous Mode'...
    ICAO_ADDR_KEY = 'Icao_addr'
    POSITION_VALID_KEY = 'Position_valid'
    BEARING_DISTANCE_VALID_KEY = 'BearingDist_valid'

    TRAFFIC_REPORTS_RECEIVED = 0

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

    def is_valid_report(self):
        """
        Is the current report valid and usable?

        Returns:
            bool -- True if the report can be trusted.
        """

        return self.position_valid and self.bearing_distance_valid

    def is_on_ground(self):
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

    def get_age(self):
        """
        Returns the age of this report in total seconds.
        """
        delta = datetime.datetime.utcnow() - self.time_decoded
        return delta.total_seconds()

    def get_identifer(self):
        """
        Returns the identifier to use of the traffic
        """

        if self.tail_number is not None and len(self.tail_number) > 1:
            return self.tail_number

        return self.icao_address

    def get_bearing(self, starting_lat, starting_lon):
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

    def get_distance(self, starting_lat, starting_lon):
        """
        Returns the distance to the traffic from the
        given point.
        """

        if not self.position_valid or self.latitude is None or self.longitude is None:
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

    def update(self, json_report):
        """
        Applies the new data to the existing traffic.
        """

        try:
            self.__json__.update(json_report)
            self.__update_from_json__()
        except:
            print("Issue in update()")

    def __init__(self, json_from_stratux):
        """
        Initializes the traffic from the JSON response.
        """

        # Create all of the possible data
        self.icao_address = None
        self.tail_number = None
        self.position_valid = None
        self.time_decoded = datetime.datetime.utcnow()
        self.latitude = None
        self.longitude = None
        self.distance = None
        self.bearing = None
        self.altitude = None

        self.__json__ = json_from_stratux
        self.__update_from_json__()

    def __update_from_json__(self):
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
            self.icao_address = self.__json__[Traffic.ICAO_ADDR_KEY]
            self.tail_number = self.__json__[Traffic.TAIL_NUMBER_KEY]
            self.position_valid = self.__json__[Traffic.POSITION_VALID_KEY]
            self.bearing_distance_valid = self.__json__[
                Traffic.BEARING_DISTANCE_VALID_KEY]
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
        except:
            print("Exception while updating...")


class SimulatedTraffic(object):
    """
    Class to simulated ADSB received traffic.
    """

    def __init__(self):
        """
        Creates a new traffic simulation object.
        """

        target_center_position = (48.160464, -122.166409)
        runway_number_position = (48.155973, -122.157582)
        starting_points = (target_center_position, runway_number_position)

        self.icao_address = random.randint(10000, 100000)
        self.tail_number = "N{0}{1}{2}".format(random.randint(
            1, 9), random.randint(0, 9), random.randint(0, 9))
        self.position_valid = True
        self.time_decoded = datetime.datetime.utcnow()
        self.latitude = SimulatedValue(0.1, 10, 1, random.randint(
            0, 9), starting_points[random.randint(0, 1)][0])
        self.longitude = SimulatedValue(0.1, 10, 1, random.randint(
            0, 9), starting_points[random.randint(0, 1)][1])
        self.distance = SimulatedValue(
            10, 1000, -1, random.randint(0, 1000), 1000)
        self.bearing = SimulatedValue(0, 180, -1, random.randint(0, 180), 180)
        self.altitude = SimulatedValue(10, 100, -1, 0, 500)
        self.speed = SimulatedValue(5, 10, 1, 85)

    def simulate(self):
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

    def to_json(self):
        """
        Returns this object back as a dictionary (deserialized json)

        Returns:
            dictionary -- The dictionary representing a traffic report.
        """

        return {'TargetType': 1,
                'Vvel': -1152,
                'Speed_valid': True,
                'Emitter_category': 3,
                'Tail': self.tail_number,
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
                'Position_valid': True,
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

    def clear(self):
        """
        Resets the traffic reports.
        """

        self.traffic = {}

    def get_unreliable_traffic(self):
        """
        Returns the traffic that DOES NOT have position data.
        """

        traffic_without_position = []

        self.__lock__.acquire()
        try:
            traffic_without_position = [self.traffic[identifier]
                                        if not self.traffic[identifier].is_valid_report()
                                        else None for identifier in self.traffic]
            traffic_without_position = filter(
                lambda x: x is not None, traffic_without_position)
        finally:
            self.__lock__.release()

        sorted_traffic = sorted(traffic_without_position,
                                key=lambda traffic: traffic.get_identifer())

        return sorted_traffic

    def get_traffic_with_position(self):
        """
        Returns the subset of traffic with actionable
        traffic data.
        """

        actionable_traffic = []

        self.__lock__.acquire()
        try:
            traffic_with_position = {k: v for k, v in self.traffic.iteritems() if v is not None and v.is_valid_report(
            ) and configuration.CONFIGURATION.ownship not in str(v.get_identifer())}
            actionable_traffic = [self.traffic[identifier]
                                  for identifier in traffic_with_position]
        finally:
            self.__lock__.release()

        sorted_traffic = sorted(
            actionable_traffic, key=lambda traffic: traffic.distance)

        return sorted_traffic

    def handle_traffic_report(self, json_report):
        """
        Updates or sets a traffic report.
        """
        self.__lock__.acquire()
        try:
            traffic_report = Traffic(json_report)
            identifier = str(traffic_report.icao_address)
            if traffic_report.icao_address in self.traffic:
                self.traffic[identifier].update(json_report)
            else:
                self.traffic[identifier] = traffic_report
        finally:
            self.__lock__.release()

        if traffic_report is not None:
            return traffic_report.get_identifer()

        return None

    def prune_traffic_reports(self):
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

    def __init__(self):
        # Traffic held by tail number
        self.traffic = {}
        self.__lock__ = threading.Lock()
        self.__prune_task__ = recurring_task.RecurringTask(
            'PruneTraffic', 10, self.prune_traffic_reports)


class AdsbTrafficClient(WebSocketClient):
    """
    Class to handle opening the WebSocket connection
    for data and then handling the incoming data.
    """

    TRAFFIC_MANAGER = TrafficManager()
    INSTANCE = None

    def __init__(self, socket_address):
        WebSocketClient.__init__(self, socket_address)

        self.create_time = datetime.datetime.utcnow()
        self.__update_task__ = None
        self.__manage_connection_task__ = None
        self.last_message_received_time = None
        self.is_connected = False
        self.is_connecting = False
        self.connect()

        self.hb = ws4py.websocket.Heartbeat(self)
        self.hb.start()
    
    def keep_alive(self):
        """
        Sends the current date/time to the otherside of the socket
        as a form of keepalive.
        """

        print('Socket KeepAlive sent {}'.format(datetime.datetime.utcnow()))
        self.send(str(datetime.datetime.utcnow()))

    def shutdown(self):
        """
        Stops the WebSocket and reception tasks.
        """

        self.hb.stop()
        self.hb = None
        self.is_connected = False
        self.is_connecting = False

        try:
            self.__update_task__.stop()
        except:
            pass

        try:
            self.__prune_task__.stop()
        except:
            pass

        try:
            self.close_connection()
        except:
            print("Issue on shutdown")

    def opened(self):
        """
        Event handler for when then connection is opened.
        """

        self.is_connected = True
        self.is_connecting = False
        print("WebSocket opened to Stratux")

    def closed(self, code, reason=None):
        """
        Event handler for when the socket is closed.

        Arguments:
            code {object} -- The code for why the socket was closed.

        Keyword Arguments:
            reason {string} -- The reason why the socket was closed. (default: {None})
        """

        self.is_connected = False
        self.is_connecting = False

        print("Closed down", code, reason)

        print("Attempting to reconnect...")
        try:
            self.close_connection()
        except KeyboardInterrupt, SystemExit:
            raise
        except:
            print("Issue trying to close_connection")

    def ponged(self, pong):
        print("Pong")

    def received_message(self, m):
        """
        Handler for receiving a message.

        Arguments:
            m {string} -- The json message in string form.
        """

        self.is_connected = True
        self.is_connecting = False
        self.last_message_received_time = datetime.datetime.utcnow()

        try:
            Traffic.TRAFFIC_REPORTS_RECEIVED += 1
            adsb_traffic = json.loads(m.data)
            AdsbTrafficClient.TRAFFIC_MANAGER.handle_traffic_report(
                adsb_traffic)
        except:
            print("Issue decoding JSON")

    def __dump_traffic_diag__(self):
        """
        Prints our current traffic understanding.
        """

        diag_traffic = AdsbTrafficClient.TRAFFIC_MANAGER.get_traffic_with_position()

        if diag_traffic is not None:
            for traffic in diag_traffic:
                print("{0} - {1} - {2}".format(traffic.get_identifer(),
                                               traffic.bearing, traffic.distance))

    def run_in_background(self):
        """
        Runs the WS traffic connector.
        """

        self.__update_task__ = recurring_task.RecurringTask(
            'TrafficUpdate', 0.1, self.run_forever, start_immediate=False)


class ConnectionManager(object):
    """
    Object to manage the connection to the Stratux WebSocket.
    Performs the connections and re-connects.
    """

    def __init__(self, socket_address, logger=None):
        self.__is_shutting_down__ = False
        self.__manage_connection_task__ = None
        self.__socket_address__ = socket_address
        self.__manage_connection_task__ = recurring_task.RecurringTask(
            'ManageConnection', 2, self.__manage_connection__, start_immediate=False)
        self.__pong_task__ = recurring_task.RecurringTask(
            'HeartbeatStratux', 2, self.pong_stratux)
        self.CONNECT_ATTEMPTS = 0
        self.SHUTDOWNS = 0
        self.SILENT_TIMEOUTS = 0
        self.__last_action_time__ = datetime.datetime.utcnow()
        self.__logger__ = logger

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

    def pong_stratux(self):
        """
        Send pong to the Stratux
        """
        ping.verbose_pong(configuration.CONFIGURATION.stratux_address())

    def ping_stratux(self):
        """
        Run a complete ping against the Stratux.
        This keeps the connection alive.
        """
        ping.verbose_ping(configuration.CONFIGURATION.stratux_address())

        if AdsbTrafficClient.INSTANCE is not None:
            AdsbTrafficClient.INSTANCE.keep_alive()

    def __get_time_since_last_action__(self):
        return (datetime.datetime.utcnow() - self.__last_action_time__).total_seconds() / 60.0

    def __manage_connection__(self):
        """
        Handles the connection.
        """

        self.ping_stratux()

        create = AdsbTrafficClient.INSTANCE is None
        restart = False
        if AdsbTrafficClient.INSTANCE is not None:
            is_silent_timeout = self.__is_connection_silently_timed_out__()
            restart |= is_silent_timeout
            restart |= not (AdsbTrafficClient.INSTANCE.is_connected
                            or AdsbTrafficClient.INSTANCE.is_connecting)

            if restart:
                self.warn('__manage_connection__() - SHUTTING DOWN EXISTING CONNECTION after {:.1f} minutes'.format(
                    self.__get_time_since_last_action__()))
                self.__last_action_time__ = datetime.datetime.utcnow()
                AdsbTrafficClient.INSTANCE.shutdown()
                create = True

                if is_silent_timeout:
                    self.warn("   => Silent timeout!")
                    self.SILENT_TIMEOUTS += 1

        if create:
            self.__last_action_time__ = datetime.datetime.utcnow()
            self.CONNECT_ATTEMPTS += 1
            self.warn('__manage_connection__() - ATTEMPTING TO CONNECT after {:.1f} minutes'.format(
                self.__get_time_since_last_action__()))
            AdsbTrafficClient.INSTANCE = AdsbTrafficClient(
                self.__socket_address__)
            AdsbTrafficClient.INSTANCE.run_in_background()
            time.sleep(30 if not self.__is_shutting_down__ else 0)
        else:
            # self.log('__manage_connection__ => OK')
            time.sleep(1)

    def reset(self):
        """
        Causes the WebSocket to reset.
        """

        try:
            self.warn("Resetting the websocket at the user's request.")
            if AdsbTrafficClient.INSTANCE is not None:
                AdsbTrafficClient.INSTANCE.shutdown()

            self.__last_action_time__ = datetime.datetime.utcnow()
            AdsbTrafficClient.INSTANCE = AdsbTrafficClient(self.__socket_address__)
            AdsbTrafficClient.INSTANCE.run_in_background()
        finally:
            self.warn("Finished with WebSocket connection reset attempt.")


    def shutdown(self):
        """
        Shutsdown the WebSocket connection.
        """

        self.__is_shutting_down__ = True
        self.SHUTDOWNS += 1
        if self.__manage_connection_task__ is not None:
            self.__manage_connection_task__.stop()

        if AdsbTrafficClient.INSTANCE is not None:
            AdsbTrafficClient.INSTANCE.shutdown()
            AdsbTrafficClient.INSTANCE = None

    def get_last_ping_time(self):
        """
        When was the last time a ping message was received?

        Returns:
            datetime -- The UTC time the last ping was received.
        """

        ping_last_received_time = ping.LastReceived.LAST_RECIEVED
        ping_last_received_time = self.__last_action_time__ if ping_last_received_time is None else ping_last_received_time

        return ping_last_received_time

    def get_last_message_time(self):
        """
        When was the last time a traffic message was received?

        Returns:
            datetime -- The UTC time the last traffic message was received.
        """

        msg_last_received_time = AdsbTrafficClient.INSTANCE.last_message_received_time
        msg_last_received_time = self.__last_action_time__ if msg_last_received_time is None else msg_last_received_time

        return msg_last_received_time

    def __is_connection_silently_timed_out__(self):
        """
        Tries to determine if the socket has stopped sending us data.

        Returns:
            bool -- True if we think the socket has closed.
        """

        now = datetime.datetime.utcnow()

        # Use the ping reception to augment the last message reception time
        # If the SDRs are not receiving any traffic, then no updates will be
        # sent... but the connection is still very much open and active.
        msg_last_received_time = self.get_last_message_time()
        msg_last_received_delta = (
            now - msg_last_received_time).total_seconds()
        
        # Do we want to include the ping as a reception time?
        # ping_last_received_time = self.get_last_ping_time()
        # ping_last_received_delta = (
        #     now - ping_last_received_time).total_seconds()

        connection_uptime = (
            now - AdsbTrafficClient.INSTANCE.create_time).total_seconds()

        if msg_last_received_delta > 60: #
            #     and ping_last_received_delta > 15:
            self.warn("{0:.1f} seconds connection uptime".format(
                connection_uptime))
            self.warn('Last report message was at {}'.format(
                msg_last_received_time))
            # self.warn('Last PING was at {}'.format(ping_last_received_time))

            return not AdsbTrafficClient.INSTANCE.is_connecting

        return False


if __name__ == '__main__':
    import time

    try:
        adsb_traffic_address = "ws://{0}/traffic".format(
            configuration.CONFIGURATION.stratux_address())
        connection_manager = ConnectionManager(adsb_traffic_address)

        while True:
            time.sleep(5)
            print("position_valid:")
            reports = AdsbTrafficClient.TRAFFIC_MANAGER.get_traffic_with_position()
            for traffic_report in reports:
                print("    {0} {1} {2}".format(traffic_report.get_identifer(
                ), traffic_report.bearing, traffic_report.distance))

            print("Other:")
            reports = AdsbTrafficClient.TRAFFIC_MANAGER.get_unreliable_traffic()
            for traffic_report in reports:
                print("    {0}".format(traffic_report.get_identifer()))

            print("---------------")

    except KeyboardInterrupt:
        connection_manager.shutdown()
