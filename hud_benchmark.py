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

# Test trig functions
with TaskProfiler("math::trig_calced"):
    for rand_val in random_angles:
        radians = math.radians(rand_val)
        cos_rand = math.cos(radians)
        sin_rant = math.sin(radians)

with TaskProfiler("math::trig_cached"):
    for rand_val in random_angles:
        int_degs = int(rand_val)
        cos_rand = fast_math. COS_BY_DEGREES[int_degs]
        sin_rant = fast_math.SIN_BY_DEGREES[int_degs]

with TaskProfiler("math::degrees_to_radians_calced"):
    for rand_val in random_angles:
        radians = math.radians(rand_val)

with TaskProfiler("math::degrees_to_radians_cached"):
    for rand_val in random_angles:
        radians = fast_math.get_radians(rand_val)

with TaskProfiler("math::radians_to_degrees_calced"):
    for rand_val in random_radians:
        degrees = math.degrees(rand_val)

with TaskProfiler("math::radians_to_degrees_cached"):
    for rand_val in random_angles:
        degrees = fast_math.get_degrees(rand_val)

with TaskProfiler("math::mult_times"):
    for rand_val in random_angles:
        radians = rand_val * 2.0
        radians = rand_val * 4.0

with TaskProfiler("math::mult_shifted"):
    for rand_val in random_angles:
        as_int = int(rand_val)
        radians = as_int << 1
        radians = as_int << 2

with TaskProfiler("math::div_divved"):
    for rand_val in random_angles:
        radians = rand_val / 2.0
        radians = rand_val / 4.0

with TaskProfiler("math::div_shifted"):
    for rand_val in random_angles:
        as_int = int(rand_val)
        radians = as_int >> 1
        radians = as_int >> 2

TaskProfiler.log(LOGGER)

quit()
