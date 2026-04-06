"""Tests for dewpoint.py"""

import json
import socket
from unittest.mock import MagicMock, patch

import pytest

from dewpoint import _DEWPOINT_COLORS, dewpoint_to_color, get_dewpoint, set_govee_color


# ---------------------------------------------------------------------------
# dewpoint_to_color
# ---------------------------------------------------------------------------


class TestDewpointToColor:
    """Verify the color mapping logic."""

    def test_very_dry(self):
        # < 50 → #0CF
        assert dewpoint_to_color(30) == (0, 204, 255)
        assert dewpoint_to_color(49.9) == (0, 204, 255)

    def test_dry(self):
        # 50 ≤ dewpoint < 56 → #0F0
        assert dewpoint_to_color(50) == (0, 255, 0)
        assert dewpoint_to_color(55.9) == (0, 255, 0)

    def test_comfortable(self):
        # 56 ≤ dewpoint < 61 → #FFCC03
        assert dewpoint_to_color(56) == (255, 204, 3)
        assert dewpoint_to_color(60.9) == (255, 204, 3)

    def test_humid(self):
        # 61 ≤ dewpoint < 66 → #FE9901
        assert dewpoint_to_color(61) == (254, 153, 1)
        assert dewpoint_to_color(65.9) == (254, 153, 1)

    def test_muggy(self):
        # 66 ≤ dewpoint < 71 → #FF6500
        assert dewpoint_to_color(66) == (255, 101, 0)
        assert dewpoint_to_color(70.9) == (255, 101, 0)

    def test_oppressive(self):
        # 71 ≤ dewpoint < 76 → #FE0000
        assert dewpoint_to_color(71) == (254, 0, 0)
        assert dewpoint_to_color(75.9) == (254, 0, 0)

    def test_miserable(self):
        # dewpoint >= 76 → #820204
        assert dewpoint_to_color(76) == (130, 2, 4)
        assert dewpoint_to_color(100) == (130, 2, 4)

    def test_returns_tuple_of_three_ints(self):
        r, g, b = dewpoint_to_color(60)
        assert all(isinstance(v, int) for v in (r, g, b))

    def test_values_are_within_byte_range(self):
        for dew in range(-20, 100):
            r, g, b = dewpoint_to_color(dew)
            assert 0 <= r <= 255
            assert 0 <= g <= 255
            assert 0 <= b <= 255


# ---------------------------------------------------------------------------
# get_dewpoint
# ---------------------------------------------------------------------------


class TestGetDewpoint:
    """Verify the Open-Meteo API call."""

    def _mock_response(self, dewpoint_f: float) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "current": {"dew_point_2m": dewpoint_f}
        }
        mock_resp.raise_for_status.return_value = None
        return mock_resp

    @patch("dewpoint.requests.Session")
    def test_returns_dewpoint_float(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.get.return_value = self._mock_response(58.3)
        result = get_dewpoint(42.36, -71.06)
        assert result == 58.3

    @patch("dewpoint.requests.Session")
    def test_passes_correct_params(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.get.return_value = self._mock_response(50.0)
        get_dewpoint(42.36, -71.06)
        call_kwargs = mock_session.get.call_args
        params = call_kwargs.kwargs["params"]
        assert params["latitude"] == 42.36
        assert params["longitude"] == -71.06
        assert params["temperature_unit"] == "fahrenheit"
        assert "dew_point_2m" in params["current"]

    @patch("dewpoint.requests.Session")
    def test_raises_on_http_error(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("HTTP 500")
        mock_session.get.return_value = mock_resp
        with pytest.raises(Exception, match="HTTP 500"):
            get_dewpoint(0, 0)


# ---------------------------------------------------------------------------
# set_govee_color
# ---------------------------------------------------------------------------


class TestSetGoveeColor:
    """Verify the Govee local LAN API (UDP) command."""

    def _make_mock_socket(self, mock_socket_cls):
        mock_sock = MagicMock()
        mock_socket_cls.return_value.__enter__.return_value = mock_sock
        return mock_sock

    @patch("dewpoint.socket.socket")
    def test_sends_udp_to_correct_address(self, mock_socket_cls):
        mock_sock = self._make_mock_socket(mock_socket_cls)
        set_govee_color("192.168.1.100", 0, 255, 0)
        mock_sock.sendto.assert_called_once()
        _, addr = mock_sock.sendto.call_args[0]
        assert addr == ("192.168.1.100", 4003)

    @patch("dewpoint.socket.socket")
    def test_sends_correct_color(self, mock_socket_cls):
        mock_sock = self._make_mock_socket(mock_socket_cls)
        set_govee_color("192.168.1.100", 10, 20, 30)
        payload_bytes, _ = mock_sock.sendto.call_args[0]
        payload = json.loads(payload_bytes.decode("utf-8"))
        assert payload["msg"]["cmd"] == "colorwc"
        assert payload["msg"]["data"]["color"] == {"r": 10, "g": 20, "b": 30}

    @patch("dewpoint.socket.socket")
    def test_uses_udp_socket(self, mock_socket_cls):
        mock_sock = self._make_mock_socket(mock_socket_cls)
        set_govee_color("192.168.1.100", 0, 0, 0)
        mock_socket_cls.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM)

    @patch("dewpoint.socket.socket")
    def test_raises_on_socket_error(self, mock_socket_cls):
        mock_sock = self._make_mock_socket(mock_socket_cls)
        mock_sock.sendto.side_effect = OSError("Network unreachable")
        with pytest.raises(OSError, match="Network unreachable"):
            set_govee_color("192.168.1.100", 0, 255, 0)
