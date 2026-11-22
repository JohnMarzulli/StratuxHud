"""
HDMI diagnostics for the Raspberry Pi.

Logs what the Pi knows about its HDMI output and whatever is attached to it:

- The kernel command line and the display related lines of config.txt
- Every DRM HDMI connector: hotplug status, enabled, DPMS, the modes offered
- The EDID of the attached device, decoded (maker, model, preferred mode, supported CEA modes, HDMI vs DVI, checksum validity)
- Firmware values from vcgencmd (power/throttling, pixel clock, HDMI config)
- The console framebuffer size, the DRM state from `kmsprint` if installed
- The display related kernel messages from this boot

It also provides `HdmiMonitor`, a background poller that logs every change
in connector state (hotplug, EDID appearing/disappearing, DPMS, undervoltage)
so a link that drops or comes up late shows up in the log with a timestamp.

Everything here is best effort. Nothing raises, every subprocess has a
timeout, and on non-Pi hosts the functions quietly do (almost) nothing.
Every line is prefixed with "HDMI:" so it is easy to grep out of the log.

Can also be run by hand on the Pi:

    python3 -m common_utils.hdmi_diagnostics            # one snapshot
    python3 -m common_utils.hdmi_diagnostics --watch    # snapshot, then watch for changes
"""

import glob
import hashlib
import os
import shutil
import subprocess
import threading
import time
from typing import Callable, Optional

LOG_PREFIX = "HDMI: "

DRM_CLASS_PATH = "/sys/class/drm"
FRAMEBUFFER_PATH = "/sys/class/graphics/fb0"
CMDLINE_PATH = "/proc/cmdline"
UPTIME_PATH = "/proc/uptime"
CONFIG_TXT_PATHS = ["/boot/firmware/config.txt", "/boot/config.txt"]

SUBPROCESS_TIMEOUT_SECONDS = 5
DEFAULT_POLL_SECONDS = 2.0
MAX_KERNEL_LINES = 80

# config.txt keys that change how the display comes up.
CONFIG_TXT_KEYS = (
    "hdmi", "dtoverlay=vc4", "disable_fw_kms_setup", "max_framebuffers",
    "display_auto_detect", "disable_overscan", "overscan", "framebuffer",
    "config_hdmi_boost", "disable_splash", "camera_auto_detect", "dtparam=audio",
    "arm_boost", "[",
)

# Kernel log lines worth keeping.
KERNEL_LOG_KEYWORDS = ("vc4", "hdmi", "drm", "edid", "hotplug", "hpd", "fbcon", "v3d", "cec")

# vcgencmd get_throttled bits.
THROTTLE_BITS = {
    0: "under-voltage NOW",
    1: "ARM frequency capped NOW",
    2: "throttled NOW",
    3: "soft temperature limit NOW",
    16: "under-voltage has occurred",
    17: "ARM frequency capping has occurred",
    18: "throttling has occurred",
    19: "soft temperature limit has occurred",
}

# The CEA-861 video codes a HUD display is likely to care about.
CEA_VIC_NAMES = {
    1: "640x480p60", 2: "720x480p60 4:3", 3: "720x480p60 16:9",
    4: "1280x720p60", 5: "1920x1080i60", 16: "1920x1080p60",
    17: "720x576p50 4:3", 18: "720x576p50 16:9", 19: "1280x720p50",
    20: "1920x1080i50", 31: "1920x1080p50", 32: "1920x1080p24",
    33: "1920x1080p25", 34: "1920x1080p30", 95: "3840x2160p30",
    97: "3840x2160p60",
}

EDID_HEADER = bytes([0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00])
EDID_BLOCK_SIZE = 128
HDMI_LLC_OUI = 0x000C03
HDMI_FORUM_OUI = 0xC45DD8


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

def __log__(logger, message: str):
    """
    Logs to a HudLogger, a plain logging.Logger, or stdout.
    """
    text = LOG_PREFIX + message

    try:
        if logger is None:
            print(text)
        elif hasattr(logger, "log_info_message"):
            logger.log_info_message(text)
        else:
            logger.info(text)
    except Exception:
        print(text)


