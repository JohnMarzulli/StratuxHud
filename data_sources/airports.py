"""
Handles fetching airports in proximity AND any known weather conditions.
"""

import requests
import requests
import json
import threading

from common_utils import tasks
from configuration import configuration
from data_sources.aircraft import Aircraft


class AirportClient:

    __AIRPORTS__ = {}
    __LOCK_OBJECT__ = threading.Lock()
    __LAST_KNOWN_POSITION__ = None

    def __init__(self, rest_address: str, aircraft: Aircraft):
        self.__airports_session__ = requests.Session()
        self.rest_address = rest_address
        self.__update_traffic_task__ = tasks.RecurringTask(
            "UpdateAirports", 15, self.update_airports
        )
        AirportClient.__AIRCRAFT__ = aircraft

    def update_airports(self):
        try:
            if AirportClient.__LAST_KNOWN_POSITION__ is None:
                return

            airports_json = self.__airports_session__.get(
                f"http://{self.rest_address}/airports/airports?lat={AirportClient.__LAST_KNOWN_POSITION__[0]}&lon={AirportClient.__LAST_KNOWN_POSITION__[1]}&dist=50",
                timeout=configuration.AHRS_TIMEOUT,
            ).json()

            AirportClient.inject(airports_json)

            return True

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            # If we are spamming the REST too quickly, then we may loose a single update.
            # Do no consider the service unavailable unless we are
            # way below the max target framerate.
            return False

    @staticmethod
    def set_last_known_position(location):
        AirportClient.__LAST_KNOWN_POSITION__ = location

    @staticmethod
    def get_nearby_airports():
        AirportClient.__LOCK_OBJECT__.acquire()

        airports_copy = AirportClient.__AIRPORTS__.copy()

        AirportClient.__LOCK_OBJECT__.release()

        return airports_copy

    @staticmethod
    def inject(airports_json):
        AirportClient.__LOCK_OBJECT__.acquire()

        AirportClient.__AIRPORTS__.clear()

        for id in airports_json:
            AirportClient.__AIRPORTS__[id] = airports_json[id]

        AirportClient.__LOCK_OBJECT__.release()


