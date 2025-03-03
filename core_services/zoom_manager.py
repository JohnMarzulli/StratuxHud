import math
from core_services.scope_range import ScopeRange

# A value of "12" is how far you will fly in
# ten minutes. Making it 12 x 2 will range
# the scope based on how far you will
# fly in 5 minutes.
__DISTANCE_PREDICTION_SCALER__ = 12 * 2

__SCOPE_RANGES__ = [
    ScopeRange(0.5, 1, False),
    ScopeRange(1, 2, True),
    ScopeRange(2, 5, True),
    ScopeRange(5, 10, True),
    ScopeRange(10, 20, True),
    ScopeRange(20, 50, True),
    ScopeRange(50, 100, False),
    ScopeRange(100, 200, False),
]


class ZoomManager(object):
    def __init__(self):
        self.__index__ = 2
        self.__is_automatic__ = True

    def is_automatic(self) -> bool:
        return self.__is_automatic__

    def return_to_automatic(self) -> None:
        self.__is_automatic__ = True

    def manual_zoom_in(self) -> None:
        self.__is_automatic__ = False

        if self.__index__ > 0:
            self.__index__ -= 1

    def manual_zoom_out(self) -> None:
        self.__is_automatic__ = False

        if self.__index__ < len(__SCOPE_RANGES__) - 1:
            self.__index__ += 1

    def automatic_zoom_in(self) -> None:
        self.__is_automatic__ = True

        new_index = self.__index__ - 1

        while (new_index > -1) and (
            not __SCOPE_RANGES__[new_index].is_available_to_autozoom
        ):
            new_index -= 1

        if new_index >= 0:
            self.__index__ = new_index
        else:
            self.__index__ = self.__get_closest_automatic_zoom_index__()

    def automatic_zoom_out(self) -> None:
        self.__is_automatic__ = True

        list_length = len(__SCOPE_RANGES__) - 1
        new_index = self.__index__ + 1

        while (new_index < list_length) and (
            not __SCOPE_RANGES__[new_index].is_available_to_autozoom
        ):
            new_index += 1

        if new_index < list_length:
            self.__index__ = new_index
        else:
            self.__index__ = self.__get_farthest_automatic_zoom_index__()

    def get_current_zoom(self) -> ScopeRange:
        return __SCOPE_RANGES__[self.__index__]

    def __get_closest_automatic_zoom_index__(self):
        # Find the index of the first item that meets the condition
        return next(
            (
                i
                for i, item in enumerate(__SCOPE_RANGES__)
                if item.is_available_to_autozoom
            ),
            None,
        )

    def __get_farthest_automatic_zoom_index__(self):
        return next(
            (
                i
                for i in reversed(range(0, len(__SCOPE_RANGES__)))
                if __SCOPE_RANGES__[i].is_available_to_autozoom
            ),
            None,
        )