def __log_lines__(logger, title: str, lines):
    lines = list(lines)

    if not lines:
        __log__(logger, "{}: <none>".format(title))
        return

    __log__(logger, "{}:".format(title))

    for line in lines:
        __log__(logger, "    " + line)


# ---------------------------------------------------------------------------
# Low level readers (never raise)
# ---------------------------------------------------------------------------

def __read_text__(path: str) -> Optional[str]:
    try:
        with open(path, "r", errors="replace") as file:
            return file.read().strip()
    except (OSError, ValueError):
        return None


def __read_bytes__(path: str) -> bytes:
    try:
        with open(path, "rb") as file:
            return file.read()
    except (OSError, ValueError):
        return b""


def __run__(command: list) -> Optional[str]:
    """
    Runs a command and returns its output, or None if it is not
    installed, fails to start, or times out.
    """
    if shutil.which(command[0]) is None:
        return None

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=SUBPROCESS_TIMEOUT_SECONDS,
            check=False)

        return result.stdout.decode("utf-8", errors="replace").strip()
    except (OSError, subprocess.SubprocessError):
        return None


def get_seconds_since_boot() -> Optional[float]:
    uptime = __read_text__(UPTIME_PATH)

    try:
        return float(uptime.split()[0]) if uptime else None
    except (AttributeError, IndexError, ValueError):
        return None


# ---------------------------------------------------------------------------
# EDID decoding
# ---------------------------------------------------------------------------

def __is_block_checksum_valid__(block: bytes) -> bool:
    return len(block) == EDID_BLOCK_SIZE and (sum(block) % 256) == 0


def __decode_detailed_timing__(descriptor: bytes) -> Optional[dict]:
    pixel_clock_khz = (descriptor[0] | (descriptor[1] << 8)) * 10

    if pixel_clock_khz == 0:
        return None

    h_active = descriptor[2] | ((descriptor[4] & 0xF0) << 4)
    h_blank = descriptor[3] | ((descriptor[4] & 0x0F) << 8)
    v_active = descriptor[5] | ((descriptor[7] & 0xF0) << 4)
    v_blank = descriptor[6] | ((descriptor[7] & 0x0F) << 8)
    interlaced = bool(descriptor[17] & 0x80)

    total = (h_active + h_blank) * (v_active + v_blank)
    refresh = (pixel_clock_khz * 1000.0 / total) if total > 0 else 0.0

    return {
        "width": h_active,
        "height": v_active * (2 if interlaced else 1),
        "refresh": round(refresh, 2),
        "pixel_clock_mhz": pixel_clock_khz / 1000.0,
        "interlaced": interlaced,
    }


def __decode_descriptor_text__(descriptor: bytes) -> str:
    return descriptor[5:18].split(b"\x0a")[0].decode("ascii", errors="replace").strip()


def __decode_cea_extension__(block: bytes, result: dict):
    result["cea_checksum_valid"] = __is_block_checksum_valid__(block)
    result["basic_audio"] = bool(block[3] & 0x40)

    dtd_offset = block[2]
    index = 4

    # Data block collection runs from byte 4 up to the DTD offset.
    while 4 <= index < min(dtd_offset, EDID_BLOCK_SIZE):
        tag = block[index] >> 5
        length = block[index] & 0x1F
        payload = block[index + 1:index + 1 + length]

        if tag == 2:  # Video data block
            for code in payload:
                vic = code & 0x7F if code <= 0xC0 else code
                native = code <= 0xC0 and bool(code & 0x80)
                result["cea_vics"].append((vic, native))
        elif tag == 3 and len(payload) >= 3:  # Vendor specific data block
            oui = payload[0] | (payload[1] << 8) | (payload[2] << 16)

            if oui == HDMI_LLC_OUI:
                result["is_hdmi"] = True

                if len(payload) >= 7 and payload[6] > 0:
                    result["max_tmds_mhz"] = payload[6] * 5
            elif oui == HDMI_FORUM_OUI:
                result["hdmi_forum"] = True

        index += 1 + length

    # Any detailed timings in the extension.
    offset = dtd_offset

    while 4 <= offset and offset + 18 <= EDID_BLOCK_SIZE - 1:
        timing = __decode_detailed_timing__(block[offset:offset + 18])

        if timing is None:
            break

        result["detailed_timings"].append(timing)
        offset += 18


