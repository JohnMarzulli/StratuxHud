"""
Handles fetching airports in proximity AND any known weather conditions.
"""

import json
import threading
from typing import Dict, List
from datetime import datetime, timezone

import requests

from common_utils import tasks
from configuration import configuration
from data_sources.airport_frequencies import AirportFrequency


class AirportClient:
    """
    Handles getting, and caching, the closest airports.
    """

    __INSTANCE__ = None
    __AIRPORTS__ = {}
    __FREQUENCIES__ = {}
    __FLIGHT_RULES__ = {}
    __LOCK_OBJECT__ = threading.Lock()
    __LAST_KNOWN_POSITION__ = None
    __EXPIRATION_DATE__ = datetime.now(timezone.utc)

    @staticmethod
    def is_airport_data_valid():
        if AirportClient.__EXPIRATION_DATE__ is not None:
            return AirportClient.__EXPIRATION_DATE__ >= datetime.now(timezone.utc)

        return False

    @staticmethod
    def set_last_known_position(location: List[int]):
        """
        Set the latest position of the aircraft
        [0] = Lat
        [1] = Lon

        Args:
            location (List[int]): The GPS coordinates of the aircraft.
        """
        AirportClient.__LAST_KNOWN_POSITION__ = location

    @staticmethod
    def get_station_coordinates(ident: str) -> List[float]:
        AirportClient.__LOCK_OBJECT__.acquire()

        coordinates = None
        if ident in AirportClient.__AIRPORTS__:
            airport = AirportClient.__AIRPORTS__[ident]
            if "coordinates" in airport:
                coordinates = [
                    airport["coordinates"]["latitude"],
                    airport["coordinates"]["longitude"],
                ]

        AirportClient.__LOCK_OBJECT__.release()

        return coordinates

    @staticmethod
    def get_nearby_airports() -> Dict[str, any]:
        """
        Get any known nearby airports.

        Returns:
            Dict[str, any]: The key is the airport identifier.
        """
        AirportClient.__LOCK_OBJECT__.acquire()

        airports_copy = AirportClient.__AIRPORTS__.copy()

        for ident in airports_copy.keys():
            if ident in AirportClient.__FLIGHT_RULES__:
                airports_copy[ident]["flightRules"] = AirportClient.__FLIGHT_RULES__[
                    ident
                ]

        AirportClient.__LOCK_OBJECT__.release()

        return airports_copy

    @staticmethod
    def get_flight_rules() -> Dict[str, str]:
        """
        Get any known flight rules

        Returns:
            Dict[str, any]: The key is the airport identifier.
        """
        AirportClient.__LOCK_OBJECT__.acquire()

        flight_rules_copy = AirportClient.__FLIGHT_RULES__.copy()

        AirportClient.__LOCK_OBJECT__.release()

        return flight_rules_copy

    @staticmethod
    def get_nearby_airport_frequencies() -> Dict[str, List[AirportFrequency]]:
        """
        Get any known nearby airport frequencies.

        Returns:
            Dict[str, any]: The key is the airport identifier.
        """
        AirportClient.__LOCK_OBJECT__.acquire()

        airports_freq_copy = AirportClient.__FREQUENCIES__.copy()

        AirportClient.__LOCK_OBJECT__.release()

        return airports_freq_copy

    @staticmethod
    def inject_airports(airports: Dict[str, any]):
        # sourcery skip: do-not-use-bare-except
        """
        Load the given airport information into the cache.
        Clears all previous information.

        Args:
            airports_json (_type_): The list of airports recieved from the TrafficToHud service.
        """
        AirportClient.__LOCK_OBJECT__.acquire()

        AirportClient.__AIRPORTS__.clear()

        for airport in airports:
            try:
                AirportClient.__AIRPORTS__[airport["ident"]] = airport
            except:
                pass

        AirportClient.__LOCK_OBJECT__.release()

    @staticmethod
    def inject_airport_frequencies(airport_frequencies: Dict[str, any]):
        """
        Takes a set of airport freqs (from service or test-mode loader)
        and inserts them into the data store.

        Args:
            airport_frequencies (Dict[str, any]): The set of frequencies to remember.
        """
        # sourcery skip: do-not-use-bare-except
        AirportClient.__LOCK_OBJECT__.acquire()

        AirportClient.__FREQUENCIES__.clear()

        for ident in airport_frequencies:
            try:
                allFreqs = [
                    AirportFrequency(info) for info in airport_frequencies[ident]
                ]
                AirportClient.__FREQUENCIES__[ident] = allFreqs
            except:
                pass

        AirportClient.__LOCK_OBJECT__.release()

    @staticmethod
    def update_expiration(expiration_date: datetime):
        if expiration_date is not None:
            AirportClient.__EXPIRATION_DATE__ = expiration_date

    @staticmethod
    def inject_flight_rules(flight_rules: Dict[str, str]):
        # sourcery skip: do-not-use-bare-except
        AirportClient.__LOCK_OBJECT__.acquire()

        for airport in flight_rules:
            try:
                AirportClient.__FLIGHT_RULES__[airport] = flight_rules[airport]
            except:
                pass

        AirportClient.__LOCK_OBJECT__.release()

    def __init__(self, rest_address: str):
        AirportClient.__LOCK_OBJECT__.acquire()

        try:
            if AirportClient.__INSTANCE__ != None:
                return

            AirportClient.__INSTANCE__ = self

            self.__airports_session__ = requests.Session()
            self.rest_address = rest_address
            # Doing all of the range calculations is probably expensive,
            # not to mention the transfer back over the local stack.
            #
            # These data are not expected to change quickly.
            # An interval of even 5 minutes may be sufficient.
            self.__update_traffic_task__ = tasks.RecurringTask(
                "UpdateAirports", 30, self.__update_airports__
            )

            self.__update_flight_rules_task__ = tasks.RecurringTask(
                "UpdateFlightRules", 30, self.__update_flight_rules__
            )

            self.__update_airport_frequencies_task__ = tasks.RecurringTask(
                "UpdateAirportFrequencies", 30, self.__update_airport_frequencies__
            )

            self.__update_airport_expiration_task__ = tasks.RecurringTask(
                "UpdateAirportExpiration", 30, self.__update_airport_expiration__
            )
        finally:
            AirportClient.__LOCK_OBJECT__.release()

    def __update_flight_rules__(self):
        # Example response
        # {"KPLU":"VFR","K4S2":"MVFR","KS39":"VFR","KBVS":"VFR","KSZT":"VFR","K0S9":"VFR","K6S2":"IFR","KS33":"VFR","K63S":"MVFR"}

        try:
            flight_rules_json = self.__airports_session__.get(
                f"http://{self.rest_address}/Weather/FlightRules",
                timeout=configuration.AHRS_TIMEOUT,
            ).json()

            AirportClient.inject_flight_rules(flight_rules_json)

            return True

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            # If we are spamming the REST too quickly, then we may loose a single update.
            # Do no consider the service unavailable unless we are
            # way below the max target framerate.
            return False

    def __update_airport_expiration__(self):
        try:
            expiration_json = self.__airports_session__.get(
                f"http://{self.rest_address}/airports/Status",
                timeout=configuration.AHRS_TIMEOUT,
            ).json()

            if not expiration_json:
                return False

            expiration_date = datetime.strptime(
                expiration_json.get("expiration"), "%Y-%m-%d").replace(tzinfo=timezone.utc)

            AirportClient.update_expiration(expiration_date)

            return True

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as ex:
            # If we are spamming the REST too quickly, then we may loose a single update.
            # Do no consider the service unavailable unless we are
            # way below the max target framerate.
            print(
                f"Exception occurred while updating airport expiration: {ex}")
            return False

    def __update_airports__(self):
        try:
            if (
                AirportClient.__LAST_KNOWN_POSITION__ is None
                or len(AirportClient.__LAST_KNOWN_POSITION__) != 2
            ):
                return

            airports_json = self.__airports_session__.get(
                f"http://{self.rest_address}/airports/airports?lat={AirportClient.__LAST_KNOWN_POSITION__[0]}&lon={AirportClient.__LAST_KNOWN_POSITION__[1]}&dist=50",
                timeout=configuration.AHRS_TIMEOUT,
            ).json()

            AirportClient.inject_airports(airports_json)

            return True

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            # If we are spamming the REST too quickly, then we may loose a single update.
            # Do no consider the service unavailable unless we are
            # way below the max target framerate.
            return False

    def __update_airport_frequencies__(self):
        try:
            if (
                AirportClient.__LAST_KNOWN_POSITION__ is None
                or len(AirportClient.__LAST_KNOWN_POSITION__) != 2
            ):
                return False

            airports_json = self.__airports_session__.get(
                f"http://{self.rest_address}/airports/Frequencies?lat={AirportClient.__LAST_KNOWN_POSITION__[0]}&lon={AirportClient.__LAST_KNOWN_POSITION__[1]}&dist=50",
                timeout=configuration.AHRS_TIMEOUT,
            ).json()

            AirportClient.inject_airport_frequencies(airports_json)

            return True

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as ex:
            # If we are spamming the REST too quickly, then we may loose a single update.
            # Do no consider the service unavailable unless we are
            # way below the max target framerate.
            print(
                f"Exception occurred while updating airport frequencies: {ex}")

            return False


