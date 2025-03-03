class ScopeRange(object):
    def __init__(
        self,
        center_ring_range: int,
        max_ring_range: int,
        is_available_to_autozoom: bool,
    ):
        self.center_ring_range = center_ring_range
        self.max_ring_range = max_ring_range
        self.is_available_to_autozoom = is_available_to_autozoom