def parse_edid(edid: bytes) -> Optional[dict]:
    """
    Decodes the parts of an EDID that matter for diagnosing a display link.

    Returns None when there is no EDID at all.
    """
    if not edid:
        return None

    result = {
        "length": len(edid),
        "header_valid": edid[:8] == EDID_HEADER,
        "checksum_valid": __is_block_checksum_valid__(edid[:EDID_BLOCK_SIZE]),
        "sha1": hashlib.sha1(edid).hexdigest()[:12],
        "manufacturer": None,
        "product_code": None,
        "serial_number": None,
        "manufacture_date": None,
        "edid_version": None,
        "digital_input": None,
        "monitor_name": None,
        "serial_text": None,
        "range_limits": None,
        "detailed_timings": [],
        "extension_count": 0,
        "is_hdmi": False,
        "hdmi_forum": False,
        "max_tmds_mhz": None,
        "basic_audio": None,
        "cea_vics": [],
        "cea_checksum_valid": None,
    }

    if len(edid) < EDID_BLOCK_SIZE or not result["header_valid"]:
        return result

    packed = (edid[8] << 8) | edid[9]
    result["manufacturer"] = "".join(
        chr(((packed >> shift) & 0x1F) + 64) for shift in (10, 5, 0))
    result["product_code"] = "0x{:04X}".format(edid[10] | (edid[11] << 8))
    result["serial_number"] = edid[12] | (edid[13] << 8) | (edid[14] << 16) | (edid[15] << 24)
    result["manufacture_date"] = "week {} of {}".format(edid[16], 1990 + edid[17])
    result["edid_version"] = "{}.{}".format(edid[18], edid[19])
    result["digital_input"] = bool(edid[20] & 0x80)
    result["extension_count"] = edid[126]

    for offset in (54, 72, 90, 108):
        descriptor = edid[offset:offset + 18]
        timing = __decode_detailed_timing__(descriptor)

        if timing is not None:
            result["detailed_timings"].append(timing)
            continue

        tag = descriptor[3]

        if tag == 0xFC:
            result["monitor_name"] = __decode_descriptor_text__(descriptor)
        elif tag == 0xFF:
            result["serial_text"] = __decode_descriptor_text__(descriptor)
        elif tag == 0xFD:
            result["range_limits"] = "V {}-{} Hz, H {}-{} kHz, max pixel clock {} MHz".format(
                descriptor[5], descriptor[6], descriptor[7], descriptor[8], descriptor[9] * 10)

    for extension in range(1, result["extension_count"] + 1):
        block = edid[extension * EDID_BLOCK_SIZE:(extension + 1) * EDID_BLOCK_SIZE]

        if len(block) == EDID_BLOCK_SIZE and block[0] == 0x02:
            __decode_cea_extension__(block, result)

    return result


def __format_timing__(timing: dict) -> str:
    return "{}x{}{}@{}Hz ({:.2f} MHz pixel clock)".format(
        timing["width"],
        timing["height"],
        "i" if timing["interlaced"] else "p",
        timing["refresh"],
        timing["pixel_clock_mhz"])