def load_example_airports():
    example_json = '[{"coordinates":{"longitude":-122.149561389,"latitude":47.280656111},"ident":"WA84","name":"Auburn Academy","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.226655,"latitude":47.3276250000001},"ident":"S50","name":"Auburn Muni","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-121.536471944,"latitude":47.3953688890001},"ident":"4W0","name":"Bandera State","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-122.0678925,"latitude":47.2681561110001},"ident":"51WA","name":"Evergreen Sky Ranch","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.009835833,"latitude":47.315656389},"ident":"95WA","name":"Black Diamond","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.764805556,"latitude":47.4902500000001},"ident":"KPWT","name":"Bremerton Ntl","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-122.773894444,"latitude":47.6079861110001},"ident":"WA96","name":"Leisureland Airpark","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.119975833,"latitude":47.183851389},"ident":"WN42","name":"Flying H Ranch","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.159027778,"latitude":48.1607500000001},"ident":"KAWO","name":"Arlington Muni","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-122.133055556,"latitude":47.215555556},"ident":"9WA7","name":"Albritton","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.898887139,"latitude":47.996084556},"ident":"WA45","name":"Olympic Fld","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.257222222,"latitude":46.8716666670001},"ident":"2W3","name":"Swanson Fld","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-122.133744722,"latitude":48.005096667},"ident":"76WA","name":"Heineck Farm","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-121.863725833,"latitude":47.559546111},"ident":"1WA6","name":"Fall City","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.580783333,"latitude":47.079219444},"ident":"KGRF","name":"Gray AAF (Joint Base Lewis-McChord)","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.014515,"latitude":48.093026389},"ident":"WA25","name":"Green Valley Airfield","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-121.533666667,"latitude":47.0131388890001},"ident":"21W","name":"Ranger Creek","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-122.608055556,"latitude":47.9386111110001},"ident":"WA22","name":"Mirth","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.103536389,"latitude":47.337096667},"ident":"S36","name":"Norman Grier Fld","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-122.529722222,"latitude":47.7983333330001},"ident":"WA61","name":"Thompson","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.736547222,"latitude":46.9707500000001},"ident":"14WA","name":"Lz Ranch","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.821247222,"latitude":47.1114850000001},"ident":"6WA2","name":"Gower Fld","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.827833333,"latitude":46.992388889},"ident":"44T","name":"Hoskins Fld","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-122.667913333,"latitude":47.4323175000001},"ident":"4WA9","name":"Port Orchard","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.022056111,"latitude":47.1956569440001},"ident":"WA77","name":"EnuMcLaw","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.092614444,"latitude":47.2085733330001},"ident":"WN87","name":"Bryan","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-121.924553889,"latitude":47.2435738890001},"ident":"WN76","name":"Bergseth Fld","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.282093889,"latitude":47.9073180560001},"ident":"KPAE","name":"Seattle Paine Fld Intl","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-122.155555556,"latitude":47.898055556},"ident":"96WA","name":"Jim & Julie\'s","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.235669722,"latitude":47.003990833},"ident":"86WA","name":"Kapowsin Fld","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.062836111,"latitude":48.110423611},"ident":"WN53","name":"Frontier Airpark","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.4377275,"latitude":48.01751225},"ident":"W10","name":"Whidbey Air Park","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-122.7718,"latitude":47.1784305560001},"ident":"00WA","name":"Howell","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-121.995243889,"latitude":47.871363611},"ident":"W16","name":"First Air Fld","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-121.922901667,"latitude":47.8723219440001},"ident":"WN20","name":"Van De Plasch","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.902544722,"latitude":46.9694044440001},"ident":"KOLM","name":"Olympia Rgnl","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-122.569021389,"latitude":47.4637077780001},"ident":"WN13","name":"Vaughan Ranch Airfield","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.810638889,"latitude":48.053805556},"ident":"0S9","name":"Jefferson County Intl","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-122.772109444,"latitude":47.9720341670001},"ident":"WA42","name":"Stacey\'s","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.840661111,"latitude":48.076944444},"ident":"WA68","name":"Sky Valley Airstrip","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.287200278,"latitude":47.1039200000001},"ident":"KPLU","name":"Pierce County/Thun Fld","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-122.859608333,"latitude":47.8400913890001},"ident":"WN00","name":"Kimshan Ranch","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.669569722,"latitude":46.8975991670001},"ident":"3WA0","name":"Taylor","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.601233889,"latitude":46.8776},"ident":"8WA0","name":"Flying B","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.21575,"latitude":47.4931388890001},"ident":"KRNT","name":"Renton Muni","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-122.301944444,"latitude":47.529972222},"ident":"KBFI","name":"Boeing Fld/King County Intl","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-122.094002778,"latitude":47.1523238890001},"ident":"02WA","name":"Cawleys South Prairie","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.371083333,"latitude":47.0703888890001},"ident":"3B8","name":"Shady Acres","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-122.476475,"latitude":47.1376777780001},"ident":"KTCM","name":"McChord Fld (Joint Base Lewis-McChord)","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.578111111,"latitude":47.2679444440001},"ident":"KTIW","name":"Tacoma Narrows","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-122.476971944,"latitude":47.458588611},"ident":"2S1","name":"Vashon Muni","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-122.790277778,"latitude":47.3552222220001},"ident":"WT77","name":"Rocky Bay","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.055972222,"latitude":47.129680556},"ident":"WN15","name":"Burnett Landing","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.522063611,"latitude":46.8470455560001},"ident":"49WA","name":"Cougar Mountain Airfield","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.553038889,"latitude":46.924984722},"ident":"06WN","name":"Western Airpark","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.311777778,"latitude":47.4498888890001},"ident":"KSEA","name":"Seattle-Tacoma Intl","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-123.147555556,"latitude":47.2335555560001},"ident":"KSHN","name":"Sanderson Fld","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-122.733179167,"latitude":47.6564319440001},"ident":"8W5","name":"Apex Airpark","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-121.339056389,"latitude":47.710935556},"ident":"S88","name":"Skykomish State","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-122.102743611,"latitude":47.9048680280001},"ident":"S43","name":"Harvey Fld","airportType":"AD","isPublic":true},{"coordinates":{"longitude":-122.043333333,"latitude":47.8133333330001},"ident":"WA04","name":"Kyles","airportType":"AD","isPublic":false},{"coordinates":{"longitude":-122.725888889,"latitude":46.9704166670001},"ident":"08WA","name":"P-L Ranch","airportType":"AD","isPublic":false}]'

    AirportClient.inject(json.loads(example_json))
