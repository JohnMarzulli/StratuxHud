"""
Gets any available NEXRAD imaging from the TrafficToHud service
and then helps render the images.
"""

import json
import math
import time
from typing import Dict, List

import requests

from common_utils import geo_math, tasks
from configuration import configuration


class ReflectivityBlock:
    def __init__(self, block):
        self.block_id = block["globalBlockReferenceId"]
        self.report_time = block["reportTime"]

        self.lat_step = block["boundaries"]["latSize"]
        self.lon_step = block["boundaries"]["lonSize"]

        self.north_western = [
            block["boundaries"]["northWestern"]["latitude"],
            block["boundaries"]["northWestern"]["longitude"],
        ]
        self.south_eastern = [
            block["boundaries"]["southEastern"]["latitude"],
            block["boundaries"]["southEastern"]["longitude"],
        ]
        self.north_eastern = (
            self.north_western[0],
            self.south_eastern[1],
        )
        self.south_western = (
            self.south_eastern[0],
            self.north_western[1],
        )

        self.reflectivity = block["reflectivity"]


class NexradClient:
    """
    Class to handle the REST calls to get NEXRAD imagery
    and help display it.
    """

    INSTANCE = None
    REFLECTIVITY: Dict[int, ReflectivityBlock] = {}

    @staticmethod
    def reflectivity_to_rgb(reflectivity_value):
        """
        Converts a reflectivity value to an RGB color.
        """
        if reflectivity_value <= 0:
            return (0, 0, 0)  # Black for no reflectivity
        elif reflectivity_value == 1:
            return (0, 255, 0)  # Green for light reflectivity
        elif reflectivity_value == 2:
            return (255, 255, 0)  # Yellow for moderate reflectivity
        elif reflectivity_value == 3:
            return (255, 165, 0)  # Orange for heavy reflectivity
        elif reflectivity_value >= 4:
            return (255, 0, 0)  # Red for very heavy reflectivity
        else:
            return (255, 255, 255)  # White for unknown reflectivity

    def __init__(self, rest_address: str):
        self.__nexrad_session__ = requests.Session()
        self.rest_address = rest_address
        self.__update_traffic_task__ = tasks.RecurringTask(
            "UpdateNexrad", 15, self.update_nexrad
        )
        NexradClient.INSTANCE = self

    def inject(self, nexrad_json):
        for id in nexrad_json:
            block_identifier = int(id)
            NexradClient.REFLECTIVITY[block_identifier] = ReflectivityBlock(
                nexrad_json[id]
            )

    def update_nexrad(self):
        """
        Calls the traffic manager and gets a list of traffic that is trustable
        for position data.
        """

        try:
            nexrad_json = self.__nexrad_session__.get(
                f"http://{self.rest_address}/Weather/Reflectivity",
                timeout=configuration.AHRS_TIMEOUT,
            ).json()

            self.inject(nexrad_json)

            self.__gc_reports__()

            return True

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            # If we are spamming the REST too quickly, then we may loose a single update.
            # Do no consider the service unavailable unless we are
            # way below the max target framerate.
            return False

    def __gc_reports__(self):
        current_time = int(time.time() * 1000)
        oldest_allowed_report_time = current_time - (15 * 60 * 1000)  # 15 minutes

        for id in list(NexradClient.REFLECTIVITY.keys()):
            if NexradClient.REFLECTIVITY[id].report_time < oldest_allowed_report_time:
                del NexradClient.REFLECTIVITY[id]

    @staticmethod
    def get_nexrad_in_range(center, radius) -> List[ReflectivityBlock]:
        """
        Returns a list of NEXRAD blocks that are within the given range.
        """

        if center is None:
            return []

        if radius <= 0.0:
            return []

        if NexradClient.REFLECTIVITY is None:
            return []

        expanded_radius = radius * 1.25

        return [
            NexradClient.REFLECTIVITY[id]
            for id in NexradClient.REFLECTIVITY
            if geo_math.get_distance(
                center, NexradClient.REFLECTIVITY[id].north_western
            )
            < expanded_radius
        ]

    @staticmethod
    def is_in_range(center, radius, block: ReflectivityBlock) -> bool:
        # geo_math.get_distance is in lat/long
        corners = [
            block.north_western,
            block.north_eastern,
            block.south_eastern,
            block.south_western,
        ]

        for corner in corners:
            distance = geo_math.get_distance(center, corner)
            if distance <= radius:
                return True

        return False

def test_nexrad_decoding():
    sample_center_location = [45.0, -122.8]
    nexrad_client = NexradClient(
        configuration.CONFIGURATION.get_traffic_manager_address()
    )
    full_file_path = configuration.get_absolute_file_path("../test_data/faa_sample_reflectivity.json")

    with open(full_file_path) as json_test_data_file:
        json_config_text = json_test_data_file.read()
        test_data_json = json.loads(json_config_text)
        nexrad_client.inject(test_data_json)

    faa_sample_reflectivity = nexrad_client.get_nexrad_in_range(sample_center_location, 50)
    assert(len(faa_sample_reflectivity) == 1)
    faa_sample_reflectivity = faa_sample_reflectivity[0]

    assert(faa_sample_reflectivity.block_id == 304496)
    assert(math.fabs(0.016 - faa_sample_reflectivity.lat_step) < 0.01)
    assert(math.fabs(45.133 -  faa_sample_reflectivity.north_western[0]) < 0.01)
    assert(math.fabs(-123.2 -  faa_sample_reflectivity.north_western[1]) < 0.01)

    assert(math.fabs(45.0666 -  faa_sample_reflectivity.south_eastern[0]) < 0.01)
    assert(math.fabs(-122.4 -  faa_sample_reflectivity.south_eastern[1]) < 0.01)

    assert(len(faa_sample_reflectivity.reflectivity) == 4)
    assert(len(faa_sample_reflectivity.reflectivity[0]) == 3)

    assert(faa_sample_reflectivity.reflectivity[0][0]["runLength"] == 7)
    assert(faa_sample_reflectivity.reflectivity[0][0]["reflectivity"] == 0)

    assert(faa_sample_reflectivity.reflectivity[0][1]["runLength"] == 18)
    assert(faa_sample_reflectivity.reflectivity[0][1]["reflectivity"] == 1)

    assert(faa_sample_reflectivity.reflectivity[0][2]["runLength"] == 7)
    assert(faa_sample_reflectivity.reflectivity[0][2]["reflectivity"] == 0)

if __name__ == "__main__":
    import time

    test_nexrad_decoding()

    nexrad_client = NexradClient(
        configuration.CONFIGURATION.get_traffic_manager_address()
    )

    while True:
        time.sleep(5)
        print("position_valid:")

        for blockIdentifier in NexradClient.REFLECTIVITY:
            print(
                "    {0} - {1} to {2}".format(
                    blockIdentifier,
                    NexradClient.REFLECTIVITY[blockIdentifier].north_western,
                    NexradClient.REFLECTIVITY[blockIdentifier].south_eastern,
                )
            )