def describe_edid(edid: bytes) -> list:
    """
    Human readable lines describing an EDID.
    """
    info = parse_edid(edid)

    if info is None:
        return ["NO EDID (nothing answered on DDC, or the link was not up when the kernel probed)"]

    lines = ["{} bytes, sha1 {}, header {}, checksum {}".format(
        info["length"],
        info["sha1"],
        "ok" if info["header_valid"] else "BAD",
        "ok" if info["checksum_valid"] else "BAD")]

    if not info["header_valid"]:
        lines.append("EDID header is invalid; first bytes: {}".format(edid[:16].hex()))
        return lines

    lines.append("Maker {} product {} serial {} ({}), EDID {}".format(
        info["manufacturer"],
        info["product_code"],
        info["serial_number"],
        info["manufacture_date"],
        info["edid_version"]))

    if info["monitor_name"] or info["serial_text"]:
        lines.append("Name '{}' serial text '{}'".format(
            info["monitor_name"] or "", info["serial_text"] or ""))

    lines.append("Sink type: {}{}{}".format(
        "HDMI" if info["is_hdmi"] else "DVI (no HDMI vendor block; no audio/InfoFrames)",
        ", HDMI 2.x" if info["hdmi_forum"] else "",
        ", max TMDS {} MHz".format(info["max_tmds_mhz"]) if info["max_tmds_mhz"] else ""))

    if info["range_limits"]:
        lines.append("Range limits: " + info["range_limits"])

    for index, timing in enumerate(info["detailed_timings"]):
        lines.append("{} timing: {}".format(
            "PREFERRED" if index == 0 else "Detailed", __format_timing__(timing)))

    if info["cea_vics"]:
        lines.append("CEA modes: " + ", ".join(
            "{}{}{}".format(
                vic,
                "=" + CEA_VIC_NAMES[vic] if vic in CEA_VIC_NAMES else "",
                " (native)" if native else "")
            for vic, native in info["cea_vics"]))

    if info["extension_count"] and info["cea_checksum_valid"] is False:
        lines.append("CEA extension checksum is BAD")

    lines.append("Extensions: {}, basic audio: {}".format(
        info["extension_count"], info["basic_audio"]))

    return lines


# ---------------------------------------------------------------------------
# DRM connectors
# ---------------------------------------------------------------------------

def find_hdmi_connectors() -> list:
    """
    Paths of the DRM HDMI connectors, e.g. /sys/class/drm/card1-HDMI-A-1
    """
    return sorted(glob.glob(os.path.join(DRM_CLASS_PATH, "card*-HDMI-A-*")))


def read_connector_state(connector_path: str) -> dict:
    modes = __read_text__(os.path.join(connector_path, "modes")) or ""

    return {
        "name": os.path.basename(connector_path),
        "status": __read_text__(os.path.join(connector_path, "status")),
        "enabled": __read_text__(os.path.join(connector_path, "enabled")),
        "dpms": __read_text__(os.path.join(connector_path, "dpms")),
        "modes": [mode for mode in modes.splitlines() if mode],
        "edid": __read_bytes__(os.path.join(connector_path, "edid")),
    }


def __summarize_connector__(state: dict) -> str:
    return "{}: status={} enabled={} dpms={} modes={} edid={}".format(
        state["name"],
        state["status"],
        state["enabled"],
        state["dpms"],
        len(state["modes"]),
        "{} bytes".format(len(state["edid"])) if state["edid"] else "none")


def save_edid(
    state: dict,
    directory: str
) -> Optional[str]:
    """
    Saves a connector's EDID to `directory` when it is valid and differs
    from what is already saved. A known good EDID can later be used with
    `drm.edid_firmware=` so the Pi no longer depends on reading it over a
    flaky link at boot.

    Returns the file path when a file was written.
    """
    edid = state["edid"]
    info = parse_edid(edid)

    if info is None or not info["header_valid"] or not info["checksum_valid"]:
        return None

    path = os.path.join(directory, "hdmi_edid_{}.bin".format(state["name"]))

    if __read_bytes__(path) == edid:
        return None

    try:
        with open(path, "wb") as file:
            file.write(edid)
        return path
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Firmware, boot config, kernel
# ---------------------------------------------------------------------------

