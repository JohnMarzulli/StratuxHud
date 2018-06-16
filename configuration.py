import json
import os

EARTH_RADIUS_NAUTICAL_MILES = 3440
EARTH_RADIUS_STATUTE_MILES = 3956
EARTH_RADIUS_KILOMETERS_MILES = 6371
MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT = 2
MAX_FRAMERATE = 60
__config_file__ = "config.json"
__working_dir__ = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_FILE = os.path.join(__working_dir__, os.path.normpath(__config_file__))



class DataSourceNames(object):
    STRATUX = "stratux"
    SIMULATION = "simulation"


class Configuration(object):
    DEFAULT_NETWORK_IP = "192.168.10.1"
    STRATUX_ADDRESS_KEY = "stratux_address"
    DATA_SOURCE_KEY = "data_source"
    DISPLAY_KEY = "display"
    FLIP_HORIZONTAL_KEY = "flip_horizontal"
    FLIP_VERTICAL_KEY = "flip_vertical"
    REVERSE_ROLL_KEY = "reverse_roll"
    REVERSE_PITCH_KEY = "reverse_pitch"
    REVERSE_YAW_KEY = "reverse_yaw"
    OWNSHIP_KEY = "ownship"
    MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT_KEY = "traffic_report_removal_minutes"
    DISTANCE_UNITS_KEY = "distance_units"

    def __get_config_value__(self, key, default_value):
        """
        Returns a configuration value, default if not found.
        """

        if self.__configuration__ is not None and key in self.__configuration__:
            return self.__configuration__[key]

        return default_value

    def __get_display_settings__(self):
        return self.__get_config_value__(Configuration.DISPLAY_KEY, None)

    def reverse_roll(self):
        """
        Should the roll be reversed?
        """
        display_settings = self.__get_display_settings__()

        if not display_settings:
            return True

        return display_settings[Configuration.REVERSE_ROLL_KEY]

    def reverse_pitch(self):
        """
        Should the pitch be reversed?
        """
        display_settings = self.__get_display_settings__()

        if not display_settings:
            return False

        return display_settings[Configuration.REVERSE_PITCH_KEY]

    def reverse_yaw(self):
        """
        Should the yaw be reversed?
        """
        display_settings = self.__get_display_settings__()

        if not display_settings:
            return True

        return display_settings[Configuration.REVERSE_YAW_KEY]

    def data_source(self):
        """
        Returns the data source to use.
        """

        return self.__get_config_value__(Configuration.DATA_SOURCE_KEY, DataSourceNames.STRATUX)

    def stratux_address(self):
        """
        Returns the stratux address.
        """

        return self.__get_config_value__(Configuration.STRATUX_ADDRESS_KEY, Configuration.DEFAULT_NETWORK_IP)

    def __load_configuration__(self, json_config_file):
        """
        Loads the configuration.
        """

        with open(json_config_file) as json_config_file:
            json_config_text = json_config_file.read()
            json_config = json.loads(json_config_text)
            return json_config

    def __init__(self, json_config_file):
        self.__configuration__ = self.__load_configuration__(json_config_file)
        self.ownship = self.__get_config_value__(Configuration.OWNSHIP_KEY, '')
        self.max_minutes_before_removal = self.__get_config_value__(
            Configuration.MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT_KEY, MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT)
        self.log_filename = "stratux_hud.log"
        self.flip_horizontal = False
        self.flip_vertical = False

        try:
            self.flip_horizontal = self.__configuration__[
                Configuration.DISPLAY_KEY][Configuration.FLIP_HORIZONTAL_KEY]
        except:
            pass

        try:
            self.flip_vertical = self.__configuration__[
                Configuration.DISPLAY_KEY][Configuration.FLIP_VERTICAL_KEY]
        except:
            pass
