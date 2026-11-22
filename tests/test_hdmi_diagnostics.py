import unittest

from common_utils import hdmi_diagnostics


def with_checksum(block: bytearray) -> bytes:
    block[127] = (256 - (sum(block[:127]) % 256)) % 256
    return bytes(block)


def make_edid(with_hdmi_extension: bool = True) -> bytes:
    """
    A minimal EDID: 1280x720p60 preferred, named "HUDTEST",
    optionally with a CEA extension carrying the HDMI vendor block.
    """
    base = bytearray(128)
    base[0:8] = hdmi_diagnostics.EDID_HEADER
    # "RPI" packed into 5 bit letters.
    packed = ((ord("R") - 64) << 10) | ((ord("P") - 64) << 5) | (ord("I") - 64)
    base[8], base[9] = packed >> 8, packed & 0xFF
    base[10], base[11] = 0x34, 0x12
    base[16], base[17] = 10, 30
    base[18], base[19] = 1, 3
    base[20] = 0x80

    # 1280x720p60: 74.25 MHz, 370 h blank, 30 v blank.
    dtd = bytearray(18)
    dtd[0], dtd[1] = 7425 & 0xFF, 7425 >> 8
    dtd[2], dtd[3], dtd[4] = 1280 & 0xFF, 370 & 0xFF, ((1280 >> 8) << 4) | (370 >> 8)
    dtd[5], dtd[6], dtd[7] = 720 & 0xFF, 30, ((720 >> 8) << 4)
    base[54:72] = dtd

    name = bytearray(18)
    name[3] = 0xFC
    name[5:18] = b"HUDTEST\n     "
    base[72:90] = name

    base[126] = 1 if with_hdmi_extension else 0
    edid = with_checksum(base)

    if not with_hdmi_extension:
        return edid

    extension = bytearray(128)
    extension[0], extension[1] = 0x02, 0x03
    blocks = bytes([
        (2 << 5) | 2, 0x84, 16,                       # Video: VIC 4 native, VIC 16
        (3 << 5) | 7, 0x03, 0x0C, 0x00, 0x10, 0x00, 0x00, 30,  # HDMI VSDB, 150 MHz TMDS
    ])
    extension[4:4 + len(blocks)] = blocks
    extension[2] = 4 + len(blocks)
    extension[3] = 0x40

    return edid + with_checksum(extension)


class TestEdidParsing(unittest.TestCase):
    def test_no_edid(self):
        self.assertIsNone(hdmi_diagnostics.parse_edid(b""))
        self.assertIn("NO EDID", hdmi_diagnostics.describe_edid(b"")[0])

    def test_basic_fields(self):
        info = hdmi_diagnostics.parse_edid(make_edid())

        self.assertTrue(info["header_valid"])
        self.assertTrue(info["checksum_valid"])
        self.assertEqual(info["manufacturer"], "RPI")
        self.assertEqual(info["product_code"], "0x1234")
        self.assertEqual(info["monitor_name"], "HUDTEST")
        self.assertEqual(info["edid_version"], "1.3")

        preferred = info["detailed_timings"][0]
        self.assertEqual((preferred["width"], preferred["height"]), (1280, 720))
        self.assertAlmostEqual(preferred["refresh"], 60.0, places=1)

    def test_hdmi_extension(self):
        info = hdmi_diagnostics.parse_edid(make_edid())

        self.assertTrue(info["is_hdmi"])
        self.assertTrue(info["cea_checksum_valid"])
        self.assertTrue(info["basic_audio"])
        self.assertEqual(info["max_tmds_mhz"], 150)
        self.assertEqual(info["cea_vics"], [(4, True), (16, False)])

    def test_dvi_only(self):
        info = hdmi_diagnostics.parse_edid(make_edid(with_hdmi_extension=False))

        self.assertFalse(info["is_hdmi"])
        self.assertIn("DVI", "\n".join(hdmi_diagnostics.describe_edid(
            make_edid(with_hdmi_extension=False))))

    def test_corrupt_edid(self):
        edid = bytearray(make_edid())
        edid[60] ^= 0xFF
        info = hdmi_diagnostics.parse_edid(bytes(edid))

        self.assertFalse(info["checksum_valid"])

    def test_garbage_edid(self):
        info = hdmi_diagnostics.parse_edid(b"\x12\x34")

        self.assertFalse(info["header_valid"])
        self.assertIn("BAD", hdmi_diagnostics.describe_edid(b"\x12\x34")[0])


class TestThrottled(unittest.TestCase):
    def test_describe(self):
        self.assertEqual(hdmi_diagnostics.describe_throttled(0), "0x0 (ok)")
        self.assertIn("under-voltage has occurred",
                      hdmi_diagnostics.describe_throttled(0x50000))
        self.assertEqual(hdmi_diagnostics.describe_throttled(None), "unknown")


class TestMonitorChanges(unittest.TestCase):
    def state(self, status="connected", edid=b"", modes=None):
        return {
            "name": "card1-HDMI-A-1",
            "status": status,
            "enabled": "enabled",
            "dpms": "On",
            "modes": modes or [],
            "edid": edid,
        }

    def test_no_change(self):
        self.assertEqual(hdmi_diagnostics.HdmiMonitor.__describe_changes__(
            self.state(), self.state()), [])

    def test_hotplug_and_edid(self):
        changes = hdmi_diagnostics.HdmiMonitor.__describe_changes__(
            self.state("disconnected"),
            self.state("connected", make_edid(), ["1280x720"]))

        self.assertEqual(len(changes), 3)
        self.assertIn("status disconnected -> connected", changes[0])


if __name__ == "__main__":
    unittest.main()
