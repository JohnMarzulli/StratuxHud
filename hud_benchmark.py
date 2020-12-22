"""
File to  run various math benchmarks in order to determine
what is the best way to go about some math on
various versions of the Pi.
"""

import logging
import math
import random

from common_utils import fast_math
from common_utils.logger import HudLogger
from common_utils.task_timer import TaskProfiler

python_logger = logging.getLogger("hud_benchmark")
python_logger.setLevel(logging.DEBUG)
LOGGER = HudLogger(python_logger)

max_test_calls = 1000000

random_angles = [random.randrange(
    0, 360) + ((random.randrange(0, 9) / 10)) for i in range(1, max_test_calls)]

random_radians = [math.radians(random.randrange(
    0, 360) + ((random.randrange(0, 9) / 10))) for i in range(1, max_test_calls)]

for attempt in range(0, 4):
    LOGGER.log_info_message("Round #{}".format(attempt))

    LOGGER.log_info_message("    trig::calced")
    # Test trig functions
    with TaskProfiler("trig::calced"):
        for rand_val in random_angles:
            radians = math.radians(rand_val)
            cos_rand = math.cos(radians)
            sin_rant = math.sin(radians)

    LOGGER.log_info_message("    trig::cached")
    with TaskProfiler("trig::cached"):
        for rand_val in random_angles:
            int_degs = int(rand_val)
            cos_rand = fast_math. COS_BY_DEGREES[int_degs]
            sin_rant = fast_math.SIN_BY_DEGREES[int_degs]

    LOGGER.log_info_message("    degrees_to_radians::calced")
    with TaskProfiler("degrees_to_radians::calced"):
        for rand_val in random_angles:
            radians = math.radians(rand_val)

    LOGGER.log_info_message("    degrees_to_radians::cached")
    with TaskProfiler("degrees_to_radians::cached"):
        for rand_val in random_angles:
            radians = fast_math.get_radians(rand_val)

    LOGGER.log_info_message("    radians_to_degrees::calced")
    with TaskProfiler("radians_to_degrees::calced"):
        for rand_val in random_radians:
            degrees = math.degrees(rand_val)

    LOGGER.log_info_message("    radians_to_degrees::cached")
    with TaskProfiler("radians_to_degrees::cached"):
        for rand_val in random_angles:
            degrees = fast_math.get_degrees(rand_val)

    LOGGER.log_info_message("    mult::operator")
    with TaskProfiler("mult::operator"):
        for rand_val in random_angles:
            radians = rand_val * 2.0
            radians = rand_val * 4.0

    LOGGER.log_info_message("    mult::shifted")
    with TaskProfiler("mult::shifted"):
        for rand_val in random_angles:
            as_int = int(rand_val)
            radians = as_int << 1
            radians = as_int << 2

    LOGGER.log_info_message("    div::operator")
    with TaskProfiler("div::operator"):
        for rand_val in random_angles:
            radians = rand_val / 2.0
            radians = rand_val / 4.0

    LOGGER.log_info_message("    div::shifted")
    with TaskProfiler("div::shifted"):
        for rand_val in random_angles:
            as_int = int(rand_val)
            radians = as_int >> 1
            radians = as_int >> 2

TaskProfiler.log(LOGGER)

quit()