def get_throttled() -> Optional[int]:
    output = __run__(["vcgencmd", "get_throttled"])

    try:
        return int(output.split("=")[1], 16) if output and "=" in output else None
    except (AttributeError, IndexError, ValueError):
        return None


def describe_throttled(value: Optional[int]) -> str:
    if value is None:
        return "unknown"

    flags = [text for bit, text in THROTTLE_BITS.items() if value & (1 << bit)]

    return "0x{:X} ({})".format(value, ", ".join(flags) if flags else "ok")


def get_firmware_lines() -> list:
    lines = []

    for command in (
        ["vcgencmd", "version"],
        ["vcgencmd", "measure_volts", "core"],
        ["vcgencmd", "measure_temp"],
        ["vcgencmd", "measure_clock", "pixel"],
        ["vcgencmd", "measure_clock", "hdmi"],
        ["vcgencmd", "display_power"],
    ):
        output = __run__(command)

        if output is not None:
            lines.append("{}: {}".format(" ".join(command[1:]), " | ".join(output.splitlines())))

    if shutil.which("vcgencmd") is not None:
        lines.append("throttled: " + describe_throttled(get_throttled()))

    for config_type in ("int", "str"):
        output = __run__(["vcgencmd", "get_config", config_type]) or ""

        for line in output.splitlines():
            key = line.split("=")[0]

            if any(word in key for word in ("hdmi", "kms", "framebuffer", "display", "overscan")):
                lines.append("config " + line)

    return lines


def get_config_txt_lines() -> list:
    for path in CONFIG_TXT_PATHS:
        text = __read_text__(path)

        if text is None:
            continue

        lines = ["(from {})".format(path)]

        for line in text.splitlines():
            stripped = line.strip()

            if stripped and not stripped.startswith("#") and stripped.lower().startswith(CONFIG_TXT_KEYS):
                lines.append(stripped)

        return lines

    return []


def get_framebuffer_lines() -> list:
    lines = []

    for name in ("name", "virtual_size", "bits_per_pixel", "modes"):
        value = __read_text__(os.path.join(FRAMEBUFFER_PATH, name))

        if value is not None:
            lines.append("{}: {}".format(name, " | ".join(value.splitlines())))

    return lines


def get_kms_lines() -> list:
    """
    The DRM state (which CRTC/plane drives which connector, and the
    CURRENT mode, which sysfs does not show). Needs kms++-utils.
    """
    output = __run__(["kmsprint"])

    return output.splitlines() if output else []


def get_kernel_display_lines() -> list:
    """
    Display related kernel messages from this boot, with monotonic
    (seconds since boot) timestamps. journalctl works for members of
    the adm/systemd-journal groups (the pi user is by default); dmesg
    is the fallback.
    """
    output = __run__(["journalctl", "-k", "-b", "-o", "short-monotonic", "--no-pager", "-q"])

    if not output:
        output = __run__(["dmesg"])

    if not output:
        return ["<unable to read the kernel log>"]

    lines = [
        line for line in output.splitlines()
        if any(keyword in line.lower() for keyword in KERNEL_LOG_KEYWORDS)]

    return lines[-MAX_KERNEL_LINES:]


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def is_supported() -> bool:
    return os.path.isdir(DRM_CLASS_PATH)


def get_edid_hex_lines(
    edid: bytes,
    bytes_per_line: int = 32
) -> list:
    """
    The raw EDID as hex, split into log sized lines. Joining the hex
    back together and running `xxd -r -p` recreates the .bin file:

        grep "EDID hex card1-HDMI-A-1" stratux_hud.log | tail -8 \\
            | sed 's/.*: //' | xxd -r -p > edid.bin
    """
    return [
        edid[offset:offset + bytes_per_line].hex()
        for offset in range(0, len(edid), bytes_per_line)]


