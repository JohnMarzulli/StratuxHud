"""
Gets any available NEXRAD imaging from the TrafficToHud service
and then helps render the images.
"""

import requests
import requests
import time

from common_utils import geo_math, tasks
from configuration import configuration

# Example response:
# {
#     "304048": {
#         "reportTime": 1736139682259,
#         "globalBlockReferenceId": 304048,
#         "boundaries": {
#             "northWestern": {
#                 "longitude": -121.6,
#                 "latitude": 45.06666666666667
#             },
#             "southEastern": {
#                 "longitude": -120.8,
#                 "latitude": 45
#             }
#         },
#         "reflectivity": [
#             [
#                 1,
#                 1,
#                 1,
#                 1,
#                 2,
#                 1,
#                 1,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0
#             ],
#             [
#                 1,
#                 1,
#                 1,
#                 1,
#                 1,
#                 1,
#                 1,
#                 1,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 1,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0
#             ],
#             [
#                 1,
#                 1,
#                 1,
#                 1,
#                 1,
#                 1,
#                 1,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 1,
#                 1,
#                 1,
#                 1,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0
#             ],
#             [
#                 1,
#                 1,
#                 0,
#                 1,
#                 1,
#                 1,
#                 1,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 1,
#                 1,
#                 1,
#                 1,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0,
#                 0
#             ]
#         ]
#     }
# }


class ReflectivityBlock:
    def __init__(self, block):
        self.block_id = block["globalBlockReferenceId"]

        self.report_time = block["reportTime"]

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
    REFLECTIVITY = {}

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

            for id in nexrad_json:
                block_identifier = int(id)
                NexradClient.REFLECTIVITY[block_identifier] = ReflectivityBlock(
                    nexrad_json[id]
                )

            current_time = int(time.time() * 1000)
            oldest_allowed_report_time = current_time - (15 * 60 * 1000)  # 15 minutes

            for id in list(NexradClient.REFLECTIVITY.keys()):
                if (
                    NexradClient.REFLECTIVITY[id].report_time
                    < oldest_allowed_report_time
                ):
                    del NexradClient.REFLECTIVITY[id]

            return True

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            # If we are spamming the REST too quickly, then we may loose a single update.
            # Do no consider the service unavailable unless we are
            # way below the max target framerate.
            return False

    @staticmethod
    def get_nexrad_in_range(center, radius):
        """
        Returns a list of NEXRAD blocks that are within the given range.
        """

        if center is None:
            return []

        if radius <= 0.0:
            return []

        if NexradClient.REFLECTIVITY is None:
            return []

        return [
            NexradClient.REFLECTIVITY[blockIdentifier]
            for blockIdentifier in NexradClient.REFLECTIVITY
            if NexradClient.is_in_range(
                center, radius, NexradClient.REFLECTIVITY[blockIdentifier]
            )
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


if __name__ == "__main__":
    import time

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
