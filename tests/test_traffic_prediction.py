import unittest
from unittest.mock import Mock, call, patch

with patch("requests.Session.get", return_value=Mock(json=lambda: {})):
    from core_services.scope_range import ScopeRange
    from data_sources.traffic import AdsbTrafficClient, Traffic
    from views.abstract_elements.adsb_element import AdsbElement
    from views.adsb_on_screen_reticles import AdsbOnScreenReticles


def point(latitude, longitude, altitude=1000):
    return {"Lat": latitude, "Lng": longitude, "Alt": altitude, "secondsAhead": 0, "Track": 0}


def make_traffic(prediction):
    return Traffic("123", {
        "displayName": "N123", "Lat": 0.01, "Lng": 0,
        "Alt": 1000, "Distance": 5280, "Bearing": 0, "Track": 0,
        "Prediction": prediction,
    })


class TrafficPredictionTests(unittest.TestCase):
    def test_reliable_endpoint_forwards_prediction(self):
        client = AdsbTrafficClient.__new__(AdsbTrafficClient)
        prediction = {"type": "straight", "points": [
            point(0.01, 0), point(0.02, 0)]}
        report = {"displayName": "N123", "Prediction": prediction}
        client.rest_address = "receiver"
        client.__traffic_session__ = Mock()
        client.__traffic_session__.get.return_value.json.return_value = {
            "123": report}
        client.received_message = Mock()
        self.assertTrue(client.update_reliable_traffic())
        self.assertEqual(
            client.__traffic_session__.get.call_args.args[0], "http://receiver/Traffic/Reliable")
        client.received_message.assert_called_once_with("123", report)

    def test_latest_prediction_replaces_previous_data(self):
        first = {"type": "straight", "points": [
            point(0.01, 0), point(0.02, 0)]}
        second = {"type": "turning", "points": [
            point(0.01, 0), point(0.02, 0.01)]}
        traffic = make_traffic(first)
        self.assertEqual(len(traffic.get_prediction_points()), 2)
        traffic.update({"Prediction": second})
        self.assertIs(traffic.prediction, second)
        traffic.update({"Prediction": None})
        self.assertEqual(traffic.get_prediction_points(), [])
        traffic.update({"Prediction": first})
        traffic.update({})
        self.assertEqual(traffic.get_prediction_points(), [])

    def test_invalid_points_break_the_path(self):
        traffic = make_traffic(
            {"points": [point(0, 0), {"Lat": 0}, point(1, 1), point(float("nan"), 0)]})
        self.assertEqual(traffic.get_prediction_points(), [
                         (0, 0, 1000), None, (1, 1, 1000), None])
        for prediction in (None, {}, {"points": None}, "invalid"):
            traffic.update({"Prediction": prediction})
            self.assertEqual(traffic.get_prediction_points(), [])

    def test_forward_projection_wraps_across_north(self):
        view = AdsbElement.__new__(AdsbElement)
        view.__center__ = [50, 50]
        view.__pixels_per_degree_y__ = 2
        orientation = Mock(alt=1000, pitch=0)
        orientation.get_onscreen_projection_heading.return_value = 359
        traffic = make_traffic(None)
        traffic.bearing = 1
        with patch("views.abstract_elements.adsb_element.apply_declination", side_effect=lambda bearing: bearing):
            self.assertEqual(view.__get_traffic_projection__(
                orientation, traffic), (54, 50))

    def test_forward_path_uses_predicted_altitude_and_clips(self):
        view = AdsbOnScreenReticles.__new__(AdsbOnScreenReticles)
        view.__width__, view.__height__ = 100, 100
        view.__line_width__ = 3
        view.__center__ = [50, 50]
        view.__pixels_per_degree_y__ = 1
        view.__zoom_tracker__ = Mock()
        view.__zoom_tracker__.is_in_inner_range.return_value = (True, 0.5)
        orientation = Mock(position=[0, 0], alt=1000, pitch=0, roll=0)
        orientation.get_onscreen_projection_heading.return_value = 0
        traffic = make_traffic({"type": "straight", "points": [
                               point(0.01, 0), point(0.02, 0.02, 2000)]})
        with patch("views.adsb_on_screen_reticles.geo_math.get_distance", return_value=1), patch(
            "views.adsb_on_screen_reticles.geo_math.get_bearing", return_value=80
        ), patch("views.hud_elements.apply_declination", side_effect=lambda bearing: bearing), patch(
            "views.abstract_elements.adsb_element.apply_declination", side_effect=lambda bearing: bearing
        ), patch("views.adsb_on_screen_reticles.drawing.renderer.segment") as segment:
            view.__render_prediction__(None, orientation, [50, 50], traffic)
        segment.assert_called_once()
        self.assertEqual(segment.call_args.kwargs["width"], 3)
        self.assertEqual(segment.call_args.args[2], [50, 50])
        self.assertEqual(segment.call_args.args[3][0], 99)
        self.assertLess(segment.call_args.args[3][1], 50)

        view.__zoom_tracker__.is_in_inner_range.return_value = (False, 2)
        with patch("views.adsb_on_screen_reticles.drawing.renderer.segment") as segment:
            view.__render_prediction__(None, orientation, [50, 50], traffic)
        segment.assert_not_called()

    def test_forward_path_does_not_connect_across_rear_bearing_wrap(self):
        view = AdsbOnScreenReticles.__new__(AdsbOnScreenReticles)
        view.__width__, view.__height__ = 100, 100
        view.__line_width__ = 1
        view.__zoom_tracker__ = Mock()
        view.__zoom_tracker__.is_in_inner_range.return_value = (True, 0.5)
        view.__get_traffic_projection__ = Mock(
            side_effect=[(50, 50), (220, 50), (-120, 50)])
        orientation = Mock(position=[0, 0], alt=1000, pitch=0, roll=0)
        orientation.get_onscreen_projection_heading.return_value = 0
        traffic = make_traffic(
            {"points": [point(0.01, 0), point(0.02, 0), point(0.03, 0)]})
        with patch("views.adsb_on_screen_reticles.geo_math.get_distance", return_value=1), patch(
            "views.adsb_on_screen_reticles.geo_math.get_bearing", side_effect=[170, 190]
        ), patch("views.hud_elements.apply_declination", side_effect=lambda bearing: bearing), patch(
            "views.adsb_on_screen_reticles.drawing.renderer.segment"
        ) as segment:
            view.__render_prediction__(None, orientation, [50, 50], traffic)
        segment.assert_called_once_with(
            None, [255, 0, 0], [50, 50], [99, 50], width=2)


if __name__ == "__main__":
    unittest.main()
