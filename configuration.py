import json
import os
from os.path import expanduser
import units
import requests
import lib.recurring_task as recurring_task
from receiver_capabilities import StratuxCapabilities
from receiver_status import StratuxStatus

EARTH_RADIUS_NAUTICAL_MILES = 3440
EARTH_RADIUS_STATUTE_MILES = 3956
EARTH_RADIUS_KILOMETERS_MILES = 6371
MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT = 2
MAX_FRAMERATE = 60
TARGET_AHRS_FRAMERATE = 60
AHRS_TIMEOUT = 1.0

VERSION = "1.7.0"

########################
# Default Config Files #
########################
#
# Base, default values.
# There are two config files. One is the
# default that everything falls back to
# The other is the user saved and modified
# file that is merged in
__config_file__ = './config.json'
__view_elements_file__ = './elements.json'
__views_file__ = './views.json'


#####################
# User Config Files #
#####################
#
# These are the user modified files
# that are merged in with the system
# defaults, overriding what is set.
__user_views_file__ = '{}/hud_views.json'.format(expanduser('~'))
__user_config_file__ = '{}/hud_config.json'.format(expanduser('~'))
__heading_bugs_file__ = '{}/hud_heading_bugs.json'.format(expanduser('~'))

__working_dir__ = os.path.dirname(os.path.abspath(__file__))


def get_absolute_file_path(relative_path):
    """
    Returns the absolute file path no matter the OS.

    Arguments:
        relative_path {string} -- The relative file path.

    Returns:
        string -- The absolute filepath.
    """

    return os.path.join(__working_dir__, os.path.normpath(relative_path))


# System Default Config Files
DEFAULT_CONFIG_FILE = get_absolute_file_path(__config_file__)
VIEW_ELEMENTS_FILE = get_absolute_file_path(__view_elements_file__)
VIEWS_FILE = get_absolute_file_path(__views_file__)
HEADING_BUGS_FILE = get_absolute_file_path(__heading_bugs_file__)


class DataSourceNames(object):
    STRATUX = "stratux"
    SIMULATION = "simulation"


