"""
Plays the scripted traffic encounters from data_sources/traffic_scenarios.py
on the traffic scope, for seeing how threats look and tuning the visuals.

    python -m views.traffic_threat_debug [scenario number or name]

Keys:
    N / P       Next / previous scenario
    Space       Pause / resume
    Left/Right  Step back / forward one second
    [ / ]       Slow down / speed up time (0.25x to 8x)
    R           Restart the scenario
    H           Show / hide the key help
    Up/Down     Zoom out / in (the scope's own keys)
    Esc         Quit

Real traffic from the traffic manager is ignored while this runs, so
only the scenario's aircraft are shown.
"""

import sys

import pygame

from core_services import traffic_threat
from core_services.traffic_threat import ThreatLevel
from data_sources import traffic, traffic_scenarios
from data_sources.ahrs_data import AhrsData
from data_sources.data_cache import HudDataCache
from rendering import colors, display
from views.abstract_elements.ahrs_element import AhrsElement
from core_services.zoom_manager import DEFAULT_ZOOM_INDEX
from views.abstract_elements.top_down_scope import TopDownScope
from views.hud_elements import create_hud_elements
from views.scope_layers import TrafficLayer

TIME_SCALES = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
DEFAULT_TIME_SCALE_INDEX = TIME_SCALES.index(1.0)
STEP_SECONDS = 1.0
# How long to hold the last frame before the scenario starts again.
END_HOLD_SECONDS = 3.0

# Most aircraft listed in the caption; the busy scenarios only list
# the ones that are threats.
MAX_LISTED_AIRCRAFT = 4

THREAT_COLORS = {
    ThreatLevel.NONE: colors.GRAY,
    ThreatLevel.WARNING: colors.YELLOW,
    ThreatLevel.ALERT: colors.RED,
    ThreatLevel.CRITICAL: colors.RED,
}

HELP_LINES = [
    "N/P scenario  SPACE pause  </> step",
    "[/] speed  R restart  UP/DN zoom  H help",
]


class TrafficScenarioScope(TopDownScope):
    """
    The traffic scope with nothing else on it, so only the scenario's
    aircraft are drawn.

    Starts at the 1/2 SM rings and stays there (no speed based
    auto-zoom), so every scenario is seen at the same scale.
    """

    RING_COLOR = colors.GREEN
    ALLOWS_AUTOMATIC_ZOOM = False
    STARTING_ZOOM_INDEX = DEFAULT_ZOOM_INDEX - 1

    FOREGROUND_LAYERS = [TrafficLayer]


class ScenarioPlayer:
    """
    Which scenario is playing, the scenario clock, and the playback
    controls.
    """

    def __init__(self, scenarios: list, starting_index: int = 0):
        self.scenarios = scenarios
        self.index = starting_index % len(scenarios)
        self.seconds = 0.0
        self.is_paused = False
        self.time_scale_index = DEFAULT_TIME_SCALE_INDEX
        self.is_help_shown = True
        self.__end_hold__ = 0.0

        self.__clear_traffic__()

    @property
    def scenario(self) -> traffic_scenarios.Scenario:
        return self.scenarios[self.index]

    @property
    def time_scale(self) -> float:
        return TIME_SCALES[self.time_scale_index]

    def advance(self, real_seconds: float):
        if self.is_paused:
            return

        if self.seconds >= self.scenario.duration_seconds:
            self.__end_hold__ += real_seconds

            if self.__end_hold__ >= END_HOLD_SECONDS:
                self.restart()

            return

        self.seconds = min(
            self.scenario.duration_seconds,
            self.seconds + real_seconds * self.time_scale,
        )

    def restart(self):
        self.seconds = 0.0
        self.__end_hold__ = 0.0
        self.__clear_traffic__()

    def select(self, offset: int):
        self.index = (self.index + offset) % len(self.scenarios)
        self.restart()

    def step(self, seconds: float):
        self.seconds = max(
            0.0, min(self.scenario.duration_seconds, self.seconds + seconds)
        )
        self.__end_hold__ = 0.0

    def handle_events(self, events: list) -> list:
        """
        Handles the playback keys, returning everything else.
        """
        unhandled = []

        for event in events:
            if event.type != pygame.KEYUP:
                unhandled.append(event)
                continue

            if event.key == pygame.K_n:
                self.select(1)
            elif event.key == pygame.K_p:
                self.select(-1)
            elif event.key == pygame.K_SPACE:
                self.is_paused = not self.is_paused
            elif event.key == pygame.K_LEFT:
                self.step(-STEP_SECONDS)
            elif event.key == pygame.K_RIGHT:
                self.step(STEP_SECONDS)
            elif event.key == pygame.K_LEFTBRACKET:
                self.time_scale_index = max(0, self.time_scale_index - 1)
            elif event.key == pygame.K_RIGHTBRACKET:
                self.time_scale_index = min(
                    len(TIME_SCALES) - 1, self.time_scale_index + 1
                )
            elif event.key == pygame.K_r:
                self.restart()
            elif event.key == pygame.K_h:
                self.is_help_shown = not self.is_help_shown
            else:
                unhandled.append(event)

        return unhandled

    def publish(self) -> AhrsData:
        """
        Sends the scenario's traffic, at the current time, through the
        same path real traffic takes, and returns our own AHRS data.
        """
        manager = traffic.AdsbTrafficClient.TRAFFIC_MANAGER

        for icao_address, report in traffic_scenarios.reports_at(
            self.scenario, self.seconds
        ):
            manager.handle_traffic_report(icao_address, report)

        HudDataCache.update_traffic_reports()

        return traffic_scenarios.ownship_at(self.scenario, self.seconds)

    def get_clock_text(self) -> str:
        """
        "T-12s" relative to the encounter, or "+34s" from the start
        when there is no single moment of encounter.
        """
        encounter = self.scenario.encounter_seconds

        if encounter is None:
            text = f"+{self.seconds:.0f}s"
        else:
            to_go = self.seconds - encounter
            text = f"T{'+' if to_go >= 0.0 else '-'}{abs(to_go):.0f}s"

        text += f"  x{self.time_scale:g}"

        if self.is_paused:
            text += "  PAUSED"

        return text

    def get_assessments(self, orientation: AhrsData) -> list:
        """
        (tail, assessment) for the scenario's aircraft, worst first.
        Threat levels come from the same tracker the scope uses, so
        they match what is drawn.
        """
        assessments = []

        for report in HudDataCache.get_reliable_traffic():
            assessment = traffic_threat.INSTANCE.assess(report, orientation)
            assessments.append((report.get_display_name(), assessment))

        assessments.sort(key=lambda pair: pair[1].level, reverse=True)

        if len(assessments) > MAX_LISTED_AIRCRAFT:
            assessments = [
                pair for pair in assessments if pair[1].level > ThreatLevel.NONE
            ][:MAX_LISTED_AIRCRAFT]

        return assessments

    def __clear_traffic__(self):
        traffic.AdsbTrafficClient.TRAFFIC_MANAGER.clear()
        traffic_threat.INSTANCE.clear()


