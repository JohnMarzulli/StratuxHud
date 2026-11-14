from typing import List
import datetime
import math


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
        return get_system_time() - self.__get_offset__()

    def report(self, reported_time: datetime.datetime) -> None:
        """
        Accept a time report from an external source.

        Args:
            reported_time (datetime.datetime): An aware UTC datetime, already normalized with to_utc().
        """
        new_report: __TimeOffsetReport__ = __TimeOffsetReport__(
            reported_time, get_system_time()
        )

        # Make sure that:
        #  1. we don't crash if there are no reports yet
        #  2. A "no reports" situation gets past the "too-soon" logic
        time_since_last_report = (
            new_report.system_time - self.__offset_reports__[-1].system_time
            if len(self.__offset_reports__) > 0
            else datetime.timedelta(
                seconds=self.__minimum_report_interval__.total_seconds() * 2
            )
        )

        if time_since_last_report < self.__minimum_report_interval__:
            return

        # Note to self: Some sort of iterable queue may be better
        if len(self.__offset_reports__) >= (self.__maximum_report_count__ - 1):
            self.__offset_reports__ = self.__offset_reports__[1:]

        self.__offset_reports__.append(new_report)
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