class Configuration(object):
    ###############################
    # Hardcoded Config Fall Backs #
    ###############################
    #
    # These are here in case the user does something
    # bad to the default config files.
    #
    DEFAULT_NETWORK_IP = "192.168.10.1"
    DEFAULT_TRAFFIC_MANAGER_ADDRESS = "localhost:8000"
    DEFAULT_AITHRE_MANAGER_ADDRESS = "localhost:8081"
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
    AITHRE_KEY = 'aithre'
    TRAFFIC_MANAGER_KEY = 'traffic_manager'
    AITHRE_MANAGER_KEY = 'aithre_manager'

    DEFAULT_DEGREES_OF_PITCH = 90
    DEFAULT_PITCH_DEGREES_DISPLAY_SCALER = 2.0

    def get_elements_list(self):
        """
        Returns the list of elements available for the views.
        """

        return self.__load_config_from_json_file__(VIEW_ELEMENTS_FILE)

    def __load_views_from_file__(self, file_name):
        views_key = 'views'

        try:
            full_views_contents = self.__load_config_from_json_file__(
                file_name)

            if full_views_contents is not None and views_key in full_views_contents:
                return full_views_contents[views_key]
        except:
            pass

        return None

    def get_views_list(self):
        """
        Loads the view configuration file.
        First looks for a user configuration file.
        If there is one, and the file is valid, then
        returns those contents.

        If there is an issue with the user file,
        then returns the system level default.

        Returns:
            array -- Array of dictionary. Each element contains the name of the view and a list of elements it is made from.
        """
        try:
            if self.__hud_views__ is None:
                self.__hud_views__ = self.__load_views_from_file__(
                    __user_views_file__)

            if self.__hud_views__ is None:
                self.__hud_views__ = self.__load_views_from_file__(VIEWS_FILE)

            if self.__hud_views__ is not None and any(self.__hud_views__):
                return self.__hud_views__

            return []
        except:
            return []

    def write_views_list(self, view_config):
        """
        Writes the view configuration to the user's version of the file.
        """

        try:
            with open(__user_views_file__, 'w') as configfile:
                configfile.write(view_config)
        except:
            print("ERROR trying to write user views file.")

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
            Configuration.MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT_KEY: self.max_minutes_before_removal,
            Configuration.DISTANCE_UNITS_KEY: self.get_units(),
            Configuration.DECLINATION_KEY: self.get_declination(),
            Configuration.DEGREES_OF_PITCH_KEY: self.get_degrees_of_pitch(),
            Configuration.PITCH_DEGREES_DISPLAY_SCALER_KEY: self.get_pitch_degrees_display_scaler(),
            Configuration.AITHRE_KEY: self.aithre_enabled,
            Configuration.TRAFFIC_MANAGER_KEY: self.get_traffic_manager_address()
        }

        return json.dumps(config_dictionary, indent=4, sort_keys=True)

    def write_config(self):
        """
        Writes the config file to the user's file.

        """

        try:
            config_to_write = self.get_json_from_config()

            with open(__user_config_file__, 'w') as configfile:
                configfile.write(config_to_write)
        except:
            print("ERROR trying to write user config file.")

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

        if Configuration.AITHRE_KEY in json_config:
            self.aithre_enabled = bool(json_config[Configuration.AITHRE_KEY])
            self.__configuration__[Configuration.AITHRE_KEY] = \
                self.aithre_enabled

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

        if Configuration.TRAFFIC_MANAGER_KEY in json_config:
            self.traffic_manager_address = json_config[Configuration.TRAFFIC_MANAGER_KEY]
            self.__configuration__[
                Configuration.TRAFFIC_MANAGER_KEY] = self.traffic_manager_address

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

    def get_traffic_manager_address(self):
        """
        Returns the address we should use for the traffic manager
        """

        return self.traffic_manager_address
    
    def get_aithre_manager_address(self):
        """
        Returns the address of the REST service that is providing
        Aithre connectivity.
        """
        return self.aithre_manager_address

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

    def get_view_index(self):
        """
        Returns the current index of the view
        that should be displayed.

        The index is relative (index 0) to the views
        configuration that is loaded from the views.json file.
        """
        return self.__view_index__

    def next_view(self):
        """
        Changes to the next view.

        Wraps around to the first view if we try to go past the last view.
        """
        self.__view_index__ += 1
        self.__clamp_view__()

    def previous_view(self):
        """
        Changes to the previous view.

        Wraps around to the last view if we try to "go previous"
        of the first view.
        """
        self.__view_index__ -= 1
        self.__clamp_view__()

    def __clamp_view__(self):
        """
        Makes sure that the view index is within bounds.
        """

        if self.__view_index__ >= (len(self.__hud_views__)):
            self.__view_index__ = 0

        if self.__view_index__ < 0:
            self.__view_index__ = (len(self.__hud_views__) - 1)

    def update_configuration(self, json_config):
        """
        Updates the master configuration from a json provided dictionary.

        Arguments:
            json_config_file {dictionary} -- JSON provided config decoded into a dictionary.
        """

        if json_config is None:
            return

        self.__configuration__.update(json_config)
        self.set_from_json(self.__configuration__)
        self.write_config()

    def __load_config_from_json_file__(self, json_config_file):
        """
            Loads the complete configuration into the system.
            Uses the default values as a base, then puts the
            user's configuration overtop.
        """
        try:
            with open(json_config_file) as json_config_file:
                json_config_text = json_config_file.read()
                json_config = json.loads(json_config_text)

                return json_config
        except:
            return {}

    def __load_configuration__(self, default_config_file, user_config_file):
        """
        Loads the configuration.
        """

        config = self.__load_config_from_json_file__(default_config_file)
        user_config = self.__load_config_from_json_file__(user_config_file)

        if user_config is not None:
            config.update(user_config)

        return config

    def __update_capabilities__(self):
        """
        Check occasionally to see if the settings
        for the Stratux have been changed that would
        affect what we should show and what is actually
        available.
        """
        self.capabilities = StratuxCapabilities(
            self.stratux_address(), self.__stratux_session__, None)
        self.stratux_status = StratuxStatus(
            self.stratux_address(), self.__stratux_session__, None)

    def __init__(self, default_config_file, user_config_file):
        self.__view_index__ = 0
        self.__hud_views__ = None
        self.get_views_list()
        self.degrees_of_pitch = Configuration.DEFAULT_DEGREES_OF_PITCH
        self.pitch_degrees_display_scaler = Configuration.DEFAULT_PITCH_DEGREES_DISPLAY_SCALER
        self.__configuration__ = self.__load_configuration__(
            default_config_file, user_config_file)
        self.max_minutes_before_removal = self.__get_config_value__(
            Configuration.MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT_KEY, MAX_MINUTES_BEFORE_REMOVING_TRAFFIC_REPORT)
        self.log_filename = "stratux_hud.log"
        self.flip_horizontal = False
        self.flip_vertical = False
        self.declination = 0.0
        self.aithre_enabled = False
        self.traffic_manager_address = self.__get_config_value__(
            Configuration.TRAFFIC_MANAGER_KEY, Configuration.DEFAULT_TRAFFIC_MANAGER_ADDRESS
        )
        self.aithre_manager_address = self.__get_config_value__(
            Configuration.AITHRE_MANAGER_KEY, Configuration.DEFAULT_AITHRE_MANAGER_ADDRESS
        )
        self.__stratux_session__ = requests.Session()

        self.stratux_status = StratuxStatus(
            self.stratux_address(), self.__stratux_session__, None)
        self.capabilities = StratuxCapabilities(
            self.stratux_address(), self.__stratux_session__, None)
        recurring_task.RecurringTask(
            'UpdateCapabilities', 15, self.__update_capabilities__)

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

        try:
            self.aithre_enabled = \
                bool(self.__configuration__[Configuration.AITHRE_KEY])
        except:
            pass

        try:
            self.traffic_manager_address = \
                self.__configuration__[Configuration.TRAFFIC_MANAGER_KEY]
        except:
            pass


CONFIGURATION = Configuration(DEFAULT_CONFIG_FILE, __user_config_file__)

if __name__ == '__main__':
    from_config = CONFIGURATION.get_json_from_config()
    CONFIGURATION.write_config()
