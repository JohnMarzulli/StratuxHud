from typing import List
import datetime
import math
import threading
from time import monotonic


CLOCK_DISCONTINUITY_THRESHOLD_SECONDS = 1.0


class __TimeOffsetReport__:
    """
    Stores a time report from an external system along with the reported system time
    that was simultaneous to the report.

    This is mean for use internal to AuthoritativeTime only
    """

    def __init__(
        self, reported_time: datetime.datetime, system_time: datetime.datetime
    ):
        self.reported_time = reported_time
        self.system_time = system_time

    def get_offset(self) -> datetime.timedelta:
        return self.system_time - self.reported_time


def get_system_time() -> datetime.datetime:
    """
    Returns the current SYSTEM time from the SYSTEM CLOCK

    This time should be authoritative when time calculations are being performed.

    Returns:
        datetime.datetime: The UTC time from the system clock.
    """
    return datetime.datetime.now(datetime.timezone.utc)


def to_utc(incoming_time: datetime.datetime) -> datetime.datetime:
    """
    Normalizes a datetime from an EXTERNAL source into an aware UTC datetime.

    Every datetime that enters the system from outside (receiver JSON, REST
    responses, parsed strings) must pass through this at the boundary, so that
    the rest of the code can assume all datetimes are timezone-aware UTC.

    Timezone-naive values are interpreted as already being UTC.

    Args:
        incoming_time (datetime.datetime): The externally sourced time.

    Returns:
        datetime.datetime: The same instant as an aware UTC datetime.
    """
    if incoming_time.tzinfo is None:
        return incoming_time.replace(tzinfo=datetime.timezone.utc)

    return incoming_time.astimezone(datetime.timezone.utc)


class AuthoritativeTime:
    """
    System designed to take reports of time from sources OTHER than the system clock
    so a true time can be calculated for internal use.

    The time returned by this system is intended only for DISPLAY, FILENAME, and logging TIMESTAMP purposes.
    It is not to be used for time calculations. The system time needs to remain authoritative when calculating timeslices
    """

    def __init__(
        self,
        minimum_report_interval: datetime.timedelta = datetime.timedelta(
            seconds=5),
        maximum_report_count: int = 20,
    ):
        """
        Create a system for tracking the time offset reported by external sources.

        Args:
            minimum_report_interval (datetime.timedelta, optional): The minimum amount of time that can pass before a new offset report is accepted. Defaults to datetime.timedelta(seconds=5).
            maximum_report_count (int, optional): The maximum number of offset reports to keep at a single time. Oldest reports are removed and new reports will replace them. Defaults to 20.
        """
        self.__current_offset__ = datetime.timedelta(seconds=0)
        self.__offset_reports__: List[__TimeOffsetReport__] = []
        self.__report_lock__ = threading.Lock()
        self.__last_observed_system_time__ = None
        self.__last_observed_monotonic__ = None
        self.__last_report_monotonic__ = None
        self.__minimum_report_interval__ = minimum_report_interval
        self.__maximum_report_count__ = maximum_report_count
        self.__minimum_reports_count_required__ = int(
            (maximum_report_count / 4) * 0.5)

    def get_display_time_utc(self) -> datetime.datetime:
        """
        Returns the probable, correct, time in the world based on
        GPS reports or other reliable sources.

        Returns:
            datetime.datetime: The probable time in the real world.
        """
        return self.to_display_time(get_system_time())

    def to_display_time(self, system_time: datetime.datetime) -> datetime.datetime:
        """
        Converts a time stamp to one that we think represents the time of the user.
        This is needed since the R-Pi's clock may drift and probably is not
        set correctly. Accurate (enough) time is being reporting through GPS means.

        Use this when the system time of an event was captured earlier
        (for example, the creation time of a log record).

        Generally, this should only be called in a few places.
        - The logging formatter
        - The test for the logging formatter
s
        Any other places should be using get_display_time_utc()
        so we can be sure that we are not offsetting ALREADY offset times.

        Args:
            system_time (datetime.datetime): An aware UTC time from the system clock.

        Returns:
            datetime.datetime: The probable time in the real world for that instant.
        """
        return system_time - self.__current_offset__

    def report(self, reported_time: datetime.datetime) -> None:
        """
        Accept a time report from an external source.

        Args:
            reported_time (datetime.datetime): An aware UTC datetime, already normalized with to_utc().
        """

        # The monotonic clock ALWAYS progresses forward.
        # "Wall Clock" is the system time and will change
        # if it is corrected by a time service or something else.
        # thus is *could* go backwacks, how ever un-likely in
        # our situation while fly an aircraft.
        #
        # The goal here is to make sure that any reports
        # that happen when the difference between time
        # passage between both clocks greatly differs are ignored
        # since a system-clock correction probably happened.
        with self.__report_lock__:
            system_time = get_system_time()
            monotonic_time = monotonic()
            if (
                self.__last_observed_system_time__ is not None
                and self.__last_observed_monotonic__ is not None
            ):
                wall_elapsed = (
                    system_time - self.__last_observed_system_time__
                ).total_seconds()
                monotonic_elapsed = monotonic_time - self.__last_observed_monotonic__
                if abs(wall_elapsed - monotonic_elapsed) > CLOCK_DISCONTINUITY_THRESHOLD_SECONDS:
                    self.__offset_reports__.clear()
                    self.__current_offset__ = datetime.timedelta(0)
                    self.__last_observed_system_time__ = system_time
                    self.__last_observed_monotonic__ = monotonic_time
                    return

            self.__last_observed_system_time__ = system_time
            self.__last_observed_monotonic__ = monotonic_time

            if (
                self.__last_report_monotonic__ is not None
                and monotonic_time - self.__last_report_monotonic__
                < self.__minimum_report_interval__.total_seconds()
            ):
                return

            new_report: __TimeOffsetReport__ = __TimeOffsetReport__(
                reported_time, system_time
            )

            # Note to self: Some sort of iterable queue may be better
            if len(self.__offset_reports__) >= (self.__maximum_report_count__ - 1):
                self.__offset_reports__ = self.__offset_reports__[1:]

            self.__offset_reports__.append(new_report)
            self.__last_report_monotonic__ = monotonic_time
            self.__current_offset__ = self.__get_offset__()

    def __get_offset__(self) -> datetime.timedelta:
        return self.__get_mean_offset__()

    def __get_mean_offset__(self) -> datetime.timedelta:
        if (
            not self.__offset_reports__
            or len(self.__offset_reports__) < self.__minimum_reports_count_required__
        ):
            return datetime.timedelta(seconds=0)

        report_count: int = len(self.__offset_reports__)
        total_seconds: float = 0.0

        # Note to self: Do I want to throw out outliers?
        # .              Do I want to spend the time to calculate outliers?
        for report in self.__offset_reports__:
            total_seconds += report.get_offset().total_seconds()

        mean_seconds_offset: float = total_seconds / report_count

        # Make sure line noise level variance is ignored
        if math.fabs(mean_seconds_offset) < 15.0:
            mean_seconds_offset = 0.0

        return datetime.timedelta(seconds=mean_seconds_offset)


DISPLAY_TIME: AuthoritativeTime = AuthoritativeTime()
