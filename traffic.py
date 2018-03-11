"""
Holds code relevant to collecting and traffic information.
"""
import configuration
import datetime
import math
import time
import threading
import json
import ws4py
from ws4py.client.threadedclient import WebSocketClient
import lib.recurring_task as recurring_task

# TODO - More work around making this a BG

class Traffic(object):
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
        return self.position_valid and self.bearing_distance_valid

    def get_age(self):
        """
        Returns the age of this report in total seconds.
        """
        delta = datetime.datetime.now() - self.time_decoded
        return delta.total_seconds()
    
    def get_identifer(self):
        """
        Returns the identifier to use of the traffic
        """

        if self.tail_number is not None and len(self.tail_number) > 1:
            return self.tail_number
        
        return self.iaco_address


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
        r = configuration.EARTH_RADIUS_STATUTE_MILES  # Radius of earth. Can change with units
        return c * r
    
    def update(self, json_report):
        """
        Applies the new data to the existing traffic.
        """

        try:
            self.__json__.update(json_report)
            self.__update_from_json__()
        except:
            print "Issue in update()"

    def __init__(self, json_from_stratux):
        """
        Initializes the traffic from the JSON response.
        """

        # Create all of the possible data
        self.iaco_address = None
        self.tail_number = None
        self.position_valid = None
        self.time_decoded = datetime.datetime.now()
        self.latitude = None
        self.longitude = None
        self.distance = None
        self.bearing = None
        self.altitude = None

        self.__json__ = json_from_stratux
        self.__update_from_json__()

    def __update_from_json__(self):
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
            self.iaco_address = self.__json__[Traffic.ICAO_ADDR_KEY]
            self.tail_number = self.__json__[Traffic.TAIL_NUMBER_KEY]
            self.position_valid = self.__json__[Traffic.POSITION_VALID_KEY]
            self.bearing_distance_valid = self.__json__[Traffic.BEARING_DISTANCE_VALID_KEY]
            self.time_decoded = datetime.datetime.now()

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
            print "Exception while updating..."

class TrafficManager(object):
    """
    Manager class that handles all of the position reports.
    """
    
    def clear(self):
        self.traffic = {}

    def get_unreliable_traffic(self):
        """
        Returns the traffic that DOES NOT have position data.
        """

        traffic_without_position = []

        self.__lock__.acquire()
        try:
            for identifier in self.traffic:
                if not self.traffic[identifier].is_valid_report():
                    if self.traffic[identifier].get_identifer() is self.__configuration__.ownship:
                        continue

                    traffic_without_position.append(self.traffic[identifier])
        finally:
            self.__lock__.release()

        sorted_traffic = sorted(traffic_without_position, key=lambda traffic: traffic.get_identifer())

        return sorted_traffic

    def get_traffic_with_position(self):
        """
        Returns the subset of traffic with actionable
        traffic data.
        """

        actionable_traffic = []

        self.__lock__.acquire()
        try:
            for identifier in self.traffic:
                if self.traffic[identifier].is_valid_report():
                    if self.traffic[identifier].get_identifer() is self.__configuration__.ownship:
                        continue

                    actionable_traffic.append(self.traffic[identifier])
        finally:
            self.__lock__.release()

        sorted_traffic = sorted(actionable_traffic, key=lambda traffic: traffic.distance)

        return sorted_traffic

    def handle_traffic_report(self, json_report):
        """
        Updates or sets a traffic report.
        """
        self.__lock__.acquire()
        try:
            traffic_report = Traffic(json_report)
            identifier = str(traffic_report.iaco_address)
            if traffic_report.iaco_address in self.traffic:
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
                nice_name = self.traffic[identifier].get_identifer()
                # print "{0} is {1}s old".format(nice_name, traffic_age)
                if traffic_age > (self.__configuration__.max_minutes_before_removal * 60):
                    # print "Pruning {0}/{1}".format(nice_name, identifier)
                    traffic_to_remove.append(identifier)

            for identifier_to_remove in traffic_to_remove:
                del self.traffic[identifier_to_remove]
        except:
            print "Issue on prune"
        finally:
            self.__lock__.release()

    def __init__(self):
        # Trafic held by tail number
        self.traffic = {}
        self.__configuration__ = configuration.Configuration(configuration.DEFAULT_CONFIG_FILE)
        self.__lock__ = threading.Lock()


class AdsbTrafficClient(WebSocketClient):
    """
    Class to handle opening the WebSocket connection
    for data and then handling the incoming data.
    """

    TRAFFIC_MANAGER = TrafficManager()

    def shutdown(self):
        try:
            self.__update_task__.stop()
            self.__prune_task__.stop()
            self.close_connection()
        except:
            print "Issue on shutdown"

    def opened(self):
        print "WebSocket opened to Stratux"

    def closed(self, code, reason=None):
        AdsbTrafficClient.TRAFFIC_MANAGER.clear()
        print "Closed down", code, reason

        print "Attempting to reconnect..."
        try:
            self.close_connection()
        except KeyboardInterrupt, SystemExit:
            raise
        except:
            print "Issue trying to close_connection"
        
        try:
            self.connect()
        except KeyboardInterrupt, SystemExit:
            raise
        except:
            print "Issue trying to reopen connection."

    def received_message(self, m):
        adsb_traffic = json.loads(m.data)
        AdsbTrafficClient.TRAFFIC_MANAGER.handle_traffic_report(adsb_traffic)
    
    def __dump_traffic_diag__(self):
        diag_traffic = AdsbTrafficClient.TRAFFIC_MANAGER.get_traffic_with_position()

        if diag_traffic is not None:
            for traffic in diag_traffic:
                print "{0} - {1} - {2}".format(traffic.get_identifer(), traffic.bearing, traffic.distance)
    
    def run_in_background(self):
        """
        Runs the WS traffic connector.
        """

        #connected = False

        #while not connected:
        try:
            self.connect()

            #connected = True

        except KeyboardInterrupt, SystemExit:
            raise
        except:
            print "Unable to connect..." # trying again."
            # time.sleep(0.5)

        self.__update_task__ = recurring_task.RecurringTask('TrafficUpdate', 0.1, self.run_forever, start_immediate=False)
        self.__prune_task__ = recurring_task.RecurringTask('PruneTraffic', 10, AdsbTrafficClient.TRAFFIC_MANAGER.prune_traffic_reports)
        # recurring_task.RecurringTask('TrafficDump', 1.0, self.__dump_traffic_diag__)

if __name__ == '__main__':
    import time

    try:
        CONFIGURATION = configuration.Configuration(configuration.DEFAULT_CONFIG_FILE)

        adsb_traffic_address= "ws://{0}/traffic".format(
            CONFIGURATION.stratux_address())
        ws = AdsbTrafficClient(adsb_traffic_address)
        ws.run_in_background()

        while True:
            time.sleep(5)
            print "position_valid:"
            reports = AdsbTrafficClient.TRAFFIC_MANAGER.get_traffic_with_position()
            for traffic_report in reports:
                print "    {0}".format(traffic_report.get_identifer())

            print "Other:"
            reports = AdsbTrafficClient.TRAFFIC_MANAGER.get_unreliable_traffic()
            for traffic_report in reports:
                print "    {0}".format(traffic_report.get_identifer())
            
            print "---------------"
            
    except KeyboardInterrupt:
           ws.shutdown()