class ScenarioCaption(AhrsElement):
    """
    The scenario's name, clock, and what should happen, in the top
    left corner; the key help in the bottom left.
    """

    player: ScenarioPlayer = None

    def __init__(
        self,
        degrees_of_pitch: float,
        pixels_per_degree_y: float,
        font,
        framebuffer_size,
        reduced_visuals: bool = False,
    ):
        super().__init__(font, framebuffer_size, reduced_visuals)

    def render(self, framebuffer, orientation: AhrsData):
        player = self.player

        if player is None:
            return

        scenario = player.scenario
        x = self.__left_border__
        y = self.__top_border__

        y += self.__render_text__(
            framebuffer,
            f"{player.index + 1}/{len(player.scenarios)} {scenario.name}",
            [x, y],
            colors.WHITE,
            0.5,
        )[1]
        y += self.__render_text__(
            framebuffer, player.get_clock_text(), [x, y], colors.YELLOW, 0.5
        )[1]

        for line in [scenario.description]:
            y += self.__render_text__(
                framebuffer, line, [x, y], colors.GRAY, 0.4
            )[1]

        for tail, assessment in player.get_assessments(orientation):
            y += self.__render_text__(
                framebuffer,
                get_assessment_text(tail, assessment),
                [x, y],
                THREAT_COLORS[assessment.level],
                0.4,
            )[1]

        if not player.is_help_shown:
            return

        line_height = int(self.__font_height__ * 0.4)
        y = self.__bottom_border__ - line_height * len(HELP_LINES)

        for line in HELP_LINES:
            self.__render_text__(framebuffer, line, [x, y], colors.GRAY, 0.4)
            y += line_height


def get_assessment_text(tail: str, assessment: traffic_threat.ThreatAssessment) -> str:
    """
    "N1HO CRITICAL straight in 12s: 0.10sm +200ft"
    """
    text = f"{tail} {assessment.level.name} {assessment.reason}"

    if assessment.seconds is not None and assessment.seconds > 0.0:
        text += f" in {assessment.seconds:.0f}s"

    if assessment.distance_sm is not None:
        text += f": {assessment.distance_sm:.2f}sm"

    if assessment.vertical_feet is not None:
        text += f" {assessment.vertical_feet:+.0f}ft"

    return text


def __ignore_real_traffic__():
    """
    The traffic client polls the traffic manager in the background;
    drop what it receives so it can't mix with the scenario.
    """
    client = traffic.AdsbTrafficClient.INSTANCE

    if client is not None:
        client.received_message = lambda *args, **kwargs: None


def __get_starting_index__(arguments: list) -> int:
    """
    The scenario to start with: a number (from 1) or part of a name.
    """
    scenarios = traffic_scenarios.SCENARIOS

    for argument in arguments:
        if argument.isdigit():
            return int(argument) - 1

        for index, scenario in enumerate(scenarios):
            if argument.lower() in scenario.name.lower():
                return index

    return 0


def run():
    __ignore_real_traffic__()

    screen = display.Display()
    pygame.mouse.set_visible(False)

    player = ScenarioPlayer(
        traffic_scenarios.SCENARIOS, __get_starting_index__(sys.argv[1:])
    )
    ScenarioCaption.player = player
    scope, caption = create_hud_elements(
        [TrafficScenarioScope, ScenarioCaption], screen.size
    )
    clock = pygame.time.Clock()

    while True:
        events = pygame.event.get()

        for event in events:
            is_escape = event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE

            if event.type == pygame.QUIT or is_escape:
                return

        scope.handle_events(player.handle_events(events))

        real_seconds = clock.tick(60) / 1000.0
        player.advance(real_seconds)
        orientation = player.publish()

        screen.clear()
        framebuffer = screen.get_framebuffer()
        scope.render(framebuffer, orientation)
        caption.render(framebuffer, orientation)
        screen.flip()


if __name__ == "__main__":
    run()
