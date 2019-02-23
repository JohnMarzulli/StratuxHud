import json
import os
import units

EARTH_RADIUS_NAUTICAL_MILES = 3440
EARTH_RADIUS_STATUTE_MILES = 3956
EARTH_RADIUS_KILOMETERS_MILES = 6371
MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT = 2
MAX_FRAMERATE = 60

VERSION = "1.4.0"

__config_file__ = './config.json'
__heading_bugs_file__ = './heading_bugs.json'
__view_elements_file__ = './elements.json'
__views_file__ = './views.json'
__working_dir__ = os.path.dirname(os.path.abspath(__file__))


def get_config_file_location():
    """
    Returns the location of the configuration file.

    Returns:
        string -- The path to the config file
    """

    return __config_file__


def get_absolute_file_path(relative_path):
    """
    Returns the absolute file path no matter the OS.

    Arguments:
        relative_path {string} -- The relative file path.

    Returns:
        string -- The absolute filepath.
    """

    return os.path.join(__working_dir__, os.path.normpath(relative_path))


DEFAULT_CONFIG_FILE = get_absolute_file_path(__config_file__)
HEADING_BUGS_FILE = get_absolute_file_path(__heading_bugs_file__)
VIEW_ELEMENTS_FILE = get_absolute_file_path(__view_elements_file__)
VIEWS_FILE = get_absolute_file_path(__views_file__)


class DataSourceNames(object):
    STRATUX = "stratux"
    SIMULATION = "simulation"