def log_hdmi_snapshot(
    logger=None,
    stage: str = "",
    include_boot_config: bool = True,
    edid_save_directory: Optional[str] = None
):
    """
    Logs everything that can be determined about the HDMI output.

    Args:
        logger: HudLogger, logging.Logger, or None to print.
        stage (str): Label for where in startup this was taken.
        include_boot_config (bool): Include cmdline/config.txt/firmware config.
        edid_save_directory (str, optional): Save a valid EDID here.
    """
    try:
        if not is_supported():
            __log__(logger, "No DRM devices ({} missing); skipping HDMI snapshot".format(DRM_CLASS_PATH))
            return

        uptime = get_seconds_since_boot()
        __log__(logger, "===== HDMI snapshot [{}] at {} s since boot =====".format(
            stage, "{:.1f}".format(uptime) if uptime is not None else "?"))

        if include_boot_config:
            __log__(logger, "cmdline: {}".format(__read_text__(CMDLINE_PATH)))
            __log_lines__(logger, "config.txt (display related)", get_config_txt_lines())

        __log_lines__(logger, "Firmware", get_firmware_lines())

        connectors = find_hdmi_connectors()

        if not connectors:
            __log__(logger, "No HDMI connectors found. Is dtoverlay=vc4-kms-v3d loaded?")

        for connector in connectors:
            state = read_connector_state(connector)
            __log__(logger, __summarize_connector__(state))
            __log__(logger, "  {} kernel preferred mode: {}".format(
                state["name"], state["modes"][0] if state["modes"] else "none"))
            __log_lines__(logger, "  {} modes".format(state["name"]), state["modes"])
            __log_lines__(logger, "  {} EDID".format(state["name"]), describe_edid(state["edid"]))

            # The raw EDID, so it can be recovered from the log alone.
            hex_lines = get_edid_hex_lines(state["edid"])

            for index, line in enumerate(hex_lines):
                __log__(logger, "EDID hex {} [{}/{}]: {}".format(
                    state["name"], index + 1, len(hex_lines), line))

            if edid_save_directory:
                saved = save_edid(state, edid_save_directory)

                if saved:
                    __log__(logger, "Saved EDID to {}".format(saved))

        __log_lines__(logger, "Console framebuffer", get_framebuffer_lines())
        __log_lines__(logger, "kmsprint", get_kms_lines() or [
                      "<kmsprint not installed: sudo apt install kms++-utils>"])
        __log_lines__(logger, "Kernel display messages", get_kernel_display_lines())
        __log__(logger, "===== end HDMI snapshot [{}] =====".format(stage))
    except Exception as ex:
        __log__(logger, "HDMI snapshot failed: {}".format(ex))


def log_pygame_display_info(logger=None):
    """
    Logs what SDL/pygame ended up with after the display was created.
    """
    try:
        import pygame

        if not pygame.display.get_init():
            __log__(logger, "pygame display is not initialized")
            return

        info = pygame.display.Info()
        surface = pygame.display.get_surface()

        __log__(logger, "pygame: driver={} desktop={}x{} surface={} bitsize={}".format(
            pygame.display.get_driver(),
            info.current_w,
            info.current_h,
            "{}x{}".format(*surface.get_size()) if surface is not None else "none",
            info.bitsize))

        if hasattr(pygame.display, "get_desktop_sizes"):
            __log__(logger, "pygame: desktop sizes {}".format(pygame.display.get_desktop_sizes()))

        if hasattr(pygame.display, "get_current_refresh_rate"):
            __log__(logger, "pygame: refresh rate {} Hz".format(
                pygame.display.get_current_refresh_rate()))
    except Exception as ex:
        __log__(logger, "pygame display info failed: {}".format(ex))


