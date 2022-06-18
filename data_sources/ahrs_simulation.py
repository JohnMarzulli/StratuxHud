from datetime import datetime, timedelta, timezone

from common_utils import fast_math, geo_math, simulated_values

from data_sources import ahrs_data


class AhrsSimulation(object):
    """
    Class to simulate the AHRS data.
    """

    def simulate(
        self
    ):
        """
        Ticks the simulated data.
        """
        hours_since_start = (datetime.now(timezone.utc) - self.__starting_time__).total_seconds() / 60.0 / 60.0

        proportion_into_simulation = hours_since_start / self.__hours_to_destination__

        simulated_lat = fast_math.interpolatef(self.__starting_lat__, self.__ending_lat__, proportion_into_simulation)
        simulated_long = fast_math.interpolatef(self.__starting_long__, self.__ending_long__, proportion_into_simulation)

        self.ahrs_data.pitch = self.pitch_simulator.simulate()
        self.ahrs_data.roll = self.roll_simulator.simulate()
        self.ahrs_data.airspeed = self.speed_simulator.simulate()
        self.ahrs_data.groundspeed = self.ahrs_data.airspeed
        self.ahrs_data.alt = self.alt_simulator.simulate()
        self.ahrs_data.slip_skid = self.skid_simulator.simulate()
        self.ahrs_data.position = [simulated_lat, simulated_long]
        self.ahrs_data.compass_heading = geo_math.get_bearing(self.ahrs_data.position, [self.__ending_lat__, self.__ending_long__])
        self.ahrs_data.gps_heading = self.ahrs_data.compass_heading

    def update(
        self
    ):
        """
        Updates the simulation and serves as the interface for the
        the AHRS/Simulation/Other sourcing
        """

        self.simulate()

    def get_ahrs(
        self
    ):
        """
        Returns the current simulated values for the AHRS data.

        Returns:
            AhrsData -- The current simulated values.
        """
        return self.ahrs_data

    def __init__(
        self
    ):
        self.ahrs_data = ahrs_data.AhrsData()

        # Simulate a flight from KAWO to OSH
        self.__starting_lat__ = 47.6
        self.__starting_long__ = -122.3
        self.__ending_lat__ = 44.0
        self.__ending_long__ = -88.5

        self.ahrs_data.position = [self.__starting_lat__, self.__starting_long__]

        self.__hours_to_destination__ = 17.5
        self.__starting_time__ = datetime.now(timezone.utc)
        self.__end_time__ = self.__starting_time__ + timedelta(hours=17.5)

        self.pitch_simulator = simulated_values.SimulatedValue(1, 30, -1)
        self.roll_simulator = simulated_values.SimulatedValue(5, 60, 1)
        self.speed_simulator = simulated_values.SimulatedValue(5, 10, 1, 0, 85)
        self.alt_simulator = simulated_values.SimulatedValue(
            10,
            100,
            -1,
            0,
            200)
        self.skid_simulator = simulated_values.SimulatedValue(
            0.5,
            1.5,
            1)