class Configuration(object):
    DEFAULT_NETWORK_IP = "192.168.10.1"
    STRATUX_ADDRESS_KEY = "stratux_address"
    DATA_SOURCE_KEY = "data_source"
    FLIP_HORIZONTAL_KEY = "flip_horizontal"
    FLIP_VERTICAL_KEY = "flip_vertical"
    OWNSHIP_KEY = "ownship"
    MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT_KEY = "traffic_report_removal_minutes"
    DISTANCE_UNITS_KEY = "distance_units"
    DECLINATION_KEY = "declination"
    DEGREES_OF_PITCH_KEY = 'degrees_of_pitch'
    PITCH_DEGREES_DISPLAY_SCALER_KEY = 'pitch_degrees_scaler'

    DEFAULT_DEGREES_OF_PITCH = 90
    DEFAULT_PITCH_DEGREES_DISPLAY_SCALER = 2.0

    def get_elements_list(self):
        with open(VIEW_ELEMENTS_FILE) as json_config_file:
            json_config_text = json_config_file.read()
            json_config = json.loads(json_config_text)

            return json_config

        return {}

    def get_views_list(self):
        """
        Returns a list of views that can be used by the HUD

        Returns:
            array -- Array of dictionary. Each element contains the name of the view and a list of elements it is made from. 
        """
        try:
            with open(VIEWS_FILE) as json_config_file:
                json_config_text = json_config_file.read()
                json_config = json.loads(json_config_text)

                return json_config['views']
        except:
            return []

    def write_views_list(self, view_config):
        with open(VIEWS_FILE, 'w') as configfile:
            configfile.write(view_config)

    def get_json_from_text(self, text):
        """
        Takes raw text and imports it into JSON.
        """

        return json.loads(text)

    def get_json_from_config(self):
        """
        Returns the current config as JSON text.

        REMARK: Returns everything back as a string...
                That is probably safer, but not nearly
                as convenient as I want
        """
        config_dictionary = {
            Configuration.STRATUX_ADDRESS_KEY: self.stratux_address(),
            Configuration.DATA_SOURCE_KEY: self.data_source(),
            Configuration.FLIP_HORIZONTAL_KEY: self.flip_horizontal,
            Configuration.FLIP_VERTICAL_KEY: self.flip_vertical,
            Configuration.OWNSHIP_KEY: self.ownship,
            Configuration.MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT_KEY: self.max_minutes_before_removal,
            Configuration.DISTANCE_UNITS_KEY: self.get_units(),
            Configuration.DECLINATION_KEY: self.get_declination(),
            Configuration.DEGREES_OF_PITCH_KEY: self.get_degrees_of_pitch(),
            Configuration.PITCH_DEGREES_DISPLAY_SCALER_KEY: self.get_pitch_degrees_display_scaler()
        }

        return json.dumps(config_dictionary, indent=4, sort_keys=True)

    def write_config(self):
        """
        Writes the config file down to file.
        """

        config_to_write = self.get_json_from_config()

        with open(get_config_file_location(), 'w') as configfile:
            configfile.write(config_to_write)

    def set_from_json(self, json_config):
        """
        Takes a JSON package and sets the config using the JSON
        """

        if json_config is None:
            return

        set_from_maps = [Configuration.STRATUX_ADDRESS_KEY,
                         Configuration.DATA_SOURCE_KEY]

        for key in set_from_maps:
            if key in json_config:
                self.__configuration__[key] = json_config[key]

        if Configuration.FLIP_HORIZONTAL_KEY in json_config:
            self.flip_horizontal = \
                bool(json_config[Configuration.FLIP_HORIZONTAL_KEY])
            self.__configuration__[Configuration.FLIP_HORIZONTAL_KEY] = \
                self.flip_horizontal

        if Configuration.FLIP_VERTICAL_KEY in json_config:
            self.flip_vertical = \
                bool(json_config[Configuration.FLIP_VERTICAL_KEY])
            self.__configuration__[Configuration.FLIP_VERTICAL_KEY] = \
                self.flip_vertical

        if Configuration.OWNSHIP_KEY in json_config:
            self.ownship = json_config[Configuration.OWNSHIP_KEY]
            self.__configuration__[Configuration.OWNSHIP_KEY] = self.ownship

        if Configuration.MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT_KEY in json_config:
            self.max_minutes_before_removal = float(
                json_config[Configuration.MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT_KEY])
            self.__configuration__[
                Configuration.MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT_KEY] = self.max_minutes_before_removal

        if Configuration.DISTANCE_UNITS_KEY in json_config:
            self.units = json_config[Configuration.DISTANCE_UNITS_KEY]
            self.__configuration__[
                Configuration.DISTANCE_UNITS_KEY] = self.units

        if Configuration.DECLINATION_KEY in json_config:
            self.declination = float(
                json_config[Configuration.DECLINATION_KEY])
            self.__configuration__[
                Configuration.DECLINATION_KEY] = self.declination

        if Configuration.DEGREES_OF_PITCH_KEY in json_config:
            self.degrees_of_pitch = int(
                json_config[Configuration.DEGREES_OF_PITCH_KEY])
            self.__configuration__[
                Configuration.DEGREES_OF_PITCH_KEY] = self.degrees_of_pitch

        if Configuration.PITCH_DEGREES_DISPLAY_SCALER_KEY in json_config:
            self.pitch_degrees_display_scaler = float(
                json_config[Configuration.PITCH_DEGREES_DISPLAY_SCALER_KEY])
            self.__configuration__[
                Configuration.PITCH_DEGREES_DISPLAY_SCALER_KEY] = self.pitch_degrees_display_scaler

    def __get_config_value__(self, key, default_value):
        """
        Returns a configuration value, default if not found.
        """

        if self.__configuration__ is not None and key in self.__configuration__:
            return self.__configuration__[key]

        return default_value

    def get_degrees_of_pitch(self):
        """
        Returns the number of degrees of pitch for the AH ladder.

        Returns:
            float -- Returns the number of degrees of pitch for the AH ladder.
        """

        return self.degrees_of_pitch

    def get_pitch_degrees_display_scaler(self):
        """
        Returns the amount of adjustment to the pitch ladder

        Returns:
            [type] -- [description]
        """

        return self.pitch_degrees_display_scaler

    def get_declination(self):
        """
        Returns the magnetic variance (true to magnetic)

        Returns:
            float -- The number of degrees to adjust the heading displayed by.
        """

        return self.declination

    def get_units(self):
        """
        Returns the units that the display should use.

        Returns:
            string -- The type of units.
        """

        return self.__get_config_value__(self.DISTANCE_UNITS_KEY, units.STATUTE)

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

    def update_configuration(self, json_config):
        """
        Updates the master configuration from a json provided dictionary.

        Arguments:
            json_config_file {dictionary} -- JSON provided config decoded into a dictionary.
        """

        self.__configuration__.update(json_config)
        self.set_from_json(self.__configuration__)
        self.write_config()

    def __load_configuration__(self, json_config_file):
        """
        Loads the configuration.
        """

        with open(json_config_file) as json_config_file:
            json_config_text = json_config_file.read()
            json_config = json.loads(json_config_text)
            return json_config

    def __init__(self, json_config_file):
        self.degrees_of_pitch = Configuration.DEFAULT_DEGREES_OF_PITCH
        self.pitch_degrees_display_scaler = Configuration.DEFAULT_PITCH_DEGREES_DISPLAY_SCALER
        self.__configuration__ = self.__load_configuration__(json_config_file)
        self.ownship = self.__get_config_value__(Configuration.OWNSHIP_KEY, '')
        self.max_minutes_before_removal = self.__get_config_value__(
            Configuration.MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT_KEY, MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT)
        self.log_filename = "stratux_hud.log"
        self.flip_horizontal = False
        self.flip_vertical = False
        self.declination = 0.0

        self.set_from_json(self.__configuration__)

        # Example config
        # "stratux_address": "192.168.10.1",
        #   "distance_units": "statute",
        #   "traffic_report_removal_minutes": 1,
        #   "flip_horizontal": false,
        #   "flip_vertical": false,
        #   "ownship": "N701GV",
        #   "data_source": "stratux",
        #   "declination": 0.0

        try:
            self.flip_horizontal = \
                self.__configuration__[Configuration.FLIP_HORIZONTAL_KEY]
        except:
            pass

        try:
            self.flip_vertical = \
                self.__configuration__[Configuration.FLIP_VERTICAL_KEY]
        except:
            pass

        try:
            self.declination = \
                float(self.__configuration__[Configuration.DECLINATION_KEY])
        except:
            pass


CONFIGURATION = Configuration(DEFAULT_CONFIG_FILE)

if __name__ == '__main__':
    from_config = CONFIGURATION.get_json_from_config()
    CONFIGURATION.write_config()