class HdmiMonitor(object):
    """
    Polls the HDMI connectors on a background thread and logs every change
    (hotplug, EDID appearing/changing/vanishing, DPMS, mode list) plus any
    change in the firmware throttling/under-voltage flags.

    Reading the sysfs files only returns the kernel's cached state; it does
    not trigger a new probe of the display, so polling is cheap and does
    not disturb the link.

    `on_change(name, old_state, new_state)` is called (on the monitor
    thread) whenever a connector changes. It could, for example, re-create
    the display when a connector goes from disconnected to connected.
    """

    def __init__(
        self,
        logger=None,
        poll_seconds: float = DEFAULT_POLL_SECONDS,
        on_change: Optional[Callable[[str, Optional[dict], dict], None]] = None,
        edid_save_directory: Optional[str] = None,
        start_immediate: bool = True
    ):
        self.__logger__ = logger
        self.__poll_seconds__ = poll_seconds
        self.__on_change__ = on_change
        self.__edid_save_directory__ = edid_save_directory
        self.__states__ = {}
        self.__throttled__ = None
        self.__stop__ = threading.Event()
        self.__thread__ = threading.Thread(
            target=self.__run__, name="HdmiMonitor", daemon=True)

        if start_immediate:
            self.start()

    def start(self) -> bool:
        if not is_supported() or self.__thread__.is_alive():
            return False

        self.__poll__(log_initial=False)
        self.__thread__.start()

        return True

    def stop(self):
        self.__stop__.set()

    def __run__(self):
        while not self.__stop__.wait(self.__poll_seconds__):
            try:
                self.__poll__()
            except Exception as ex:
                __log__(self.__logger__, "HDMI monitor poll failed: {}".format(ex))

    def __poll__(
        self,
        log_initial: bool = True
    ):
        for connector in find_hdmi_connectors():
            state = read_connector_state(connector)
            old_state = self.__states__.get(state["name"])
            self.__states__[state["name"]] = state

            if old_state is None:
                if log_initial:
                    __log__(self.__logger__, "Connector appeared: " +
                            __summarize_connector__(state))
                continue

            changes = self.__describe_changes__(old_state, state)

            if not changes:
                continue

            uptime = get_seconds_since_boot()
            __log__(self.__logger__, "{} changed at {} s since boot: {}".format(
                state["name"],
                "{:.1f}".format(uptime) if uptime is not None else "?",
                "; ".join(changes)))

            if old_state["edid"] != state["edid"]:
                __log_lines__(self.__logger__, "  New EDID", describe_edid(state["edid"]))

            if self.__edid_save_directory__:
                saved = save_edid(state, self.__edid_save_directory__)

                if saved:
                    __log__(self.__logger__, "Saved EDID to {}".format(saved))

            if self.__on_change__ is not None:
                try:
                    self.__on_change__(state["name"], old_state, state)
                except Exception as ex:
                    __log__(self.__logger__, "HDMI on_change callback failed: {}".format(ex))

        throttled = get_throttled()

        if throttled is not None and throttled != self.__throttled__:
            if self.__throttled__ is not None or throttled != 0:
                __log__(self.__logger__, "Throttle flags: " + describe_throttled(throttled))

            self.__throttled__ = throttled

    @staticmethod
    def __describe_changes__(
        old_state: dict,
        new_state: dict
    ) -> list:
        changes = []

        for key in ("status", "enabled", "dpms"):
            if old_state[key] != new_state[key]:
                changes.append("{} {} -> {}".format(key, old_state[key], new_state[key]))

        if old_state["modes"] != new_state["modes"]:
            changes.append("modes {} -> {} (first: {})".format(
                len(old_state["modes"]),
                len(new_state["modes"]),
                new_state["modes"][0] if new_state["modes"] else "none"))

        if old_state["edid"] != new_state["edid"]:
            changes.append("EDID {} -> {} bytes".format(
                len(old_state["edid"]), len(new_state["edid"])))

        return changes


if __name__ == "__main__":
    import sys

    log_hdmi_snapshot(None, "manual", edid_save_directory=os.getcwd())

    if "--watch" in sys.argv:
        print(LOG_PREFIX + "Watching for HDMI changes; Ctrl+C to stop.")
        monitor = HdmiMonitor(None, edid_save_directory=os.getcwd())

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            monitor.stop()
