"""
Module for determining declination based on GPS
"""

import os


class Declination(object):
    """
    Class to load the coordinate to declination mapping
    """

    __DECLINATION__ = {}

    @staticmethod
    def load_data():
        """
        Loads the coordinate to declination data into memory and
        prepares it for fast look up.
        """

        filepath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../data/grid_world.csv")

        with open(filepath) as declination_file:
            file_contents = declination_file.read()
            file_lines = file_contents.splitlines()

            for line in file_lines:
                if line is None or len(line) < 1:
                    continue

                if line.startswith("#"):
                    continue

                column_data = line.split(',')

                if len(column_data) < 7:
                    continue

                # [0] Date in decimal years
                # [1] Latitude in decimal Degrees
                # [2] Longitude in decimal Degrees
                # [3] Elevation in km GPS
                # [4] Declination in Degree
                # [5] Declination_sv in Degree
                # [6] Declination_uncertainty in Degree

                lattitude = int(float(column_data[1]))
                longitude = int(float(column_data[2]))
                declination = float(column_data[4])

                if lattitude not in Declination.__DECLINATION__:
                    Declination.__DECLINATION__[lattitude] = {}

                Declination.__DECLINATION__[lattitude][longitude] = declination

    @staticmethod
    def round_coordinate(
        coordinate: float
    ) -> int:
        """
        Rounds a GPS coordinate.

        Args:
            coordinate (float): The un-rounded GPS coordinate.

        Returns:
            int: A rounded integer.
        """
        rounded = coordinate + 0.5 if coordinate > 0 else coordinate - 0.5
        return int(rounded)

    @staticmethod
    def get_declination(
        lattitude: float,
        longitude: float
    ) -> float:
        """
        Given a lattitude and longitude, get the declination.

        Args:
            lattitude (float): The lattitude of the position we want to get declination for.
            longitude (float): The longitude of the position we want to get declination for.

        Returns:
            float: The probable declination in the area.
        """
        rounded_lat = Declination.round_coordinate(lattitude)
        rounded_long = Declination.round_coordinate(longitude)

        rounded_lat = 89 if rounded_lat > 89 else rounded_lat
        rounded_long = -180 if rounded_long < -180 else rounded_long
        rounded_long = 180 if rounded_long > 180 else rounded_long

        return Declination.__DECLINATION__[rounded_lat][rounded_long]


Declination.load_data()