def load_example_flight_rules():
    AirportClient.inject_flight_rules(
        {
            "KPLU": "VFR",
            "K4S2": "MVFR",
            "KS39": "VFR",
            "KBVS": "VFR",
            "KSZT": "VFR",
            "K0S9": "VFR",
            "K6S2": "IFR",
            "KS33": "VFR",
            "K63S": "MVFR",
            "KRNT": "IFR",
            "KSEA": "VFR",
            "KBFI": "MVFR",
            "1WA6": "LIFR",
        }
    )


def load_example_airports():
    example_airport_json = load_test_data(
        "../test_data/example_airport_response.json")
    example_frequency_json = load_test_data(
        "../test_data/example_freq_response.json")

    AirportClient.inject_airports(example_airport_json)
    AirportClient.inject_airport_frequencies(example_frequency_json)
    AirportClient.set_last_known_position([-122.2, 47.5])


def load_test_data(file_name: str):
    full_file_path = configuration.get_absolute_file_path(file_name)

    with open(full_file_path) as json_test_data_file:
        json_config_text = json_test_data_file.read()
        return json.loads(json_config_text)


airport_client_instance = AirportClient(
    configuration.CONFIGURATION.get_traffic_manager_address()
)

if __name__ == "__main__":
    load_example_airports()
    nearby_airports = AirportClient.get_nearby_airports()
    nearby_freqs = AirportClient.get_nearby_airport_frequencies()

    print(f"Found {len(nearby_airports)} airports")
    print(f"Found {len(nearby_freqs)} freqs")
