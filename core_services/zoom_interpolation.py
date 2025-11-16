from common_utils.fast_math import interpolatef
from core_services.scope_range import ScopeRange

SECONDS_FOR_ZOOM = 3.0


def get_actual_zoom(
    seconds_into_zoom: float,
    starting_zoom: ScopeRange,
    target_zoom: ScopeRange,
) -> ScopeRange:
    """
    Given a starting zoom, a target zoom, and a time that the zoom was started
    get the middle and outer zoom ranges based on a smooth interpolation.

    Args:
        seconds_into_zoom (float): How many seconds into the zoom are we?
        starting_zoom (ScopeRange): What where the scope ranges when we started?
        target_zoom (ScopeRange): What are the target scope ranges?

    Returns:
        ScopeRange: The scope ranges to use for display
    """
    proportion_into_zoom = seconds_into_zoom / SECONDS_FOR_ZOOM

    if proportion_into_zoom >= 1.0:
        return target_zoom

    middle_ring_zoom = interpolatef(
        starting_zoom.center_ring_range,
        target_zoom.center_ring_range,
        proportion_into_zoom,
    )

    outter_ring_zoom = interpolatef(
        starting_zoom.max_ring_range,
        target_zoom.max_ring_range,
        proportion_into_zoom,
    )

    return ScopeRange(middle_ring_zoom, outter_ring_zoom, True)


if __name__ == "__main__":
    close_in_zoom = ScopeRange(0.5, 1.0, True)
    far_out_zoom = ScopeRange(10, 20, True)

    print("Starting Zoom interpolation tests")

    # Test zooming out along the time scale

    in_to_out_starting = get_actual_zoom(0.0, close_in_zoom, far_out_zoom)
    assert in_to_out_starting.center_ring_range == close_in_zoom.center_ring_range
    assert in_to_out_starting.max_ring_range == close_in_zoom.max_ring_range

    in_to_out_halfway = get_actual_zoom(1.5, close_in_zoom, far_out_zoom)
    assert (
        in_to_out_halfway.center_ring_range
        == (close_in_zoom.center_ring_range + far_out_zoom.center_ring_range) / 2
    )

    assert (
        in_to_out_halfway.max_ring_range
        == (close_in_zoom.max_ring_range + far_out_zoom.max_ring_range) / 2
    )

    in_to_out_finished = get_actual_zoom(3.0, close_in_zoom, far_out_zoom)
    assert in_to_out_finished.center_ring_range == far_out_zoom.center_ring_range
    assert in_to_out_finished.max_ring_range == far_out_zoom.max_ring_range

    in_to_out_overdone = get_actual_zoom(4.0, close_in_zoom, far_out_zoom)
    assert in_to_out_overdone.center_ring_range == far_out_zoom.center_ring_range
    assert in_to_out_overdone.max_ring_range == far_out_zoom.max_ring_range

    # Test zooming back along the time scale

    out_to_in_starting = get_actual_zoom(0.0, far_out_zoom, close_in_zoom)
    assert out_to_in_starting.center_ring_range == far_out_zoom.center_ring_range
    assert out_to_in_starting.max_ring_range == far_out_zoom.max_ring_range

    out_to_in_halfway = get_actual_zoom(1.5, far_out_zoom, close_in_zoom)
    assert (
        out_to_in_halfway.center_ring_range
        == (close_in_zoom.center_ring_range + far_out_zoom.center_ring_range) / 2
    )

    assert (
        out_to_in_halfway.max_ring_range
        == (close_in_zoom.max_ring_range + far_out_zoom.max_ring_range) / 2
    )

    out_to_in_finished = get_actual_zoom(3.0, far_out_zoom, close_in_zoom)
    assert out_to_in_finished.center_ring_range == close_in_zoom.center_ring_range
    assert out_to_in_finished.max_ring_range == close_in_zoom.max_ring_range

    out_to_in_overdone = get_actual_zoom(4.0, far_out_zoom, close_in_zoom)
    assert out_to_in_overdone.center_ring_range == close_in_zoom.center_ring_range
    assert out_to_in_overdone.max_ring_range == close_in_zoom.max_ring_range

    print("Finished Zoom interpolation tests")