def get_ideal_scope_range(groundspeed: float) -> ScopeRange:
    """
    Given a ground speed, figure out how far the scope should be.
    This is done by figuring out how far you will be in 10 minutes

    Args:
        groundspeed (float): The speed to calculate the ideal scope range from. This is in final units (so MPH, KPH, KNOTS)

    Returns:
        (int, int): The maximum distance the scope will cover and the distance between each ring.

    >>> get_ideal_scope_range(0.0)
    (1, 0)
    >>> get_ideal_scope_range(0)
    (1, 0)
    >>> get_ideal_scope_range(-1 * __DISTANCE_PREDICTION_SCALER__)
    (1, 0)
    >>> get_ideal_scope_range(-1.0 * __DISTANCE_PREDICTION_SCALER__)
    (1, 0)
    >>> get_ideal_scope_range(0.5 * __DISTANCE_PREDICTION_SCALER__)
    (1, 0)
    >>> get_ideal_scope_range(1 * __DISTANCE_PREDICTION_SCALER__)
    (1, 0)
    >>> get_ideal_scope_range(1.0 * __DISTANCE_PREDICTION_SCALER__)
    (1, 0)
    >>> get_ideal_scope_range(1.1 * __DISTANCE_PREDICTION_SCALER__)
    (2, 1)
    >>> get_ideal_scope_range(1.5 * __DISTANCE_PREDICTION_SCALER__)
    (2, 1)
    >>> get_ideal_scope_range(1.9 * __DISTANCE_PREDICTION_SCALER__)
    (2, 1)
    >>> get_ideal_scope_range(2.0 * __DISTANCE_PREDICTION_SCALER__)
    (2, 1)
    >>> get_ideal_scope_range(2.1 * __DISTANCE_PREDICTION_SCALER__)
    (5, 3)
    >>> get_ideal_scope_range(5 * __DISTANCE_PREDICTION_SCALER__)
    (5, 3)
    >>> get_ideal_scope_range(9.9 * __DISTANCE_PREDICTION_SCALER__)
    (10, 5)
    >>> get_ideal_scope_range(10 * __DISTANCE_PREDICTION_SCALER__)
    (10, 5)
    >>> get_ideal_scope_range(14.9 * __DISTANCE_PREDICTION_SCALER__)
    (15, 5)
    >>> get_ideal_scope_range(15 * __DISTANCE_PREDICTION_SCALER__)
    (15, 5)
    >>> get_ideal_scope_range(19.9 * __DISTANCE_PREDICTION_SCALER__)
    (20, 10)
    >>> get_ideal_scope_range(20 * __DISTANCE_PREDICTION_SCALER__)
    (20, 10)
    >>> get_ideal_scope_range(20.1 * __DISTANCE_PREDICTION_SCALER__)
    (50, 25)
    >>> get_ideal_scope_range(50 * __DISTANCE_PREDICTION_SCALER__)
    (50, 25)
    >>> get_ideal_scope_range(100 * __DISTANCE_PREDICTION_SCALER__)
    (50, 25)
    """

    predicted_travel_distance = math.fabs(groundspeed) / __DISTANCE_PREDICTION_SCALER__

    # The idea is to return the first range in the set
    # that is further than you will fly in 10 minutes.
    for possible_range in __SCOPE_RANGES__:
        if (
            possible_range.is_available_to_autozoom
            and possible_range.max_ring_range >= predicted_travel_distance
        ):
            return possible_range

    return next(
        (item for item in reversed(__SCOPE_RANGES__) if item.is_available_to_autozoom),
        None,
    )


if __name__ == "__main__":
    zoom_manager = ZoomManager()

    print("Starting tests")

    # Test 1
    #
    # Make sure the defaults hold
    assert zoom_manager.is_automatic() == True
    assert zoom_manager.get_current_zoom().center_ring_range == 2

    # Test 2
    #
    # Make sure an "automatic" zoom decreases the scope range
    zoom_manager.automatic_zoom_in()
    assert zoom_manager.is_automatic() == True
    assert zoom_manager.get_current_zoom().center_ring_range == 1

    # Test 3
    #
    # Make sure the lower limit is enforced
    zoom_manager.automatic_zoom_in()
    assert zoom_manager.is_automatic() == True
    assert zoom_manager.get_current_zoom().center_ring_range == 1

    # Test 4
    #
    # Make sure the upper limit is enforced
    for _ in range(10):
        zoom_manager.automatic_zoom_out()

    assert zoom_manager.is_automatic() == True
    assert zoom_manager.get_current_zoom().center_ring_range == 20

    ## Test 5
    #
    # Make sure we can zoom back in
    zoom_manager.automatic_zoom_in()

    assert zoom_manager.is_automatic() == True
    assert zoom_manager.get_current_zoom().center_ring_range == 10

    # Test 6
    #
    # Make sure we can manual zoom out
    zoom_manager.manual_zoom_out()
    assert zoom_manager.is_automatic() == False
    assert zoom_manager.get_current_zoom().center_ring_range == 20

    # Test 6
    #
    # Make sure we can manual zoom out even more
    zoom_manager.manual_zoom_out()
    assert zoom_manager.is_automatic() == False
    assert zoom_manager.get_current_zoom().center_ring_range == 50

    # Test 7
    #
    # Make sure we can manual zoom even more than that...
    zoom_manager.manual_zoom_out()
    assert zoom_manager.is_automatic() == False
    assert zoom_manager.get_current_zoom().center_ring_range == 100

    # Test 7
    #
    # Make sure the manual zoom outer limit is obeyed
    zoom_manager.manual_zoom_out()
    assert zoom_manager.is_automatic() == False
    assert zoom_manager.get_current_zoom().center_ring_range == 100

    # Test 7
    #
    # Make sure the automatic zoom in skips the forbidden range
    zoom_manager.automatic_zoom_in()
    assert zoom_manager.is_automatic() == True
    assert zoom_manager.get_current_zoom().center_ring_range == 20

    # Test 8
    #
    # Make sure the lower automatic limit is enforced
    for _ in range(10):
        zoom_manager.automatic_zoom_in()

    assert zoom_manager.is_automatic() == True
    assert zoom_manager.get_current_zoom().center_ring_range == 1

    print("All tests passed")
