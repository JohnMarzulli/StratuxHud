from common_utils import simulated_values

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
        self.ahrs_data.pitch = self.pitch_simulator.simulate()
        self.ahrs_data.roll = self.roll_simulator.simulate()
        self.ahrs_data.compass_heading = self.yaw_simulator.simulate()
        self.ahrs_data.gps_heading = self.ahrs_data.compass_heading
        self.ahrs_data.airspeed = self.speed_simulator.simulate()
        self.ahrs_data.groundspeed = self.ahrs_data.airspeed
        self.ahrs_data.alt = self.alt_simulator.simulate()

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

        self.pitch_simulator = simulated_values.SimulatedValue(1, 30, -1)
        self.roll_simulator = simulated_values.SimulatedValue(5, 60, 1)
        self.yaw_simulator = simulated_values.SimulatedValue(5, 60, 1, 30, 180)
        self.speed_simulator = simulated_values.SimulatedValue(5, 10, 1, 0, 85)
        self.alt_simulator = simulated_values.SimulatedValue(
            10,
            100,
            -1,
            0,
            200)
